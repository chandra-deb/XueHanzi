"""Download stroke order diagrams and practice sheets from strokeorder.com.

Usage (from the project root, with requirements-dev.txt installed):

    python scripts/download_stroke_order.py            # all levels
    python scripts/download_stroke_order.py 1 2        # only HSK 1 and 2
    python scripts/download_stroke_order.py --dest /path/to/strokeorderDownloads

Files are written as ``<dest>/hsk<N>/<hanzi>.png`` and
``<dest>/hsk<N>/sheets/<hanzi>-sheet.png``. Characters that are already on disk
are skipped, so the script can be interrupted and re-run.
"""

import argparse
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from xuehanzi.config import Config  # noqa: E402
from xuehanzi.services.vocabulary import HSK_LEVELS, load_level  # noqa: E402

BASE_URL = "https://www.strokeorder.com"


def fetch_image(session: requests.Session, src: str, target: Path) -> bool:
    response = session.get(f"{BASE_URL}{src}", timeout=30)
    if response.status_code != 200:
        return False
    target.write_bytes(response.content)
    return True


def download_character(session: requests.Session, hanzi: str, level_dir: Path) -> None:
    diagram = level_dir / f"{hanzi}.png"
    sheet = level_dir / "sheets" / f"{hanzi}-sheet.png"
    if diagram.exists() and sheet.exists():
        return

    page = session.get(f"{BASE_URL}/chinese/{hanzi}", timeout=30)
    soup = BeautifulSoup(page.text, "html.parser")
    blocks = soup.find_all("div", class_="stroke-article-content")

    for block, target in zip(blocks[:2], (diagram, sheet)):
        if target.exists():
            continue
        img = block.find("img")
        if img is None or not fetch_image(session, img["src"], target):
            print(f"  could not download {target.name}")
        else:
            print(f"  saved {target.relative_to(level_dir.parent)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("levels", nargs="*", type=int, choices=HSK_LEVELS, help="HSK levels (default: all)")
    parser.add_argument("--dest", type=Path, default=Config.STROKE_ORDER_DIR)
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    args = parser.parse_args()

    session = requests.Session()
    for level in args.levels or HSK_LEVELS:
        level_dir = args.dest / f"hsk{level}"
        (level_dir / "sheets").mkdir(parents=True, exist_ok=True)

        seen: set[str] = set()
        for word in load_level(level):
            for hanzi in word["hanzi"]:
                if hanzi in seen:
                    continue
                seen.add(hanzi)
                print(f"HSK {level}: {hanzi}")
                download_character(session, hanzi, level_dir)
                time.sleep(args.delay)


if __name__ == "__main__":
    main()
