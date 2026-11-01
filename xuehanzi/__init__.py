"""XueHanzi - a multi-user Chinese (HSK) vocabulary trainer."""

from __future__ import annotations

import os

from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .utils import current_path


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_object: type | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    if not app.config.get("SECRET_KEY"):
        if app.debug or app.testing:
            app.config["SECRET_KEY"] = "insecure-development-key"
        else:
            raise RuntimeError(
                "SECRET_KEY is not set. Generate one with "
                '`python -c "import secrets; print(secrets.token_hex(32))"` '
                "and put it in your environment or .env file."
            )

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("postgres://"):  # old-style URL used by some hosts
        app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace("postgres://", "postgresql://", 1)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registers the tables)
    from .cli import register_commands
    from .views import auth, characters, main, practice, tags

    for module in (auth, main, characters, practice, tags):
        app.register_blueprint(module.bp)

    register_commands(app)
    register_error_handlers(app)
    app.jinja_env.globals["current_path"] = current_path

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(CSRFError)
    def csrf_failed(_error):
        flash("Your session expired. Please try again.", "error")
        return redirect(url_for("main.home"))

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500
