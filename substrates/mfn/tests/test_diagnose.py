"""Tests for mfn.diagnose(), diagnose_streaming(), DiagnosisDiff, and mfn.watch()."""

from __future__ import annotations

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.diagnosis import (
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_STABLE,
    SEVERITY_WARNING,
    DiagnosisDiff,
    DiagnosisReport,
)
from mycelium_fractal_net.types.field import (
    SimulationSpec,
)

VALID_SEVERITIES = {SEVERITY_STABLE, SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_CRITICAL}

_BASELINE = SimulationSpec(grid_size=32, steps=60, seed=42)


def _seq(spec: SimulationSpec = _BASELINE) -> mfn.FieldSequence:
    return mfn.simulate(spec)


# ══════════════════════════════════════════════════
#  diagnose() tests
# ══════════════════════════════════════════════════


class TestDiagnose:
    def test_returns_report(self) -> None:
        report = mfn.diagnose(_seq())
        assert isinstance(report, DiagnosisReport)
        assert report.severity in VALID_SEVERITIES

    def test_fields_complete(self) -> None:
        report = mfn.diagnose(_seq())
        assert report.anomaly is not None
        assert report.warning is not None
        assert report.forecast is not None
        assert report.causal is not None
        assert report.descriptor is not None
        assert isinstance(report.narrative, str)
        assert len(report.narrative) > 10
        assert "diagnosis_time_ms" in report.metadata

    def test_summary_format(self) -> None:
        s = mfn.diagnose(_seq()).summary()
        assert "DIAGNOSIS:" in s
        assert "anomaly=" in s
        assert "ews=" in s

    def test_to_dict_keys(self) -> None:
        d = mfn.diagnose(_seq()).to_dict()
        for key in ("severity", "narrative", "anomaly", "warning", "causal", "plan", "metadata"):
            assert key in d

    def test_is_ok_and_needs_intervention(self) -> None:
        report = mfn.diagnose(_seq(), skip_intervention=True)
        assert isinstance(report.is_ok(), bool)
        assert not report.needs_intervention()

    def test_deterministic(self) -> None:
        seq = _seq()
        r1 = mfn.diagnose(seq, skip_intervention=True)
        r2 = mfn.diagnose(seq, skip_intervention=True)
        assert r1.severity == r2.severity
        assert r1.warning.ews_score == r2.warning.ews_score
        assert r1.anomaly.label == r2.anomaly.label

    def test_skip_intervention(self) -> None:
        report = mfn.diagnose(_seq(), skip_intervention=True)
        assert report.plan is None


# ══════════════════════════════════════════════════
#  mode tests
# ══════════════════════════════════════════════════


class TestDiagnoseMode:
    def test_fast_mode(self) -> None:
        report = mfn.diagnose(_seq(), mode="fast")
        assert isinstance(report, DiagnosisReport)
        assert report.plan is None  # fast skips intervention
        assert report.metadata["causal_mode"] == "permissive"

    def test_full_mode(self) -> None:
        report = mfn.diagnose(_seq(), mode="full")
        assert isinstance(report, DiagnosisReport)
        assert report.metadata["causal_mode"] == "strict"


# ══════════════════════════════════════════════════
#  streaming tests
# ══════════════════════════════════════════════════


class TestDiagnoseStreaming:
    def test_yields_steps(self) -> None:
        steps_seen: list[str] = []
        gen = mfn.diagnose_streaming(_seq())
        try:
            while True:
                step_name, result = next(gen)
                steps_seen.append(step_name)
                assert result is not None
        except StopIteration as e:
            report = e.value
            assert isinstance(report, DiagnosisReport)

        assert "extract" in steps_seen
        assert "anomaly" in steps_seen
        assert "warning" in steps_seen
        assert "forecast" in steps_seen
        assert "causal" in steps_seen

    def test_streaming_matches_full(self) -> None:
        seq = _seq()
        full = mfn.diagnose(seq, skip_intervention=True)

        gen = mfn.diagnose_streaming(seq)
        try:
            while True:
                next(gen)
        except StopIteration as e:
            streaming = e.value

        assert full.severity == streaming.severity
        assert full.anomaly.label == streaming.anomaly.label


