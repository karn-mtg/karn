"""
Fetch Scryfall Tagger community tags for cards and enrich the DB.

Strategy: Scryfall does not expose a bulk-tags download endpoint. Tags live at
tagger.scryfall.com which serves a React SPA — the underlying API endpoint is
`https://tagger.scryfall.com/tags/card/<scryfall_id>` returning JSON.

We fetch per-card using async httpx with bounded concurrency (CONCURRENCY slots)
so the full ~30k card fetch takes ~5-10 minutes instead of ~1.7 hours.

Saves:     db/tags_scryfall.json   {card_id: [tag1, tag2, ...]}
Updates:   ChromaDB metadata field `scryfall_tags` (comma-joined string)
           ChromaDB metadata field `clusters` (backfilled via TAGGER_TAG_TO_CLUSTER)
Graph:     Adds tag nodes at L3 + cluster->card edges for backfilled clusters
"""

from __future__ import annotations

import asyncio
import json
import re

import httpx

from arsenal.cards.config import BASE_DIR, CHROMA_DIR, GRAPH_JSON_PATH, TAGGER_TAG_TO_CLUSTER
from arsenal.cards.embedder import get_or_create_collection
from arsenal.cards.graph_builder import load_graph, save_graph

OUTPUT_JSON = BASE_DIR / "tags_scryfall.json"

TAGGER_CARD_URL = "https://tagger.scryfall.com/card/{scryfall_id}"
TAGGER_API_URL  = "https://tagger.scryfall.com/tags/card/{scryfall_id}"

CONCURRENCY   = 10    # concurrent HTTP connections
REQUEST_DELAY = 0.1   # seconds to sleep after each request (per slot)
TIMEOUT       = 15

FUNCTIONAL_TAG_KEYWORDS = {
    "removal", "ramp", "draw", "card draw", "board wipe", "wrath",
    "counter magic", "counterspell", "tutor", "sacrifice outlet",
    "mana rock", "mana dork", "reanimation", "recursion", "protection",
    "haste enabler", "token", "anthem", "pump", "combo", "infinite",
    "win condition", "lifegain", "mill", "discard", "land destruction",
    "stax", "tax", "flicker", "blink", "graveyard hate", "exile",
    "copy", "clone", "bounce", "tuck", "wheel",
}


def _tag_is_functional(tag_name: str) -> bool:
    lower = tag_name.lower()
    return any(kw in lower for kw in FUNCTIONAL_TAG_KEYWORDS)


def _parse_tags_from_json(data: dict) -> list[str]:
    tags = []
    for tag_obj in data.get("tags", []):
        name = (
            tag_obj.get("name")
            or tag_obj.get("label")
            or tag_obj.get("slug", "").replace("-", " ")
        )
        if name:
            tags.append(name.strip().lower())
    return tags


def _scrape_tags_from_html(html: str) -> list[str]:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return []
    tags: list[str] = []
    _collect_tags_recursive(data, tags)
    return list(dict.fromkeys(tags))


