from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_

from ..extensions import db
from ..forms import CompanyForm, ConfirmForm, ReviewForm, VacancyForm
from ..i18n import _
from ..models import Application, Company, User, Vacancy
from ..services import VACANCY_SORTS, filter_vacancies
from ..utils import admin_required, delete_cv
from . import bp


@bp.before_request
@admin_required
def guard():
    """Бүкіл /admin бөлімі тек әкімшіге."""


def _paginate(query):
    page = request.args.get("page", 1, type=int)
    return query.paginate(page=page, per_page=current_app.config["ADMIN_PER_PAGE"], error_out=False)


def _require_post_confirm():
    if not ConfirmForm().validate_on_submit():
        abort(400)


# ---------------------------------------------------------------- Dashboard
@bp.route("/")
def dashboard():
    counts = dict(db.session.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    stats = {
        "vacancies": Vacancy.query.count(),
        "active": Vacancy.query.filter_by(is_active=True).count(),
        "companies": Company.query.count(),
        "users": User.query.count(),
        "applications": Application.query.count(),
        "by_status": {key: counts.get(key, 0) for key in Application.STATUSES},
    }
    top = (
        db.session.query(Vacancy, func.count(Application.id).label("n"))
        .outerjoin(Application)
        .group_by(Vacancy.id)
        .order_by(func.count(Application.id).desc())
        .limit(5)
        .all()
    )
    recent = Application.query.order_by(Application.created_at.desc()).limit(6).all()
    return render_template("admin/dashboard.html", stats=stats, top=top, recent=recent)


# ---------------------------------------------------------------- Vacancies CRUD
def _company_choices(form):
    form.company_id.choices = [(c.id, c.name) for c in Company.query.order_by(Company.name)]
    if not form.company_id.choices:
        flash(_("Алдымен кемінде бір компания қосыңыз."), "warning")


@bp.route("/vacancies")
def vacancies():
    pagination = _paginate(filter_vacancies(request.args, only_active=False))
    return render_template(
        "admin/vacancies.html",
        pagination=pagination,
        sorts={k: _(v[0]) for k, v in VACANCY_SORTS.items()},
        current_sort=request.args.get("sort", "new"),
    )


@bp.route("/vacancies/new", methods=["GET", "POST"])
def vacancy_create():
    form = VacancyForm()
    _company_choices(form)
    if request.method == "GET" and request.args.get("company", type=int):
        form.company_id.data = request.args.get("company", type=int)
    if form.validate_on_submit():
        vacancy = Vacancy()
        form.populate_obj(vacancy)
        db.session.add(vacancy)
        db.session.commit()
        flash(_("«{title}» вакансиясы қосылды.", title=vacancy.title), "success")
        return redirect(url_for("admin.vacancies"))
    return render_template("admin/vacancy_form.html", form=form, vacancy=None)


@bp.route("/vacancies/<int:vacancy_id>/edit", methods=["GET", "POST"])
def vacancy_edit(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id)
    form = VacancyForm(obj=vacancy)
    _company_choices(form)
    if form.validate_on_submit():
        form.populate_obj(vacancy)
        db.session.commit()
        flash(_("Вакансия жаңартылды."), "success")
        return redirect(url_for("admin.vacancies"))
    return render_template("admin/vacancy_form.html", form=form, vacancy=vacancy)


@bp.route("/vacancies/<int:vacancy_id>/toggle", methods=["POST"])
def vacancy_toggle(vacancy_id):
    _require_post_confirm()
    vacancy = db.get_or_404(Vacancy, vacancy_id)
    vacancy.is_active = not vacancy.is_active
    db.session.commit()
    flash(_("Вакансия белсендірілді.") if vacancy.is_active else _("Вакансия жабылды."), "info")
    return redirect(request.referrer or url_for("admin.vacancies"))


@bp.route("/vacancies/<int:vacancy_id>/delete", methods=["POST"])
def vacancy_delete(vacancy_id):
    _require_post_confirm()
    vacancy = db.get_or_404(Vacancy, vacancy_id)
    for application in vacancy.applications:
        delete_cv(application.cv_filename)
    db.session.delete(vacancy)
    db.session.commit()
    flash(_("«{title}» өшірілді.", title=vacancy.title), "info")
    return redirect(url_for("admin.vacancies"))


# ---------------------------------------------------------------- Companies CRUD
@bp.route("/companies")
def companies():
    q = (request.args.get("q") or "").strip()[:100]
    query = Company.query
    if q:
        query = query.filter(or_(Company.name.ilike(f"%{q}%"), Company.city.ilike(f"%{q}%")))
    return render_template("admin/companies.html", pagination=_paginate(query.order_by(Company.name)), q=q)


@bp.route("/companies/new", methods=["GET", "POST"])
def company_create():
    form = CompanyForm()
    if form.validate_on_submit():
        company = Company()
        form.populate_obj(company)
        db.session.add(company)
        db.session.commit()
        flash(_("«{name}» компаниясы қосылды.", name=company.name), "success")
        return redirect(url_for("admin.companies"))
    return render_template("admin/company_form.html", form=form, company=None)


@bp.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = db.get_or_404(Company, company_id)
    form = CompanyForm(obj=company)
    if form.validate_on_submit():
        form.populate_obj(company)
        db.session.commit()
        flash(_("Компания жаңартылды."), "success")
        return redirect(url_for("admin.companies"))
    return render_template("admin/company_form.html", form=form, company=company)


@bp.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    _require_post_confirm()
    company = db.get_or_404(Company, company_id)
    for vacancy in company.vacancies:
        for application in vacancy.applications:
            delete_cv(application.cv_filename)
    db.session.delete(company)
    db.session.commit()
    flash(_("«{name}» және оның вакансиялары өшірілді.", name=company.name), "info")
    return redirect(url_for("admin.companies"))


# ---------------------------------------------------------------- Applications
APP_SORTS = {
    "new": ("Жаңалары", Application.created_at.desc()),
    "old": ("Ескілері", Application.created_at.asc()),
    "status": ("Мәртебе", Application.status.asc()),
}


@bp.route("/applications")
def applications():
    query = Application.query.join(Vacancy).join(User, Application.user_id == User.id)
    status = request.args.get("status")
    if status in Application.STATUSES:
        query = query.filter(Application.status == status)
    vacancy_id = request.args.get("vacancy", type=int)
    if vacancy_id:
        query = query.filter(Application.vacancy_id == vacancy_id)
    q = (request.args.get("q") or "").strip()[:100]
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like), Vacancy.title.ilike(like)))
    sort = request.args.get("sort", "new")
    query = query.order_by(APP_SORTS.get(sort, APP_SORTS["new"])[1])
    return render_template(
        "admin/applications.html",
        pagination=_paginate(query),
        status=status,
        q=q,
        sorts={k: _(v[0]) for k, v in APP_SORTS.items()},
        current_sort=sort,
        vacancy=db.session.get(Vacancy, vacancy_id) if vacancy_id else None,
    )


