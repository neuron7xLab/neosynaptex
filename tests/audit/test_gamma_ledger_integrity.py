"""Deterministic tests for the γ-ledger integrity gate."""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.audit.gamma_ledger_integrity import (
    ALLOWED_STATUSES,
    METHOD_TIER_REGEX,
    REQUIRED_ENTRY_KEYS,
    IntegrityError,
    load_ledger,
    run_check,
)

_VALID_ENTRY = {
    "substrate": "test_substrate",
    "description": "synthetic fixture",
    "gamma": 1.0,
    "ci_low": 0.9,
    "ci_high": 1.1,
    "r2": 0.85,
    "n_pairs": 10,
    "p_permutation": 0.02,
    "status": "VALIDATED",
    "tier": "evidential",
    "locked": True,
    "data_source": {"file": "data/test.csv", "sha256": None},
    "adapter_code_hash": None,
    "derivation_method": "test method",
    "method_tier": "T3",
}


def _write_ledger(tmp_path: pathlib.Path, entries: dict) -> pathlib.Path:
    path = tmp_path / "gamma_ledger.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "invariant": "gamma derived only, never assigned",
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_required_keys_covers_core_shape():
    for key in ("gamma", "ci_low", "ci_high", "status", "method_tier", "locked"):
        assert key in REQUIRED_ENTRY_KEYS


def test_allowed_statuses_includes_validated():
    assert "VALIDATED" in ALLOWED_STATUSES


def test_method_tier_regex_matches_t1_through_t5():
    for tier in ("T1", "T2", "T3", "T4", "T5"):
        assert METHOD_TIER_REGEX.match(tier)
    for bad in ("T0", "T6", "T12", "tier5", "T5x"):
        assert not METHOD_TIER_REGEX.match(bad)


# ---------------------------------------------------------------------------
# load_ledger
# ---------------------------------------------------------------------------


def test_load_ledger_missing_raises(tmp_path):
    with pytest.raises(IntegrityError, match="not found"):
        load_ledger(tmp_path / "nope.json")


def test_load_ledger_bad_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json {", encoding="utf-8")
    with pytest.raises(IntegrityError, match="JSON parse error"):
        load_ledger(path)


def test_load_ledger_missing_top_key_raises(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
    with pytest.raises(IntegrityError, match="missing top-level key"):
        load_ledger(path)


def test_load_ledger_entries_not_object_raises(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(
        json.dumps({"version": "1.0", "invariant": "x", "entries": []}),
        encoding="utf-8",
    )
    with pytest.raises(IntegrityError, match="entries.*object"):
        load_ledger(path)


def test_load_ledger_valid_parses(tmp_path):
    ledger = _write_ledger(tmp_path, {"foo": _VALID_ENTRY})
    data = load_ledger(ledger)
    assert "foo" in data["entries"]


# ---------------------------------------------------------------------------
# run_check — valid fixtures
# ---------------------------------------------------------------------------


def test_run_check_passes_on_valid_single_entry(tmp_path):
    path = _write_ledger(tmp_path, {"test_entry": _VALID_ENTRY})
    code, msg = run_check(path)
    assert code == 0, msg
    assert "1 γ-ledger entries" in msg


def test_run_check_passes_with_null_optional_numerics(tmp_path):
    entry = dict(_VALID_ENTRY, r2=None, n_pairs=None, p_permutation=None)
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 0, msg


# ---------------------------------------------------------------------------
# run_check — integrity violations
# ---------------------------------------------------------------------------


def test_run_check_fails_on_ci_envelope_violation(tmp_path):
    entry = dict(_VALID_ENTRY, gamma=0.5, ci_low=0.9, ci_high=1.1)
    path = _write_ledger(tmp_path, {"bad": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "CI envelope violation" in msg


def test_run_check_fails_on_negative_ci_low(tmp_path):
    entry = dict(_VALID_ENTRY, gamma=0.5, ci_low=-0.1, ci_high=1.1)
    path = _write_ledger(tmp_path, {"neg": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "ci_low" in msg and "> 0" in msg


def test_run_check_fails_on_non_numeric_gamma(tmp_path):
    entry = dict(_VALID_ENTRY, gamma="one point zero")
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "must be numeric" in msg


def test_run_check_fails_on_missing_required_key(tmp_path):
    entry = {k: v for k, v in _VALID_ENTRY.items() if k != "status"}
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "missing keys" in msg and "status" in msg


def test_run_check_fails_on_unknown_status(tmp_path):
    entry = dict(_VALID_ENTRY, status="MAYBE")
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "status 'MAYBE'" in msg


def test_run_check_fails_on_bad_method_tier(tmp_path):
    entry = dict(_VALID_ENTRY, method_tier="T6")
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "method_tier" in msg and "'T6'" in msg


def test_run_check_fails_on_non_bool_locked(tmp_path):
    entry = dict(_VALID_ENTRY, locked="yes")
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "locked" in msg


def test_run_check_fails_on_data_source_missing_keys(tmp_path):
    entry = dict(_VALID_ENTRY, data_source={"file": "x.csv"})
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "data_source missing key" in msg


def test_run_check_fails_on_non_numeric_optional_field(tmp_path):
    entry = dict(_VALID_ENTRY, r2="zero point eight five")
    path = _write_ledger(tmp_path, {"e": entry})
    code, msg = run_check(path)
    assert code == 2
    assert "r2" in msg and "must be numeric or null" in msg


# ---------------------------------------------------------------------------
# Live repo invariant
# ---------------------------------------------------------------------------


def test_repo_canonical_gamma_ledger_passes_integrity():
    code, msg = run_check()
    assert code == 0, msg
