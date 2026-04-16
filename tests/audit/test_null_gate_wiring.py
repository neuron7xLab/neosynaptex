"""Mandatory-gate semantics for the null-family screening tool.

Covers three regressions simultaneously:

1. The null-family gate must be registered in the Auditor's ``TOOLS``
   registry (previously absent, which let global audits pass without
   the falsification budget check).
2. Mandatory tools must FAIL closed when their module is missing, their
   cache is absent, or they return a non-zero exit code. The old
   ``ToolVerdict.ok`` treated every skip as a pass.
3. The gate itself must read the on-disk verdict and fail on anything
   other than ``NULL_FAMILY_SELECTED``.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tools.adversarial.auditor import (
    TOOLS,
    AuditorTool,
    ToolVerdict,
    run_all,
)
from tools.audit import null_family_gate

# --------------------------------------------------------------------------
# TOOLS registry wiring
# --------------------------------------------------------------------------


def test_null_family_gate_is_registered_and_mandatory() -> None:
    names = [t.name for t in TOOLS]
    assert "null_family_gate" in names
    gate = next(t for t in TOOLS if t.name == "null_family_gate")
    assert gate.mandatory is True
    assert gate.module_path == "tools.audit.null_family_gate"


def test_measurement_contract_verifier_is_mandatory() -> None:
    verifier = next(t for t in TOOLS if t.name == "measurement_contract_verifier")
    assert verifier.mandatory is True


# --------------------------------------------------------------------------
# ToolVerdict.ok mandatory/skip semantics
# --------------------------------------------------------------------------


def test_mandatory_skip_is_not_ok() -> None:
    v = ToolVerdict(
        name="x", exit_code=0, duration_ms=0.0, message="skipped", skipped=True, mandatory=True
    )
    assert v.ok is False


def test_optional_skip_is_ok() -> None:
    v = ToolVerdict(
        name="x", exit_code=0, duration_ms=0.0, message="skipped", skipped=True, mandatory=False
    )
    assert v.ok is True


def test_nonzero_exit_fails_regardless_of_mandatory() -> None:
    for mandatory in (True, False):
        v = ToolVerdict(
            name="x",
            exit_code=2,
            duration_ms=0.0,
            message="bad",
            skipped=False,
            mandatory=mandatory,
        )
        assert v.ok is False


# --------------------------------------------------------------------------
# Gate behaviour under different cached verdicts
# --------------------------------------------------------------------------


def _write_verdict(path: pathlib.Path, verdict: str, **extra: object) -> None:
    payload: dict[str, object] = {"VERDICT": verdict, "chosen_family": None}
    payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_gate_passes_on_null_family_selected(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cache.json"
    _write_verdict(path, "NULL_FAMILY_SELECTED", chosen_family="AR(1)-IAAFT")
    monkeypatch.setenv(null_family_gate.RESULTS_JSON_ENV, str(path))
    exit_code, message = null_family_gate.run_check()
    assert exit_code == 0
    assert "admissible null selected" in message


def test_gate_fails_on_no_admissible_null_found(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cache.json"
    _write_verdict(path, "NO_ADMISSIBLE_NULL_FOUND")
    monkeypatch.setenv(null_family_gate.RESULTS_JSON_ENV, str(path))
    exit_code, message = null_family_gate.run_check()
    assert exit_code == 2
    assert "NO_ADMISSIBLE_NULL_FOUND" in message


def test_gate_fails_when_cache_missing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setenv(null_family_gate.RESULTS_JSON_ENV, str(missing))
    exit_code, message = null_family_gate.run_check()
    assert exit_code == 2
    assert "cache absent" in message


def test_gate_fails_on_malformed_cache(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv(null_family_gate.RESULTS_JSON_ENV, str(bad))
    exit_code, message = null_family_gate.run_check()
    assert exit_code == 2
    assert "unreadable or malformed" in message


def test_gate_fails_when_verdict_missing(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"chosen_family": None}), encoding="utf-8")
    monkeypatch.setenv(null_family_gate.RESULTS_JSON_ENV, str(path))
    exit_code, message = null_family_gate.run_check()
    assert exit_code == 2
    assert "no VERDICT field" in message


# --------------------------------------------------------------------------
# Aggregate ``run_all`` behaviour with the gate wired mandatory
# --------------------------------------------------------------------------


def test_run_all_fails_when_mandatory_module_unimportable() -> None:
    fake = AuditorTool(
        name="phantom",
        module_path="tools.audit.definitely_does_not_exist",
        mandatory=True,
    )
    report = run_all(tools=(fake,))
    assert report.ok is False
    # Exactly one verdict, not skipped, non-zero exit_code.
    (v,) = report.verdicts
    assert v.skipped is False
    assert v.mandatory is True
    assert v.exit_code != 0