@bp.route("/applications/<int:app_id>", methods=["GET", "POST"])
def application_review(app_id):
    application = db.get_or_404(Application, app_id)
    if application.status == "pending" and request.method == "GET":
        # Әкімші ашқанда автоматты түрде «қаралуда»
        application.status = "reviewing"
        db.session.commit()
    form = ReviewForm(obj=application)
    if form.validate_on_submit():
        form.populate_obj(application)
        db.session.commit()
        flash(_("Мәртебе: «{status}». Сақталды.", status=application.status_label), "success")
        return redirect(url_for("admin.applications"))
    return render_template("admin/application_review.html", application=application, form=form)


@bp.route("/applications/<int:app_id>/delete", methods=["POST"])
def application_delete(app_id):
    _require_post_confirm()
    application = db.get_or_404(Application, app_id)
    delete_cv(application.cv_filename)
    db.session.delete(application)
    db.session.commit()
    flash(_("Өтініш өшірілді."), "info")
    return redirect(url_for("admin.applications"))


# ---------------------------------------------------------------- Users
@bp.route("/users")
def users():
    q = (request.args.get("q") or "").strip()[:100]
    query = User.query
    if q:
        query = query.filter(or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%"), User.username.ilike(f"%{q}%")))
    return render_template("admin/users.html", pagination=_paginate(query.order_by(User.created_at.desc())), q=q)


@bp.route("/users/<int:user_id>/role", methods=["POST"])
def user_toggle_role(user_id):
    _require_post_confirm()
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash(_("Өз рөліңізді өзгерте алмайсыз."), "warning")
    else:
        user.role = User.ROLE_USER if user.is_admin else User.ROLE_ADMIN
        db.session.commit()
        flash(_("{name}: рөлі «{role}» болып өзгерді.", name=user.full_name, role=user.role), "success")
    return redirect(url_for("admin.users"))
