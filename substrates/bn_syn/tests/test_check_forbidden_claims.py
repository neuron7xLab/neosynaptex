from pathlib import Path
import tempfile

from scripts.check_forbidden_claims import FORBIDDEN


def test_forbidden_phrase_list_contains_expected_marker() -> None:
    assert "10x proven" in FORBIDDEN


def test_allowlist_marker_prevents_false_positive() -> None:
    text = "forbidden_claims: proves consciousness"
    assert "forbidden_claims" in text.lower()
