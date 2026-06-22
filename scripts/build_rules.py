"""
Build the MTG Rules search index and section chunks.

Usage:
    python build_rules.py [--force-download] [--force-reindex] [--force-wiki] [--no-wiki] [--no-embed] [--force-reembed]
"""

import argparse
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MTG rules index and section chunks")
    parser.add_argument("--force-download", action="store_true", help="Re-download rules TXT even if present")
    parser.add_argument("--force-reindex", action="store_true", help="Rebuild the keyword index even if already present")
    parser.add_argument("--force-wiki", action="store_true", help="Re-fetch and replace wiki enrichment")
    parser.add_argument("--no-wiki", action="store_true", help="Skip wiki enrichment step")
    parser.add_argument("--no-embed", action="store_true", help="Skip rules vector DB embedding step")
    parser.add_argument("--force-reembed", action="store_true", help="Force rebuild of rules vector DB")
    args = parser.parse_args()

    t_total = time.time()

    print("[1/5] Downloading and parsing Comprehensive Rules...")
    from arsenal.rules.parser import (
        GLOSSARY_JSON,
        RULES_JSON,
        build_parsed_artifacts,
        load_glossary,
        load_rules,
    )

    if RULES_JSON.exists() and GLOSSARY_JSON.exists() and not args.force_download:
        rules = load_rules()
        glossary = load_glossary()
        print(f"  Using cached artifacts ({len(rules):,} rules, {len(glossary):,} glossary terms)")
    else:
        rules, glossary = build_parsed_artifacts(force_download=args.force_download)
        print(f"  Parsed {len(rules):,} rules, {len(glossary):,} glossary terms")

    print("[2/5] Generating section chunks (arsenal/rules/chunks/)...")
    from arsenal.rules.generate_chunks import CHUNKS_DIR, generate_all

    existing_chunks = list(CHUNKS_DIR.glob("*.md")) if CHUNKS_DIR.exists() else []
    if len(existing_chunks) >= 10 and not args.force_download:
        print(f"  Chunks already present ({len(existing_chunks)} files) — skipping regeneration")
        print("  Use --force-download to regenerate")
    else:
        generate_all(rules, glossary)
        print(f"  Generated {len(list(CHUNKS_DIR.glob('*.md')))} chunk files -> arsenal/rules/chunks/")

    if not args.no_wiki:
        print("[3/5] Enriching chunks with MTG wiki content...")
        from arsenal.rules.enrichers.wiki import WIKI_TOPICS, enrich_with_wiki
        enrich_with_wiki(force=args.force_wiki)
        print(f"  Processed {len(WIKI_TOPICS)} wiki topics")
    else:
        print("[3/5] Skipping wiki enrichment (--no-wiki)")

    print("[4/5] Building keyword search index...")
    from arsenal.rules.search import KEYWORD_INDEX_PATH, build_search_index

    if args.force_reindex and KEYWORD_INDEX_PATH.exists():
        KEYWORD_INDEX_PATH.unlink()
        print("  Cleared existing keyword index")

    build_search_index(rules)

    # Step 5: Embed rules into vector DB
    if "--no-embed" not in sys.argv:
        from arsenal.rules.vectordb import build_rules_vectordb
        from arsenal.cards.config import BASE_DIR
        force_embed = "--force-reembed" in sys.argv
        print("Step 5: Building rules vector DB...")
        build_rules_vectordb(
            rules=rules,
            glossary=glossary,
            db_path=str(BASE_DIR),
            force=force_embed,
        )
        print("  Done.")
    else:
        print("[5/5] Skipping rules vector DB embedding (--no-embed)")

    elapsed = time.time() - t_total
    chunk_count = len(list(CHUNKS_DIR.glob("*.md"))) if CHUNKS_DIR.exists() else 0

    print(f"\n  Build time:     {elapsed:.1f}s")
    print(f"  Rules indexed:  {len(rules):,}")
    print(f"  Glossary terms: {len(glossary):,}")
    print(f"  Chunk files:    {chunk_count}")
    if not args.no_wiki:
        print("\nCommit these files:")
        print("  arsenal/rules/data/rules.json")
        print("  arsenal/rules/data/glossary.json")
        print("  arsenal/rules/data/keyword_index.json")
        print("  arsenal/rules/chunks/*.md")


if __name__ == "__main__":
    main()
