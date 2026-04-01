"""Tests for DiagnosisDiff — temporal diff between diagnostic reports."""

from __future__ import annotations

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.diagnosis import DiagnosisDiff
from mycelium_fractal_net.types.field import SimulationSpec


def _report(seed: int = 42) -> mfn.DiagnosisReport:
    seq = mfn.simulate(SimulationSpec(grid_size=32, steps=60, seed=seed))
    return mfn.diagnose(seq, skip_intervention=True)


def test_diff_same_report_is_stable() -> None:
    r = _report()
    diff = r.diff(r)
    assert isinstance(diff, DiagnosisDiff)
    assert not diff.has_changes
    assert diff.severity_direction == "unchanged"
    assert diff.ews_trend == "stable"
    assert diff.overall_trend == "stable"


def test_diff_different_seeds() -> None:
    r0 = _report(42)
    r1 = _report(99)
    diff = r0.diff(r1)
    assert isinstance(diff, DiagnosisDiff)
    assert isinstance(diff.ews_score_delta, float)
    assert isinstance(diff.overall_trend, str)


def test_diff_to_dict_complete() -> None:
    r = _report()
    d = r.diff(r).to_dict()
    assert "severity" in d
    assert "direction" in d["severity"]
    assert "ews" in d
    assert "trend" in d["ews"]
    assert "overall_trend" in d
    assert "has_changes" in d


def test_diff_summary_format() -> None:
    r = _report()
    s = r.diff(r).summary()
    assert "[DIFF:" in s
    assert "trend=" in s
    assert "overall=" in s


def test_diff_fields_present() -> None:
    r = _report()
    diff = r.diff(r)
    assert hasattr(diff, "severity_direction")
    assert hasattr(diff, "ews_trend")
    assert hasattr(diff, "overall_trend")
    assert hasattr(diff, "time_to_transition_delta")
    assert hasattr(diff, "ews_score_from")
    assert hasattr(diff, "ews_score_to")
