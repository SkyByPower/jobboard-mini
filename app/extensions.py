from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from .i18n import gettext

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Бұл бетті көру үшін жүйеге кіріңіз."
login_manager.login_message_category = "warning"
login_manager.localize_callback = gettext
