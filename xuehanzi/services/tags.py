"""Creating and editing a user's tags."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select

from ..extensions import db
from ..models import Character, Tag, User

MAX_TAG_NAME_LENGTH = 50


class TagError(ValueError):
    """A tag operation was rejected; the message is safe to show to the user."""


def list_tags(user: User) -> list[Tag]:
    return user.tags.order_by(func.lower(Tag.name)).all()


def get_tag(user: User, tag_id: int) -> Tag | None:
    return Tag.query.filter_by(id=tag_id, user_id=user.id).first()


def create_tag(user: User, name: str) -> Tag:
    name = " ".join(name.split())
    if not name:
        raise TagError("Tag name cannot be empty.")
    if len(name) > MAX_TAG_NAME_LENGTH:
        raise TagError(f"Tag name must be at most {MAX_TAG_NAME_LENGTH} characters.")
    if user.tags.filter(func.lower(Tag.name) == name.lower()).first():
        raise TagError(f'You already have a tag called "{name}".')

    tag = Tag(user_id=user.id, name=name)
    db.session.add(tag)
    db.session.commit()
    return tag


def delete_tag(tag: Tag) -> None:
    db.session.delete(tag)
    db.session.commit()


def tags_of_character(user: User, character: Character) -> list[Tag]:
    return [tag for tag in list_tags(user) if character in tag.characters]


def set_character_tags(user: User, character: Character, tag_ids: set[int]) -> None:
    """Make ``character`` belong to exactly the given tags (among the user's own)."""
    for tag in list_tags(user):
        attached = character in tag.characters
        if tag.id in tag_ids and not attached:
            tag.characters.append(character)
        elif tag.id not in tag_ids and attached:
            tag.characters.remove(character)
    db.session.commit()


def attach(tag: Tag, character: Character) -> None:
    if character not in tag.characters:
        tag.characters.append(character)
        db.session.commit()


def detach(tag: Tag, character: Character) -> None:
    if character in tag.characters:
        tag.characters.remove(character)
        db.session.commit()


@dataclass
class BulkAddReport:
    total: int = 0
    added: list[str] = field(default_factory=list)
    already_in_tag: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


def add_characters_in_bulk(tag: Tag, text: str) -> BulkAddReport:
    """Add whitespace-separated words/characters to ``tag``."""
    words = text.split()
    report = BulkAddReport(total=len(words))
    in_tag = {c.id for c in tag.characters}

    for word in words:
        character = db.session.execute(
            select(Character).where(Character.hanzi == word).order_by(Character.id).limit(1)
        ).scalar_one_or_none()
        if character is None:
            report.unknown.append(word)
        elif character.id in in_tag:
            report.already_in_tag.append(word)
        else:
            tag.characters.append(character)
            in_tag.add(character.id)
            report.added.append(word)

    db.session.commit()
    return report
