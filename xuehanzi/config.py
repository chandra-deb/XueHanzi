"""Application configuration.

Values are read from environment variables (a local ``.env`` file is loaded
automatically by Flask when ``python-dotenv`` is installed).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{PROJECT_DIR / 'instance' / 'xuehanzi.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Anyone may create an account unless this is switched off. Accounts can
    # still be created from the command line with ``flask create-user``.
    ALLOW_REGISTRATION = _env_bool("ALLOW_REGISTRATION", True)

    # Where the downloaded stroke order images live.
    STROKE_ORDER_DIR = Path(
        os.environ.get("STROKE_ORDER_DIR", BASE_DIR / "static" / "strokeorderDownloads")
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    ALLOW_REGISTRATION = True
