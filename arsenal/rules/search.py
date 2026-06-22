from __future__ import annotations

import json
import os
import re
from pathlib import Path

DATA_DIR = Path(os.environ.get("KARN_DATA_DIR") or Path(__file__).parent / "data")
KEYWORD_INDEX_PATH = DATA_DIR / "keyword_index.json"

_STOPWORDS = {
    "the", "and", "for", "are", "was", "its", "not", "but", "can", "has",
    "may", "any", "all", "one", "two", "into", "from", "that", "this",
    "with", "have", "been", "they", "each", "when", "then", "than",
}


def build_search_index(rules: dict) -> None:
    """Build the keyword inverted index from parsed rules and write keyword_index.json."""
    index: dict[str, list[str]] = {}
    for rule_id, rule in rules.items():
        words = re.findall(r"[a-z]+", rule["text"].lower())
        for word in set(words):
            if len(word) < 3:
                continue
            if word not in index:
                index[word] = []
            index[word].append(rule_id)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(KEYWORD_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    print(f"  Keyword index: {len(index):,} terms")


_keyword_index: dict[str, list[str]] | None = None
_rules_cache: dict | None = None


def _get_rules_cached() -> dict:
    global _rules_cache
    if _rules_cache is None:
        from arsenal.rules.parser import load_rules
        _rules_cache = load_rules()
    return _rules_cache


def _get_keyword_index() -> dict[str, list[str]]:
    global _keyword_index
    if _keyword_index is None:
        if not KEYWORD_INDEX_PATH.exists():
            raise FileNotFoundError("Keyword index not found. Run build_rules.py first.")
        with open(KEYWORD_INDEX_PATH, encoding="utf-8") as f:
            _keyword_index = json.load(f)
    return _keyword_index


def search_rules(query: str, top_k: int = 5) -> list[dict]:
    """Search rules by keyword query.

    Tokenises the query, counts how many query tokens appear in each rule's
    text, normalises by rule text length to avoid long rules dominating, and
    returns the top_k results sorted by descending score.  Each returned dict
    is the original rule dict with an extra ``score`` field (float, 0–1).
    """
    index = _get_keyword_index()
    words = re.findall(r"[a-z]+", query.lower())
    words = [w for w in words if len(w) >= 3 and w not in _STOPWORDS]

    if not words:
        return []

    # Count how many query tokens hit each rule
    hit_counts: dict[str, int] = {}
    for word in words:
        for rule_id in index.get(word, []):
            hit_counts[rule_id] = hit_counts.get(rule_id, 0) + 1

    if not hit_counts:
        return []

    rules = _get_rules_cached()

    # Normalise: divide raw hit count by the number of words in the rule text
    # (clamped to 1 to avoid division by zero).  Multiply by query coverage
    # (fraction of query words that matched) so rules matching more query
    # terms rank higher than rules that only match one common word many times.
    query_len = max(len(words), 1)
    scored: list[tuple[float, str]] = []
    for rule_id, hits in hit_counts.items():
        if rule_id not in rules:
            continue
        rule_text = rules[rule_id]["text"]
        text_words = max(len(rule_text.split()), 1)
        coverage = hits / query_len          # 0–1: fraction of query covered
        density = hits / text_words          # reward concise, focused rules
        score = coverage * 0.7 + density * 0.3
        scored.append((score, rule_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    results: list[dict] = []
    for score, rule_id in top:
        entry = dict(rules[rule_id])
        entry["score"] = round(score, 4)
        results.append(entry)
    return results
