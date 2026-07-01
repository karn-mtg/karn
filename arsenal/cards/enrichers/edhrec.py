"""
Fetch EDHREC rank and salt score for cards in the ChromaDB collection.

API:  https://json.edhrec.com/cards/{slug}.json
      where slug = card name lowercased, spaces → hyphens, punctuation stripped.

Uses async httpx with bounded concurrency so the full ~30k card fetch takes
~5-10 minutes instead of ~1.7 hours.

Saves:     db/edhrec_data.json   {card_id: {edhrec_rank, salt_score}}
Updates:   ChromaDB metadata fields: edhrec_rank (int), salt_score (float)
"""

from __future__ import annotations

import asyncio
import json
import re

import httpx

from arsenal.cards.config import BASE_DIR, CHROMA_DIR
from arsenal.cards.embedder import get_or_create_collection

OUTPUT_JSON = BASE_DIR / "edhrec_data.json"

EDHREC_BASE   = "https://json.edhrec.com/cards/{slug}.json"
CONCURRENCY   = 10    # concurrent HTTP connections
REQUEST_DELAY = 0.1   # seconds to sleep after each request (per slot)
TIMEOUT       = 15


def _name_to_slug(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("’", "").replace("'", "")  # curly and straight apostrophes
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s/]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _parse_edhrec_response(data: dict) -> dict | None:
    card_data = data.get("card") or data
    rank = card_data.get("rank") or card_data.get("edhrec_rank")
    salt = card_data.get("salt") or card_data.get("salt_score")

    if rank is None:
        for val in data.values():
            if isinstance(val, dict):
                rank = val.get("rank") or val.get("edhrec_rank")
                salt = val.get("salt") or val.get("salt_score")
                if rank is not None:
                    break

    if rank is None and salt is None:
        return None

    return {
        "edhrec_rank": int(rank) if rank is not None else None,
        "salt_score":  float(salt) if salt is not None else None,
    }


async def _fetch_edhrec_card_async(
    card_id: str,
    name: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    async with semaphore:
        try:
            slug = _name_to_slug(name)
            resp = await client.get(
                EDHREC_BASE.format(slug=slug),
                headers={"User-Agent": "karn-mtg-enricher/1.0"},
            )
            result = _parse_edhrec_response(resp.json()) if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            result = None
        finally:
            await asyncio.sleep(REQUEST_DELAY)
    return result


async def _fetch_all_edhrec_async(
    ids: list[str],
    metadatas: list[dict],
) -> dict[str, dict]:
    semaphore  = asyncio.Semaphore(CONCURRENCY)
    counter    = [0]
    total      = len(ids)
    edhrec_map: dict[str, dict] = {}

    async def _tracked(card_id: str, meta: dict) -> None:
        name = (meta or {}).get("name", "")
        if name:
            result = await _fetch_edhrec_card_async(card_id, name, client, semaphore)
            if result:
                edhrec_map[card_id] = result
        counter[0] += 1
        if counter[0] % 500 == 0 or counter[0] == total:
            print(f"\r  {counter[0]:,}/{total:,} cards ({len(edhrec_map):,} hits)", end="", flush=True)

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        await asyncio.gather(*[_tracked(card_id, meta) for card_id, meta in zip(ids, metadatas)])

    print()
    return edhrec_map


def _update_chroma_edhrec(edhrec_map: dict[str, dict]) -> None:
    collection = get_or_create_collection(CHROMA_DIR)

    update_ids = list(edhrec_map.keys())
    if not update_ids:
        print("  No EDHREC data to update in ChromaDB")
        return

    results = collection.get(ids=update_ids, include=["metadatas"])
    id_to_meta: dict[str, dict] = {
        doc_id: (meta or {})
        for doc_id, meta in zip(results["ids"], results["metadatas"])
    }

    UPDATE_BATCH = 100
    updated = 0
    for i in range(0, len(update_ids), UPDATE_BATCH):
        batch_ids = update_ids[i : i + UPDATE_BATCH]
        new_metadatas = []
        for doc_id in batch_ids:
            meta = dict(id_to_meta.get(doc_id, {}))
            edata = edhrec_map[doc_id]
            if edata.get("edhrec_rank") is not None:
                meta["edhrec_rank"] = edata["edhrec_rank"]
            if edata.get("salt_score") is not None:
                meta["salt_score"] = edata["salt_score"]
            new_metadatas.append(meta)
        collection.update(ids=batch_ids, metadatas=new_metadatas)
        updated += len(batch_ids)

    print(f"  Updated EDHREC metadata for {updated:,} card documents")


def run(force: bool = False) -> None:
    """Main entry point. Idempotent: skips fetch if output JSON already exists."""
    collection = get_or_create_collection(CHROMA_DIR)

    if OUTPUT_JSON.exists() and not force:
        print(f"  {OUTPUT_JSON} already exists — loading from cache")
        edhrec_map: dict[str, dict] = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        print(f"  Loaded EDHREC data for {len(edhrec_map):,} cards from cache")
    else:
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

        print(f"  Fetching EDHREC data for {len(ids):,} cards "
              f"({CONCURRENCY} concurrent, {REQUEST_DELAY}s delay)...")
        edhrec_map = asyncio.run(_fetch_all_edhrec_async(ids, metadatas))
        print(f"  {len(edhrec_map):,}/{len(ids):,} cards had EDHREC data")

        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_JSON.write_text(json.dumps(edhrec_map, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved EDHREC data for {len(edhrec_map):,} cards → {OUTPUT_JSON}")

    print("  Updating ChromaDB EDHREC metadata...")
    _update_chroma_edhrec(edhrec_map)

    print(f"  EDHREC enrichment complete ({len(edhrec_map):,} cards enriched)")
