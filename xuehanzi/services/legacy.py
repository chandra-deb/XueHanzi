"""Importing data from the old single-user ``characters.db``.

The old schema kept ``is_known``/``can_write`` directly on each character and
had global tags. This moves all of that into one user's account.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from ..extensions import db
from ..models import Character, CharacterProgress, Tag, User


@dataclass
class ImportReport:
    progress_rows: int = 0
    tags_created: int = 0
    tags_reused: int = 0
    tag_links: int = 0
    unmapped: list[str] = field(default_factory=list)


class _CharacterIndex:
    """Finds the new vocabulary row that corresponds to an old one."""

    def __init__(self) -> None:
        self.by_key: dict[tuple[int, int], Character] = {}
        self.by_level_hanzi: dict[tuple[int, str], Character] = {}
        self.by_hanzi: dict[str, Character] = {}
        for character in db.session.execute(select(Character).order_by(Character.id)).scalars():
            self.by_key[(character.hsk_level, character.hsk_serial)] = character
            self.by_level_hanzi.setdefault((character.hsk_level, character.hanzi), character)
            self.by_hanzi.setdefault(character.hanzi, character)

    def find(self, level: int | None, serial: int | None, hanzi: str) -> Character | None:
        candidate = self.by_key.get((level, serial))
        if candidate is not None and candidate.hanzi == hanzi:
            return candidate
        return self.by_level_hanzi.get((level, hanzi)) or self.by_hanzi.get(hanzi)


def import_legacy_database(path: str | Path, user: User) -> ImportReport:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    index = _CharacterIndex()
    report = ImportReport()

    legacy = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    legacy.row_factory = sqlite3.Row
    try:
        mapping: dict[int, Character] = {}
        flags: dict[int, tuple[bool, bool]] = {}

        for row in legacy.execute(
            "SELECT id, hsk_level, hsk_serial, character, is_known, can_write FROM character"
        ):
            new = index.find(row["hsk_level"], row["hsk_serial"], row["character"])
            if new is None:
                report.unmapped.append(f'{row["character"]} (old id {row["id"]})')
                continue
            mapping[row["id"]] = new
            known, write = flags.get(new.id, (False, False))
            flags[new.id] = (known or bool(row["is_known"]), write or bool(row["can_write"]))

        existing = {
            p.character_id: p
            for p in CharacterProgress.query.filter_by(user_id=user.id).all()
        }
        for character_id, (known, write) in flags.items():
            if not (known or write):
                continue
            progress = existing.get(character_id)
            if progress is None:
                progress = CharacterProgress(user_id=user.id, character_id=character_id)
                db.session.add(progress)
            progress.is_known = progress.is_known or known
            progress.can_write = progress.can_write or write
            report.progress_rows += 1

        tags: dict[int, Tag] = {}
        for row in legacy.execute("SELECT id, name FROM tag"):
            name = (row["name"] or "").strip()
            if not name:
                continue
            tag = user.tags.filter(Tag.name == name).first()
            if tag is None:
                tag = Tag(user_id=user.id, name=name)
                db.session.add(tag)
                report.tags_created += 1
            else:
                report.tags_reused += 1
            tags[row["id"]] = tag

        for row in legacy.execute("SELECT tag_id, character_id FROM character_tags"):
            tag = tags.get(row["tag_id"])
            character = mapping.get(row["character_id"])
            if tag is not None and character is not None and character not in tag.characters:
                tag.characters.append(character)
                report.tag_links += 1
    finally:
        legacy.close()

    db.session.commit()
    return report
