from flask import Blueprint, abort, current_app, render_template, request, send_from_directory
from flask_login import current_user

from ..services import characters as chars
from ..services import strokeorder
from ..utils import redirect_back
from . import require_login

bp = require_login(Blueprint("characters", __name__))


@bp.get("/characters/<int:character_id>")
def detail(character_id: int):
    entry = chars.get_entry(current_user, character_id)
    if entry is None:
        abort(404)
    return render_template(
        "characters/detail.html",
        entry=entry,
        images=strokeorder.image_files(entry.character),
    )


def _optional_flag(name: str) -> bool | None:
    """Read a ``0``/``1`` form flag. Missing means "leave unchanged"."""
    values = request.form.getlist(name)
    if not values:
        return None
    return values[-1].strip().lower() in {"1", "on", "true"}


@bp.post("/characters/<int:character_id>/progress")
def update_progress(character_id: int):
    chars.set_progress(
        current_user,
        character_id,
        is_known=_optional_flag("is_known"),
        can_write=_optional_flag("can_write"),
    )
    return redirect_back("characters.detail", character_id=character_id)


@bp.get("/strokeorder/<path:filename>")
def stroke_order_image(filename: str):
    return send_from_directory(
        current_app.config["STROKE_ORDER_DIR"], filename, max_age=60 * 60 * 24 * 30
    )
