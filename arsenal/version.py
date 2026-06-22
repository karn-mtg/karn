from __future__ import annotations

import sys
from pathlib import Path

_DB_VERSION_FILES = {
    "cards": "cards-db-version.txt",
    "rules": "rules-db-version.txt",
    "agent": "agent-version.txt",
}


def get_version() -> str:
    # Layer 1: installed package metadata (dev / pip install -e)
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version("karn-arsenal")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass

    # Layer 2: version.txt next to the running executable (install_local.py path)
    try:
        candidate = Path(sys.executable).parent / "version.txt"
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    except Exception:
        pass

    # Layer 3: version.txt bundled inside PyInstaller _MEIPASS (from karn.spec datas)
    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / "version.txt"
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text
    except Exception:
        pass

    return "unknown"


def get_db_version(component: str) -> str | None:
    filename = _DB_VERSION_FILES.get(component)
    if not filename:
        return None
    try:
        from arsenal.cards.config import BASE_DIR
        text = (BASE_DIR / filename).read_text(encoding="utf-8").strip()
        return text or None
    except Exception:
        return None
