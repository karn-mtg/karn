"""
Fetch combo data from Commander Spellbook public API and enrich the DB.

Saves:     db/combos_spellbook.json
Updates:   ChromaDB metadata field `combos` (comma-joined combo IDs)
Updates:   graph.json (new combo edges)
"""

from __future__ import annotations

import json
import time

import httpx

from arsenal.cards.config import BASE_DIR, CHROMA_DIR, GRAPH_JSON_PATH
from arsenal.cards.embedder import get_or_create_collection
from arsenal.cards.graph_builder import load_graph, save_graph

API_BASE = "https://backend.commanderspellbook.com/variants/"
OUTPUT_JSON = BASE_DIR / "combos_spellbook.json"
REQUEST_DELAY = 0.5   # seconds between paginated requests
MAX_RETRIES   = 5     # retries on 429 / transient errors


def _fetch_all_variants() -> list[dict]:
    """Paginate through the Commander Spellbook API and return all raw variant dicts."""
    variants: list[dict] = []
    url: str | None = API_BASE
    page = 0

    with httpx.Client(timeout=30, headers={"User-Agent": "karn-mtg-enricher/1.0"}) as client:
        while url:
            for attempt in range(MAX_RETRIES):
                resp = client.get(url)
                if resp.status_code == 429:
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s, 40s, 80s
                    print(f"\r  Rate limited — waiting {wait}s (attempt {attempt + 1}/{MAX_RETRIES})", flush=True)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            else:
                raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} retries (429)")

            data = resp.json()
            batch = data.get("results", [])
            variants.extend(batch)
            page += 1
            print(f"\r  Fetched page {page} ({len(variants):,} variants so far)", end="", flush=True)

            url = data.get("next")  # null when last page
            if url:
                time.sleep(REQUEST_DELAY)

    print()  # newline after \r progress
    return variants


def _parse_variant(variant: dict, index: int) -> dict:
    """Convert a raw API variant into our combo shape."""
    card_names: list[str] = []
    for use in variant.get("uses", []):
        card_obj = use.get("card") or {}
        name = card_obj.get("name", "").strip()
        if name:
            card_names.append(name)

    feature_strs: list[str] = []
    for feat in variant.get("produces", []):
        feature_obj = feat.get("feature") or {}
        desc = feature_obj.get("name", "").strip()
        if desc:
            feature_strs.append(desc)

    description = (
        variant.get("description")
        or variant.get("notes")
        or ", ".join(feature_strs)
        or "No description"
    ).strip()

    combo_type = "combo"
    lower_desc = description.lower()
    if "infinite" in lower_desc:
        combo_type = "infinite"
    elif "win" in lower_desc or "instant win" in lower_desc:
        combo_type = "instant_win"

    return {
        "id": f"spellbook:{variant.get('id', index)}",
        "cards": card_names,
        "type": combo_type,
        "description": description,
    }


