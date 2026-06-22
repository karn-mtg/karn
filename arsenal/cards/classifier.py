import re

from arsenal.cards.config import MECHANIC_CLUSTERS, TRIBE_SUBTYPES

_REMINDER_RE = re.compile(r"\([^)]+\)")
_COMPILED_CLUSTERS: dict[str, list[re.Pattern]] = {
    name: [re.compile(p, re.IGNORECASE) for p in patterns]
    for name, patterns in MECHANIC_CLUSTERS.items()
    if patterns
}


def strip_reminder_text(text: str) -> str:
    return _REMINDER_RE.sub("", text)


def classify_card(card: dict) -> list[str]:
    oracle = strip_reminder_text(card.get("oracle_text", "") or "")
    type_line = card.get("type_line", "") or ""
    scryfall_keywords = card.get("keywords", []) or []

    search_text = f"{oracle} {type_line} {' '.join(scryfall_keywords)}".lower()

    clusters: list[str] = []

    for cluster_name, patterns in _COMPILED_CLUSTERS.items():
        for pat in patterns:
            if pat.search(search_text):
                clusters.append(cluster_name)
                break

    # Tribal: check subtype words in the type_line
    type_words = set(type_line.split())
    if type_words & TRIBE_SUBTYPES:
        clusters.append("Tribal")

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for c in clusters:
        if c not in seen:
            seen.add(c)
            result.append(c)

    return result
