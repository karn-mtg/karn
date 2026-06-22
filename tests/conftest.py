from __future__ import annotations
import pytest


@pytest.fixture(scope="session")
def sample_rules() -> dict:
    return {
        "702": {
            "id": "702", "text": "Keyword Abilities", "section": 7,
            "children": ["702.19"], "examples": [], "parent": None,
        },
        "702.19": {
            "id": "702.19", "text": "Flying. A creature with flying can only be blocked by creatures with flying or reach.",
            "section": 7, "children": ["702.19a"], "examples": ["Example: Aven Windreader has flying."], "parent": "702",
        },
        "702.19a": {
            "id": "702.19a", "text": "Flying is an evasion ability.",
            "section": 7, "children": [], "examples": [], "parent": "702.19",
        },
    }


@pytest.fixture(scope="session")
def sample_glossary() -> dict:
    return {
        "Flying": "Flying is an evasion ability. A creature with flying can only be blocked by creatures with flying or reach.",
        "Trample": "Trample is a static ability that modifies the rules for assigning combat damage.",
    }
