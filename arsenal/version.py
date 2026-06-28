from __future__ import annotations

import os
import sys
from pathlib import Path

_AGENT_DIR = Path(
    os.environ.get("KARN_AGENT_DIR") or Path.home() / "karnData" / "arsenal" / "agent"
).expanduser()

# Maps component → (base_dir, version_file). agent uses its own dir.
_DB_VERSION_FILES: dict[str, tuple[Path | None, str]] = {
    "cards": (None, "cards-db-version.txt"),   # None → resolved from BASE_DIR at call time
    "rules": (None, "rules-db-version.txt"),
    "agent": (_AGENT_DIR, "agent-version.txt"),
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
    entry = _DB_VERSION_FILES.get(component)
    if not entry:
        return None
    base_dir, filename = entry
    try:
        if base_dir is None:
            from arsenal.cards.config import BASE_DIR
            base_dir = BASE_DIR
        text = (base_dir / filename).read_text(encoding="utf-8").strip()
        return text or None
    except Exception:
        return None
