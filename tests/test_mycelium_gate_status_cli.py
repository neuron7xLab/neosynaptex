"""Tests for tools/audit/mycelium_gate_status.py CLI.

Numbered tests:
1. ``build_gate_status_document`` returns the locked Gate 0 verdict.
2. Output document is strict-JSON serialisable with ``allow_nan=False``.
3. CLI ``--out`` writes a strict-JSON file.
4. CLI without ``--out`` writes to stdout.
5. Output contains no ``NaN``, ``Infinity``, or ``-Infinity`` tokens.
6. Output ``substrate`` is ``"mycelium"``, ``gate`` is ``"GAMMA_GATE_0"``.
7. References section points at the method-gate doc, architecture doc,
   and contract module.
8. Exit code is 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.audit.mycelium_gate_status import (  # noqa: E402
    build_gate_status_document,
    main,
)


# 1
def test_build_document_returns_locked_verdict() -> None:
    doc = build_gate_status_document()
    assert doc["verdict"]["claim_status"] == "NO_ADMISSIBLE_CLAIM"
    assert doc["verdict"]["gate_status"] == "BLOCKED_BY_METHOD_DEFINITION"
    assert len(doc["verdict"]["reasons"]) == 6


# 2
def test_document_is_strict_json_serialisable() -> None:
    doc = build_gate_status_document()
    raw = json.dumps(doc, allow_nan=False, sort_keys=True)
    # Round-trip
    assert json.loads(raw) == doc


# 3
def test_cli_writes_strict_json_to_out(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    rc = main(["--out", str(out)])
    assert rc == 0
    raw = out.read_text(encoding="utf-8")
    doc = json.loads(raw)
    assert doc["verdict"]["gate_status"] == "BLOCKED_BY_METHOD_DEFINITION"


# 4
def test_cli_writes_to_stdout(capsys: object) -> None:
    rc = main([])
    assert rc == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    doc = json.loads(captured.out)
    assert doc["verdict"]["claim_status"] == "NO_ADMISSIBLE_CLAIM"


# 5
def test_no_non_finite_tokens(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    main(["--out", str(out)])
    raw = out.read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert "Infinity" not in raw
    assert "-Infinity" not in raw


# 6
def test_substrate_and_gate_labels() -> None:
    doc = build_gate_status_document()
    assert doc["substrate"] == "mycelium"
    assert doc["gate"] == "GAMMA_GATE_0"


# 7
def test_references_section() -> None:
    doc = build_gate_status_document()
    refs = doc["references"]
    assert refs["method_gate_doc"] == "docs/method_gates/MYCELIUM_GAMMA_GATE_0.md"
    assert refs["architecture_doc"] == "docs/architecture/recursive_claim_refinement.md"
    assert refs["contract_module"] == "contracts.mycelium_pre_admission"


# 8
def test_exit_code_is_zero(tmp_path: Path) -> None:
    out = tmp_path / "evidence.json"
    assert main(["--out", str(out)]) == 0
    assert main([]) == 0


def test_reasons_count_matches_six_falsifiability_rows() -> None:
    """Reasons list length must equal 6 — the §4 falsifiability rows."""
    doc = build_gate_status_document()
    assert len(doc["verdict"]["reasons"]) == 6


def test_reasons_are_strings() -> None:
    doc = build_gate_status_document()
    for r in doc["verdict"]["reasons"]:
        assert isinstance(r, str)
        assert r.isupper() or "_" in r
