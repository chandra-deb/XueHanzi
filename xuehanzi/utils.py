from __future__ import annotations

from urllib.parse import urlsplit

from flask import redirect, request, session, url_for

_RETURN_URL_KEY = "return_url"


def is_safe_path(target: str | None) -> bool:
    """True for same-site relative paths such as ``/tags/3?x=1``."""
    if not target:
        return False
    parts = urlsplit(target)
    return (
        not parts.scheme
        and not parts.netloc
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
    )


def current_path() -> str:
    """Path + query string of the current request."""
    return request.full_path.rstrip("?")


def redirect_back(default_endpoint: str = "main.home", **values):
    """Redirect to the ``next`` form/query value if it is safe, else to a default."""
    target = request.values.get("next")
    if is_safe_path(target):
        return redirect(target)
    return redirect(url_for(default_endpoint, **values))


def remember_return_url() -> None:
    """Remember the current page so practice pages can offer a "back" link."""
    session[_RETURN_URL_KEY] = current_path()


def get_return_url(default: str = "/") -> str:
    target = session.get(_RETURN_URL_KEY)
    return target if is_safe_path(target) else default


def parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "on", "yes"}
