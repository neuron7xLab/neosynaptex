"""Tests for formal/falsification_protocol.py — 14 tests covering all conditions."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from formal.falsification_protocol import (
    FalsificationProtocol,
    FalsificationReport,
)

LEDGER_PATH = Path(__file__).resolve().parent.parent / "evidence" / "gamma_ledger.json"


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def protocol() -> FalsificationProtocol:
    return FalsificationProtocol(ledger_path=LEDGER_PATH)


@pytest.fixture()
def report(protocol: FalsificationProtocol) -> FalsificationReport:
    return protocol.evaluate_all()


def _make_ledger(entries: dict[str, dict[str, object]]) -> Path:
    """Write a temporary ledger and return its path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump({"version": "1.0.0", "entries": entries}, tmp)
        tmp.flush()
        return Path(tmp.name)


# ── Structural tests ───────────────────────────────────────────────────


def test_conditions_count() -> None:
    conds = FalsificationProtocol.conditions()
    assert len(conds) >= 8


def test_conditions_ids() -> None:
    conds = FalsificationProtocol.conditions()
    ids = {c.id for c in conds}
    for fid in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
        assert fid in ids, f"Missing condition {fid}"


def test_condition_is_frozen() -> None:
    cond = FalsificationProtocol.conditions()[0]
    with pytest.raises(AttributeError):
        cond.id = "X"  # type: ignore[misc]


def test_all_fields_non_empty() -> None:
    for cond in FalsificationProtocol.conditions():
        assert cond.id
        assert cond.description
        assert cond.test_procedure
        assert cond.threshold


# ── Evaluation tests ───────────────────────────────────────────────────


def test_evaluate_all_runs(report: FalsificationReport) -> None:
    assert isinstance(report, FalsificationReport)
    assert len(report.conditions) >= 8


def test_evaluate_all_counts(report: FalsificationReport) -> None:
    total = report.n_falsified + report.n_partial + report.n_not_falsified
    assert total == len(report.conditions)


def test_verdict_valid(report: FalsificationReport) -> None:
    assert report.verdict in {"SURVIVES", "WEAKENED", "FALSIFIED"}


def test_every_condition_has_evidence(report: FalsificationReport) -> None:
    for cond in report.conditions:
        assert cond.evidence, f"{cond.id} has empty evidence"


def test_every_condition_has_valid_status(report: FalsificationReport) -> None:
    valid = {"NOT_FALSIFIED", "PARTIALLY_FALSIFIED", "FALSIFIED"}
    for cond in report.conditions:
        assert cond.current_status in valid, f"{cond.id}: {cond.current_status}"


# ── Markdown report tests ──────────────────────────────────────────────


def test_report_markdown_non_empty(protocol: FalsificationProtocol) -> None:
    md = protocol.report_markdown()
    assert len(md) > 100


def test_report_markdown_contains_all_ids(protocol: FalsificationProtocol) -> None:
    md = protocol.report_markdown()
    for fid in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
        assert fid in md, f"Markdown missing {fid}"


# ── Synthetic falsification scenarios ──────────────────────────────────


def test_f1_falsified_single_category() -> None:
    """If all substrates share one category, F1 should be FALSIFIED."""
    entries = {
        "only_bio_1": {
            "substrate": "zebrafish",
            "gamma": 1.0,
            "ci_low": 0.9,
            "ci_high": 1.1,
            "status": "VALIDATED",
        },
        "only_bio_2": {
            "substrate": "zebrafish",
            "gamma": 0.95,
            "ci_low": 0.85,
            "ci_high": 1.05,
            "status": "VALIDATED",
        },
    }
    path = _make_ledger(entries)
    proto = FalsificationProtocol(ledger_path=path)
    rep = proto.evaluate_all()
    f1 = next(c for c in rep.conditions if c.id == "F1")
    assert f1.current_status == "FALSIFIED"


def test_f8_falsified_zero_gamma() -> None:
    """A validated entry with γ ≤ 0 should trigger F8 FALSIFIED."""
    entries = {
        "bad_entry": {
            "substrate": "zebrafish",
            "gamma": 0.0,
            "ci_low": -0.1,
            "ci_high": 0.1,
            "status": "VALIDATED",
        },
    }
    path = _make_ledger(entries)
    proto = FalsificationProtocol(ledger_path=path)
    rep = proto.evaluate_all()
    f8 = next(c for c in rep.conditions if c.id == "F8")
    assert f8.current_status == "FALSIFIED"


def test_falsified_verdict_triggers() -> None:
    """Any FALSIFIED condition should give verdict=FALSIFIED."""
    entries = {
        "zero_gamma": {
            "substrate": "zebrafish",
            "gamma": -1.0,
            "ci_low": -2.0,
            "ci_high": 0.0,
            "status": "VALIDATED",
        },
    }
    path = _make_ledger(entries)
    proto = FalsificationProtocol(ledger_path=path)
    rep = proto.evaluate_all()
    assert rep.verdict == "FALSIFIED"
