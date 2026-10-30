"""Веб-беттер мен API ортақ қолданатын сұраныс логикасы (DRY)."""

from sqlalchemy import func, or_

from .models import Company, Vacancy

VACANCY_SORTS = {
    "new": ("Жаңалары", Vacancy.created_at.desc()),
    "old": ("Ескілері", Vacancy.created_at.asc()),
    "salary_desc": ("Жалақы ↓", func.coalesce(Vacancy.salary_max, Vacancy.salary_min, 0).desc()),
    "salary_asc": ("Жалақы ↑", func.coalesce(Vacancy.salary_min, Vacancy.salary_max, 0).asc()),
    "title": ("Атауы А–Я", Vacancy.title.asc()),
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def filter_vacancies(args, only_active=True):
    """request.args негізінде іздеу + сүзгі + сұрыптау қолданылған Query қайтарады."""
    stmt = Vacancy.query.join(Company)
    if only_active:
        stmt = stmt.filter(Vacancy.is_active.is_(True))

    q = (args.get("q") or "").strip()[:100]
    if q:
        like = f"%{q}%"
        stmt = stmt.filter(
            or_(
                Vacancy.title.ilike(like),
                Vacancy.title_ru.ilike(like),
                Vacancy.description.ilike(like),
                Vacancy.description_ru.ilike(like),
                Company.name.ilike(like),
            )
        )

    city = (args.get("city") or "").strip()
    if city:
        stmt = stmt.filter(Vacancy.city == city)

    company_id = _to_int(args.get("company"))
    if company_id:
        stmt = stmt.filter(Vacancy.company_id == company_id)

    types = [t for t in args.getlist("type") if t in Vacancy.EMPLOYMENT_TYPES] if hasattr(args, "getlist") else []
    if types:
        stmt = stmt.filter(Vacancy.employment_type.in_(types))

    experience = args.get("experience")
    if experience in Vacancy.EXPERIENCE_LEVELS:
        stmt = stmt.filter(Vacancy.experience == experience)

    salary_from = _to_int(args.get("salary_from"))
    if salary_from:
        stmt = stmt.filter(func.coalesce(Vacancy.salary_max, Vacancy.salary_min, 0) >= salary_from)

    sort = args.get("sort", "new")
    stmt = stmt.order_by(VACANCY_SORTS.get(sort, VACANCY_SORTS["new"])[1], Vacancy.id.desc())
    return stmt


def vacancy_cities():
    from .extensions import db

    rows = db.session.query(Vacancy.city).filter(Vacancy.is_active.is_(True)).distinct().order_by(Vacancy.city)
    return [r[0] for r in rows]
