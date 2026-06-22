"""
Re-run individual enrichers against an already-built card database.

build_db.py now runs all three enrichers as part of its core pipeline
(steps 4, 7, 8). Use this script only when you want to refresh a specific
enricher's data without rebuilding the entire database — for example, to
pick up new Commander Spellbook combos or refresh EDHREC scores.

Usage:
    python enrich_db.py [--spellbook] [--tagger] [--edhrec] [--all] [--force]

Flags:
    --spellbook   Re-run Commander Spellbook combo enricher
    --tagger      Re-run Scryfall Tagger functional tag enricher
    --edhrec      Re-run EDHREC rank + salt score enricher
    --all         Run all enrichers
    --force       Re-fetch even if cached output JSON already exists

Prerequisites:
    db/chroma_db/ must exist (run build_db.py first)
"""

import argparse
import sys
import time


def _check_db_exists() -> None:
    from arsenal.cards.config import CHROMA_DIR
    if not CHROMA_DIR.exists():
        print(f"ERROR: {CHROMA_DIR} not found.")
        print("  Run 'python scripts/build_db.py' first to build the base database.")
        sys.exit(1)
    print(f"  Found ChromaDB at {CHROMA_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich the MTG card DB with external data sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--spellbook", action="store_true", help="Commander Spellbook combos")
    parser.add_argument("--tagger", action="store_true", help="Scryfall Tagger functional tags")
    parser.add_argument("--edhrec", action="store_true", help="EDHREC rank + salt score")
    parser.add_argument("--all", dest="all_enrichers", action="store_true", help="Run all enrichers")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cache exists")
    args = parser.parse_args()

    run_spellbook = args.spellbook or args.all_enrichers
    run_tagger = args.tagger or args.all_enrichers
    run_edhrec = args.edhrec or args.all_enrichers

    if not any([run_spellbook, run_tagger, run_edhrec]):
        parser.print_help()
        print("\nERROR: specify at least one enricher flag (or --all)")
        sys.exit(1)

    t_total = time.time()

    print("[0/N] Checking database...")
    _check_db_exists()

    step = 1
    total_steps = sum([run_spellbook, run_tagger, run_edhrec])

    if run_spellbook:
        print(f"\n[{step}/{total_steps}] Commander Spellbook combos...")
        from arsenal.cards.enrichers.commander_spellbook import run as run_spellbook_fn
        run_spellbook_fn(force=args.force)
        step += 1

    if run_tagger:
        print(f"\n[{step}/{total_steps}] Scryfall Tagger tags...")
        from arsenal.cards.enrichers.scryfall_tagger import run as run_tagger_fn
        run_tagger_fn(force=args.force)
        step += 1

    if run_edhrec:
        print(f"\n[{step}/{total_steps}] EDHREC rank + salt scores...")
        from arsenal.cards.enrichers.edhrec import run as run_edhrec_fn
        run_edhrec_fn(force=args.force)
        step += 1

    elapsed = time.time() - t_total
    print(f"\nEnrichment complete in {elapsed:.1f}s")
    print("\nArtifacts written to: db/")
    if run_spellbook:
        print("  db/combos_spellbook.json  — Commander Spellbook combo data")
    if run_tagger:
        print("  db/tags_scryfall.json     — Scryfall Tagger functional tags")
    if run_edhrec:
        print("  db/edhrec_data.json       — EDHREC rank + salt scores")
    print("\nChromaDB metadata fields added/updated:")
    if run_spellbook:
        print("  combos        — comma-joined combo IDs per card")
    if run_tagger:
        print("  scryfall_tags — comma-joined functional tag names")
    if run_edhrec:
        print("  edhrec_rank   — integer popularity rank")
        print("  salt_score    — float saltiness score")


if __name__ == "__main__":
    main()
