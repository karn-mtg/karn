"""
Propagate Scryfall tags and mechanic clusters to cards that missed tagger
coverage, using existing similar_to graph edges as a voting mechanism.

Run this after a full build_db.py (similarity edges must exist in graph.json).

Usage:
    python scripts/propagate_tags.py [--dry-run] [--min-tag-votes N] [--min-cluster-votes N]

Algorithm:
    For each card that has similar_to neighbors in the graph:
        1. Collect the scryfall_tags and clusters from all neighbors.
        2. For each tag/cluster the card currently lacks:
             - Tag vote threshold (default 2): add if ≥ N neighbors have it.
             - Cluster vote threshold (default 3): add if ≥ N neighbors have it.
        3. Write updated metadata to ChromaDB (batched).
        4. Add cluster->card edges to graph for newly assigned clusters.

Cards with zero similar_to edges are skipped (no neighbors = no signal).
"""

import argparse
from collections import Counter

from arsenal.cards.config import CHROMA_DIR, GRAPH_JSON_PATH
from arsenal.cards.embedder import get_or_create_collection
from arsenal.cards.graph_builder import load_graph, save_graph


def _load_all_metadata(collection) -> dict[str, dict]:
    """Single bulk fetch → {card_id: metadata_dict}."""
    result = collection.get(include=["metadatas"])
    return {
        doc_id: (meta or {})
        for doc_id, meta in zip(result["ids"], result["metadatas"])
    }


def _parse_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {v.strip() for v in value.split(",") if v.strip()}


def _get_similar_neighbors(graph, card_node_id: str) -> list[str]:
    """Return card_ids (not node_ids) of all similar_to out-neighbors."""
    neighbors: list[str] = []
    for _, neighbor, edge_data in graph.out_edges(card_node_id, data=True):
        if edge_data.get("edge_type") == "similar_to":
            # node_id is "card:<oracle_id>" — strip the prefix
            neighbors.append(neighbor.removeprefix("card:"))
    return neighbors


def _compute_votes(
    card_meta: dict,
    neighbor_metas: list[dict],
) -> tuple[Counter, Counter]:
    """
    Count how many neighbors have each tag/cluster that this card lacks.
    Returns (tag_votes, cluster_votes).
    """
    card_tags     = _parse_csv(card_meta.get("scryfall_tags"))
    card_clusters = _parse_csv(card_meta.get("clusters"))

    tag_votes:     Counter = Counter()
    cluster_votes: Counter = Counter()

    for meta in neighbor_metas:
        for tag in _parse_csv(meta.get("scryfall_tags")):
            if tag not in card_tags:
                tag_votes[tag] += 1
        for cluster in _parse_csv(meta.get("clusters")):
            if cluster not in card_clusters:
                cluster_votes[cluster] += 1

    return tag_votes, cluster_votes


