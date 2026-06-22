# arsenal/server.py
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context

from arsenal.cards._db import (
    get_db as _get_db,
    get_prints as _get_prints,
    get_card_count,
    is_ready,
    parse_card_row,
    parse_prints_row,
    reload_db,
    start_preload_thread,
)
from arsenal.rules.generate_chunks import CHUNKS_DIR, SECTION_NAMES
from arsenal.rules.parser import load_glossary, load_rules
from arsenal.version import get_version, get_db_version

mcp = FastMCP("karn")
_START_TIME = time.time()

# ---------------------------------------------------------------------------
# Rules lazy state
# ---------------------------------------------------------------------------

import threading as _threading

_rules: dict | None = None
_glossary: dict | None = None
_search_loaded: bool = False
_rules_lock = _threading.Lock()
_glossary_lock = _threading.Lock()
_search_lock = _threading.Lock()


def _get_rules() -> dict:
    global _rules
    if _rules is None:
        with _rules_lock:
            if _rules is None:
                _rules = load_rules()
    return _rules


def _get_glossary() -> dict:
    global _glossary
    if _glossary is None:
        with _glossary_lock:
            if _glossary is None:
                _glossary = load_glossary()
    return _glossary


def _ensure_search() -> None:
    global _search_loaded
    if not _search_loaded:
        with _search_lock:
            if not _search_loaded:
                from arsenal.rules.search import _get_keyword_index
                _get_keyword_index()
                _search_loaded = True


_SECTION_KEYWORDS: dict[str, int] = {
    "game concepts": 1,
    "parts of a card": 2,
    "card types": 3,
    "zones": 4,
    "turn structure": 5,
    "turn": 5,
    "combat": 5,
    "spells": 6,
    "abilities": 6,
    "effects": 6,
    "stack": 6,
    "priority": 6,
    "triggered": 6,
    "replacement": 6,
    "layer": 6,
    "additional rules": 7,
    "state-based": 7,
    "multiplayer": 8,
    "casual": 9,
    "variants": 9,
}

_SAFE_CHUNK_NAME = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _load_chunk(section_num: int) -> str | None:
    for p in CHUNKS_DIR.glob(f"{section_num:02d}_*.md"):
        if CHUNKS_DIR in p.resolve().parents or p.resolve() == CHUNKS_DIR:
            return p.read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# Card tools (7)
# ---------------------------------------------------------------------------

@mcp.tool()
def search_cards(
    query: str,
    top_k: int = 10,
    color_identity: str = "",
    clusters: str = "",
    max_cmc: float = 0,
    format_legal: str = "",
) -> list[dict]:
    """Search MTG cards by natural language. Returns cards ranked by semantic similarity."""
    db = _get_db()
    color_list = [c.strip() for c in color_identity.split(",") if c.strip()] or None
    cluster_list = [c.strip() for c in clusters.split(",") if c.strip()] or None
    cmc_filter = max_cmc if max_cmc > 0 else None
    fmt = format_legal.strip() or None
    results = db.query(
        query,
        top_k=top_k,
        color_identity=color_list,
        clusters=cluster_list,
        max_cmc=cmc_filter,
        format_legal=fmt,
    )
    return [r.to_dict() for r in results]


@mcp.tool()
def traverse_graph(node_path: str, top_k: int = 20) -> list[dict]:
    """Navigate the card graph hierarchy. node_path e.g. 'color:B/archetype:Aristocrats/cluster:Dies'."""
    db = _get_db()
    return [r.to_dict() for r in db.traverse(node_path, top_k=top_k)]


@mcp.tool()
def get_combos(card_name: str) -> list[dict]:
    """Get known combos involving the named card."""
    db = _get_db()
    return [r.to_dict() for r in db.get_combos(card_name)]


@mcp.tool()
def get_similar(card_name: str, top_k: int = 10) -> list[dict]:
    """Get cards that play similarly to the named card."""
    db = _get_db()
    return [r.to_dict() for r in db.get_similar(card_name, top_k=top_k)]


@mcp.tool()
def get_card(name: str) -> dict | str:
    """Get details of a specific card by exact name."""
    db = _get_db()
    result = db.get_by_name(name)
    if result is None:
        return "Card not found."
    return result.to_dict()


