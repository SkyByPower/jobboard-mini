from flask import jsonify, render_template, request
from flask_wtf.csrf import CSRFError

from .extensions import db
from .i18n import _

PAGES = {
    400: ("Қате сұраныс", "Сұраныс дұрыс құрылмаған немесе форма ескірген."),
    403: ("Рұқсат жоқ", "Бұл бетке кіру құқығыңыз жоқ."),
    404: ("Бет табылмады", "Сіз іздеген бет жоқ немесе басқа жерге көшірілген."),
    413: ("Файл тым үлкен", "Жүктелетін файлдың ең үлкен көлемі — 5 МБ."),
    500: ("Сервер қатесі", "Бізде бірдеңе дұрыс болмады. Біраздан соң қайталап көріңіз."),
}


def _render(code):
    title, message = (_(text) for text in PAGES[code])
    if request.path.startswith("/api/"):
        return jsonify(error=title), code
    return render_template("errors/error.html", code=code, title=title, message=message), code


def register_error_handlers(app):
    for code in (400, 403, 404, 413):
        app.register_error_handler(code, lambda e, c=code: _render(c))

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return _render(400)

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return _render(500)
