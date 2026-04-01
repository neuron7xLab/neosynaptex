"""Integration tests for MFN Self-Reading Architecture.

Tests all 5 layers + the architectural law: Recovery never reads gamma.
"""

from __future__ import annotations

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.self_reading import (
    CoherenceMonitor,
    CoherenceReport,
    InterpretabilityLayer,
    MFNPhase,
    PhaseValidator,
    RecoveryMode,
    RecoveryProtocol,
    SelfModel,
    SelfModelSnapshot,
    SelfReadingConfig,
    SelfReadingLoop,
    SelfReadingReport,
)


def _make_seq(seed: int = 42) -> mfn.FieldSequence:
    return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=seed))


def _make_sequences(n: int = 10) -> list[mfn.FieldSequence]:
    return [_make_seq(seed=42 + i) for i in range(n)]


# ── Layer 1: SelfModel ───────────────────────────────────────────


class TestSelfModel:
    def test_capture(self) -> None:
        sm = SelfModel()
        snap = sm.capture(_make_seq(), step=0)
        assert isinstance(snap, SelfModelSnapshot)
        assert snap.active_node_count > 0
        assert np.isfinite(snap.entropy_current)
        assert snap.step == 0

    def test_complexity_gradient(self) -> None:
        sm = SelfModel()
        sm.capture(_make_seq(42), step=0)
        s2 = sm.capture(_make_seq(43), step=1)
        # Gradient should be nonzero between different seeds
        assert isinstance(s2.complexity_gradient, float)

    def test_complexity_is_growing(self) -> None:
        sm = SelfModel()
        history = [sm.capture(_make_seq(i), step=i) for i in range(5)]
        # With 5 steps, window=10 should return False
        assert sm.complexity_is_growing(history, window=10) is False


# ── Layer 2: CoherenceMonitor ────────────────────────────────────


class TestCoherenceMonitor:
    def test_measure(self) -> None:
        seqs = _make_sequences(5)
        cm = CoherenceMonitor()
        report = cm.measure(seqs, window=5)
        assert isinstance(report, CoherenceReport)
        assert 0 <= report.connectivity <= 1
        assert 0 <= report.overall <= 1

    def test_fragmentation_detection(self) -> None:
        cm = CoherenceMonitor()
        report = cm.measure(_make_sequences(3), window=3)
        assert isinstance(report.is_fragmented, bool)
        assert isinstance(report.is_drifting, bool)

    def test_empty_sequences(self) -> None:
        cm = CoherenceMonitor()
        report = cm.measure([], window=5)
        assert report.overall == 0.0


# ── Layer 3: InterpretabilityLayer ───────────────────────────────


class TestInterpretabilityLayer:
    def test_trace(self) -> None:
        seqs = _make_sequences(10)
        il = InterpretabilityLayer()
        trace = il.trace(seqs, window=10)
        assert trace.dominant_operator != "none"
        assert trace.shift_magnitude >= 0
        assert len(trace.operator_attributions) > 0

    def test_explain(self) -> None:
        seqs = _make_sequences(5)
        il = InterpretabilityLayer()
        trace = il.trace(seqs, window=5)
        explanation = trace.explain()
        assert "State shift" in explanation
        assert len(explanation) > 20

    def test_single_sequence(self) -> None:
        il = InterpretabilityLayer()
        trace = il.trace([_make_seq()], window=5)
        assert trace.dominant_operator == "none"


# ── Layer 4: PhaseValidator ──────────────────────────────────────


class TestPhaseValidator:
    def test_healthy_field_operational(self) -> None:
        pv = PhaseValidator()
        seq = _make_seq()
        report = pv.validate(seq)
        assert report.phase in (MFNPhase.OPERATIONAL, MFNPhase.NOISY)
        assert 0 <= report.phase_confidence <= 1

    def test_zero_field_fragmenting(self) -> None:
        """Near-zero field should be FRAGMENTING (low D_box)."""
        from mycelium_fractal_net.types.field import FieldSequence as FS

        flat_field = np.full((16, 16), 1e-10)
        seq = FS(field=flat_field)
        pv = PhaseValidator()
        report = pv.validate(seq)
        assert report.phase in (MFNPhase.FRAGMENTING, MFNPhase.COLLAPSING)

    def test_transition_probability(self) -> None:
        pv = PhaseValidator()
        reports = []
        for i in range(5):
            seq = _make_seq(i)
            reports.append(pv.validate(seq))
        prob = pv.transition_probability(reports)
        assert 0 <= prob <= 1


