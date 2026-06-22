from __future__ import annotations
from arsenal.cards.classifier import classify_card


def test_etb_trigger_classified():
    card = {"oracle_text": "When this creature enters the battlefield, draw a card."}
    clusters = classify_card(card)
    assert "ETB" in clusters


def test_flying_classified():
    card = {"oracle_text": "Flying\nThis creature has flying."}
    clusters = classify_card(card)
    assert "Flying" in clusters


def test_empty_text_returns_empty():
    card = {"oracle_text": ""}
    clusters = classify_card(card)
    assert isinstance(clusters, list)
