import os

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..forms import ApplicationForm, ConfirmForm
from ..i18n import COOKIE_NAME, LANGUAGES, _
from ..models import Application, Company, User, Vacancy
from ..services import VACANCY_SORTS, filter_vacancies, vacancy_cities
from ..utils import delete_cv, safe_next, save_cv
from . import bp


@bp.route("/")
def index():
    latest = Vacancy.query.filter_by(is_active=True).order_by(Vacancy.created_at.desc()).limit(6).all()
    top_companies = (
        Company.query.outerjoin(Vacancy)
        .group_by(Company.id)
        .order_by(func.count(Vacancy.id).desc())
        .limit(6)
        .all()
    )
    stats = {
        "vacancies": Vacancy.query.filter_by(is_active=True).count(),
        "companies": Company.query.count(),
        "applications": Application.query.count(),
        "users": User.query.count(),
    }
    return render_template("main/index.html", latest=latest, top_companies=top_companies, stats=stats)


@bp.route("/vacancies")
def vacancies():
    page = request.args.get("page", 1, type=int)
    pagination = filter_vacancies(request.args).paginate(
        page=page, per_page=current_app.config["VACANCIES_PER_PAGE"], error_out=False
    )
    return render_template(
        "main/vacancies.html",
        pagination=pagination,
        cities=vacancy_cities(),
        companies=Company.query.order_by(Company.name).all(),
        sorts={k: _(v[0]) for k, v in VACANCY_SORTS.items()},
        current_sort=request.args.get("sort", "new"),
        selected_types=request.args.getlist("type"),
    )


@bp.route("/vacancies/<int:vacancy_id>", methods=["GET", "POST"])
def vacancy_detail(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id)
    if not vacancy.is_active and not (current_user.is_authenticated and current_user.is_admin):
        abort(404)

    existing = None
    if current_user.is_authenticated:
        existing = current_user.applications.filter_by(vacancy_id=vacancy.id).first()

    form = ApplicationForm()
    if request.method == "GET" and current_user.is_authenticated:
        form.phone.data = current_user.phone

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if current_user.is_admin:
            flash(_("Әкімші өтініш жібере алмайды."), "warning")
        elif existing:
            flash(_("Бұл вакансияға өтініш жіберіп қойғансыз."), "warning")
        elif not vacancy.is_active:
            flash(_("Бұл вакансия бойынша өтінім қабылданбайды."), "warning")
        else:
            try:
                stored, original = save_cv(form.cv.data)
            except ValueError as exc:
                form.cv.errors.append(str(exc))
            else:
                application = Application(
                    user=current_user,
                    vacancy=vacancy,
                    phone=form.phone.data,
                    expected_salary=form.expected_salary.data,
                    cover_letter=form.cover_letter.data,
                    cv_filename=stored,
                    cv_original_name=original,
                )
                db.session.add(application)
                db.session.commit()
                flash(_("Өтініш сәтті жіберілді! Нәтижесін «Менің өтініштерім» бетінен бақылаңыз."), "success")
                return redirect(url_for("main.my_applications"))

    similar = (
        Vacancy.query.filter(Vacancy.is_active.is_(True), Vacancy.id != vacancy.id)
        .filter((Vacancy.company_id == vacancy.company_id) | (Vacancy.employment_type == vacancy.employment_type))
        .order_by(Vacancy.created_at.desc())
        .limit(3)
        .all()
    )
    return render_template("main/vacancy_detail.html", vacancy=vacancy, form=form, existing=existing, similar=similar)


@bp.route("/vacancies/<int:vacancy_id>/save", methods=["POST"])
@login_required
def toggle_save(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id)
    if not ConfirmForm().validate_on_submit():
        abort(400)
    if current_user.has_saved(vacancy):
        current_user.saved.remove(vacancy)
        saved = False
    else:
        current_user.saved.append(vacancy)
        saved = True
    db.session.commit()
    if request.accept_mimetypes.best == "application/json" or request.is_json:
        return jsonify(saved=saved)
    flash(_("Сақталғандарға қосылды.") if saved else _("Сақталғандардан алынды."), "info")
    return redirect(request.referrer or url_for("main.vacancy_detail", vacancy_id=vacancy.id))


@bp.route("/saved")
@login_required
def saved():
    items = current_user.saved.order_by(Vacancy.created_at.desc()).all()
    return render_template("main/saved.html", items=items)


@bp.route("/companies")
def companies():
    q = (request.args.get("q") or "").strip()[:100]
    query = Company.query
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%") | Company.industry.ilike(f"%{q}%"))
    return render_template("main/companies.html", companies=query.order_by(Company.name).all(), q=q)


@bp.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = db.get_or_404(Company, company_id)
    items = company.vacancies.filter_by(is_active=True).order_by(Vacancy.created_at.desc()).all()
    return render_template("main/company_detail.html", company=company, items=items)


@bp.route("/my/applications")
@login_required
def my_applications():
    status = request.args.get("status")
    query = current_user.applications
    if status in Application.STATUSES:
        query = query.filter_by(status=status)
    items = query.order_by(Application.created_at.desc()).all()
    return render_template("main/my_applications.html", items=items, status=status)


@bp.route("/my/applications/<int:app_id>/withdraw", methods=["POST"])
@login_required
def withdraw_application(app_id):
    application = db.get_or_404(Application, app_id)
    if application.user_id != current_user.id:
        abort(403)
    if not ConfirmForm().validate_on_submit():
        abort(400)
    if application.status not in ("pending", "reviewing"):
        flash(_("Шешім шыққан өтінішті кері қайтаруға болмайды."), "warning")
    else:
        delete_cv(application.cv_filename)
        db.session.delete(application)
        db.session.commit()
        flash(_("Өтініш кері қайтарылды."), "info")
    return redirect(url_for("main.my_applications"))


@bp.route("/applications/<int:app_id>/cv")
@login_required
def download_cv(app_id):
    """CV тек иесіне және әкімшіге қолжетімді."""
    application = db.get_or_404(Application, app_id)
    if application.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    folder = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isfile(os.path.join(folder, application.cv_filename)):
        abort(404)
    return send_from_directory(
        folder,
        application.cv_filename,
        mimetype="application/pdf",
        as_attachment=request.args.get("download") == "1",
        download_name=application.cv_original_name,
    )


@bp.route("/lang/<code>")
def set_language(code):
    """Тілді ауыстырады (cookie, 1 жыл) және сол бетке қайтарады."""
    if code not in LANGUAGES:
        abort(404)
    response = redirect(safe_next(request.args.get("next")) or url_for("main.index"))
    response.set_cookie(COOKIE_NAME, code, max_age=365 * 24 * 3600, samesite="Lax", httponly=True)
    return response
