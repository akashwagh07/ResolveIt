"""Tests for ontology validation, canonical categories, and alias resolution."""

from backend.app.ontology import ALIASES, CATEGORIES, is_valid_issue, resolve_alias


def test_alias_map_and_resolution():
    assert "ANIMAL_CARCASS" in ALIASES
    cat, iss = resolve_alias("WASTE", "ANIMAL_CARCASS")
    assert cat == "WASTE"
    assert iss == "DEAD_ANIMAL"

    # Direct code normalization
    cat2, iss2 = resolve_alias("waste", "animal-carcass")
    assert cat2 == "WASTE"
    assert iss2 == "DEAD_ANIMAL"

    # Non-alias remains as normalized
    cat3, iss3 = resolve_alias("roads", "pothole")
    assert cat3 == "ROADS"
    assert iss3 == "POTHOLE"


def test_is_valid_issue_with_alias():
    assert is_valid_issue("WASTE", "ANIMAL_CARCASS") is True
    assert is_valid_issue("WASTE", "DEAD_ANIMAL") is True
    assert is_valid_issue("ROADS", "POTHOLE") is True
    assert is_valid_issue("OTHER", "ANYTHING_ELSE") is True
    assert is_valid_issue("INVALID", "ISSUE") is False
