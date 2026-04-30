"""Phase 4a — adversarial tests for tools.audit.horizon_trace_lint.

Each test constructs a minimal contract dict (or modifies a baseline)
and asserts that the lint either passes (returns empty list) or
catches the specific fail-closed violation.

Numbered tests:
1.  Real ``serotonergic_kuramoto`` contract → admissible (0 violations).
2.  Missing ``claim_boundary`` block → REJECTED.
3.  ``hidden_core_is_evidence: true`` → REJECTED.
4.  ``boundary_trace_required: false`` → REJECTED.
5.  ``ledger_mutation_allowed: true`` → REJECTED.
6.  ``gamma_promotion_allowed: true`` → REJECTED.
7.  Observable missing ``expected_null_behavior`` → REJECTED.
8.  Observable structural field empty (``definition: ""``) → REJECTED.
9.  Observable interpretive field null (``boundary_meaning: null``) →
    REJECTED.
10. Observable list field null (``failure_modes: null``) → REJECTED.
11. ``coordinates`` block empty → REJECTED.
12. ``forbidden_claims`` missing → REJECTED.
13. ``forbidden_claims: []`` → REJECTED.
14. CLI invocation on the real contract returns exit 0.
"""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.audit.horizon_trace_lint import (
    REQUIRED_OBSERVABLE_FIELDS,
    LintViolation,
    lint_contract,
    lint_contract_path,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_CONTRACT_PATH = (
    _REPO_ROOT / "substrates" / "serotonergic_kuramoto" / "horizon_trace_contract.yaml"
)


def _baseline_contract() -> dict[str, Any]:
    """Build a minimal admissible contract for adversarial mutation."""
    return {
        "substrate": "synthetic_for_lint",
        "phase": "4a",
        "claim_boundary": {
            "hidden_core_is_evidence": False,
            "boundary_trace_required": True,
            "ledger_mutation_allowed": False,
            "gamma_promotion_allowed": False,
        },
        "observables": {
            "x": {
                "status": "ADMISSIBLE_TRACE",
                "source_path": "tests/_dummy.py",
                "code_symbol": "Dummy.x",
                "definition": "constant 1.0 for testing",
                "units_or_scale": "dimensionless",
                "boundary_meaning": "TODO_OR_FOUND",
                "expected_null_behavior": "TODO_OR_FOUND",
                "failure_modes": [],
                "falsifiers": [],
            }
        },
        "coordinates": {
            "raw_c": {
                "status": "SUSPECT",
                "reason": "test baseline",
                "required_tests": [],
            }
        },
        "forbidden_claims": ["test forbidden"],
    }


def _rules(violations: list[LintViolation]) -> set[str]:
    return {v.rule for v in violations}


# 1
def test_real_contract_is_admissible() -> None:
    assert _REAL_CONTRACT_PATH.is_file()
    violations = lint_contract_path(_REAL_CONTRACT_PATH)
    assert not violations, "real contract must be admissible at Phase 4a:\n" + "\n".join(
        str(v) for v in violations
    )


# 2
def test_missing_claim_boundary_rejected() -> None:
    c = _baseline_contract()
    del c["claim_boundary"]
    rules = _rules(lint_contract(c))
    assert "missing_claim_boundary" in rules


# 3
def test_hidden_core_claimed_as_evidence_rejected() -> None:
    c = _baseline_contract()
    c["claim_boundary"]["hidden_core_is_evidence"] = True
    rules = _rules(lint_contract(c))
    assert "hidden_core_claimed_as_evidence" in rules


# 4
def test_boundary_trace_not_required_rejected() -> None:
    c = _baseline_contract()
    c["claim_boundary"]["boundary_trace_required"] = False
    rules = _rules(lint_contract(c))
    assert "boundary_trace_not_required" in rules


# 5
def test_ledger_mutation_allowed_rejected() -> None:
    c = _baseline_contract()
    c["claim_boundary"]["ledger_mutation_allowed"] = True
    rules = _rules(lint_contract(c))
    assert "ledger_mutation_allowed" in rules


# 6
def test_gamma_promotion_allowed_rejected() -> None:
    c = _baseline_contract()
    c["claim_boundary"]["gamma_promotion_allowed"] = True
    rules = _rules(lint_contract(c))
    assert "gamma_promotion_allowed" in rules


# 7
def test_observable_missing_field_rejected() -> None:
    c = _baseline_contract()
    del c["observables"]["x"]["expected_null_behavior"]
    rules = _rules(lint_contract(c))
    assert "observable_field_missing" in rules


# 8
@pytest.mark.parametrize(
    "field", ["status", "source_path", "code_symbol", "definition", "units_or_scale"]
)
def test_observable_structural_field_empty_rejected(field: str) -> None:
    c = _baseline_contract()
    c["observables"]["x"][field] = ""
    rules = _rules(lint_contract(c))
    assert "observable_field_empty" in rules


# 9
@pytest.mark.parametrize("field", ["boundary_meaning", "expected_null_behavior"])
def test_observable_interpretive_field_null_rejected(field: str) -> None:
    c = _baseline_contract()
    c["observables"]["x"][field] = None
    rules = _rules(lint_contract(c))
    assert "observable_interpretive_null" in rules


# 10
@pytest.mark.parametrize("field", ["failure_modes", "falsifiers"])
def test_observable_list_field_null_rejected(field: str) -> None:
    c = _baseline_contract()
    c["observables"]["x"][field] = None
    rules = _rules(lint_contract(c))
    assert "observable_list_field_null" in rules


# 11
def test_coordinates_empty_rejected() -> None:
    c = _baseline_contract()
    c["coordinates"] = {}
    rules = _rules(lint_contract(c))
    assert "missing_coordinates" in rules


# 12
def test_forbidden_claims_missing_rejected() -> None:
    c = _baseline_contract()
    del c["forbidden_claims"]
    rules = _rules(lint_contract(c))
    assert "missing_forbidden_claims" in rules


# 13
def test_forbidden_claims_empty_rejected() -> None:
    c = _baseline_contract()
    c["forbidden_claims"] = []
    rules = _rules(lint_contract(c))
    assert "forbidden_claims_empty" in rules


# 14
def test_cli_invocation_on_real_contract_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "tools.audit.horizon_trace_lint", str(_REAL_CONTRACT_PATH)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"CLI exit {proc.returncode}; stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )


# Sanity: required-fields tuple is what the test suite expects.
def test_required_fields_tuple_is_canonical() -> None:
    expected = (
        "status",
        "source_path",
        "code_symbol",
        "definition",
        "units_or_scale",
        "boundary_meaning",
        "expected_null_behavior",
        "failure_modes",
        "falsifiers",
    )
    assert expected == REQUIRED_OBSERVABLE_FIELDS


# Sanity: baseline contract is itself admissible (catches accidental
# regressions in _baseline_contract).
def test_baseline_contract_is_admissible() -> None:
    violations = lint_contract(copy.deepcopy(_baseline_contract()))
    assert not violations, (
        "baseline contract used by adversarial tests must itself be "
        f"admissible:\n{[str(v) for v in violations]}"
    )
