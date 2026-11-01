"""Loading the bundled HSK word lists into the database."""

from __future__ import annotations

import json
from pathlib import Path

from ..extensions import db
from ..models import Character

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HSK_LEVELS = (1, 2, 3, 4, 5, 6)


def load_level(level: int) -> list[dict]:
    with open(DATA_DIR / f"hsk{level}.json", encoding="utf-8") as fh:
        return json.load(fh)


def seed_vocabulary() -> tuple[int, int]:
    """Insert or update every bundled word. Safe to run repeatedly.

    Words are identified by ``(hsk_level, hsk_serial)``. Returns the number of
    ``(created, updated)`` characters.
    """
    existing = {(c.hsk_level, c.hsk_serial): c for c in Character.query.all()}
    created = updated = 0

    for level in HSK_LEVELS:
        for word in load_level(level):
            fields = {
                "hanzi": word["hanzi"],
                "pinyin": word["pinyin"],
                "meaning": ", ".join(word["translations"]),
            }
            character = existing.get((level, word["id"]))
            if character is None:
                db.session.add(
                    Character(hsk_level=level, hsk_serial=word["id"], **fields)
                )
                created += 1
                continue

            candidate = Character(hsk_level=level, hsk_serial=word["id"], **fields)
            changed = False
            for name in ("hanzi", "pinyin", "no_tone_pinyin", "meaning"):
                if getattr(character, name) != getattr(candidate, name):
                    setattr(character, name, getattr(candidate, name))
                    changed = True
            updated += changed

    db.session.commit()
    return created, updated
