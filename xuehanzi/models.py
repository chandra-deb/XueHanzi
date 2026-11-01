"""Database models.

Data is split in two groups:

* **Shared** data that is identical for every learner: :class:`Character`.
* **Per-user** data: :class:`User`, :class:`CharacterProgress` and :class:`Tag`
  (a tag belongs to exactly one user, so its character links are private too).
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import func
from unidecode import unidecode
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    tags = db.relationship(
        "Tag", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    progress = db.relationship(
        "CharacterProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        # Usernames are unique regardless of letter case.
        db.Index("uq_user_username_lower", func.lower(username), unique=True),
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @classmethod
    def get_by_username(cls, username: str) -> User | None:
        return cls.query.filter(func.lower(cls.username) == username.strip().lower()).first()

    def __repr__(self) -> str:
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


class Character(db.Model):
    """A vocabulary entry (shared by all users, read-only at runtime)."""

    __tablename__ = "character"

    id = db.Column(db.Integer, primary_key=True)
    hsk_level = db.Column(db.Integer, nullable=False, index=True)
    hsk_serial = db.Column(db.Integer, nullable=False)
    hanzi = db.Column(db.String(16), nullable=False, index=True)
    pinyin = db.Column(db.String(64), nullable=False)
    no_tone_pinyin = db.Column(db.String(64), nullable=False, index=True)
    meaning = db.Column(db.String(512), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("hsk_level", "hsk_serial", name="uq_character_level_serial"),
    )

    def __init__(self, *, hsk_level, hsk_serial, hanzi, pinyin, meaning):
        self.hsk_level = hsk_level
        self.hsk_serial = hsk_serial
        self.hanzi = hanzi
        self.pinyin = pinyin
        self.no_tone_pinyin = unidecode(pinyin).replace(" ", "").lower()
        self.meaning = meaning

    def __repr__(self) -> str:
        return f"<Character {self.hanzi}>"


class CharacterProgress(db.Model):
    """What one user knows about one character.

    A row only exists once the user has marked the character; no row means
    "new" (neither known nor writable).
    """

    __tablename__ = "character_progress"

    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    character_id = db.Column(
        db.Integer, db.ForeignKey("character.id", ondelete="CASCADE"), primary_key=True
    )
    is_known = db.Column(db.Boolean, nullable=False, default=False)
    can_write = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    user = db.relationship("User", back_populates="progress")
    character = db.relationship("Character")


character_tags = db.Table(
    "character_tags",
    db.Column(
        "tag_id", db.Integer, db.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True
    ),
    db.Column(
        "character_id",
        db.Integer,
        db.ForeignKey("character.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(db.Model):
    """A user's own collection of characters."""

    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(50), nullable=False)

    user = db.relationship("User", back_populates="tags")
    # Deliberately no backref on Character: a character is shared by all users,
    # so "its tags" only makes sense in the context of one user.
    characters = db.relationship("Character", secondary=character_tags, lazy="select")

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"
