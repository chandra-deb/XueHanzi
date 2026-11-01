"""User-scoped queries over the shared vocabulary.

Every function here takes the ``user`` whose progress/tags should be applied,
so views never have to remember to filter by user themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, case, func, or_, select

from ..extensions import db
from ..models import Character, CharacterProgress, Tag, User, character_tags
from .vocabulary import HSK_LEVELS


@dataclass(frozen=True)
class CharacterEntry:
    """A character together with one user's progress on it."""

    character: Character
    is_known: bool = False
    can_write: bool = False

    @property
    def status(self) -> str:
        if self.can_write:
            return "can-write"
        if self.is_known:
            return "known"
        return "new"


def _progress_join(user: User):
    return and_(
        CharacterProgress.character_id == Character.id,
        CharacterProgress.user_id == user.id,
    )


def _entries_stmt(
    user: User,
    *,
    level: int | None = None,
    tag_ids: list[int] | None = None,
    known: bool = False,
    writable: bool = False,
):
    stmt = select(
        Character, CharacterProgress.is_known, CharacterProgress.can_write
    ).outerjoin(CharacterProgress, _progress_join(user))

    if level is not None:
        stmt = stmt.where(Character.hsk_level == level)
    if known:
        stmt = stmt.where(CharacterProgress.is_known.is_(True))
    if writable:
        stmt = stmt.where(CharacterProgress.can_write.is_(True))
    if tag_ids:
        # Joining through Tag.user_id guarantees only the user's own tags count.
        in_tags = (
            select(character_tags.c.character_id)
            .join(Tag, Tag.id == character_tags.c.tag_id)
            .where(Tag.user_id == user.id, Tag.id.in_(tag_ids))
        )
        stmt = stmt.where(Character.id.in_(in_tags))
    return stmt


def _to_entries(rows) -> list[CharacterEntry]:
    return [CharacterEntry(c, bool(known), bool(write)) for c, known, write in rows]


def list_entries(
    user: User,
    *,
    level: int | None = None,
    tag_ids: list[int] | None = None,
    known: bool = False,
    writable: bool = False,
) -> list[CharacterEntry]:
    stmt = _entries_stmt(
        user, level=level, tag_ids=tag_ids, known=known, writable=writable
    ).order_by(Character.id)
    return _to_entries(db.session.execute(stmt).all())


def get_entry(user: User, character_id: int) -> CharacterEntry | None:
    stmt = _entries_stmt(user).where(Character.id == character_id)
    entries = _to_entries(db.session.execute(stmt).all())
    return entries[0] if entries else None


def random_entry(
    user: User,
    *,
    level: int | None = None,
    tag_ids: list[int] | None = None,
    known: bool = False,
    writable: bool = False,
) -> CharacterEntry | None:
    stmt = (
        _entries_stmt(user, level=level, tag_ids=tag_ids, known=known, writable=writable)
        .order_by(func.random())
        .limit(1)
    )
    entries = _to_entries(db.session.execute(stmt).all())
    return entries[0] if entries else None


def entries_by_ids(user: User, character_ids: list[int]) -> list[CharacterEntry]:
    if not character_ids:
        return []
    stmt = _entries_stmt(user).where(Character.id.in_(character_ids)).order_by(Character.id)
    return _to_entries(db.session.execute(stmt).all())


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def search(user: User, query: str, limit: int = 10) -> dict[str, list[CharacterEntry]]:
    """Search by hanzi, toneless pinyin and meaning."""
    query = query.strip()
    if not query:
        return {"hanzi": [], "pinyin": [], "meaning": []}

    def run(column, text):
        stmt = (
            _entries_stmt(user)
            .where(column.like(f"%{_escape_like(text)}%", escape="\\"))
            .order_by(Character.hsk_level, Character.hsk_serial)
            .limit(limit)
        )
        return _to_entries(db.session.execute(stmt).all())

    toneless = query.replace(" ", "").lower()
    return {
        "hanzi": run(Character.hanzi, query),
        "pinyin": run(Character.no_tone_pinyin, toneless),
        "meaning": run(Character.meaning, query),
    }


def set_progress(
    user: User,
    character_id: int,
    *,
    is_known: bool | None = None,
    can_write: bool | None = None,
) -> CharacterProgress | None:
    """Update a user's flags for a character; ``None`` leaves a flag unchanged.

    Rows with both flags off are removed so "no row" always means "new".
    Returns the row, or ``None`` if the character does not exist / was cleared.
    """
    if db.session.get(Character, character_id) is None:
        return None

    progress = db.session.get(CharacterProgress, (user.id, character_id))
    if progress is None:
        progress = CharacterProgress(
            user_id=user.id, character_id=character_id, is_known=False, can_write=False
        )
        db.session.add(progress)

    if is_known is not None:
        progress.is_known = is_known
    if can_write is not None:
        progress.can_write = can_write

    if not progress.is_known and not progress.can_write:
        db.session.delete(progress)
        progress = None

    db.session.commit()
    return progress


def level_stats(user: User) -> list[dict]:
    """Totals and percentages per HSK level for the dashboard."""
    stmt = (
        select(
            Character.hsk_level,
            func.count(Character.id),
            func.coalesce(func.sum(case((CharacterProgress.is_known.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(case((CharacterProgress.can_write.is_(True), 1), else_=0)), 0),
        )
        .outerjoin(CharacterProgress, _progress_join(user))
        .group_by(Character.hsk_level)
    )
    by_level = {row[0]: row[1:] for row in db.session.execute(stmt).all()}

    def percent(part: int, total: int) -> int:
        return round(part / total * 100) if total else 0

    stats = []
    for level in HSK_LEVELS:
        total, known, writable = by_level.get(level, (0, 0, 0))
        stats.append(
            {
                "level": level,
                "total": total,
                "known": known,
                "known_percent": percent(known, total),
                "writable": writable,
                "writable_percent": percent(writable, total),
            }
        )
    return stats


def tag_stats(user: User, tags: list[Tag]) -> dict[int, dict[str, int]]:
    """Per-tag counts of total / known / writable / new characters for ``user``."""
    stats = {tag.id: {"total": 0, "known": 0, "writable": 0, "new": 0} for tag in tags}
    if not tags:
        return stats

    marked = or_(CharacterProgress.is_known.is_(True), CharacterProgress.can_write.is_(True))
    stmt = (
        select(
            character_tags.c.tag_id,
            func.count(),
            func.coalesce(func.sum(case((CharacterProgress.is_known.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(case((CharacterProgress.can_write.is_(True), 1), else_=0)), 0),
            func.coalesce(func.sum(case((marked, 0), else_=1)), 0),
        )
        .select_from(character_tags)
        .outerjoin(
            CharacterProgress,
            and_(
                CharacterProgress.character_id == character_tags.c.character_id,
                CharacterProgress.user_id == user.id,
            ),
        )
        .where(character_tags.c.tag_id.in_(stats.keys()))
        .group_by(character_tags.c.tag_id)
    )
    for tag_id, total, known, writable, new in db.session.execute(stmt).all():
        stats[tag_id] = {"total": total, "known": known, "writable": writable, "new": new}
    return stats