def propagate(min_tag_votes: int, min_cluster_votes: int, dry_run: bool) -> None:
    print(f"Loading graph from {GRAPH_JSON_PATH}...")
    graph = load_graph(GRAPH_JSON_PATH)

    print(f"Loading ChromaDB from {CHROMA_DIR}...")
    collection = get_or_create_collection(CHROMA_DIR)
    all_meta = _load_all_metadata(collection)
    print(f"  Loaded metadata for {len(all_meta):,} cards")

    # Collect all existing cluster node IDs for safe edge creation
    existing_cluster_nodes: set[str] = {
        n for n in graph.nodes if graph.nodes[n].get("type") == "cluster"
    }

    updates: dict[str, dict] = {}               # card_id -> updated metadata dict
    cluster_backfill: dict[str, set[str]] = {}  # card_id -> new clusters
    dry_run_count = 0

    card_nodes = [n for n in graph.nodes if graph.nodes[n].get("type") == "card"]
    processed = skipped = 0

    for card_node in card_nodes:
        card_id = card_node.removeprefix("card:")
        neighbor_ids = _get_similar_neighbors(graph, card_node)
        if not neighbor_ids:
            skipped += 1
            continue

        card_meta = all_meta.get(card_id, {})
        neighbor_metas = [all_meta[nid] for nid in neighbor_ids if nid in all_meta]
        if not neighbor_metas:
            skipped += 1
            continue

        tag_votes, cluster_votes = _compute_votes(card_meta, neighbor_metas)

        new_tags     = {t for t, v in tag_votes.items()     if v >= min_tag_votes}
        new_clusters = {c for c, v in cluster_votes.items() if v >= min_cluster_votes}

        if not new_tags and not new_clusters:
            processed += 1
            continue

        if dry_run:
            name = card_meta.get("name", card_id)
            if new_tags:
                print(f"  [DRY RUN] {name!r}: would add tags={sorted(new_tags)}")
            if new_clusters:
                print(f"  [DRY RUN] {name!r}: would add clusters={sorted(new_clusters)}")
            dry_run_count += 1
            processed += 1
            continue

        updated = dict(card_meta)
        if new_tags:
            existing = _parse_csv(updated.get("scryfall_tags"))
            existing.update(new_tags)
            updated["scryfall_tags"] = ",".join(sorted(existing))
        if new_clusters:
            existing = _parse_csv(updated.get("clusters"))
            existing.update(new_clusters)
            updated["clusters"] = ",".join(sorted(existing))
            cluster_backfill[card_id] = new_clusters

        updates[card_id] = updated
        processed += 1

    print(f"  Scanned {processed:,} cards with neighbors, skipped {skipped:,} with none")

    if dry_run:
        print(f"\n[DRY RUN] {dry_run_count:,} cards would be updated. Run without --dry-run to apply.")
        return

    if not updates:
        print("  No cards needed updates.")
        return

    # Batch-update ChromaDB
    UPDATE_BATCH = 100
    update_ids = list(updates.keys())
    written = 0
    for i in range(0, len(update_ids), UPDATE_BATCH):
        batch_ids = update_ids[i : i + UPDATE_BATCH]
        collection.update(
            ids=batch_ids,
            metadatas=[updates[doc_id] for doc_id in batch_ids],
        )
        written += len(batch_ids)
    print(f"  Updated ChromaDB metadata for {written:,} cards")

    # Update graph cluster edges
    edges_added = 0
    if cluster_backfill:
        for card_id, new_clusters in cluster_backfill.items():
            card_node = f"card:{card_id}"
            if not graph.has_node(card_node):
                continue
            for cluster in new_clusters:
                cluster_node = f"cluster:{cluster}"
                if cluster_node in existing_cluster_nodes and not graph.has_edge(cluster_node, card_node):
                    graph.add_edge(cluster_node, card_node)
                    edges_added += 1
        save_graph(graph, GRAPH_JSON_PATH)

    # Summary
    total_new_tags     = sum(len(_parse_csv(updates[c].get("scryfall_tags")) - _parse_csv(all_meta.get(c, {}).get("scryfall_tags"))) for c in updates)
    total_new_clusters = sum(len(v) for v in cluster_backfill.values())
    print("\nPropagation complete:")
    print(f"  Cards updated:        {len(updates):,}")
    print(f"  New tag assignments:  {total_new_tags:,}")
    print(f"  New cluster assigns:  {total_new_clusters:,}")
    print(f"  Graph edges added:    {edges_added:,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Propagate tags/clusters to cards missed by tagger using similarity voting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run",             action="store_true", help="Preview changes without writing")
    parser.add_argument("--min-tag-votes",        type=int, default=2, metavar="N",
                        help="Minimum neighbor votes to add a tag (default: 2)")
    parser.add_argument("--min-cluster-votes",    type=int, default=3, metavar="N",
                        help="Minimum neighbor votes to add a cluster (default: 3)")
    args = parser.parse_args()

    propagate(
        min_tag_votes=args.min_tag_votes,
        min_cluster_votes=args.min_cluster_votes,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