@mcp.tool()
def get_card_prints(oracle_id: str) -> list[dict]:
    """Get all printings of a card by oracle ID — includes image URLs, set info, prices."""
    con = _get_prints()
    if not con:
        return []
    rows = con.execute(
        "SELECT * FROM card_images WHERE oracle_id = ? ORDER BY released_at ASC",
        (oracle_id,),
    ).fetchall()
    return [parse_prints_row(row) for row in rows]


@mcp.tool()
def search_cards_in_set(set_code: str, query: str = "", top_k: int = 20) -> list[dict]:
    """Get cards from a specific set. Optionally filter by semantic query."""
    con = _get_prints()
    if not con:
        return []
    safe_set = set_code.strip().lower()
    if query.strip():
        db = _get_db()
        results = db.query(query, top_k=top_k * 3)
        oracle_ids = [r.id for r in results]
        if not oracle_ids:
            return []
        placeholders = ",".join("?" * len(oracle_ids))
        rows = con.execute(
            f"""
            SELECT DISTINCT c.oracle_id, c.name, c.type_line, c.mana_cost, c.cmc,
                            c.color_identity, c.oracle_text, c.legalities, c.full_data
            FROM cards c
            JOIN card_images ci ON ci.oracle_id = c.oracle_id
            WHERE ci.set_code = ? AND c.oracle_id IN ({placeholders})
            LIMIT ?
            """,
            [safe_set, *oracle_ids, top_k],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT DISTINCT c.oracle_id, c.name, c.type_line, c.mana_cost, c.cmc,
                            c.color_identity, c.oracle_text, c.legalities, c.full_data
            FROM cards c
            JOIN card_images ci ON ci.oracle_id = c.oracle_id
            WHERE ci.set_code = ?
            ORDER BY c.name ASC
            LIMIT ?
            """,
            (safe_set, top_k),
        ).fetchall()
    return [parse_card_row(row) for row in rows]


# ---------------------------------------------------------------------------
# Rules tools (5)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_rule(rule_id: str) -> str:
    """Get the exact text of a rule by its ID (e.g. '702.19', '101.1a')."""
    rules = _get_rules()
    rule_id = rule_id.strip().rstrip(".")
    entry = rules.get(rule_id)
    if not entry:
        return f"Rule {rule_id} not found."
    lines = [f"Rule {entry['id']}: {entry['text']}"]
    for ex in entry.get("examples", []):
        lines.append(f"  {ex}")
    children = entry.get("children", [])
    if children:
        lines.append(f"  Subrules: {', '.join(children)}")
    return "\n".join(lines)


@mcp.tool()
def search_rules(query: str, top_k: int = 5) -> list[dict]:
    """Search rules by natural language query. Tries semantic vector search first,
    falls back to keyword (BM25-style) search. Returns rules with IDs and text."""
    try:
        from arsenal.rules.vectordb import semantic_search_rules
        from arsenal.cards.config import BASE_DIR
        results = semantic_search_rules(query, top_k=top_k, db_path=str(BASE_DIR))
        if results:
            return results
    except Exception as exc:
        print(f"[arsenal] semantic rules search failed, falling back to keyword: {exc}", file=sys.stderr)
    _ensure_search()
    from arsenal.rules.search import search_rules as _kw_search
    return [
        {"id": r["id"], "text": r["text"], "section": r.get("section_name", ""), "score": r.get("score")}
        for r in _kw_search(query, top_k=top_k)
    ]


@mcp.tool()
def get_section(name: str) -> str:
    """Get a summary of a top-level rules section. name can be a number (e.g. '5')
    or keyword (e.g. 'combat', 'turn structure')."""
    name_stripped = name.strip()

    section_num: int | None = None
    if name_stripped.isdigit():
        section_num = int(name_stripped)
    else:
        lower = name_stripped.lower()
        for kw, num in _SECTION_KEYWORDS.items():
            if kw in lower or lower in kw:
                section_num = num
                break

    if section_num is None:
        return f"Section '{name}' not found. Valid sections: " + ", ".join(
            f"{n} ({s})" for n, s in SECTION_NAMES.items()
        )

    chunk = _load_chunk(section_num)
    if chunk:
        return chunk

    rules = _get_rules()
    section_name = SECTION_NAMES.get(section_num, "")
    prefix = str(section_num * 100)
    top_rules = sorted(
        [r for rid, r in rules.items() if rid.startswith(prefix) and "." not in rid],
        key=lambda r: r["id"],
    )[:20]
    lines = [f"Section {section_num}: {section_name}", ""]
    for r in top_rules:
        lines.append(f"  {r['id']}: {r['text'][:120]}")
    return "\n".join(lines)


@mcp.tool()
def get_glossary(term: str) -> str:
    """Look up an MTG term in the official glossary."""
    glossary = _get_glossary()
    term_stripped = term.strip()

    exact = glossary.get(term_stripped)
    if exact:
        return f"{term_stripped}: {exact}"

    lower = term_stripped.lower()
    for key, val in glossary.items():
        if key.lower() == lower:
            return f"{key}: {val}"

    matches = [k for k in glossary if lower in k.lower()]
    if matches:
        return "\n\n".join(f"{k}: {glossary[k]}" for k in matches[:5])

    return f"Term '{term}' not found in the MTG glossary."


@mcp.tool()
def get_related_rules(rule_id: str) -> list[str]:
    """Find rules that reference or are referenced by the given rule ID."""
    rules = _get_rules()
    rule_id = rule_id.strip().rstrip(".")

    if rule_id not in rules:
        return [f"Rule {rule_id} not found."]

    related: list[str] = []
    entry = rules[rule_id]
    if entry.get("parent"):
        related.append(entry["parent"])
    related.extend(entry.get("children", []))

    pattern = re.compile(r"\b" + re.escape(rule_id) + r"\b")
    for rid, r in rules.items():
        if rid != rule_id and pattern.search(r["text"]):
            related.append(rid)

    cross_ref_re = re.compile(r"rule (\d{3}(?:\.\d+[a-kmnp-z]?)?)", re.IGNORECASE)
    for match in cross_ref_re.finditer(entry["text"]):
        ref = match.group(1)
        if ref != rule_id and ref in rules:
            related.append(ref)

    seen: set[str] = set()
    deduped: list[str] = []
    for r in related:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped


# ---------------------------------------------------------------------------
# Primer tool (1)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_rules_primer() -> str:
    """Return a compact Magic: The Gathering rules primer (~1,500 tokens).
    Covers turn structure, zones, stack, card types, combat, state-based actions,
    Commander-specific rules, and common gotchas. Call this before asking more
    specific questions with get_rule() or search_rules()."""
    primer_path = Path(__file__).parent / "rules" / "data" / "rules_summary.md"
    return primer_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Management tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_health() -> dict:
    """Get server health status: readiness, version, DB versions, card count, uptime."""
    return {
        "status": "ready" if is_ready() else "warming_up",
        "version": get_version(),
        "cards_db_version": get_db_version("cards"),
        "rules_db_version": get_db_version("rules"),
        "agent_version": get_db_version("agent"),
        "card_count": get_card_count(),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@mcp.tool()
def check_updates() -> dict:
    """Check GitHub for available updates to each database component."""
    from scripts.install_data import check_db_versions
    try:
        components = check_db_versions()
    except Exception as exc:
        components = {"error": str(exc)}
    return {"binary_version": get_version(), "components": components}


@mcp.tool()
async def update_component(component: str, ctx: Context) -> dict:
    """
    Download and install the latest version of a DB component.
    component must be 'cards' or 'rules'.
    Reports download progress via MCP progress notifications.
    """
    from scripts.install_data import install_component_async

    if component not in ("cards", "rules", "agent"):
        return {"success": False, "error": f"Unknown component {component!r}. Must be 'cards', 'rules', or 'agent'."}

    async def _on_progress(downloaded: int, total: int) -> None:
        try:
            await ctx.report_progress(downloaded, total)
        except Exception:
            pass

    result = await install_component_async(component, on_progress=_on_progress)

    if result["installed"]:
        if component == "cards":
            reload_db()
        elif component == "rules":
            global _rules, _glossary, _search_loaded
            _rules = None
            _glossary = None
            _search_loaded = False

    return {
        "success": result["installed"],
        "version": result["version"],
        "error": result["error"],
        "component": component,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _warn_if_db_missing() -> None:
    db_dir = Path(
        os.environ.get("KARN_DATA_DIR") or Path.home() / "karnData" / "arsenal" / "db"
    ).expanduser()
    for component, version_file in (("cards", "cards-db-version.txt"), ("rules", "rules-db-version.txt")):
        if not (db_dir / version_file).exists():
            print(
                f"[arsenal] WARNING: {component} DB not installed. "
                f"Run: python scripts/install_data.py --component {component}",
                file=sys.stderr,
            )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    _warn_if_db_missing()
    start_preload_thread()
    mcp.run()


if __name__ == "__main__":
    main()
