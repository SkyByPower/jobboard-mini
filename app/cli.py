"""CLI командалары: `flask init-db`, `flask seed`, `flask create-admin`."""

import os
import random
import sys
from datetime import timedelta

import click

from .extensions import db
from .models import Application, Company, User, Vacancy, utcnow

# (атауы, сала, сала_ru, қала, сайт, сипаттама, сипаттама_ru)
COMPANIES = [
    ("Qazaq Pay", "Финтех", "Финтех", "Алматы", "https://qazaqpay.example.kz",
     "Қазақстандағы ең ірі финтех экожүйелерінің бірі. Миллиондаған пайдаланушыға арналған төлем, маркетплейс және банк өнімдерін жасаймыз.",
     "Одна из крупнейших финтех-экосистем Казахстана. Создаём платёжные, маркетплейс- и банковские продукты для миллионов пользователей."),
    ("Steppe Soft", "IT аутсорсинг", "IT-аутсорсинг", "Астана", "https://steppesoft.example.kz",
     "Халықаралық клиенттерге веб және мобильді қосымшалар әзірлейтін өнім студиясы. Шағын команда, үлкен жауапкершілік.",
     "Продуктовая студия, которая разрабатывает веб- и мобильные приложения для международных клиентов. Небольшая команда, большая ответственность."),
    ("Nomad Logistics", "Логистика", "Логистика", "Қарағанды", "https://nomadlog.example.kz",
     "Орталық Азия бойынша жүк тасымалдау және қойма логистикасы. Маршруттарды оңтайландыру жүйесін өзіміз жасаймыз.",
     "Грузоперевозки и складская логистика по Центральной Азии. Сами разрабатываем систему оптимизации маршрутов."),
    ("Altyn Health", "Медицина", "Медицина", "Алматы", "https://altynhealth.example.kz",
     "Цифрлық денсаулық сақтау платформасы: онлайн-кеңес, электронды медициналық карта және клиникаларға арналған CRM.",
     "Платформа цифрового здравоохранения: онлайн-консультации, электронная медкарта и CRM для клиник."),
    ("EduQaz", "EdTech", "EdTech", "Шымкент", "https://eduqaz.example.kz",
     "Мектеп оқушылары мен студенттерге арналған қазақ тіліндегі онлайн-білім беру платформасы.",
     "Онлайн-платформа образования на казахском языке для школьников и студентов."),
    ("Baiterek Energy", "Энергетика", "Энергетика", "Атырау", "https://baiterek-energy.example.kz",
     "Жаңартылатын энергия көздерін енгізетін инженерлік компания: күн және жел электр станциялары.",
     "Инженерная компания, внедряющая возобновляемые источники энергии: солнечные и ветровые электростанции."),
]

# (атауы, атауы_ru, компания, қала, түрі, тәжірибе, жалақы_мин, жалақы_макс)
VACANCIES = [
    ("Python Backend әзірлеуші", "Python Backend-разработчик", "Qazaq Pay", "Алматы", "full_time", "middle", 700_000, 1_100_000),
    ("Frontend әзірлеуші (React)", "Frontend-разработчик (React)", "Steppe Soft", "Астана", "remote", "junior", 450_000, 700_000),
    ("Data Analyst", "Data Analyst", "Qazaq Pay", "Алматы", "full_time", "junior", 500_000, 800_000),
    ("QA инженері", "QA-инженер", "Steppe Soft", "Астана", "full_time", "junior", 350_000, 550_000),
    ("Логистика менеджері", "Менеджер по логистике", "Nomad Logistics", "Қарағанды", "full_time", "middle", 400_000, 600_000),
    ("Flutter әзірлеуші", "Flutter-разработчик", "Altyn Health", "Алматы", "remote", "middle", 600_000, 900_000),
    ("UI/UX дизайнер", "UI/UX-дизайнер", "EduQaz", "Шымкент", "part_time", "junior", 300_000, 450_000),
    ("Python тағылымдамасы", "Стажировка Python", "Steppe Soft", "Астана", "internship", "none", 150_000, 200_000),
    ("DevOps инженері", "DevOps-инженер", "Qazaq Pay", "Алматы", "full_time", "senior", 1_200_000, 1_800_000),
    ("Әдіскер (контент)", "Методист (контент)", "EduQaz", "Шымкент", "remote", "none", 250_000, None),
    ("Электр инженері", "Инженер-электрик", "Baiterek Energy", "Атырау", "contract", "senior", 900_000, 1_400_000),
    ("Медбике-кеңесші (онлайн)", "Медсестра-консультант (онлайн)", "Altyn Health", "Алматы", "part_time", "junior", None, 350_000),
    ("SMM маманы", "SMM-специалист", "EduQaz", "Шымкент", "remote", "junior", 280_000, 400_000),
    ("Жүргізуші-экспедитор", "Водитель-экспедитор", "Nomad Logistics", "Қарағанды", "full_time", "none", 320_000, 420_000),
    ("Project Manager", "Project Manager", "Baiterek Energy", "Атырау", "full_time", "middle", None, None),
]

REQUIREMENTS = {
    "none": "Үйренуге деген ынта\nКомандада жұмыс істей білу\nҚазақ және орыс тілдері",
    "junior": "1 жылдан астам тәжірибе\nНегізгі құралдарды білу\nЖауапкершілік пен ұқыптылық\nАғылшын тілі — оқу деңгейінде",
    "middle": "3 жылдан астам тәжірибе\nӨз бетінше міндеттерді шеше білу\nКод ревью мәдениеті\nАғылшын тілі — B1",
    "senior": "5 жылдан астам тәжірибе\nАрхитектуралық шешімдер қабылдау\nКомандаға тәлімгерлік\nАғылшын тілі — B2+",
}

