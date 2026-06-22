from __future__ import annotations
import pytest
from unittest.mock import patch
from arsenal.rules.search import search_rules


SAMPLE_RULES = {
    "702.19": {"id": "702.19", "text": "Flying is an evasion ability.", "section_name": "Keywords", "children": [], "examples": []},
    "702.20": {"id": "702.20", "text": "Trample is a static ability.", "section_name": "Keywords", "children": [], "examples": []},
}

SAMPLE_INDEX = {
    "flying": ["702.19"],
    "evasion": ["702.19"],
    "trample": ["702.20"],
    "static": ["702.20"],
    "ability": ["702.19", "702.20"],
}


@pytest.fixture(autouse=True)
def patch_index_and_rules():
    with patch("arsenal.rules.search._keyword_index", SAMPLE_INDEX), \
         patch("arsenal.rules.search._rules_cache", SAMPLE_RULES):
        yield


def test_search_returns_most_relevant_rule():
    results = search_rules("flying evasion ability", top_k=2)
    assert results[0]["id"] == "702.19"


def test_search_empty_query_returns_empty():
    results = search_rules("", top_k=5)
    assert results == []


def test_search_no_matches_returns_empty():
    results = search_rules("zombie graveyard sacrifice", top_k=5)
    assert results == []


def test_search_score_in_zero_one_range():
    results = search_rules("flying", top_k=5)
    for r in results:
        assert 0.0 <= r["score"] <= 1.0
