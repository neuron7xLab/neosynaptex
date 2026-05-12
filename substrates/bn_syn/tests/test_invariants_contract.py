from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_invariants_have_test_refs_and_bindings() -> None:
    data = yaml.safe_load((ROOT / "invariants.yaml").read_text(encoding="utf-8"))
    invs = data["invariants"]
    test_file = (ROOT / "tests" / "test_regime.py").read_text(encoding="utf-8")

    for inv in invs:
        assert "test_ref" in inv and inv["test_ref"]
        assert f"def {inv['test_ref']}" in test_file
