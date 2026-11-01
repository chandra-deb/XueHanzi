from flask import Blueprint, abort, render_template, request
from flask_login import current_user

from ..services import characters as chars
from ..services.vocabulary import HSK_LEVELS
from ..utils import remember_return_url
from . import require_login

bp = require_login(Blueprint("main", __name__))


@bp.get("/")
def home():
    remember_return_url()
    return render_template(
        "main/home.html", stats=chars.level_stats(current_user), levels=HSK_LEVELS
    )


@bp.get("/hsk/<int:level>")
def hsk_level(level: int):
    if level not in HSK_LEVELS:
        abort(404)
    remember_return_url()
    entries = chars.list_entries(current_user, level=level)
    return render_template("main/hsk_level.html", level=level, entries=entries)


@bp.get("/known")
def known():
    remember_return_url()
    entries = chars.list_entries(current_user, known=True)
    return render_template(
        "main/collection.html",
        title="Known characters",
        entries=entries,
        practice_label="Do recall practice",
        practice_endpoint="practice.read",
        practice_args={"marked": 1},
    )


@bp.get("/writable")
def writable():
    remember_return_url()
    entries = chars.list_entries(current_user, writable=True)
    return render_template(
        "main/collection.html",
        title="Characters I can write",
        entries=entries,
        practice_label="Do writing practice",
        practice_endpoint="practice.write",
        practice_args={"marked": 1},
    )


@bp.get("/search")
def search():
    query = request.args.get("q", "").strip()
    results = chars.search(current_user, query)
    return render_template("main/search.html", query=query, results=results, tag=None)
