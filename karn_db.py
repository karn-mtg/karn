"""
Thin facade for Karn AI integration.

Usage:
    from karn_db import query, traverse, get_combos

All functions return plain dicts — JSON-serializable for prompt injection.
"""

from __future__ import annotations

from arsenal.cards.query import CardDB

_db: CardDB | None = None


def _get_db() -> CardDB:
    global _db
    if _db is None:
        _db = CardDB()
    return _db


def query(text: str, filters: dict | None = None, top_k: int = 10) -> list[dict]:
    """Semantic search. filters may include: color_identity, clusters, max_cmc, card_types, format_legal."""
    db = _get_db()
    return [r.to_dict() for r in db.query(text, top_k=top_k, **(filters or {}))]


def traverse(node_path: str, top_k: int | None = None) -> list[dict]:
    """Graph traversal. node_path e.g. 'color:B/archetype:Aristocrats/cluster:Dies'."""
    db = _get_db()
    return [r.to_dict() for r in db.traverse(node_path, top_k=top_k)]


def get_combos(card_name: str) -> list[dict]:
    """Return known combos involving the named card."""
    db = _get_db()
    return [r.to_dict() for r in db.get_combos(card_name)]


def get_similar(card_name: str, top_k: int = 10) -> list[dict]:
    """Return cards that play similarly to the named card."""
    db = _get_db()
    return [r.to_dict() for r in db.get_similar(card_name, top_k=top_k)]


def get_card(name: str) -> dict | None:
    db = _get_db()
    results = db.query(name, top_k=1)
    if results and results[0].name.lower() == name.lower():
        return results[0].to_dict()
    return None
