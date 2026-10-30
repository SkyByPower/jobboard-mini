import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from .i18n import _, _l
from .models import Application, User, Vacancy

PHONE_RE = r"^\+?[0-9\s\-()]{10,20}$"
PHONE_MSG = _l("Телефон форматы: +7 700 123 45 67")
REQ = _l("Бұл өріс міндетті.")
BAD_EMAIL = _l("Email дұрыс емес.")


def strip(value):
    return value.strip() if isinstance(value, str) else value


def length(min_=None, max_=None):
    if min_ and max_:
        msg = _l("Ұзындығы {min}–{max} таңба болуы керек.", min=min_, max=max_)
    elif max_:
        msg = _l("Ең көбі {max} таңба.", max=max_)
    else:
        msg = _l("Кемінде {min} таңба.", min=min_)
    return Length(min=min_ or -1, max=max_ or -1, message=msg)


def translated_choices(mapping):
    return [(key, _l(label)) for key, label in mapping.items()]


class RegisterForm(FlaskForm):
    full_name = StringField(_l("Аты-жөні"), filters=[strip], validators=[DataRequired(REQ), length(3, 80)])
    username = StringField(
        _l("Логин"),
        filters=[strip],
        validators=[
            DataRequired(REQ),
            length(3, 30),
            Regexp(r"^[A-Za-z0-9_.]+$", message=_l("Тек латын әріптері, сандар, _ және .")),
        ],
    )
    email = StringField("Email", filters=[strip], validators=[DataRequired(REQ), Email(BAD_EMAIL), length(max_=120)])
    phone = StringField(_l("Телефон"), filters=[strip], validators=[Optional(), Regexp(PHONE_RE, message=PHONE_MSG)])
    password = PasswordField(_l("Құпиясөз"), validators=[DataRequired(REQ), length(6, 64)])
    confirm = PasswordField(
        _l("Құпиясөзді қайталаңыз"),
        validators=[DataRequired(REQ), EqualTo("password", message=_l("Құпиясөздер сәйкес емес."))],
    )
    submit = SubmitField(_l("Тіркелу"))

    def validate_password(self, field):
        if not (re.search(r"[A-Za-zА-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі]", field.data) and re.search(r"\d", field.data)):
            raise ValidationError(_("Құпиясөзде кемінде бір әріп және бір сан болуы керек."))

    def validate_username(self, field):
        if User.query.filter(User.username.ilike(field.data)).first():
            raise ValidationError(_("Бұл логин бос емес."))

    def validate_email(self, field):
        if User.query.filter(User.email.ilike(field.data)).first():
            raise ValidationError(_("Бұл email тіркелген."))


class LoginForm(FlaskForm):
    login = StringField(_l("Логин немесе email"), filters=[strip], validators=[DataRequired(REQ), length(3, 120)])
    password = PasswordField(_l("Құпиясөз"), validators=[DataRequired(REQ)])
    remember = BooleanField(_l("Мені есте сақта"))
    submit = SubmitField(_l("Кіру"))


class CompanyForm(FlaskForm):
    name = StringField(_l("Атауы"), filters=[strip], validators=[DataRequired(REQ), length(2, 100)])
    industry = StringField(_l("Сала"), filters=[strip], validators=[DataRequired(REQ), length(2, 60)])
    city = StringField(_l("Қала"), filters=[strip], validators=[DataRequired(REQ), length(2, 60)])
    description = TextAreaField(_l("Сипаттама"), filters=[strip], validators=[DataRequired(REQ), length(20, 3000)])
    website = StringField(
        _l("Веб-сайт"),
        filters=[strip],
        validators=[Optional(), URL(message=_l("URL дұрыс емес (https://...)")), length(max_=200)],
    )
    email = StringField("Email", filters=[strip], validators=[Optional(), Email(BAD_EMAIL), length(max_=120)])
    phone = StringField(_l("Телефон"), filters=[strip], validators=[Optional(), Regexp(PHONE_RE, message=PHONE_MSG)])
    submit = SubmitField(_l("Сақтау"))

    def __init__(self, *args, obj=None, **kwargs):
        super().__init__(*args, obj=obj, **kwargs)
        self._current_id = obj.id if obj is not None else None

    def validate_name(self, field):
        from .models import Company

        existing = Company.query.filter(Company.name.ilike(field.data)).first()
        if existing and existing.id != self._current_id:
            raise ValidationError(_("Мұндай компания бар."))


