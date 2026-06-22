"""
Package a local database and upload it to a GitHub release.

Components:
  cards  — packages DB_DIR contents → karn-cards-db-v{version}.tar.gz
  rules  — packages arsenal/rules data → karn-rules-db-v{version}.tar.gz

Usage:
    python upload_data.py --component cards --release cards-db-v1.0.0
    python upload_data.py --component rules --release rules-db-v1.0.0

Requires the GitHub CLI (`gh`) to be installed and authenticated.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

DB_DIR = Path(
    os.environ.get("KARN_DATA_DIR") or Path.home() / "karnData" / "arsenal" / "db"
).expanduser()
GITHUB_REPO = os.environ.get("KARN_GITHUB_REPO", "YOUR_ORG/karn")

_REPO_ROOT = Path(__file__).parent.parent

_COMPONENT_CONFIG = {
    "cards": {
        "tag_prefix": "cards-db-v",
        "asset_template": "karn-cards-db-v{version}.tar.gz",
        "source_dir": DB_DIR,
        "label": "Cards DB",
    },
    "rules": {
        "tag_prefix": "rules-db-v",
        "asset_template": "karn-rules-db-v{version}.tar.gz",
        "source_dir": None,  # resolved at runtime: arsenal/rules/data + chunks
        "label": "Rules DB",
    },
}


def _check_gh() -> None:
    result = subprocess.run(["gh", "--version"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: GitHub CLI (gh) not found. Install from https://cli.github.com/")
        sys.exit(1)


def _pack_cards(archive_path: Path) -> None:
    if not DB_DIR.exists() or not any(DB_DIR.iterdir()):
        print(f"ERROR: {DB_DIR} is empty or missing. Run `python scripts/build_db.py` first.")
        sys.exit(1)

    print(f"Packaging {DB_DIR} → {archive_path.name} ...")
    include_names = {"chroma_db", "graph.json", "prints.db"}
    with tarfile.open(archive_path, "w:gz") as tf:
        for item in DB_DIR.iterdir():
            if item.name in include_names:
                tf.add(item, arcname=item.name)
    size_mb = archive_path.stat().st_size / 1024 / 1024
    print(f"  Packed {size_mb:.1f} MB")


def _pack_rules(archive_path: Path) -> None:
    data_dir = _REPO_ROOT / "arsenal" / "rules" / "data"
    chunks_dir = _REPO_ROOT / "arsenal" / "rules" / "chunks"
    include_files = {"rules.json", "glossary.json", "keyword_index.json"}

    if not any((data_dir / f).exists() for f in include_files):
        print(f"ERROR: Rules data missing in {data_dir}. Run `python scripts/build_rules.py` first.")
        sys.exit(1)

    print(f"Packaging rules data → {archive_path.name} ...")
    with tarfile.open(archive_path, "w:gz") as tf:
        for fname in include_files:
            path = data_dir / fname
            if path.exists():
                tf.add(path, arcname=fname)
        if chunks_dir.exists():
            tf.add(chunks_dir, arcname="chunks")
    size_mb = archive_path.stat().st_size / 1024 / 1024
    print(f"  Packed {size_mb:.1f} MB")


def _upload(archive_path: Path, release_tag: str) -> None:
    cmd = ["gh", "release", "upload", release_tag, str(archive_path), "--clobber",
           "--repo", GITHUB_REPO]
    print(f"Uploading to release {release_tag} ...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ERROR: Upload failed.")
        sys.exit(1)
    print(f"  Uploaded {archive_path.name} to release {release_tag}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload Arsenal DB artifact to a GitHub release")
    parser.add_argument(
        "--component", choices=["cards", "rules"], required=True,
        help="Which database to package",
    )
    parser.add_argument(
        "--release", metavar="TAG", required=True,
        help="Release tag, e.g. cards-db-v1.0.0 or rules-db-v1.0.0",
    )
    args = parser.parse_args()

    cfg = _COMPONENT_CONFIG[args.component]
    version = args.release.removeprefix(cfg["tag_prefix"])
    asset_name = cfg["asset_template"].format(version=version)

    _check_gh()

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / asset_name
        if args.component == "cards":
            _pack_cards(archive_path)
        else:
            _pack_rules(archive_path)
        _upload(archive_path, args.release)


if __name__ == "__main__":
    main()
