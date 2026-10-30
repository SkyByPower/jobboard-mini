import io

from app.extensions import db
from app.models import Application, Company, Vacancy
from conftest import PDF, login

ADMIN = {"X-API-Key": "admin-token"}
USER = {"X-API-Key": "user-token"}


# ------------------------------------------------------------------ pages / errors
def test_public_pages(client):
    for url in ("/", "/vacancies", "/companies", "/vacancies/1", "/auth/login", "/auth/register"):
        assert client.get(url).status_code == 200, url


def test_custom_404(client):
    res = client.get("/no-such-page")
    assert res.status_code == 404
    assert "Бет табылмады".encode() in res.data


def test_custom_500(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    app.add_url_rule("/boom", "boom", lambda: 1 / 0)
    res = app.test_client().get("/boom")
    assert res.status_code == 500
    assert "Сервер қатесі".encode() in res.data


def test_search_filter_sort_pagination(client):
    assert "Python Developer".encode() in client.get("/vacancies?q=python&type=remote&sort=salary_desc").data
    assert "Python Developer".encode() not in client.get("/vacancies?q=nothing-here").data
    assert client.get("/vacancies?page=99").status_code == 200


# ------------------------------------------------------------------ auth + roles
def test_register_validation(client):
    res = client.post("/auth/register", data={
        "full_name": "A", "username": "x", "email": "bad", "password": "123", "confirm": "321",
    })
    assert "Email дұрыс емес".encode() in res.data
    assert "сәйкес емес".encode() in res.data


def test_register_and_login(client):
    res = client.post("/auth/register", data={
        "full_name": "Жаңа Қолданушы", "username": "newbie", "email": "new@mail.kz",
        "phone": "+7 700 123 45 67", "password": "secret1", "confirm": "secret1",
    }, follow_redirects=True)
    assert "Тіркелу сәтті".encode() in res.data
    client.post("/auth/logout")
    assert "Сәлем".encode() in login(client, "newbie", "secret1").data


def test_admin_area_requires_admin(client):
    assert client.get("/admin/").status_code == 302  # қонақ → login
    login(client, "user", "user123")
    assert client.get("/admin/").status_code == 403
    client.post("/auth/logout")
    login(client, "admin", "admin123")
    assert client.get("/admin/").status_code == 200


# ------------------------------------------------------------------ CRUD
def test_admin_vacancy_crud(client, app):
    login(client, "admin", "admin123")
    data = {
        "title": "QA Engineer", "company_id": 1, "city": "Астана", "employment_type": "full_time",
        "experience": "none", "salary_min": 200000, "salary_max": 300000,
        "description": "Тестілеу бойынша маманға арналған вакансия сипаттамасы.", "requirements": "Мұқияттылық",
        "is_active": "y",
    }
    assert client.post("/admin/vacancies/new", data=data, follow_redirects=True).status_code == 200
    with app.app_context():
        vacancy = Vacancy.query.filter_by(title="QA Engineer").one()
        vid = vacancy.id
    data["title"] = "Senior QA Engineer"
    client.post(f"/admin/vacancies/{vid}/edit", data=data)
    with app.app_context():
        assert db.session.get(Vacancy, vid).title == "Senior QA Engineer"
    client.post(f"/admin/vacancies/{vid}/delete")
    with app.app_context():
        assert db.session.get(Vacancy, vid) is None


def test_vacancy_salary_range_validation(client):
    login(client, "admin", "admin123")
    res = client.post("/admin/vacancies/new", data={
        "title": "Bad", "company_id": 1, "city": "Астана", "employment_type": "full_time", "experience": "none",
        "salary_min": 500000, "salary_max": 100000,
        "description": "Жеткілікті ұзын сипаттама мәтіні мұнда жазылған.", "requirements": "Талаптар тізімі",
    })
    assert "кем болмауы керек".encode() in res.data


def test_company_crud(client, app):
    login(client, "admin", "admin123")
    client.post("/admin/companies/new", data={
        "name": "New Co", "industry": "IT", "city": "Шымкент", "description": "Жаңа компанияның толық сипаттамасы.",
        "website": "https://new.example.kz",
    })
    with app.app_context():
        cid = Company.query.filter_by(name="New Co").one().id
    client.post(f"/admin/companies/{cid}/delete")
    with app.app_context():
        assert db.session.get(Company, cid) is None


# ------------------------------------------------------------------ file upload
def _apply(client, filename="cv.pdf", content=PDF):
    return client.post("/vacancies/1", data={
        "phone": "+7 701 111 22 33",
        "cover_letter": "Сәлеметсіз бе! Мен осы вакансияға өте қызығушылық танытамын.",
        "cv": (io.BytesIO(content), filename),
    }, content_type="multipart/form-data", follow_redirects=True)


def test_apply_with_pdf_and_review(client, app):
    login(client, "user", "user123")
    assert "Өтініш сәтті жіберілді".encode() in _apply(client).data
    with app.app_context():
        application = Application.query.one()
        assert application.cv_filename.endswith(".pdf") and application.cv_filename != "cv.pdf"
        app_id = application.id
    assert client.get(f"/applications/{app_id}/cv").status_code == 200
    # қайталап жіберу мүмкін емес
    assert "жіберіп қойғансыз".encode() in _apply(client).data

    client.post("/auth/logout")
    login(client, "admin", "admin123")
    client.post(f"/admin/applications/{app_id}", data={"status": "accepted", "admin_note": "Құттықтаймыз!"})
    with app.app_context():
        assert db.session.get(Application, app_id).status == "accepted"


def test_upload_rejects_non_pdf(client, app):
    login(client, "user", "user123")
    assert "Тек PDF".encode() in _apply(client, "virus.exe", b"MZ...").data
    assert "PDF емес".encode() in _apply(client, "fake.pdf", b"not a pdf").data
    with app.app_context():
        assert Application.query.count() == 0


def test_cv_is_private(client, app):
    login(client, "user", "user123")
    _apply(client)
    client.post("/auth/logout")
    assert client.get("/applications/1/cv").status_code == 302  # қонақ


# ------------------------------------------------------------------ API
def test_api_list_and_get(client):
    res = client.get("/api/vacancies?q=python")
    assert res.status_code == 200 and res.json["total"] == 1
    assert client.get("/api/vacancies/1").json["title"] == "Python Developer"
    assert client.get("/api/vacancies/999").status_code == 404
    assert client.get("/api/companies").json["items"][0]["name"] == "Test Co"


def test_api_create_update_delete(client):
    payload = {
        "title": "API Vacancy", "company_id": 1, "city": "Алматы",
        "description": "API арқылы құрылған вакансияның толық сипаттамасы.", "requirements": "REST, JSON",
        "employment_type": "remote", "salary_min": 100000,
    }
    assert client.post("/api/vacancies", json=payload).status_code == 401
    assert client.post("/api/vacancies", json=payload, headers=USER).status_code == 403
    res = client.post("/api/vacancies", json=payload, headers=ADMIN)
    assert res.status_code == 201
    vid = res.json["id"]

    assert client.put(f"/api/vacancies/{vid}", json={"salary_max": 50}, headers=ADMIN).status_code == 422
    res = client.put(f"/api/vacancies/{vid}", json={"title": "API Vacancy v2"}, headers=ADMIN)
    assert res.json["title"] == "API Vacancy v2"

    assert client.delete(f"/api/vacancies/{vid}", headers=ADMIN).status_code == 200
    assert client.get(f"/api/vacancies/{vid}").status_code == 404


def test_api_validation_errors(client):
    res = client.post("/api/vacancies", json={"title": "x"}, headers=ADMIN)
    assert res.status_code == 422
    assert {"title", "company_id", "description"} <= set(res.json["details"])


def test_api_application_status(client):
    login(client, "user", "user123")
    _apply(client)
    assert len(client.get("/api/applications", headers=USER).json["items"]) == 1
    assert client.put("/api/applications/1/status", json={"status": "accepted"}, headers=USER).status_code == 403
    res = client.put("/api/applications/1/status", json={"status": "rejected", "admin_note": "Кешіріңіз"}, headers=ADMIN)
    assert res.status_code == 200 and res.json["status"] == "rejected"
    assert client.put("/api/applications/1/status", json={"status": "wat"}, headers=ADMIN).status_code == 422
