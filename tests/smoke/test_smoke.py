def test_server_imports_cleanly():
    from arsenal.server import mcp
    assert mcp is not None


def test_exactly_16_tools():
    from arsenal.server import mcp
    tool_names = list(mcp._tool_manager._tools.keys())
    assert len(tool_names) == 16, f"Expected 16 tools, got {len(tool_names)}: {tool_names}"


def test_all_expected_tools_present():
    from arsenal.server import mcp
    tools = set(mcp._tool_manager._tools.keys())
    expected = {
        "search_cards", "traverse_graph", "get_combos", "get_similar",
        "get_card", "get_card_prints", "search_cards_in_set",
        "get_rule", "search_rules", "get_section", "get_glossary",
        "get_related_rules", "get_rules_primer",
        "get_health", "check_updates", "update_component",
    }
    assert tools == expected, f"Tool mismatch. Extra: {tools - expected}, Missing: {expected - tools}"


def test_cards_package_importable():
    from arsenal.cards.config import MECHANIC_CLUSTERS, CHROMA_COLLECTION
    assert "ETB" in MECHANIC_CLUSTERS
    assert CHROMA_COLLECTION == "mtg_cards"


def test_rules_package_importable():
    from arsenal.rules.parser import parse_rules
    assert callable(parse_rules)
