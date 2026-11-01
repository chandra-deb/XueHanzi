"""Locating downloaded stroke order images for a word."""

from __future__ import annotations

from pathlib import Path

from flask import current_app

from ..models import Character


def image_files(character: Character) -> list[str]:
    """Paths (relative to ``STROKE_ORDER_DIR``) of the images that exist.

    For every distinct hanzi in the word there is a stroke diagram and a
    practice sheet, stored per HSK level.
    """
    root = Path(current_app.config["STROKE_ORDER_DIR"])
    level = f"hsk{character.hsk_level}"

    files: list[str] = []
    for hanzi in dict.fromkeys(character.hanzi):
        for relative in (f"{level}/{hanzi}.png", f"{level}/sheets/{hanzi}-sheet.png"):
            if (root / relative).is_file():
                files.append(relative)
    return files
