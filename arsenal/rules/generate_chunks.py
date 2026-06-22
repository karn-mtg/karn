"""Generate per-section markdown chunks from the parsed rules JSON.

Output goes to arsenal/rules/chunks/ which IS committed to the repo.
Re-run this whenever the rules source changes.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_data_env = os.environ.get("KARN_DATA_DIR")
CHUNKS_DIR = (Path(_data_env) if _data_env else Path(__file__).parent) / "chunks"

SECTION_NAMES = {
    1: "Game Concepts",
    2: "Parts of a Card",
    3: "Card Types",
    4: "Zones",
    5: "Turn Structure",
    6: "Spells, Abilities, and Effects",
    7: "Additional Rules",
    8: "Multiplayer Rules",
    9: "Casual Variants",
}

_RULES_SOURCE = "Magic: The Gathering Comprehensive Rules (2026-04-17)"

# Sort key that handles mixed numeric/alpha rule IDs correctly
_PART_RE = re.compile(r"(\d+|[a-z]+)")


def _sort_key(rule_id: str) -> list:
    parts = _PART_RE.findall(rule_id.replace(".", " "))
    return [(0, int(p)) if p.isdigit() else (1, p) for p in parts]


def generate_section_chunks(rules: dict) -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    by_section: dict[int, list[dict]] = {i: [] for i in range(1, 10)}
    for rule in rules.values():
        s = rule.get("section")
        if isinstance(s, int) and s in by_section:
            by_section[s].append(rule)

    for section_num, section_rules in by_section.items():
        section_name = SECTION_NAMES[section_num]
        slug = section_name.lower().replace(",", "").replace(" ", "_")
        path = CHUNKS_DIR / f"{section_num:02d}_{slug}.md"

        section_rules.sort(key=lambda r: _sort_key(r["id"]))

        lines: list[str] = [
            f"# Section {section_num}: {section_name}",
            "",
            f"> {_RULES_SOURCE}",
            "",
        ]

        for rule in section_rules:
            rid = rule["id"]
            text = rule["text"]
            examples = rule.get("examples") or []

            dot_count = rid.count(".")
            trailing_alpha = rid[-1].isalpha() if rid else False

            if dot_count == 0:
                # Top-level rule heading (e.g. 500)
                lines.append(f"## {rid}. {text}")
                lines.append("")
            elif dot_count == 1 and not trailing_alpha:
                # First subrule (e.g. 500.1)
                lines.append(f"**{rid}** {text}")
                for ex in examples:
                    lines.append(f"  > {ex}")
            else:
                # Lettered subrule (e.g. 500.1a)
                lines.append(f"- **{rid}** {text}")
                for ex in examples:
                    lines.append(f"  > {ex}")

        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  {path.name}  ({len(section_rules)} rules)")


def generate_glossary_chunk(glossary: dict) -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHUNKS_DIR / "glossary.md"

    lines: list[str] = [
        "# MTG Official Glossary",
        "",
        f"> {_RULES_SOURCE}",
        "",
    ]
    for term in sorted(glossary, key=str.lower):
        lines.append(f"**{term}**")
        lines.append(glossary[term])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  glossary.md  ({len(glossary)} terms)")


def generate_all(rules: dict, glossary: dict) -> None:
    generate_section_chunks(rules)
    generate_glossary_chunk(glossary)
