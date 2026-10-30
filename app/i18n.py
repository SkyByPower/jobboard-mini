"""Қарапайым көптілділік (kk / ru).

Қазақша мәтін — кілт, орысша аудармасы `translations_ru.RU` сөздігінде.
Тіл `lang` cookie-де сақталады; аударма табылмаса, қазақша мәтін көрсетіледі.
"""

from flask import has_request_context, request
from markupsafe import escape

from .translations_ru import RU

LANGUAGES = {"kk": "ҚАЗ", "ru": "РУС"}
DEFAULT_LANGUAGE = "kk"
COOKIE_NAME = "lang"

# main.js қолданатын мәтіндер (бетке JSON ретінде беріледі)
JS_STRINGS = [
    "Жабу",
    "Сенімдісіз бе?",
    "Тек PDF файлдар рұқсат етіледі.",
    "Файл {mb} МБ-тан аспауы керек.",
    "Сақталғандарға қосылды",
    "Сақталғандардан алынды",
    "Қате орын алды, қайталап көріңіз.",
    "Көшірілді!",
    "Көшіру мүмкін болмады",
    # static.js (GitHub Pages көшірмесі)
    "Ештеңе табылмады",
    "Сүзгі шарттарын өзгертіп көріңіз.",
    "Сүзгіні тазалау",
]


def get_locale():
    if not has_request_context():
        return DEFAULT_LANGUAGE
    lang = request.cookies.get(COOKIE_NAME)
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def gettext(text, **kwargs):
    if get_locale() == "ru":
        text = RU.get(text, text)
    return text.format(**kwargs) if kwargs else text


_ = gettext


def pgettext(context, text, **kwargs):
    """Бір қазақша сөздің орысшасы контекстке қарай әртүрлі болғанда (мысалы, «6 Компаний»)."""
    if get_locale() == "ru":
        text = RU.get(f"{context}|{text}", RU.get(text, text))
    return text.format(**kwargs) if kwargs else text


_p = pgettext


class LazyString:
    """Форма өрістерінің белгілері сияқты класс деңгейіндегі мәтіндер үшін:
    аударма сұраныс кезінде (ағымдағы тілмен) орындалады."""

    def __init__(self, text, **kwargs):
        self.text = text
        self.kwargs = kwargs

    def __str__(self):
        return gettext(self.text, **self.kwargs)

    def __html__(self):
        return str(escape(str(self)))

    def __mod__(self, other):  # WTForms: message % dict(min=..., max=...)
        return str(self) % other

    def __add__(self, other):
        return str(self) + str(other)

    def __radd__(self, other):
        return str(other) + str(self)

    def __len__(self):
        return len(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.text)

    def __repr__(self):
        return f"LazyString({self.text!r})"


lazy_gettext = LazyString
_l = lazy_gettext


def js_strings():
    return {key: gettext(key) for key in JS_STRINGS}


def init_i18n(app):
    app.jinja_env.globals.update(_=gettext, _p=pgettext)

    @app.context_processor
    def inject_language():
        return {"current_lang": get_locale(), "LANGUAGES": LANGUAGES, "js_i18n": js_strings()}
