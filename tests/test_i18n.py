"""Көптілділік тесттері: әр қазақша мәтіннің орысша аудармасы бар екенін тексереді."""

import pathlib
import re

from app.admin.routes import APP_SORTS
from app.errors import PAGES
from app.i18n import JS_STRINGS
from app.models import Application, Vacancy
from app.services import VACANCY_SORTS
from app.translations_ru import RU

ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"
CALL = re.compile(r"""(?<![\w.])(?:_|_l|gettext)\(\s*(['"])(.+?)(?<!\\)\1""", re.S)
PCALL = re.compile(r"""(?<![\w.])(?:_p|pgettext)\(\s*(['"])(\w+)\1\s*,\s*(['"])(.+?)(?<!\\)\3""", re.S)


def collect_keys():
    keys = []
    for path in list(ROOT.rglob("*.py")) + list((ROOT / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        keys += [m.group(2) for m in CALL.finditer(text)]
        keys += [f"{m.group(2)}|{m.group(4)}" for m in PCALL.finditer(text)]
    for mapping in (Vacancy.EMPLOYMENT_TYPES, Vacancy.EXPERIENCE_LEVELS, Application.STATUSES):
        keys += list(mapping.values())
    keys += [label for label, _ in VACANCY_SORTS.values()] + [label for label, _ in APP_SORTS.values()]
    keys += [text for pair in PAGES.values() for text in pair] + JS_STRINGS
    # тек кириллица бар мәтіндер аударылады
    return sorted({k for k in keys if re.search(r"[А-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі]", k)})


def test_every_string_has_russian_translation():
    missing = [k for k in collect_keys() if k not in RU]
    assert not missing, "Аудармасы жоқ мәтіндер:\n" + "\n".join(missing)


def test_placeholders_match():
    for kk, ru in RU.items():
        assert set(re.findall(r"\{\w+\}", kk)) == set(re.findall(r"\{\w+\}", ru)), kk


def test_language_switch(client):
    res = client.get("/lang/ru?next=/vacancies")
    assert res.status_code == 302 and res.headers["Location"].endswith("/vacancies")
    page = client.get("/vacancies").data.decode()
    assert "Все" in page and 'lang="ru"' in page
    client.get("/lang/kk")
    assert 'lang="kk"' in client.get("/").data.decode()


def test_language_switch_rejects_bad_input(client):
    assert client.get("/lang/en").status_code == 404
    res = client.get("/lang/ru?next=https://evil.example.com")
    assert res.headers["Location"].endswith("/")


def test_content_translation_with_fallback(client, app):
    from app.extensions import db
    from app.models import Vacancy

    with app.app_context():
        vacancy = db.session.get(Vacancy, 1)
        vacancy.title_ru = "Python-разработчик"
        vacancy.city = "Қарағанды"
        db.session.commit()
    client.get("/lang/ru")
    page = client.get("/vacancies/1").data.decode()
    assert "Python-разработчик" in page and "Караганда" in page
    # орысша нұсқасы жоқ өріс — қазақшасы көрсетіледі
    assert "Python әзірлеушіге арналған" in page
    client.get("/lang/kk")
    assert "Python Developer" in client.get("/vacancies/1").data.decode()


def test_russian_form_errors(client):
    client.get("/lang/ru")
    res = client.post("/auth/register", data={"email": "bad"})
    html = res.data.decode()
    assert "Email указан неверно." in html and "Обязательное поле." in html