def fetch_and_merge_combos(seeded_combos: list[dict], force: bool = False) -> list[dict]:
    """
    Fetch Commander Spellbook variants (or reload from cache) and merge with
    seeded_combos. Seeded combos take priority: if a seeded combo's card set
    matches a Spellbook variant's card set, the seeded entry is kept and the
    Spellbook duplicate is dropped.

    Does NOT touch ChromaDB or the graph — returns the merged list only.
    Call update_chroma_combos() separately once ChromaDB exists.
    """
    if OUTPUT_JSON.exists() and not force:
        print(f"  {OUTPUT_JSON} already exists — loading from cache")
        spellbook_combos: list[dict] = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        print(f"  Loaded {len(spellbook_combos):,} Spellbook combos from cache")
    else:
        print("  Fetching variants from Commander Spellbook API...")
        variants = _fetch_all_variants()
        print(f"  Parsing {len(variants):,} variants...")
        spellbook_combos = [_parse_variant(v, i) for i, v in enumerate(variants)]
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(spellbook_combos, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved {len(spellbook_combos):,} combos → {OUTPUT_JSON}")

    # Give seeded combos stable IDs and build a fingerprint set for dedup
    tagged_seeded: list[dict] = []
    seeded_fingerprints: set[frozenset] = set()
    for i, c in enumerate(seeded_combos):
        entry = dict(c)
        entry.setdefault("id", f"seeded:{i}")
        tagged_seeded.append(entry)
        seeded_fingerprints.add(frozenset(n.lower() for n in c.get("cards", [])))

    # Append Spellbook combos that don't duplicate a seeded one
    merged = list(tagged_seeded)
    for combo in spellbook_combos:
        fp = frozenset(n.lower() for n in combo.get("cards", []))
        if fp not in seeded_fingerprints:
            merged.append(combo)

    print(f"  Merged combo set: {len(merged):,} total "
          f"({len(tagged_seeded)} seeded + {len(merged) - len(tagged_seeded):,} from Spellbook)")
    return merged


def update_chroma_combos(combos: list[dict]) -> None:
    """
    For each card in each combo, append the combo ID to its `combos` metadata field.
    Uses get() + update() to be idempotent.
    """
    collection = get_or_create_collection(CHROMA_DIR)

    # Build mapping: card_name -> list of combo IDs
    # ChromaDB has no name index; we fetch all docs and build a name->id map.
    print("  Building card-name index from ChromaDB...")
    ids: list[str] = []
    metadatas: list[dict] = []
    offset, batch_size = 0, 5000
    while True:
        batch = collection.get(include=["metadatas"], limit=batch_size, offset=offset)
        if not batch["ids"]:
            break
        ids.extend(batch["ids"])
        metadatas.extend(batch["metadatas"])
        offset += batch_size

    name_to_id: dict[str, str] = {}
    id_to_meta: dict[str, dict] = {}
    for doc_id, meta in zip(ids, metadatas):
        name = (meta or {}).get("name", "")
        if name:
            name_to_id[name] = doc_id
        id_to_meta[doc_id] = meta or {}

    # Accumulate combo IDs per card doc_id
    card_combo_additions: dict[str, list[str]] = {}
    for combo in combos:
        combo_id = combo["id"]
        for card_name in combo["cards"]:
            doc_id = name_to_id.get(card_name)
            if doc_id:
                card_combo_additions.setdefault(doc_id, []).append(combo_id)

    # Update ChromaDB metadata in batches
    UPDATE_BATCH = 100
    update_ids = list(card_combo_additions.keys())
    updated = 0
    for i in range(0, len(update_ids), UPDATE_BATCH):
        batch_ids = update_ids[i : i + UPDATE_BATCH]
        new_metadatas = []
        for doc_id in batch_ids:
            existing_meta = dict(id_to_meta[doc_id])
            existing_combos = set(
                x for x in existing_meta.get("combos", "").split(",") if x
            )
            existing_combos.update(card_combo_additions[doc_id])
            existing_meta["combos"] = ",".join(sorted(existing_combos))
            new_metadatas.append(existing_meta)

        collection.update(ids=batch_ids, metadatas=new_metadatas)
        updated += len(batch_ids)

    print(f"  Updated combos metadata for {updated:,} card documents")


def _update_graph_combos(combos: list[dict]) -> None:
    """Add combo edges to the graph (same pattern as graph_builder.py)."""
    if not GRAPH_JSON_PATH.exists():
        print("  WARNING: graph.json not found — skipping graph update")
        return

    G = load_graph(GRAPH_JSON_PATH)

    # Build name -> node_id map from existing card nodes
    card_name_to_node: dict[str, str] = {
        G.nodes[n]["label"]: n
        for n in G.nodes
        if G.nodes[n].get("type") == "card"
    }

    edges_added = 0
    for combo in combos:
        combo_id = combo["id"]
        combo_card_nodes = [
            card_name_to_node[name]
            for name in combo["cards"]
            if name in card_name_to_node
        ]
        for src in combo_card_nodes:
            for dst in combo_card_nodes:
                if src != dst:
                    G.add_edge(
                        src,
                        dst,
                        edge_type="combo",
                        combo_id=combo_id,
                        combo_type=combo.get("type", "combo"),
                    )
                    edges_added += 1

    print(f"  Added {edges_added:,} combo edges to graph")
    save_graph(G, GRAPH_JSON_PATH)


def run(force: bool = False) -> None:
    """Main entry point. Idempotent: skips fetch if output JSON already exists."""
    if OUTPUT_JSON.exists() and not force:
        print(f"  {OUTPUT_JSON} already exists — skipping fetch (use --force to re-run)")
        combos = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        print(f"  Loaded {len(combos):,} combos from cache")
    else:
        print("  Fetching variants from Commander Spellbook API...")
        variants = _fetch_all_variants()
        print(f"  Parsing {len(variants):,} variants...")
        combos = [_parse_variant(v, i) for i, v in enumerate(variants)]

        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(combos, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved {len(combos):,} combos → {OUTPUT_JSON}")

    print("  Updating ChromaDB combo metadata...")
    update_chroma_combos(combos)

    print("  Updating graph combo edges...")
    _update_graph_combos(combos)

    print(f"  Commander Spellbook enrichment complete ({len(combos):,} combos)")
