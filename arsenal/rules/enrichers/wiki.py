"""Fetch key MTG wiki pages and append community context to section chunk files.

Uses the MediaWiki ?action=raw endpoint to get clean wikitext, then converts
it to readable markdown and appends it under a "Community Context" heading.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx

from arsenal.rules.generate_chunks import CHUNKS_DIR

# Each entry: (section_number, topic_label, wiki_page_slug)
WIKI_TOPICS: list[tuple[int, str, str]] = [
    (4,  "Graveyard",              "Graveyard"),
    (5,  "Turn",                   "Turn"),
    (5,  "Combat Phase",           "Combat_phase"),
    (6,  "Stack",                  "Stack"),
    (6,  "Priority",               "Priority"),
    (6,  "Triggered Ability",      "Triggered_ability"),
    (6,  "Activated Ability",      "Activated_ability"),
    (6,  "Static Ability",         "Static_ability"),
    (6,  "Replacement Effect",     "Replacement_effect"),
    (6,  "Layer System",           "Layer"),
    (7,  "State-Based Actions",    "State-based_action"),
]

_WIKI_RAW = "https://mtg.fandom.com/wiki/{}?action=raw"
_REQUEST_DELAY = 0.4  # seconds between requests


def _fetch_wikitext(slug: str) -> str | None:
    url = _WIKI_RAW.format(slug)
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        print(f"    WARNING: failed to fetch {url}: {e}")
        return None


# --- wikitext → markdown conversion ---

_TEMPLATE_RE = re.compile(r"\{\{[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)?\}\}", re.DOTALL)
_FILE_LINK_RE = re.compile(r"\[\[(?:File|Image):[^\]]+\]\]", re.IGNORECASE)
_CATEGORY_RE = re.compile(r"\[\[Category:[^\]]+\]\]", re.IGNORECASE)
_PIPE_LINK_RE = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")
_SIMPLE_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_EXT_LINK_RE = re.compile(r"\[https?://\S+ ([^\]]+)\]")
_BOLD_ITALIC_RE = re.compile(r"'{5}(.+?)'{5}")
_BOLD_RE = re.compile(r"'{3}(.+?)'{3}")
_ITALIC_RE = re.compile(r"'{2}(.+?)'{2}")
_H4_RE = re.compile(r"^====(.+?)====\s*$", re.MULTILINE)
_H3_RE = re.compile(r"^===(.+?)===\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^==(.+?)==\s*$", re.MULTILINE)
_REF_RE = re.compile(r"<ref[^>]*>.*?</ref>", re.DOTALL | re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_INDENT_RE = re.compile(r"^[:;]+", re.MULTILINE)
_BULLETS_RE = re.compile(r"^\*+\s*", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^#+\s*", re.MULTILINE)
_BLANK_RUNS_RE = re.compile(r"\n{3,}")


def _wikitext_to_markdown(raw: str) -> str:
    # Remove references and HTML tags early
    text = _REF_RE.sub("", raw)
    text = _HTML_TAG_RE.sub("", text)

    # Remove boilerplate sections that add no value
    for stop_heading in ("==References==", "==See also==", "==External links==",
                         "==Gallery==", "==Rulings=="):
        idx = text.find(stop_heading)
        if idx != -1:
            text = text[:idx]

    # Remove templates (multi-pass for nested)
    for _ in range(4):
        text = _TEMPLATE_RE.sub("", text)

    text = _FILE_LINK_RE.sub("", text)
    text = _CATEGORY_RE.sub("", text)

    # Convert links
    text = _PIPE_LINK_RE.sub(r"\2", text)
    text = _SIMPLE_LINK_RE.sub(r"\1", text)
    text = _EXT_LINK_RE.sub(r"\1", text)

    # Convert emphasis
    text = _BOLD_ITALIC_RE.sub(r"**_\1_**", text)
    text = _BOLD_RE.sub(r"**\1**", text)
    text = _ITALIC_RE.sub(r"_\1_", text)

    # Convert headings (bump down one level so they nest under ##)
    text = _H4_RE.sub(r"##### \1", text)
    text = _H3_RE.sub(r"#### \1", text)
    text = _H2_RE.sub(r"### \1", text)

    # Convert list markers
    text = _INDENT_RE.sub("", text)
    text = _BULLETS_RE.sub("- ", text)
    text = _NUMBERED_RE.sub("1. ", text)

    # Clean up blank lines
    text = _BLANK_RUNS_RE.sub("\n\n", text)

    return text.strip()


def _section_chunk_path(section_num: int) -> Path | None:
    for p in CHUNKS_DIR.glob(f"{section_num:02d}_*.md"):
        return p
    return None


def enrich_with_wiki(force: bool = False) -> None:
    if not CHUNKS_DIR.exists():
        raise RuntimeError(f"Chunks directory not found: {CHUNKS_DIR}. Run generate_chunks first.")

    for section_num, topic_label, slug in WIKI_TOPICS:
        chunk_path = _section_chunk_path(section_num)
        if not chunk_path:
            print(f"  SKIP {topic_label}: no chunk file for section {section_num}")
            continue

        existing = chunk_path.read_text(encoding="utf-8")

        anchor = f"<!-- wiki:{slug} -->"
        if anchor in existing and not force:
            print(f"  SKIP {topic_label}: already enriched")
            continue

        print(f"  Fetching wiki: {topic_label} ({slug})...")
        wikitext = _fetch_wikitext(slug)
        time.sleep(_REQUEST_DELAY)

        if not wikitext:
            print(f"  SKIP {topic_label}: fetch failed")
            continue

        md = _wikitext_to_markdown(wikitext)
        if len(md) < 100:
            print(f"  SKIP {topic_label}: content too short after conversion")
            continue

        # Trim to a reasonable length — first ~4000 chars keeps the intro + key sections
        if len(md) > 4000:
            md = md[:4000].rsplit("\n", 1)[0] + "\n\n_[truncated]_"

        section_block = (
            f"\n\n{anchor}\n"
            f"### {topic_label} — Community Context\n\n"
            f"{md}\n"
        )

        if anchor in existing:
            # Replace existing block
            start = existing.index(anchor)
            end = existing.find("\n<!-- wiki:", start + 1)
            if end == -1:
                end = len(existing)
            chunk_path.write_text(existing[:start] + section_block + existing[end:], encoding="utf-8")
        else:
            with open(chunk_path, "a", encoding="utf-8") as f:
                f.write(section_block)

        print(f"  OK {topic_label} → {chunk_path.name}")
