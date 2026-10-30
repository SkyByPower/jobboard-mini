from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import ConfirmForm, LoginForm, RegisterForm
from ..i18n import _
from ..models import User
from ..utils import safe_next
from . import bp


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            username=form.username.data,
            email=form.email.data.lower(),
            phone=form.phone.data or None,
        )
        user.set_password(form.password.data)
        user.regenerate_token()
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(_("Қош келдіңіз, {name}! Тіркелу сәтті өтті.", name=user.full_name), "success")
        return redirect(url_for("main.vacancies"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.login.data.lower()
        user = User.query.filter((User.username == form.login.data) | (User.email == ident)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(_("Сәлем, {name}!", name=user.full_name), "success")
            default = url_for("admin.dashboard") if user.is_admin else url_for("main.vacancies")
            return redirect(safe_next(request.args.get("next")) or default)
        flash(_("Логин немесе құпиясөз қате."), "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash(_("Сіз жүйеден шықтыңыз."), "info")
    return redirect(url_for("main.index"))


@bp.route("/profile")
@login_required
def profile():
    stats = {key: current_user.applications.filter_by(status=key).count() for key in ("pending", "reviewing", "accepted", "rejected")}
    return render_template("auth/profile.html", stats=stats)


@bp.route("/profile/token", methods=["POST"])
@login_required
def regenerate_token():
    if ConfirmForm().validate_on_submit():
        current_user.regenerate_token()
        db.session.commit()
        flash(_("Жаңа API токен жасалды."), "success")
    return redirect(url_for("auth.profile"))