SALARY_RANGE = _l("0 – 10 000 000 аралығында болуы керек.")


class VacancyForm(FlaskForm):
    title = StringField(_l("Лауазым"), filters=[strip], validators=[DataRequired(REQ), length(3, 120)])
    company_id = SelectField(_l("Компания"), coerce=int, validators=[DataRequired(_l("Компанияны таңдаңыз."))])
    city = StringField(_l("Қала"), filters=[strip], validators=[DataRequired(REQ), length(2, 60)])
    employment_type = SelectField(_l("Жұмыс түрі"), choices=translated_choices(Vacancy.EMPLOYMENT_TYPES))
    experience = SelectField(_l("Тәжірибе"), choices=translated_choices(Vacancy.EXPERIENCE_LEVELS))
    salary_min = IntegerField(
        _l("Жалақы (бастап, ₸)"), validators=[Optional(), NumberRange(0, 10_000_000, SALARY_RANGE)]
    )
    salary_max = IntegerField(
        _l("Жалақы (дейін, ₸)"), validators=[Optional(), NumberRange(0, 10_000_000, SALARY_RANGE)]
    )
    description = TextAreaField(_l("Сипаттама"), filters=[strip], validators=[DataRequired(REQ), length(30, 5000)])
    requirements = TextAreaField(
        _l("Талаптар (әр жолға біреуден)"), filters=[strip], validators=[DataRequired(REQ), length(10, 3000)]
    )
    is_active = BooleanField(_l("Белсенді (өтінім қабылданады)"), default=True)
    submit = SubmitField(_l("Сақтау"))

    def validate_salary_max(self, field):
        if field.data is not None and self.salary_min.data is not None and field.data < self.salary_min.data:
            raise ValidationError(_("«Дейін» мәні «бастап» мәнінен кем болмауы керек."))

    def validate_employment_type(self, field):
        if field.data not in Vacancy.EMPLOYMENT_TYPES:
            raise ValidationError(_("Жарамсыз мән."))


class ApplicationForm(FlaskForm):
    phone = StringField(
        _l("Байланыс телефоны"), filters=[strip], validators=[DataRequired(REQ), Regexp(PHONE_RE, message=PHONE_MSG)]
    )
    expected_salary = IntegerField(
        _l("Күтілетін жалақы (₸)"),
        validators=[Optional(), NumberRange(50_000, 10_000_000, _l("50 000 – 10 000 000 аралығында."))],
    )
    cover_letter = TextAreaField(_l("Ілеспе хат"), filters=[strip], validators=[DataRequired(REQ), length(30, 2000)])
    cv = FileField(
        _l("Түйіндеме (CV, PDF)"),
        validators=[
            FileRequired(_l("CV файлын жүктеңіз.")),
            FileAllowed(["pdf"], _l("Тек PDF файлдар рұқсат етіледі.")),
        ],
    )
    submit = SubmitField(_l("Өтініш жіберу"))


class ReviewForm(FlaskForm):
    status = SelectField(_l("Мәртебе"), choices=translated_choices(Application.STATUSES))
    admin_note = TextAreaField(_l("Үміткерге хабарлама"), filters=[strip], validators=[Optional(), length(max_=1000)])
    submit = SubmitField(_l("Сақтау"))


class ConfirmForm(FlaskForm):
    """Өшіру/ауыстыру сияқты POST әрекеттері үшін бос форма (тек CSRF)."""
