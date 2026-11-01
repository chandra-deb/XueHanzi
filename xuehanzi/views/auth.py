from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..forms import LoginForm, RegisterForm
from ..models import User
from ..utils import is_safe_path

bp = Blueprint("auth", __name__)

# Verified when the username is unknown so response time doesn't reveal which
# usernames exist.
_DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")


def _after_login_redirect():
    target = request.args.get("next")
    return redirect(target if is_safe_path(target) else url_for("main.home"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_username(form.username.data)
        password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
        if check_password_hash(password_hash, form.password.data) and user:
            login_user(user, remember=form.remember.data)
            return _after_login_redirect()
        flash("Invalid username or password.", "error")

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config["ALLOW_REGISTRATION"]:
        abort(404)
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to XueHanzi! Your account has been created.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/register.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
