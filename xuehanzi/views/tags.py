from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models import Character
from ..services import characters as chars
from ..services import tags as tag_service
from ..utils import redirect_back, remember_return_url
from . import require_login

bp = require_login(Blueprint("tags", __name__))


def _get_tag_or_404(tag_id: int):
    tag = tag_service.get_tag(current_user, tag_id)
    if tag is None:
        abort(404)
    return tag


def _get_character_or_404(character_id: int) -> Character:
    character = db.session.get(Character, character_id)
    if character is None:
        abort(404)
    return character


@bp.route("/tags", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            tag = tag_service.create_tag(current_user, request.form.get("name", ""))
        except tag_service.TagError as error:
            flash(str(error), "error")
        else:
            flash(f'Tag "{tag.name}" created.', "success")
        return redirect(url_for("tags.index"))

    remember_return_url()
    tags = tag_service.list_tags(current_user)
    return render_template(
        "tags/index.html", tags=tags, stats=chars.tag_stats(current_user, tags)
    )


@bp.get("/tags/<int:tag_id>")
def detail(tag_id: int):
    tag = _get_tag_or_404(tag_id)
    remember_return_url()
    entries = chars.list_entries(current_user, tag_ids=[tag.id])

    sections = [
        ("Can read and write", [e for e in entries if e.is_known and e.can_write]),
        ("Can write", [e for e in entries if e.can_write and not e.is_known]),
        ("Can read", [e for e in entries if e.is_known and not e.can_write]),
        ("New", [e for e in entries if not e.is_known and not e.can_write]),
    ]
    return render_template(
        "tags/detail.html",
        tag=tag,
        total=len(entries),
        sections=[(title, items) for title, items in sections if items],
    )


@bp.post("/tags/<int:tag_id>/delete")
def delete(tag_id: int):
    tag = _get_tag_or_404(tag_id)
    name = tag.name
    tag_service.delete_tag(tag)
    flash(f'Tag "{name}" deleted.', "info")
    return redirect(url_for("tags.index"))


@bp.route("/tags/<int:tag_id>/bulk-add", methods=["GET", "POST"])
def bulk_add(tag_id: int):
    tag = _get_tag_or_404(tag_id)
    if request.method == "POST":
        report = tag_service.add_characters_in_bulk(tag, request.form.get("characters", ""))
        return render_template("tags/bulk_report.html", tag=tag, report=report)
    return render_template("tags/bulk_add.html", tag=tag)


@bp.get("/tags/<int:tag_id>/search")
def search(tag_id: int):
    tag = _get_tag_or_404(tag_id)
    query = request.args.get("q", "").strip()
    results = chars.search(current_user, query)
    return render_template(
        "main/search.html",
        query=query,
        results=results,
        tag=tag,
        tag_member_ids={c.id for c in tag.characters},
    )


@bp.post("/tags/<int:tag_id>/characters/<int:character_id>/<action>")
def change_membership(tag_id: int, character_id: int, action: str):
    if action not in {"add", "remove"}:
        abort(404)
    tag = _get_tag_or_404(tag_id)
    character = _get_character_or_404(character_id)
    if action == "add":
        tag_service.attach(tag, character)
    else:
        tag_service.detach(tag, character)
    return redirect_back("tags.detail", tag_id=tag.id)


@bp.route("/characters/<int:character_id>/tags", methods=["GET", "POST"])
def character_tags(character_id: int):
    character = _get_character_or_404(character_id)
    if request.method == "POST":
        tag_ids = set(request.form.getlist("tags", type=int))
        tag_service.set_character_tags(current_user, character, tag_ids)
        flash("Tags updated.", "success")
        return redirect_back("characters.detail", character_id=character.id)

    attached = {t.id for t in tag_service.tags_of_character(current_user, character)}
    return render_template(
        "tags/character_tags.html",
        character=character,
        tags=tag_service.list_tags(current_user),
        attached=attached,
    )
