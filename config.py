import os

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")
    # Flask-SQLAlchemy салыстырмалы SQLite жолын instance/ папкасынан есептейді
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///jobboard.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Жүктелетін файлдар (CV) — public static ішінде емес, тек рұқсатпен беріледі
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "instance", "uploads", "cv"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    ALLOWED_CV_EXTENSIONS = {"pdf"}

    DISPLAY_UTC_OFFSET = int(os.getenv("DISPLAY_UTC_OFFSET", "5"))

    VACANCIES_PER_PAGE = 6
    ADMIN_PER_PAGE = 10

    # freeze.py статикалық көшірме жасағанда ғана қосылады (GitHub Pages)
    STATIC_EXPORT = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