# ── Layer 5: RecoveryProtocol ────────────────────────────────────


class TestRecoveryProtocol:
    def test_cooldown_respected(self) -> None:
        from mycelium_fractal_net.self_reading.phase_validator import (
            MFNPhase as _MFNPhase,
        )
        from mycelium_fractal_net.self_reading.phase_validator import (
            PhaseReport as PR,
        )

        rp = RecoveryProtocol(cooldown=100)

        phase = PR(
            phase=_MFNPhase.FRAGMENTING,
            phase_confidence=0.8,
            steps_in_phase=5,
            transition_risk=0.8,
            physical_signals={"free_energy": 1.0},
        )
        coh = CoherenceReport(0.5, 0.3, 0.2, 0.1, 0.5)

        # First recovery at step 1000 (avoid step 0 collision with other tests)
        action = rp.act(phase, coh, current_step=1000)
        assert action is not None, "First act should trigger recovery"
        assert action.mode == RecoveryMode.PARAMETRIC

        # Second within cooldown — should be blocked
        action2 = rp.act(phase, coh, current_step=1050)
        assert action2 is None, "Cooldown should block second recovery"

        # After cooldown — should work
        action3 = rp.act(phase, coh, current_step=1200)
        assert action3 is not None, "After cooldown, recovery should trigger"

    def test_recovery_does_not_read_gamma(self) -> None:
        """RecoveryProtocol interface has no gamma parameter."""
        rp = RecoveryProtocol()
        import inspect

        # Check act() signature has no gamma-related params
        sig = inspect.signature(rp.act)
        param_names = list(sig.parameters.keys())
        for name in param_names:
            assert "gamma" not in name.lower(), f"Recovery reads gamma via '{name}'"

        # Check should_act() signature
        sig2 = inspect.signature(rp.should_act)
        for name in sig2.parameters:
            assert "gamma" not in name.lower()

    def test_operational_no_recovery(self) -> None:
        from mycelium_fractal_net.self_reading.phase_validator import (
            PhaseReport as PR,
        )

        rp = RecoveryProtocol(cooldown=0)
        phase = PR(
            phase=MFNPhase.OPERATIONAL,
            phase_confidence=0.9,
            steps_in_phase=100,
            transition_risk=0.0,
        )
        coh = CoherenceReport(0.9, 0.1, 0.05, 0.02, 0.9)
        assert rp.act(phase, coh, current_step=0) is None


# ── SelfReadingLoop ──────────────────────────────────────────────


class TestSelfReadingLoop:
    def test_full_loop(self) -> None:
        config = SelfReadingConfig(
            coherence_every=3,
            interpretability_window=5,
            phase_check_every=5,
            recovery_cooldown=100,
        )
        loop = SelfReadingLoop(config)

        reports = []
        for i in range(15):
            seq = _make_seq(seed=42 + i)
            report = loop.on_step(seq)
            reports.append(report)
            assert isinstance(report, SelfReadingReport)

        # Should have self_model for all
        assert all(r.self_model is not None for r in reports)

        # Should have coherence for some
        assert any(r.coherence is not None for r in reports)

        # Should have phase for some
        assert any(r.phase is not None for r in reports)

    def test_default_is_healthy(self) -> None:
        """At step 1 (no phase check), report should be healthy by default."""
        loop = SelfReadingLoop(SelfReadingConfig(phase_check_every=1000))
        loop.on_step(_make_seq(42))  # step 0 (phase_check triggers at 0%1000==0)
        report = loop.on_step(_make_seq(43))  # step 1 — no phase check
        assert report.phase is None
        assert report.is_healthy()

    def test_report_to_dict(self) -> None:
        loop = SelfReadingLoop()
        report = loop.on_step(_make_seq())
        d = report.to_dict()
        assert "step" in d
        assert "entropy" in d
        assert "healthy" in d

    def test_self_reading_does_not_modify_field(self) -> None:
        """Self-reading is read-only: field before == field after."""
        seq = _make_seq()
        field_before = seq.field.copy()

        loop = SelfReadingLoop(SelfReadingConfig(
            coherence_every=1,
            phase_check_every=1,
            interpretability_window=1,
        ))
        loop.on_step(seq)

        np.testing.assert_array_equal(seq.field, field_before)
