"""
Build the MTG card vector database + graph.

Usage:
    python build_db.py [options]

Output artifacts (in db/):
    chroma_db/    - ChromaDB persistent vector store
    graph.json    - NetworkX DAG with 4-level hierarchy + combo/similarity/tag edges
    prints.db     - SQLite card+image database (used by karnforge)

Enricher flags (all ON by default, use --no-X to skip):
    --no-spellbook     Skip Commander Spellbook combo fetch
    --no-tagger        Skip Scryfall Tagger tag enrichment
    --no-edhrec        Skip EDHREC rank + salt score enrichment
    --no-similarity-edges  Skip similarity edge computation
    --no-prints        Skip prints.db build

Force-refresh flags (re-fetch even if cached on disk):
    --force-download   Re-download Scryfall bulk data
    --force-reembed    Re-embed all cards into ChromaDB
    --force-spellbook  Re-fetch Commander Spellbook combos
    --force-tagger     Re-fetch Scryfall Tagger tags
    --force-edhrec     Re-fetch EDHREC data
    --force-prints     Force rebuild of prints.db
"""

import argparse
import concurrent.futures
import json
import time
from pathlib import Path


def build_similarity_edges(
    cards: list[dict],
    embeddings,  # np.ndarray shape [len(cards), dim] — pre-computed in step 6
) -> list[tuple[str, str, float]]:
    from arsenal.cards.embedder import get_collection_for_query

    # Use get_collection_for_query (no EF) since we're passing pre-computed embeddings
    collection = get_collection_for_query()
    total = len(cards)
    similarities: list[tuple[str, str, float]] = []
    THRESHOLD  = 0.15
    BATCH_SIZE = 100

    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch     = cards[batch_start:batch_end]

        # Slice the pre-computed embeddings — no re-encoding needed
        batch_embeddings = embeddings[batch_start:batch_end].tolist()

        results = collection.query(
            query_embeddings=batch_embeddings,
            n_results=6,
            include=["distances"],
        )

        for i, card in enumerate(batch):
            card_id = card["id"]
            for nid, dist in zip(results["ids"][i], results["distances"][i]):
                if nid != card_id and dist <= THRESHOLD:
                    similarities.append((card_id, nid, 1.0 - dist))

        print(f"\r  {batch_end:,}/{total:,} cards processed", end="", flush=True)

    print(f"\r  {total:,}/{total:,} cards processed")
    print(f"  Found {len(similarities):,} similarity edges")
    return similarities


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build MTG card database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--force-download",    action="store_true", help="Re-download Scryfall data even if fresh")
    parser.add_argument("--force-reembed",     action="store_true", help="Re-embed all cards even if already done")
    parser.add_argument("--force-spellbook",   action="store_true", help="Re-fetch Spellbook combos even if cached")
    parser.add_argument("--force-tagger",      action="store_true", help="Re-fetch Scryfall Tagger tags even if cached")
    parser.add_argument("--force-edhrec",      action="store_true", help="Re-fetch EDHREC data even if cached")
    parser.add_argument("--force-prints",      action="store_true", help="Force rebuild of prints.db even if it exists")
    parser.add_argument("--no-spellbook",      action="store_true", help="Skip Commander Spellbook combo fetch")
    parser.add_argument("--no-tagger",         action="store_true", help="Skip Scryfall Tagger enrichment")
    parser.add_argument("--no-edhrec",         action="store_true", help="Skip EDHREC enrichment")
    parser.add_argument("--no-similarity-edges", action="store_true", help="Skip similarity edge computation")
    parser.add_argument("--no-prints",         action="store_true", help="Skip prints.db build")
    args = parser.parse_args()

    t_total = time.time()

    from arsenal.cards.config import GRAPH_JSON_PATH
    from arsenal.cards.downloader import download_bulk_data, download_default_cards, load_cards

    # ── Step 1 ──────────────────────────────────────────────────────────────
    if not args.no_prints:
        print("[1/11] Downloading Scryfall oracle + default_cards in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            oracle_future  = pool.submit(download_bulk_data,     args.force_download)
            default_future = pool.submit(download_default_cards, args.force_download)
            json_path    = oracle_future.result()
            default_json = default_future.result()
    else:
        print("[1/11] Downloading Scryfall oracle cards...")
        json_path    = download_bulk_data(force_refresh=args.force_download)
        default_json = None

    # ── Step 2 ──────────────────────────────────────────────────────────────
    print("[2/11] Loading and normalizing cards...")
    cards = load_cards(json_path)

    # ── Step 3 ──────────────────────────────────────────────────────────────
    print("[3/11] Classifying cards into mechanic clusters...")
    from arsenal.cards.classifier import classify_card
    card_clusters: dict[str, list[str]] = {}
    for card in cards:
        card_clusters[card["id"]] = classify_card(card)

    cluster_counts: dict[str, int] = {}
    for clusters in card_clusters.values():
        for c in clusters:
            cluster_counts[c] = cluster_counts.get(c, 0) + 1
    top = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    print(f"  Top clusters: {', '.join(f'{k}={v:,}' for k, v in top)}")

    # ── Step 4 ──────────────────────────────────────────────────────────────
    combos_path = Path(__file__).parent.parent / "arsenal" / "cards" / "combos.json"
    with open(combos_path, encoding="utf-8") as f:
        seeded_combos = json.load(f)

    if not args.no_spellbook:
        print("[4/11] Fetching Commander Spellbook combos + merging with seeded combos...")
        from arsenal.cards.enrichers.commander_spellbook import fetch_and_merge_combos
        combos = fetch_and_merge_combos(seeded_combos, force=args.force_spellbook)
    else:
        print(f"[4/11] Using {len(seeded_combos)} seeded combos only (--no-spellbook)")
        combos = [dict(c, id=f"seeded:{i}") for i, c in enumerate(seeded_combos)]

    # ── Step 5 ──────────────────────────────────────────────────────────────
    print("[5/11] Building graph...")
    from arsenal.cards.graph_builder import build_graph, save_graph
    graph = build_graph(cards, card_clusters, combos)
    save_graph(graph, GRAPH_JSON_PATH)

    # ── Step 6 ──────────────────────────────────────────────────────────────
    print("[6/11] Embedding cards into ChromaDB...")
    from arsenal.cards.embedder import build_embeddings
    embeddings = build_embeddings(cards, card_clusters, force_reembed=args.force_reembed)

    if not args.no_spellbook:
        print("  Updating ChromaDB with combo metadata...")
        from arsenal.cards.enrichers.commander_spellbook import update_chroma_combos
        update_chroma_combos(combos)

    # ── Step 7 ──────────────────────────────────────────────────────────────
    if not args.no_tagger:
        print("[7/11] Fetching Scryfall Tagger tags → ChromaDB + cluster backfill + graph tag nodes...")
        from arsenal.cards.enrichers.scryfall_tagger import run as run_tagger
        run_tagger(force=args.force_tagger)
    else:
        print("[7/11] Skipping Scryfall Tagger (--no-tagger)")

    # ── Step 8 ──────────────────────────────────────────────────────────────
    if not args.no_edhrec:
        print("[8/11] Fetching EDHREC rank + salt scores → ChromaDB...")
        from arsenal.cards.enrichers.edhrec import run as run_edhrec
        run_edhrec(force=args.force_edhrec)
    else:
        print("[8/11] Skipping EDHREC (--no-edhrec)")

    # ── Step 9 ──────────────────────────────────────────────────────────────
    if not args.no_similarity_edges:
        print("[9/11] Computing similarity edges (top-5 per card)...")
        similarities = build_similarity_edges(cards, embeddings)
        if similarities:
            print("  Adding similarity edges to graph...")
            from arsenal.cards.graph_builder import add_similarity_edges
            add_similarity_edges(graph, similarities)
            save_graph(graph, GRAPH_JSON_PATH)
        else:
            print("  No similarity edges met the threshold")
    else:
        print("[9/11] Skipping similarity edges (--no-similarity-edges)")

    # ── Step 10 ─────────────────────────────────────────────────────────────
    if not args.no_prints and default_json is not None:
        print("[10/11] Building prints.db (SQLite card+image database)...")
        from arsenal.cards.prints_builder import build_prints_db
        build_prints_db(source_json=default_json, force=args.force_prints)
    else:
        print("[10/11] Skipping prints.db (--no-prints)")

    # ── Step 11 ─────────────────────────────────────────────────────────────
    print("[11/11] Done!")
    elapsed = time.time() - t_total
    print(f"\n  Total build time: {elapsed / 60:.1f} minutes")
    print(f"  Cards indexed:   {len(cards):,}")
    print(f"  Combos loaded:   {len(combos):,}")
    print(f"  Graph nodes:     {graph.number_of_nodes():,}")
    print(f"  Graph edges:     {graph.number_of_edges():,}")
    print("\nArtifacts written to: db/")
    print("  db/chroma_db/    - Vector store")
    print("  db/graph.json    - Navigation graph")
    if not args.no_spellbook:
        print("  db/combos_spellbook.json  - Commander Spellbook combos (cached)")
    if not args.no_tagger:
        print("  db/tags_scryfall.json     - Scryfall Tagger tags (cached)")
    if not args.no_edhrec:
        print("  db/edhrec_data.json       - EDHREC rank + salt scores (cached)")
    if not args.no_prints:
        print("  db/prints.db     - SQLite card+image database (used by karnforge)")
    print("\nNext step (optional — fills tag gaps via card similarity):")
    print("  python scripts/propagate_tags.py --dry-run")
    print("\nSmoke test:")
    print("  python -c \"from karn_db import query; r = query('sacrifice outlet for mana', top_k=3); print(r[0])\"")


if __name__ == "__main__":
    main()
