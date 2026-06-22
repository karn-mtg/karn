import json
import time
from pathlib import Path

import httpx

from arsenal.cards.config import SCRYFALL_BULK_API, SCRYFALL_BULK_JSON, SCRYFALL_DEFAULT_CARDS_JSON

CACHE_MAX_AGE_SECONDS = 86400  # 24 hours


def download_bulk_data(force_refresh: bool = False) -> Path:
    SCRYFALL_BULK_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not force_refresh and SCRYFALL_BULK_JSON.exists():
        age = time.time() - SCRYFALL_BULK_JSON.stat().st_mtime
        if age < CACHE_MAX_AGE_SECONDS:
            print(f"  Using cached Scryfall data ({age / 3600:.1f}h old)")
            return SCRYFALL_BULK_JSON

    print("  Fetching Scryfall bulk-data index...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(SCRYFALL_BULK_API)
        resp.raise_for_status()
        bulk_index = resp.json()

    download_url = None
    for entry in bulk_index.get("data", []):
        if entry.get("type") == "oracle_cards":
            download_url = entry["download_uri"]
            break

    if not download_url:
        raise RuntimeError("Could not find oracle_cards entry in Scryfall bulk-data index")

    print("  Downloading oracle cards from Scryfall (~120MB)...")
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        with client.stream("GET", download_url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(SCRYFALL_BULK_JSON, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:.1f}%", end="", flush=True)
    print()
    return SCRYFALL_BULK_JSON


def download_default_cards(force_refresh: bool = False) -> Path:
    """Download Scryfall default_cards bulk (one preferred printing per card, ~350 MB)."""
    SCRYFALL_DEFAULT_CARDS_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not force_refresh and SCRYFALL_DEFAULT_CARDS_JSON.exists():
        age = time.time() - SCRYFALL_DEFAULT_CARDS_JSON.stat().st_mtime
        if age < CACHE_MAX_AGE_SECONDS:
            print(f"  Using cached default_cards ({age / 3600:.1f}h old)")
            return SCRYFALL_DEFAULT_CARDS_JSON

    print("  Fetching Scryfall bulk-data index...")
    with httpx.Client(timeout=30) as client:
        resp = client.get(SCRYFALL_BULK_API)
        resp.raise_for_status()
        bulk_index = resp.json()

    download_url = None
    for entry in bulk_index.get("data", []):
        if entry.get("type") == "default_cards":
            download_url = entry["download_uri"]
            break

    if not download_url:
        raise RuntimeError("Could not find default_cards entry in Scryfall bulk-data index")

    print("  Downloading default cards from Scryfall (~350 MB)...")
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        with client.stream("GET", download_url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(SCRYFALL_DEFAULT_CARDS_JSON, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:.1f}%", end="", flush=True)
    print()
    return SCRYFALL_DEFAULT_CARDS_JSON


def load_cards(json_path: Path) -> list[dict]:
    print(f"  Parsing {json_path.name}...")
    with open(json_path, encoding="utf-8") as f:
        raw_cards = json.load(f)

    cards = []
    for raw in raw_cards:
        if raw.get("lang") != "en":
            continue
        layout = raw.get("layout", "")
        # skip tokens, emblems, art cards, etc.
        if layout in ("token", "emblem", "art_series", "double_faced_token", "reversible_card"):
            continue
        # skip basic lands to keep the DB focused (they don't need retrieval)
        type_line = raw.get("type_line", "")
        if "Basic Land" in type_line and "Legendary" not in type_line:
            continue
        card = normalize_card(raw)
        if card:
            cards.append(card)

    print(f"  Loaded {len(cards):,} cards")
    return cards


def normalize_card(raw: dict) -> dict | None:
    card_id = raw.get("id") or raw.get("oracle_id")
    if not card_id:
        return None

    name = raw.get("name", "")
    type_line = raw.get("type_line", "")
    mana_cost = raw.get("mana_cost", "") or ""
    cmc = float(raw.get("cmc", 0) or 0)
    rarity = raw.get("rarity", "common")
    colors = raw.get("colors") or []
    color_identity = raw.get("color_identity") or []
    keywords = raw.get("keywords") or []
    legalities = raw.get("legalities") or {}

    # Gather oracle text — handle double-faced cards
    oracle_text = _extract_oracle_text(raw)

    # Resolve color bucket for graph L1
    if len(color_identity) == 0:
        color_bucket = "C"
    elif len(color_identity) > 1:
        color_bucket = "M"
    else:
        color_bucket = color_identity[0]

    return {
        "id": card_id,
        "name": name,
        "oracle_text": oracle_text,
        "type_line": type_line,
        "mana_cost": mana_cost,
        "cmc": cmc,
        "colors": colors,
        "color_identity": color_identity,
        "color_bucket": color_bucket,
        "keywords": keywords,
        "rarity": rarity,
        "legalities": legalities,
        "set_name": raw.get("set_name", ""),
    }


def _extract_oracle_text(raw: dict) -> str:
    if "oracle_text" in raw:
        return raw["oracle_text"] or ""

    # double-faced and other multi-part cards store faces separately
    faces = raw.get("card_faces") or []
    parts = [face.get("oracle_text", "") or "" for face in faces]
    return " // ".join(p for p in parts if p)