REQUIREMENTS_RU = {
    "none": "Желание учиться\nУмение работать в команде\nКазахский и русский языки",
    "junior": "Опыт работы от 1 года\nЗнание основных инструментов\nОтветственность и аккуратность\nАнглийский — на уровне чтения",
    "middle": "Опыт работы от 3 лет\nУмение самостоятельно решать задачи\nКультура код-ревью\nАнглийский — B1",
    "senior": "Опыт работы от 5 лет\nПринятие архитектурных решений\nМенторство в команде\nАнглийский — B2+",
}

USERS = [
    ("aruzhan", "Аружан Серікова", "aruzhan@mail.kz", "+7 701 111 22 33"),
    ("dias", "Диас Нұрланов", "dias@mail.kz", "+7 702 222 33 44"),
    ("madina", "Мадина Әлиева", "madina@mail.kz", "+7 705 333 44 55"),
]

MINI_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R"
    b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\nBT /F1 24 Tf 72 760 Td (Demo CV) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def register_cli(app):
    # Windows консолінде (cp1252) қазақ әріптері шықпай қалмауы үшін
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower() not in ("utf-8", "utf8"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Бар кестелерді өшіріп, қайта құру.")
    def init_db(drop):
        """Деректер қорының кестелерін құрады."""
        if drop:
            db.drop_all()
        db.create_all()
        click.secho("✓ Кестелер құрылды.", fg="green")

    @app.cli.command("seed")
    def seed():
        """Демо деректерді жүктейді (кестелерді қайта құрады)."""
        db.drop_all()
        db.create_all()
        rnd = random.Random(42)
        now = utcnow()

        admin = User(username="admin", full_name="Admin", email="admin@jobboard.kz", role=User.ROLE_ADMIN)
        admin.set_password("admin123")
        admin.api_token = "admin-demo-token"
        db.session.add(admin)

        users = []
        for i, (username, name, email, phone) in enumerate(USERS):
            user = User(username=username, full_name=name, email=email, phone=phone)
            user.set_password("user123")
            user.api_token = f"user-demo-token-{i + 1}"
            users.append(user)
        db.session.add_all(users)

        companies = {}
        for name, industry, industry_ru, city, site, desc, desc_ru in COMPANIES:
            slug = name.split()[0].lower()
            companies[name] = Company(
                name=name, industry=industry, industry_ru=industry_ru, city=city, website=site,
                description=desc, description_ru=desc_ru,
                email=f"hr@{slug}.kz", phone="+7 727 300 00 00",
            )
        db.session.add_all(companies.values())

        vacancies = []
        for i, (title, title_ru, comp, city, etype, exp, smin, smax) in enumerate(VACANCIES):
            company = companies[comp]
            vacancy = Vacancy(
                title=title, title_ru=title_ru, company=company, city=city, employment_type=etype, experience=exp,
                salary_min=smin, salary_max=smax,
                description=(
                    f"{company.name} командасы «{title}» лауазымына маман іздейді. "
                    "Сізді заманауи жұмыс орны, икемді кесте, кәсіби даму бюджеті және достық ұжым күтеді. "
                    "Біз нәтижеге бағытталған, жаңа нәрсе үйренуден қорықпайтын адамдарды бағалаймыз."
                ),
                description_ru=(
                    f"Команда {company.name} ищет специалиста на позицию «{title_ru}». "
                    "Вас ждут современное рабочее место, гибкий график, бюджет на профессиональное развитие "
                    "и дружный коллектив. Мы ценим людей, нацеленных на результат и не боящихся учиться новому."
                ),
                requirements=REQUIREMENTS[exp],
                requirements_ru=REQUIREMENTS_RU[exp],
                created_at=now - timedelta(days=i * 2, hours=rnd.randint(0, 20)),
            )
            vacancies.append(vacancy)
        db.session.add_all(vacancies)
        db.session.flush()

        folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(folder, exist_ok=True)
        statuses = ["pending", "reviewing", "accepted", "rejected"]
        for u_index, user in enumerate(users):
            for v_index in rnd.sample(range(len(vacancies)), 3):
                stored = f"demo-{u_index}-{v_index}.pdf"
                with open(os.path.join(folder, stored), "wb") as fh:
                    fh.write(MINI_PDF)
                db.session.add(Application(
                    user=user, vacancy=vacancies[v_index], phone=user.phone,
                    expected_salary=rnd.choice([None, 400_000, 600_000]),
                    cover_letter="Сәлеметсіз бе! Осы вакансия маған өте қызықты. Тәжірибем мен дағдыларым "
                                 "сіздің командаңызға пайдалы болады деп сенемін.",
                    cv_filename=stored, cv_original_name=f"{user.username}_cv.pdf",
                    status=rnd.choice(statuses),
                    created_at=now - timedelta(hours=rnd.randint(1, 200)),
                ))
        users[0].saved.extend(vacancies[:3])
        db.session.commit()
        click.secho("✓ Демо деректер жүктелді.", fg="green")
        click.echo("  admin / admin123   (API токен: admin-demo-token)")
        click.echo("  aruzhan / user123  (API токен: user-demo-token-1)")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin(username, email, password):
        """Жаңа әкімші аккаунтын құрады."""
        user = User(username=username, full_name=username, email=email.lower(), role=User.ROLE_ADMIN)
        user.set_password(password)
        user.regenerate_token()
        db.session.add(user)
        db.session.commit()
        click.secho(f"✓ Әкімші құрылды: {username}", fg="green")