def _collect_tags_recursive(obj, tags: list[str], depth: int = 0) -> None:
    if depth > 12:
        return
    if isinstance(obj, dict):
        for key in ("slug", "name", "label"):
            if key in obj and isinstance(obj[key], str):
                candidate = obj[key].replace("-", " ").strip().lower()
                if _tag_is_functional(candidate) and len(candidate) > 2:
                    tags.append(candidate)
        for v in obj.values():
            _collect_tags_recursive(v, tags, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _collect_tags_recursive(item, tags, depth + 1)


async def _fetch_card_tags_async(
    scryfall_id: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[str]:
    async with semaphore:
        try:
            resp = await client.get(
                TAGGER_API_URL.format(scryfall_id=scryfall_id),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "karn-mtg-enricher/1.0 (MTG research tool)",
                },
            )
            if resp.status_code == 200:
                tags = _parse_tags_from_json(resp.json())
            else:
                page_resp = await client.get(
                    TAGGER_CARD_URL.format(scryfall_id=scryfall_id),
                    headers={"User-Agent": "karn-mtg-enricher/1.0"},
                )
                tags = _scrape_tags_from_html(page_resp.text) if page_resp.status_code == 200 else []
        except (httpx.HTTPError, ValueError, KeyError):
            tags = []
        finally:
            await asyncio.sleep(REQUEST_DELAY)
    return [t for t in tags if _tag_is_functional(t)]


async def _fetch_all_tags_async(ids: list[str]) -> dict[str, list[str]]:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    counter   = [0]
    total     = len(ids)
    tags_map: dict[str, list[str]] = {}

    async def _tracked(card_id: str) -> None:
        tags = await _fetch_card_tags_async(card_id, client, semaphore)
        if tags:
            tags_map[card_id] = tags
        counter[0] += 1
        if counter[0] % 500 == 0 or counter[0] == total:
            tagged = len(tags_map)
            print(f"\r  {counter[0]:,}/{total:,} cards ({tagged:,} tagged)", end="", flush=True)

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        await asyncio.gather(*[_tracked(card_id) for card_id in ids])

    print()  # newline after \r progress
    return tags_map


def _update_chroma_tags(tags_map: dict[str, list[str]]) -> None:
    """Upsert scryfall_tags metadata and backfill clusters from TAGGER_TAG_TO_CLUSTER."""
    collection = get_or_create_collection(CHROMA_DIR)

    update_ids = list(tags_map.keys())
    if not update_ids:
        print("  No tags to update in ChromaDB")
        return

    results = collection.get(ids=update_ids, include=["metadatas"])
    id_to_meta: dict[str, dict] = {
        doc_id: (meta or {})
        for doc_id, meta in zip(results["ids"], results["metadatas"])
    }

    UPDATE_BATCH = 100
    updated = 0
    cluster_backfill: dict[str, set[str]] = {}

    for i in range(0, len(update_ids), UPDATE_BATCH):
        batch_ids = update_ids[i : i + UPDATE_BATCH]
        new_metadatas = []
        for doc_id in batch_ids:
            meta = dict(id_to_meta.get(doc_id, {}))
            tag_list = tags_map.get(doc_id, [])
            meta["scryfall_tags"] = ",".join(tag_list)

            existing_clusters = {c for c in meta.get("clusters", "").split(",") if c}
            new_clusters: set[str] = set()
            for tag in tag_list:
                cluster = TAGGER_TAG_TO_CLUSTER.get(tag)
                if cluster and cluster not in existing_clusters:
                    new_clusters.add(cluster)
            if new_clusters:
                existing_clusters.update(new_clusters)
                meta["clusters"] = ",".join(sorted(existing_clusters))
                cluster_backfill[doc_id] = new_clusters

            new_metadatas.append(meta)
        collection.update(ids=batch_ids, metadatas=new_metadatas)
        updated += len(batch_ids)

    new_cluster_count = sum(len(v) for v in cluster_backfill.values())
    print(f"  Updated scryfall_tags metadata for {updated:,} card documents")
    print(f"  Cluster backfill: {new_cluster_count:,} new cluster assignments across {len(cluster_backfill):,} cards")

    if cluster_backfill:
        _update_graph_cluster_backfill(cluster_backfill)


def _update_graph_cluster_backfill(backfill: dict[str, set[str]]) -> None:
    if not GRAPH_JSON_PATH.exists():
        print("  WARNING: graph.json not found — skipping cluster backfill graph update")
        return

    G = load_graph(GRAPH_JSON_PATH)
    edges_added = 0

    for card_id, new_clusters in backfill.items():
        card_node = f"card:{card_id}"
        if not G.has_node(card_node):
            continue
        for cluster in new_clusters:
            cluster_node = f"cluster:{cluster}"
            if G.has_node(cluster_node) and not G.has_edge(cluster_node, card_node):
                G.add_edge(cluster_node, card_node)
                edges_added += 1

    if edges_added:
        save_graph(G, GRAPH_JSON_PATH)
    print(f"  Graph cluster backfill: {edges_added:,} new edges added")


def _update_graph_tags(tags_map: dict[str, list[str]]) -> None:
    if not GRAPH_JSON_PATH.exists():
        print("  WARNING: graph.json not found — skipping graph tag update")
        return

    G = load_graph(GRAPH_JSON_PATH)

    card_id_to_node: dict[str, str] = {
        n.split("card:")[-1]: n
        for n in G.nodes
        if G.nodes[n].get("type") == "card"
    }

    GRAPH_TAG_NODES = {
        "removal", "ramp", "draw", "board wipe", "counter magic",
        "tutor", "mana rock", "mana dork", "recursion", "win condition",
        "stax", "combo",
    }

    nodes_added = 0
    edges_added = 0

    for card_id, tag_list in tags_map.items():
        card_node = card_id_to_node.get(card_id)
        if not card_node:
            continue
        for tag in tag_list:
            if tag in GRAPH_TAG_NODES:
                tag_node = f"tag:{tag}"
                if not G.has_node(tag_node):
                    G.add_node(tag_node, type="tag", label=tag)
                    nodes_added += 1
                if not G.has_edge(card_node, tag_node):
                    G.add_edge(card_node, tag_node, edge_type="has_tag", tag=tag)
                    edges_added += 1

    print(f"  Graph: added {nodes_added} tag nodes, {edges_added} tag edges")
    if nodes_added or edges_added:
        save_graph(G, GRAPH_JSON_PATH)


def run(force: bool = False) -> None:
    """Main entry point. Idempotent: skips fetch if output JSON already exists."""
    collection = get_or_create_collection(CHROMA_DIR)

    if OUTPUT_JSON.exists() and not force:
        print(f"  {OUTPUT_JSON} already exists — loading from cache")
        tags_map: dict[str, list[str]] = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        print(f"  Loaded tags for {len(tags_map):,} cards from cache")
    else:
        ids: list[str] = []
        offset, batch_size = 0, 5000
        while True:
            batch = collection.get(include=[], limit=batch_size, offset=offset)
            if not batch["ids"]:
                break
            ids.extend(batch["ids"])
            offset += batch_size

        print(f"  Fetching Scryfall Tagger tags for {len(ids):,} cards "
              f"({CONCURRENCY} concurrent, {REQUEST_DELAY}s delay)...")
        tags_map = asyncio.run(_fetch_all_tags_async(ids))
        print(f"  {len(tags_map):,}/{len(ids):,} cards had functional tags")

        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(tags_map, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved tags for {len(tags_map):,} cards → {OUTPUT_JSON}")

    print("  Updating ChromaDB tag metadata...")
    _update_chroma_tags(tags_map)

    print("  Updating graph tag nodes/edges...")
    _update_graph_tags(tags_map)

    print(f"  Scryfall Tagger enrichment complete ({len(tags_map):,} cards tagged)")
