import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Company, User, Vacancy  # noqa: E402
from config import TestConfig  # noqa: E402

PDF = b"%PDF-1.4\n%test\n%%EOF\n"


@pytest.fixture()
def app():
    upload_dir = tempfile.mkdtemp()

    class Cfg(TestConfig):
        UPLOAD_FOLDER = upload_dir

    app = create_app(Cfg)
    with app.app_context():
        db.create_all()
        admin = User(username="admin", full_name="Admin Test", email="admin@test.kz", role="admin", api_token="admin-token")
        admin.set_password("admin123")
        user = User(username="user", full_name="User Test", email="user@test.kz", api_token="user-token")
        user.set_password("user123")
        company = Company(name="Test Co", industry="IT", city="Алматы", description="Тест компаниясы, сипаттамасы жеткілікті ұзын.")
        vacancy = Vacancy(
            title="Python Developer", company=company, city="Алматы", employment_type="remote", experience="junior",
            salary_min=300000, salary_max=500000,
            description="Python әзірлеушіге арналған тест вакансиясының толық сипаттамасы.",
            requirements="Python\nSQL",
        )
        db.session.add_all([admin, user, company, vacancy])
        db.session.commit()
        yield app
        db.session.remove()
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post("/auth/login", data={"login": username, "password": password}, follow_redirects=True)
