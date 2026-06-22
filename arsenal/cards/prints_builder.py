"""Build prints.db — SQLite card database from Scryfall default_cards bulk.

Schema is identical to karnforge's cards.db so karnforge can open it directly
without any query changes. Includes cards, card_images, tokens, token_images,
and metadata tables.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from arsenal.cards.config import PRINTS_DB_PATH, SCRYFALL_DEFAULT_CARDS_JSON

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    oracle_id        TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    lang             TEXT,
    layout           TEXT,
    mana_cost        TEXT,
    cmc              REAL,
    type_line        TEXT,
    oracle_text      TEXT,
    power            TEXT,
    toughness        TEXT,
    loyalty          TEXT,
    defense          TEXT,
    hand_modifier    TEXT,
    life_modifier    TEXT,
    colors           TEXT,
    color_identity   TEXT,
    produced_mana    TEXT,
    keywords         TEXT,
    legalities       TEXT,
    games            TEXT,
    reserved         INTEGER,
    edhrec_rank      INTEGER,
    penny_rank       INTEGER,
    all_parts        TEXT,
    prices           TEXT,
    purchase_uris    TEXT,
    rulings_uri      TEXT,
    scryfall_uri     TEXT,
    sets             TEXT,
    full_data        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    id               TEXT PRIMARY KEY,
    oracle_id        TEXT,
    name             TEXT NOT NULL,
    layout           TEXT,
    type_line        TEXT,
    oracle_text      TEXT,
    power            TEXT,
    toughness        TEXT,
    colors           TEXT,
    color_identity   TEXT,
    keywords         TEXT,
    all_parts        TEXT,
    full_data        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS card_images (
    id               TEXT PRIMARY KEY,
    oracle_id        TEXT NOT NULL,
    set_code         TEXT,
    set_name         TEXT,
    set_type         TEXT,
    rarity           TEXT,
    released_at      TEXT,
    collector_number TEXT,
    artist           TEXT,
    frame            TEXT,
    frame_effects    TEXT,
    promo            INTEGER,
    reprint          INTEGER,
    variation        INTEGER,
    story_spotlight  INTEGER,
    prices           TEXT,
    purchase_uris    TEXT,
    image_uris       TEXT,
    card_faces       TEXT
);

CREATE TABLE IF NOT EXISTS token_images (
    id               TEXT PRIMARY KEY,
    token_oracle_id  TEXT,
    set_code         TEXT,
    set_name         TEXT,
    released_at      TEXT,
    collector_number TEXT,
    artist           TEXT,
    image_uris       TEXT,
    card_faces       TEXT
);

CREATE TABLE IF NOT EXISTS metadata (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    last_updated_at     TEXT,
    source_updated_at   TEXT,
    file_size           INTEGER,
    card_count          INTEGER,
    token_count         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_cards_name       ON cards (name);
CREATE INDEX IF NOT EXISTS idx_cards_type_line  ON cards (type_line);
CREATE INDEX IF NOT EXISTS idx_cards_cmc        ON cards (cmc);
CREATE INDEX IF NOT EXISTS idx_images_oracle_id ON card_images (oracle_id);
CREATE INDEX IF NOT EXISTS idx_images_set_code  ON card_images (set_code);
CREATE INDEX IF NOT EXISTS idx_tokens_name      ON tokens (name);

CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
    name,
    type_line,
    oracle_text,
    content='cards',
    content_rowid='rowid'
);
"""

_JUMPSTART_SETS = frozenset(["jmp", "j22", "jmp22", "j21", "jmp21", "j20", "jmp20"])


def _is_token(card: dict) -> bool:
    layout = (card.get("layout") or "").lower()
    type_line = (card.get("type_line") or "").lower()
    return layout == "token" or "token" in type_line


def _is_jumpstart_cover(card: dict) -> bool:
    set_code = (card.get("set") or "").lower()
    if set_code not in _JUMPSTART_SETS:
        return False
    return not card.get("mana_cost") and len(card.get("oracle_text") or "") < 50


def _jv(value) -> str | None:
    return None if value is None else json.dumps(value)


def _extract_oracle_text(card: dict) -> str:
    faces = card.get("card_faces") or []
    parts = [f.get("oracle_text", "") or "" for f in faces]
    return " // ".join(p for p in parts if p)


def _card_row(card: dict) -> tuple:
    oracle_id = card.get("oracle_id") or card.get("id")
    return (
        oracle_id,
        card.get("name"),
        card.get("lang"),
        card.get("layout"),
        card.get("mana_cost"),
        card.get("cmc"),
        card.get("type_line"),
        card.get("oracle_text") or _extract_oracle_text(card),
        card.get("power"),
        card.get("toughness"),
        card.get("loyalty"),
        card.get("defense"),
        card.get("hand_modifier"),
        card.get("life_modifier"),
        _jv(card.get("colors")),
        _jv(card.get("color_identity")),
        _jv(card.get("produced_mana")),
        _jv(card.get("keywords")),
        _jv(card.get("legalities")),
        _jv(card.get("games")),
        1 if card.get("reserved") else 0,
        card.get("edhrec_rank"),
        card.get("penny_rank"),
        _jv(card.get("all_parts")),
        _jv(card.get("prices")),
        _jv(card.get("purchase_uris")),
        card.get("rulings_uri"),
        card.get("scryfall_uri"),
        None,                # sets — populated later via UPDATE
        json.dumps(card),
    )


