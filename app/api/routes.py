"""REST API. Аутентификация: `X-API-Key: <token>` тақырыбы (токен профиль бетінде) немесе сессия."""

from functools import wraps

from flask import g, jsonify, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from ..extensions import db
from ..models import Application, Company, User, Vacancy
from ..services import filter_vacancies
from ..utils import delete_cv
from . import bp


def error(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


@bp.errorhandler(HTTPException)
def handle_http_error(exc):
    return error(exc.code, exc.description)


def _resolve_user():
    token = request.headers.get("X-API-Key")
    if token:
        return User.query.filter_by(api_token=token).first()
    # API CSRF-тен босатылған, сондықтан сессия тек қауіпсіз (оқу) әдістерге жарамды
    if request.method in ("GET", "HEAD") and current_user.is_authenticated:
        return current_user
    return None


def auth_required(admin=False):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = _resolve_user()
            if user is None:
                return error(401, "Аутентификация қажет (X-API-Key).")
            if admin and not user.is_admin:
                return error(403, "Тек әкімшіге рұқсат.")
            g.api_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator


# ------------------------------------------------------------- validation
def validate_vacancy_payload(data, partial=False):
    """JSON деректерін тексереді. (cleaned, errors) қайтарады."""
    errors, cleaned = {}, {}
    if not isinstance(data, dict):
        return None, {"body": "JSON объект күтілді."}

    rules = {
        "title": (3, 120),
        "description": (30, 5000),
        "requirements": (10, 3000),
        "city": (2, 60),
    }
    for field, (lo, hi) in rules.items():
        if field not in data:
            if not partial:
                errors[field] = "Міндетті өріс."
            continue
        value = data[field]
        if not isinstance(value, str) or not lo <= len(value.strip()) <= hi:
            errors[field] = f"Мәтін, ұзындығы {lo}–{hi}."
        else:
            cleaned[field] = value.strip()

    if "company_id" in data or not partial:
        company = db.session.get(Company, data.get("company_id")) if isinstance(data.get("company_id"), int) else None
        if company is None:
            errors["company_id"] = "Компания табылмады."
        else:
            cleaned["company_id"] = company.id

    for field, choices in (("employment_type", Vacancy.EMPLOYMENT_TYPES), ("experience", Vacancy.EXPERIENCE_LEVELS)):
        if field in data:
            if data[field] not in choices:
                errors[field] = "Рұқсат етілген мәндер: " + ", ".join(choices)
            else:
                cleaned[field] = data[field]

    for field in ("salary_min", "salary_max"):
        if field in data and data[field] is not None:
            value = data[field]
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000_000:
                errors[field] = "Бүтін сан, 0–10 000 000."
            else:
                cleaned[field] = value
        elif field in data:
            cleaned[field] = None

    lo, hi = cleaned.get("salary_min"), cleaned.get("salary_max")
    if lo is not None and hi is not None and hi < lo:
        errors["salary_max"] = "salary_max >= salary_min болуы керек."

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            errors["is_active"] = "true/false."
        else:
            cleaned["is_active"] = data["is_active"]

    return cleaned, errors


# ------------------------------------------------------------- vacancies
@bp.get("/vacancies")
def list_vacancies():
    """GET /api/vacancies?q=python&city=Алматы&type=remote&sort=salary_desc&page=1&per_page=10"""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    pagination = filter_vacancies(request.args).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        items=[v.to_dict() for v in pagination.items],
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )


@bp.get("/vacancies/<int:vacancy_id>")
def get_vacancy(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id, description="Вакансия табылмады.")
    return jsonify(vacancy.to_dict())


@bp.post("/vacancies")
@auth_required(admin=True)
def create_vacancy():
    cleaned, errors = validate_vacancy_payload(request.get_json(silent=True))
    if errors:
        return error(422, "Валидация қатесі.", errors)
    vacancy = Vacancy(**cleaned)
    db.session.add(vacancy)
    db.session.commit()
    return jsonify(vacancy.to_dict()), 201


@bp.put("/vacancies/<int:vacancy_id>")
@auth_required(admin=True)
def update_vacancy(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id, description="Вакансия табылмады.")
    cleaned, errors = validate_vacancy_payload(request.get_json(silent=True), partial=True)
    if errors:
        return error(422, "Валидация қатесі.", errors)
    for key, value in cleaned.items():
        setattr(vacancy, key, value)
    if vacancy.salary_min is not None and vacancy.salary_max is not None and vacancy.salary_max < vacancy.salary_min:
        db.session.rollback()
        return error(422, "Валидация қатесі.", {"salary_max": "salary_max >= salary_min болуы керек."})
    db.session.commit()
    return jsonify(vacancy.to_dict())


@bp.delete("/vacancies/<int:vacancy_id>")
@auth_required(admin=True)
def delete_vacancy(vacancy_id):
    vacancy = db.get_or_404(Vacancy, vacancy_id, description="Вакансия табылмады.")
    for application in vacancy.applications:
        delete_cv(application.cv_filename)
    db.session.delete(vacancy)
    db.session.commit()
    return jsonify(message="Өшірілді.", id=vacancy_id)


# ------------------------------------------------------------- companies
@bp.get("/companies")
def list_companies():
    return jsonify(items=[c.to_dict() for c in Company.query.order_by(Company.name)])


# ------------------------------------------------------------- applications
@bp.get("/applications")
@auth_required()
def list_applications():
    """Әкімші — барлық өтініштер, user — тек өзінікі. ?status=pending"""
    user = g.api_user
    query = Application.query if user.is_admin else Application.query.filter_by(user_id=user.id)
    status = request.args.get("status")
    if status in Application.STATUSES:
        query = query.filter_by(status=status)
    return jsonify(items=[a.to_dict() for a in query.order_by(Application.created_at.desc())])


@bp.put("/applications/<int:app_id>/status")
@auth_required(admin=True)
def update_application_status(app_id):
    application = db.get_or_404(Application, app_id, description="Өтініш табылмады.")
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in Application.STATUSES:
        return error(422, "Валидация қатесі.", {"status": "Рұқсат: " + ", ".join(Application.STATUSES)})
    note = data.get("admin_note")
    if note is not None and (not isinstance(note, str) or len(note) > 1000):
        return error(422, "Валидация қатесі.", {"admin_note": "Мәтін, ең көбі 1000 таңба."})
    application.status = status
    if note is not None:
        application.admin_note = note.strip()
    db.session.commit()
    return jsonify(application.to_dict())
