import os
import uuid
from datetime import timedelta
from functools import wraps
from urllib.parse import urlsplit

from flask import abort, current_app, request, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename

from .forms import ConfirmForm
from .i18n import gettext
from .models import Application, Vacancy


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def safe_next(target):
    """Open redirect-тен қорғау: тек осы сайттың ішкі жолдары."""
    if target and target.startswith("/") and not target.startswith(("//", "/\\")) and not urlsplit(target).netloc:
        return target
    return None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_CV_EXTENSIONS"]


def save_cv(file_storage):
    """PDF-ті тексеріп, кездейсоқ атаумен сақтайды. (stored_name, original_name) қайтарады."""
    original = secure_filename(file_storage.filename or "")
    if not original or not allowed_file(original):
        raise ValueError(gettext("Тек PDF файлдар рұқсат етіледі."))

    # Кеңейтімге ғана сенбей, файлдың «сиқырлы байттарын» тексереміз
    head = file_storage.stream.read(5)
    file_storage.stream.seek(0)
    if head != b"%PDF-":
        raise ValueError(gettext("Файл мазмұны PDF емес."))

    stored = f"{uuid.uuid4().hex}.pdf"
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], stored))
    return stored, original


def delete_cv(stored_name):
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(stored_name))
    if os.path.isfile(path):
        os.remove(path)


def page_url(page):
    """Ағымдағы сүзгі параметрлерін сақтап, басқа бетке сілтеме жасайды."""
    args = request.args.to_dict()
    args["page"] = page
    return url_for(request.endpoint, **(request.view_args or {}), **args)


def sort_url(key):
    args = request.args.to_dict()
    args.pop("page", None)
    args["sort"] = key
    return url_for(request.endpoint, **(request.view_args or {}), **args)


def register_template_helpers(app):
    @app.context_processor
    def inject():
        pending = 0
        if current_user.is_authenticated and current_user.is_admin and (request.endpoint or "").startswith("admin."):
            pending = Application.query.filter_by(status="pending").count()
        return {
            "pending_count": pending,
            "page_url": page_url,
            "sort_url": sort_url,
            "confirm_form": ConfirmForm(),
            "EMPLOYMENT_TYPES": Vacancy.EMPLOYMENT_TYPES,
            "EXPERIENCE_LEVELS": Vacancy.EXPERIENCE_LEVELS,
            "STATUSES": Application.STATUSES,
        }

    @app.template_filter("date")
    def format_date(value, fmt="%d.%m.%Y"):
        # БД-да UTC сақталады, көрсеткенде жергілікті уақыт (Қазақстан: UTC+5)
        if not value:
            return ""
        return (value + timedelta(hours=app.config["DISPLAY_UTC_OFFSET"])).strftime(fmt)

    @app.template_filter("ago")
    def time_ago(value):
        from .models import utcnow

        if not value:
            return ""
        seconds = int((utcnow() - value).total_seconds())
        if seconds < 60:
            return gettext("жаңа ғана")
        if seconds > 30 * 86400:
            return value.strftime("%d.%m.%Y")
        for template, size in (("{n} күн бұрын", 86400), ("{n} сағ бұрын", 3600), ("{n} мин бұрын", 60)):
            if seconds >= size:
                return gettext(template, n=seconds // size)
        return value.strftime("%d.%m.%Y")
