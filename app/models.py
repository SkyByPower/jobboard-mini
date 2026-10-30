import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .i18n import gettext as _
from .i18n import get_locale


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TranslatableMixin:
    """Мазмұн өрістерінің орысша нұсқасы (`<өріс>_ru`). Бос болса — қазақшасы көрсетіледі."""

    def tr(self, field):
        if get_locale() == "ru":
            value = getattr(self, f"{field}_ru", None)
            if value:
                return value
        return getattr(self, field)

    @property
    def city_label(self):
        return _(self.city)


# көп–көп: пайдаланушы ⇄ сақталған вакансиялар
saved_vacancies = db.Table(
    "saved_vacancies",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("vacancy_id", db.Integer, db.ForeignKey("vacancies.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    ROLE_USER = "user"
    ROLE_ADMIN = "admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default=ROLE_USER)
    api_token = db.Column(db.String(64), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    applications = db.relationship(
        "Application", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    saved = db.relationship("Vacancy", secondary=saved_vacancies, lazy="dynamic", back_populates="saved_by")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def regenerate_token(self):
        self.api_token = secrets.token_hex(24)
        return self.api_token

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def initials(self):
        parts = self.full_name.split()
        return "".join(p[0] for p in parts[:2]).upper() or self.username[:2].upper()

    def has_saved(self, vacancy):
        return self.saved.filter(saved_vacancies.c.vacancy_id == vacancy.id).count() > 0

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Company(TranslatableMixin, db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    industry = db.Column(db.String(60), nullable=False)
    industry_ru = db.Column(db.String(60))
    city = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    description_ru = db.Column(db.Text)
    website = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=utcnow)

    vacancies = db.relationship(
        "Vacancy", back_populates="company", cascade="all, delete-orphan", lazy="dynamic"
    )

    @property
    def initials(self):
        return "".join(w[0] for w in self.name.split()[:2]).upper()

    @property
    def hue(self):
        """Логотип орнына градиент түсі (атауға байланысты тұрақты)."""
        return sum(ord(c) for c in self.name) * 37 % 360

    @property
    def active_vacancies_count(self):
        return self.vacancies.filter_by(is_active=True).count()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "industry_ru": self.industry_ru,
            "city": self.city,
            "website": self.website,
            "vacancies": self.active_vacancies_count,
        }


class Vacancy(TranslatableMixin, db.Model):
    __tablename__ = "vacancies"

    EMPLOYMENT_TYPES = {
        "full_time": "Толық күн",
        "part_time": "Толық емес күн",
        "remote": "Қашықтан",
        "internship": "Тағылымдама",
        "contract": "Келісімшарт",
    }
    EXPERIENCE_LEVELS = {
        "none": "Тәжірибесіз",
        "junior": "1–3 жыл",
        "middle": "3–5 жыл",
        "senior": "5+ жыл",
    }

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False, index=True)
    title_ru = db.Column(db.String(120))
    description = db.Column(db.Text, nullable=False)
    description_ru = db.Column(db.Text)
    requirements = db.Column(db.Text, nullable=False)
    requirements_ru = db.Column(db.Text)
    city = db.Column(db.String(60), nullable=False)
    employment_type = db.Column(db.String(20), nullable=False, default="full_time")
    experience = db.Column(db.String(20), nullable=False, default="none")
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    company = db.relationship("Company", back_populates="vacancies")
    applications = db.relationship(
        "Application", back_populates="vacancy", cascade="all, delete-orphan", lazy="dynamic"
    )
    saved_by = db.relationship("User", secondary=saved_vacancies, lazy="dynamic", back_populates="saved")

    @property
    def employment_label(self):
        return _(self.EMPLOYMENT_TYPES.get(self.employment_type, self.employment_type))

    @property
    def experience_label(self):
        return _(self.EXPERIENCE_LEVELS.get(self.experience, self.experience))

    @property
    def salary_label(self):
        fmt = lambda n: f"{n:,}".replace(",", " ")  # noqa: E731
        if self.salary_min and self.salary_max:
            return f"{fmt(self.salary_min)} – {fmt(self.salary_max)} ₸"
        if self.salary_min:
            return _("{n} ₸-ден", n=fmt(self.salary_min))
        if self.salary_max:
            return _("{n} ₸-ге дейін", n=fmt(self.salary_max))
        return _("Келісім бойынша")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_ru": self.title_ru,
            "description": self.description,
            "description_ru": self.description_ru,
            "requirements": self.requirements,
            "requirements_ru": self.requirements_ru,
            "city": self.city,
            "employment_type": self.employment_type,
            "experience": self.experience,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "is_active": self.is_active,
            "company": {"id": self.company.id, "name": self.company.name},
            "applications": self.applications.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (db.UniqueConstraint("user_id", "vacancy_id", name="uq_user_vacancy"),)

    STATUSES = {
        "pending": "Күтуде",
        "reviewing": "Қаралуда",
        "accepted": "Қабылданды",
        "rejected": "Қабылданбады",
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    vacancy_id = db.Column(db.Integer, db.ForeignKey("vacancies.id"), nullable=False)
    cover_letter = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    expected_salary = db.Column(db.Integer)
    cv_filename = db.Column(db.String(255), nullable=False)  # дискідегі қауіпсіз (uuid) атау
    cv_original_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    admin_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="applications")
    vacancy = db.relationship("Vacancy", back_populates="applications")

    @property
    def status_label(self):
        return _(self.STATUSES.get(self.status, self.status))

    def to_dict(self):
        return {
            "id": self.id,
            "vacancy": {"id": self.vacancy.id, "title": self.vacancy.title},
            "user": {"id": self.user.id, "full_name": self.user.full_name},
            "status": self.status,
            "status_label": self.status_label,
            "admin_note": self.admin_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