# ══════════════════════════════════════════════════
#  DiagnosisDiff tests
# ══════════════════════════════════════════════════


class TestDiagnosisDiff:
    def test_same_reports_no_diff(self) -> None:
        report = mfn.diagnose(_seq(), skip_intervention=True)
        diff = report.diff(report)
        assert isinstance(diff, DiagnosisDiff)
        assert not diff.has_changes
        assert diff.ews_score_delta == 0.0
        assert diff.overall_trend == "stable"

    def test_different_seeds_may_diff(self) -> None:
        r1 = mfn.diagnose(
            _seq(SimulationSpec(grid_size=32, steps=60, seed=42)), skip_intervention=True
        )
        r2 = mfn.diagnose(
            _seq(SimulationSpec(grid_size=32, steps=60, seed=99)), skip_intervention=True
        )
        diff = r1.diff(r2)
        assert isinstance(diff, DiagnosisDiff)
        d = diff.to_dict()
        assert "severity" in d
        assert "has_changes" in d

    def test_diff_summary(self) -> None:
        r1 = mfn.diagnose(_seq(), skip_intervention=True)
        diff = r1.diff(r1)
        assert "[DIFF:" in diff.summary()
        assert "overall=" in diff.summary()

    def test_diff_to_dict(self) -> None:
        r1 = mfn.diagnose(_seq(), skip_intervention=True)
        diff = r1.diff(r1)
        d = diff.to_dict()
        assert d["has_changes"] is False


# ══════════════════════════════════════════════════
#  watch() tests
# ══════════════════════════════════════════════════


class TestWatch:
    def test_basic_watch(self) -> None:
        spec = SimulationSpec(grid_size=16, steps=8, seed=42)
        reports = mfn.watch(spec, n_steps_per_tick=8, n_ticks=3)
        assert len(reports) == 3
        for r in reports:
            assert isinstance(r, DiagnosisReport)

    def test_callback_stops(self) -> None:
        spec = SimulationSpec(grid_size=16, steps=8, seed=42)
        reports = mfn.watch(
            spec,
            n_steps_per_tick=8,
            n_ticks=10,
            callback=lambda report, tick: tick < 2,
        )
        assert len(reports) <= 3  # stops at tick 2 (0, 1, 2 then callback returns False)

    def test_callback_receives_report(self) -> None:
        spec = SimulationSpec(grid_size=16, steps=8, seed=42)
        received: list[DiagnosisReport] = []

        def cb(report: DiagnosisReport, tick: int) -> bool:
            received.append(report)
            return True

        mfn.watch(spec, n_steps_per_tick=8, n_ticks=3, callback=cb)
        assert len(received) == 3

    def test_watch_deterministic(self) -> None:
        spec = SimulationSpec(grid_size=16, steps=8, seed=42)
        r1 = mfn.watch(spec, n_steps_per_tick=8, n_ticks=3)
        r2 = mfn.watch(spec, n_steps_per_tick=8, n_ticks=3)
        for a, b in zip(r1, r2, strict=False):
            assert a.severity == b.severity
            assert a.warning.ews_score == b.warning.ews_score


# ══════════════════════════════════════════════════
#  early_warning standalone
# ══════════════════════════════════════════════════


class TestEarlyWarning:
    def test_standalone(self) -> None:
        w = mfn.early_warning(_seq())
        assert isinstance(w, mfn.CriticalTransitionWarning)
        assert 0.0 <= w.ews_score <= 1.0
        assert isinstance(w.transition_type, str)
        assert w.causal_certificate != ""
        d = w.to_dict()
        assert "ews_score" in d
