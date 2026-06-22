from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

RULES_URL = "https://media.wizards.com/2026/downloads/MagicCompRules%2020260417.txt"

DATA_DIR = Path(os.environ.get("KARN_DATA_DIR") or Path(__file__).parent / "data")
RULES_TXT = DATA_DIR / "rules.txt"
RULES_JSON = DATA_DIR / "rules.json"
GLOSSARY_JSON = DATA_DIR / "glossary.json"

_SECTION_HEADERS = {
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

_RULE_ID_RE = re.compile(r"^(\d{3}(?:\.\d+[a-kmnp-z]?)?)\.?\s+(.+)$")
_SUBRULE_RE = re.compile(r"^\d{3}\.\d+[a-kmnp-z]$")
_CHILD_RE = re.compile(r"^\d{3}\.\d+$")
_TOP_RE = re.compile(r"^\d{3}$")


def _section_for(rule_id: str) -> int:
    return int(rule_id[:1])


def _parent_of(rule_id: str) -> str | None:
    if _SUBRULE_RE.match(rule_id):
        return re.sub(r"[a-kmnp-z]$", "", rule_id)
    if _CHILD_RE.match(rule_id):
        return rule_id.split(".")[0]
    return None


def download_rules(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RULES_TXT.exists() and not force:
        return RULES_TXT
    print(f"  Downloading rules from {RULES_URL}...")
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(RULES_URL)
        resp.raise_for_status()
    RULES_TXT.write_bytes(resp.content)
    print(f"  Saved {len(resp.content):,} bytes to {RULES_TXT}")
    return RULES_TXT


def parse_rules(txt_path_or_text: Path | str) -> tuple[dict, dict]:
    if isinstance(txt_path_or_text, str):
        raw = txt_path_or_text
    else:
        content = txt_path_or_text.read_bytes()
        # Wizards CDN serves rules.txt as UTF-16 LE with BOM; fall back to UTF-8
        if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
            raw = content.decode("utf-16")
        else:
            raw = content.decode("utf-8-sig", errors="replace")
    lines = raw.splitlines()

    rules: dict[str, dict] = {}
    glossary: dict[str, str] = {}

    in_glossary = False
    current_term: str | None = None
    current_def_lines: list[str] = []

    # pending examples for the last rule we saw
    last_rule_id: str | None = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Glossary handler runs first so it can see blank-line entry separators.
        if in_glossary:
            raw_line = lines[i].rstrip()
            if not raw_line.strip():
                if current_term and current_def_lines:
                    glossary[current_term] = " ".join(current_def_lines).strip()
                current_term = None
                current_def_lines = []
                i += 1
                continue
            if current_term is None:
                current_term = raw_line.strip()
                current_def_lines = []
            else:
                current_def_lines.append(raw_line.strip())
            i += 1
            continue

        if not line:
            i += 1
            continue

        # Detect glossary section — guard against the TOC "Glossary" entry.
        # The TOC only has top-level entries ("100", "702") with no dots; the
        # real rules body always contains subrules ("100.1", "702.19a") first.
        if re.match(r"^Glossary\s*$", line, re.IGNORECASE) and any("." in rid for rid in rules):
            in_glossary = True
            i += 1
            continue

        # Example lines
        if line.startswith("Example:"):
            if last_rule_id and last_rule_id in rules:
                rules[last_rule_id]["examples"].append(line)
            i += 1
            continue

        m = _RULE_ID_RE.match(line)
        if not m:
            i += 1
            continue

        rule_id = m.group(1)
        text = m.group(2).strip()

        # Skip section header lines like "100. General" — the number ends with a dot
        # but has no dot in the id itself at the top 3-digit level when followed
        # by a section title only. We still want them as section-level entries.
        section = _section_for(rule_id)
        section_name = _SECTION_HEADERS.get(section, "")
        parent = _parent_of(rule_id)

        entry: dict = {
            "id": rule_id,
            "text": text,
            "parent": parent,
            "children": [],
            "section": section,
            "section_name": section_name,
            "examples": [],
        }
        rules[rule_id] = entry
        last_rule_id = rule_id

        # Register as child of parent
        if parent and parent in rules:
            if rule_id not in rules[parent]["children"]:
                rules[parent]["children"].append(rule_id)

        i += 1

    # Flush last glossary entry
    if current_term and current_def_lines:
        glossary[current_term] = " ".join(current_def_lines).strip()

    return rules, glossary


def build_parsed_artifacts(force_download: bool = False) -> tuple[dict, dict]:
    txt_path = download_rules(force=force_download)
    rules, glossary = parse_rules(txt_path)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RULES_JSON, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False)
    with open(GLOSSARY_JSON, "w", encoding="utf-8") as f:
        json.dump(glossary, f, ensure_ascii=False)

    return rules, glossary


def load_rules() -> dict:
    if not RULES_JSON.exists():
        raise FileNotFoundError(f"Rules index not found at {RULES_JSON}. Run build_rules.py first.")
    with open(RULES_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_glossary() -> dict:
    if not GLOSSARY_JSON.exists():
        raise FileNotFoundError(f"Glossary not found at {GLOSSARY_JSON}. Run build_rules.py first.")
    with open(GLOSSARY_JSON, encoding="utf-8") as f:
        return json.load(f)
