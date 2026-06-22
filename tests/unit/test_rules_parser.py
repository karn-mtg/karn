from __future__ import annotations
from arsenal.rules.parser import parse_rules


MINIMAL_RULES_TXT = """\
100. General

100.1. These Magic rules apply to any Magic game.
100.1a The rules text of a card takes precedence over these rules.

Glossary

Flying
Flying is an evasion ability. A creature with flying can only be blocked by creatures with flying or reach.

"""


def test_parse_rules_extracts_top_level_rule():
    rules, _ = parse_rules(MINIMAL_RULES_TXT)
    assert "100.1" in rules


def test_parse_rules_extracts_subrule():
    rules, _ = parse_rules(MINIMAL_RULES_TXT)
    assert "100.1a" in rules


def test_parse_rules_sets_parent():
    rules, _ = parse_rules(MINIMAL_RULES_TXT)
    assert rules["100.1a"]["parent"] == "100.1"


def test_parse_glossary_extracts_flying():
    _, glossary = parse_rules(MINIMAL_RULES_TXT)
    assert "Flying" in glossary
    assert "evasion" in glossary["Flying"].lower()
