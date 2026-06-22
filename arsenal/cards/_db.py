"""Shared DB singleton used by both the MCP server and the HTTP API."""
from __future__ import annotations

import json
import sqlite3
import sys
import threading

_db = None
_db_lock = threading.Lock()
_reload_lock = threading.Lock()
_prints_con = None
_prints_lock = threading.Lock()
_db_ready = threading.Event()


def get_db():
    global _db
    if _db is None:
        with _db_lock:
            if _db is None:
                from arsenal.cards.config import CHROMA_DIR
                if not CHROMA_DIR.exists():
                    raise RuntimeError(
                        f"Card database not built. Run: python build_db.py\n"
                        f"Expected at: {CHROMA_DIR}"
                    )
                from arsenal.cards.query import CardDB
                _db = CardDB()
                _db_ready.set()
    return _db


def is_ready() -> bool:
    return _db_ready.is_set()


def preload_db() -> None:
    try:
        get_db()
    except Exception as exc:
        print(f"[arsenal] WARNING: failed to preload card DB: {exc}", file=sys.stderr)


def get_prints():
    global _prints_con
    if _prints_con is None:
        with _prints_lock:
            if _prints_con is None:
                from arsenal.cards.config import PRINTS_DB_PATH
                if not PRINTS_DB_PATH.exists():
                    return None
                uri = PRINTS_DB_PATH.as_uri() + "?mode=ro"
                con = sqlite3.connect(uri, uri=True, check_same_thread=False)
                con.row_factory = sqlite3.Row
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("PRAGMA cache_size=-65536")  # 64 MB
                _prints_con = con
    return _prints_con


def parse_prints_row(row) -> dict:
    d = dict(row)
    for field in ("image_uris", "card_faces", "frame_effects", "prices", "purchase_uris"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def parse_card_row(row) -> dict:
    d = dict(row)
    for field in ("color_identity", "legalities", "full_data"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def get_card_count() -> int:
    if _db is None:
        return 0
    try:
        return _db._count
    except Exception:
        return 0


def reload_db() -> None:
    """Reset all DB singletons and restart the preload thread. Call after a data update."""
    global _db, _prints_con
    with _reload_lock:
        with _db_lock:
            with _prints_lock:
                if _prints_con is not None:
                    try:
                        _prints_con.close()
                    except Exception:
                        pass
                    _prints_con = None
                _db = None
                _db_ready.clear()
    start_preload_thread()


def start_preload_thread() -> None:
    threading.Thread(target=preload_db, daemon=True).start()