def _token_row(card: dict) -> tuple:
    return (
        card.get("id"),
        card.get("oracle_id"),
        card.get("name"),
        card.get("layout"),
        card.get("type_line"),
        card.get("oracle_text") or _extract_oracle_text(card),
        card.get("power"),
        card.get("toughness"),
        _jv(card.get("colors")),
        _jv(card.get("color_identity")),
        _jv(card.get("keywords")),
        _jv(card.get("all_parts")),
        json.dumps(card),
    )


def _image_row(card: dict) -> tuple:
    oracle_id = card.get("oracle_id") or card.get("id")
    return (
        card.get("id"),
        oracle_id,
        card.get("set"),
        card.get("set_name"),
        card.get("set_type"),
        card.get("rarity"),
        card.get("released_at"),
        card.get("collector_number"),
        card.get("artist"),
        card.get("frame"),
        _jv(card.get("frame_effects")),
        1 if card.get("promo") else 0,
        1 if card.get("reprint") else 0,
        1 if card.get("variation") else 0,
        1 if card.get("story_spotlight") else 0,
        _jv(card.get("prices")),
        _jv(card.get("purchase_uris")),
        _jv(card.get("image_uris")),
        _jv(card.get("card_faces")),
    )


def _token_image_row(card: dict) -> tuple:
    return (
        card.get("id"),
        card.get("oracle_id"),
        card.get("set"),
        card.get("set_name"),
        card.get("released_at"),
        card.get("collector_number"),
        card.get("artist"),
        _jv(card.get("image_uris")),
        _jv(card.get("card_faces")),
    )


def build_prints_db(
    source_json: Path = SCRYFALL_DEFAULT_CARDS_JSON,
    dest_db: Path = PRINTS_DB_PATH,
    force: bool = False,
) -> None:
    if dest_db.exists() and not force:
        print(f"  prints.db already exists at {dest_db} (use --force-prints to rebuild)")
        return

    dest_db.parent.mkdir(parents=True, exist_ok=True)
    if dest_db.exists():
        dest_db.unlink()

    print(f"  Parsing {source_json.name} ({source_json.stat().st_size // 1024 // 1024} MB)...")
    t_parse = time.time()
    with open(source_json, encoding="utf-8") as f:
        raw_cards = json.load(f)
    print(f"  Parsed {len(raw_cards):,} entries in {time.time() - t_parse:.1f}s")

    # Build row tuples in one pass — much faster than calling execute() per row
    print("  Building row buffers...")
    t_buf = time.time()
    card_rows: list[tuple] = []
    card_image_rows: list[tuple] = []
    token_rows: list[tuple] = []
    token_image_rows: list[tuple] = []
    seen_oracle_ids: set[str] = set()

    for card in raw_cards:
        if card.get("lang") != "en":
            continue
        if _is_jumpstart_cover(card):
            continue

        if _is_token(card):
            token_rows.append(_token_row(card))
            token_image_rows.append(_token_image_row(card))
        else:
            oracle_id = card.get("oracle_id") or card.get("id")
            if oracle_id and oracle_id not in seen_oracle_ids:
                card_rows.append(_card_row(card))
                seen_oracle_ids.add(oracle_id)
            card_image_rows.append(_image_row(card))

    print(f"  Buffered {len(card_rows):,} cards, {len(card_image_rows):,} images, "
          f"{len(token_rows):,} tokens in {time.time() - t_buf:.1f}s")

    print("  Writing prints.db...")
    t_write = time.time()
    con = sqlite3.connect(str(dest_db))

    # Build-time PRAGMAs — safe to use for a write-once build script
    con.executescript("""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA cache_size=-65536;
        PRAGMA temp_store=MEMORY;
    """)
    con.executescript(SCHEMA)

    with con:
        cur = con.cursor()

        cur.executemany(
            "INSERT OR IGNORE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            card_rows,
        )
        cur.executemany(
            "INSERT OR IGNORE INTO card_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            card_image_rows,
        )
        cur.executemany(
            "INSERT OR IGNORE INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            token_rows,
        )
        cur.executemany(
            "INSERT OR IGNORE INTO token_images VALUES (?,?,?,?,?,?,?,?,?)",
            token_image_rows,
        )

    print(f"  Rows inserted in {time.time() - t_write:.1f}s")

    print("  Updating card sets lookup...")
    with con:
        con.execute("""
            UPDATE cards
            SET sets = (
                SELECT json_group_array(set_code)
                FROM (
                    SELECT DISTINCT set_code
                    FROM card_images
                    WHERE card_images.oracle_id = cards.oracle_id
                      AND set_code IS NOT NULL
                    ORDER BY set_code
                )
            )
        """)
        con.execute("""
            INSERT INTO metadata (id, last_updated_at, file_size, card_count, token_count)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_updated_at = excluded.last_updated_at,
                file_size       = excluded.file_size,
                card_count      = excluded.card_count,
                token_count     = excluded.token_count
        """, (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            source_json.stat().st_size,
            len(card_rows),
            len(token_rows),
        ))

    print("  Building FTS index...")
    with con:
        con.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")

    # Restore safe PRAGMAs for runtime use by karnforge
    con.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
    con.close()

    db_mb = dest_db.stat().st_size / 1024 / 1024
    print(f"  prints.db built: {db_mb:.0f} MB — {len(card_rows):,} cards, {len(token_rows):,} tokens "
          f"in {time.time() - t_write:.1f}s total write time")
