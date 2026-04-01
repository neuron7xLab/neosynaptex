from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARB_RULES_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "02_governance" / "ARB_RULES.md"


def test_arb_rules_contract() -> None:
    text = ARB_RULES_PATH.read_text(encoding="utf-8")
    assert "Quorum: 2" in text
    assert "P0" in text
