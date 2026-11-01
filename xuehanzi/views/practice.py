from flask import Blueprint, render_template, request
from flask_login import current_user

from ..services import characters as chars
from ..services import strokeorder
from ..services.vocabulary import HSK_LEVELS
from ..utils import current_path, get_return_url, parse_bool
from . import require_login

bp = require_login(Blueprint("practice", __name__, url_prefix="/practice"))


def _filters() -> dict:
    """Which characters to practise, taken from the query string.

    * ``level``  - a single HSK level
    * ``tags``   - one or more of the user's tag ids (any of them)
    * ``marked`` - only characters the user has marked (known / writable)
    """
    level = request.args.get("level", type=int)
    return {
        "level": level if level in HSK_LEVELS else None,
        "tag_ids": request.args.getlist("tags", type=int),
        "marked": parse_bool(request.args.get("marked")),
    }


def _render(kind: str):
    filters = _filters()
    marked = filters.pop("marked")
    entry = chars.random_entry(
        current_user,
        known=marked and kind == "read",
        writable=marked and kind == "write",
        **filters,
    )
    images = strokeorder.image_files(entry.character) if entry and kind == "write" else []
    return render_template(
        f"practice/{kind}.html",
        entry=entry,
        images=images,
        back_url=get_return_url(),
        next_url=current_path(),
    )


@bp.get("/read")
def read():
    return _render("read")


@bp.get("/write")
def write():
    return _render("write")
