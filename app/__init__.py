import os

from flask import Flask

from config import Config
from .extensions import csrf, db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (модельдерді тіркеу)
    from .admin import bp as admin_bp
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .errors import register_error_handlers
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)  # API токенмен қорғалады

    register_error_handlers(app)

    from .cli import register_cli
    from .i18n import init_i18n
    from .utils import register_template_helpers

    register_cli(app)
    register_template_helpers(app)
    init_i18n(app)

    return app
