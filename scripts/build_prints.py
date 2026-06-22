"""Download Scryfall default_cards and build prints.db.

Faster alternative to build_db.py when you only need the SQLite card database
for KarnForge (no ChromaDB embeddings, no graph).

Usage:
    python build_prints.py [--force]
"""

import argparse

from arsenal.cards.downloader import download_default_cards
from arsenal.cards.prints_builder import build_prints_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Build prints.db from Scryfall data")
    parser.add_argument("--force", action="store_true", help="Rebuild even if prints.db already exists")
    args = parser.parse_args()

    print("[1/2] Downloading Scryfall default_cards...")
    default_json = download_default_cards()

    print("[2/2] Building prints.db...")
    build_prints_db(source_json=default_json, force=args.force)

    print("\nDone. prints.db is ready for KarnForge.")


if __name__ == "__main__":
    main()
