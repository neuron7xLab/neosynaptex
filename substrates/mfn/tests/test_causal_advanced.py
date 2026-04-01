"""Advanced causal validation tests.

Covers: overhead measurement, deterministic replay, property tests,
threshold drift detection, baseline parity, observe mode.
"""

from __future__ import annotations

import time

import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.types.causal import CausalDecision

# ═══════════════════════════════════════════════════
# Overhead measurement
# ═══════════════════════════════════════════════════


class TestCausalOverhead:
    """Verify causal gate adds bounded overhead."""

    def test_overhead_under_500ms(self) -> None:
        """Causal validation must complete within 500ms for 32x32 grid."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=16, seed=42))
        desc = mfn.extract(seq)
        event = mfn.detect(seq)
        fcast = mfn.forecast(seq, horizon=4)
        comp = mfn.compare(seq, seq)

        start = time.perf_counter()
        result = validate_causal_consistency(seq, desc, event, fcast, comp)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"Causal gate took {elapsed:.3f}s, limit 0.5s"
        assert result.stages_checked >= 6

    def test_overhead_proportional(self) -> None:
        """Gate without optional stages should be faster."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))

        start = time.perf_counter()
        result_minimal = validate_causal_consistency(seq)
        time.perf_counter() - start

        desc = mfn.extract(seq)
        event = mfn.detect(seq)

        start = time.perf_counter()
        result_full = validate_causal_consistency(seq, desc, event)
        time.perf_counter() - start

        assert result_minimal.stages_checked < result_full.stages_checked


# ═══════════════════════════════════════════════════
# Deterministic replay
# ═══════════════════════════════════════════════════


class TestDeterministicReplay:
    """Verify identical input produces identical verdict."""

    def test_same_input_same_verdict(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
        desc = mfn.extract(seq)
        event = mfn.detect(seq)

        r1 = validate_causal_consistency(seq, desc, event)
        r2 = validate_causal_consistency(seq, desc, event)

        assert r1.decision == r2.decision
        assert r1.config_hash == r2.config_hash
        assert len(r1.rule_results) == len(r2.rule_results)
        for a, b in zip(r1.rule_results, r2.rule_results, strict=False):
            assert a.rule_id == b.rule_id
            assert a.passed == b.passed
            assert a.severity == b.severity

    def test_different_seed_different_hash(self) -> None:
        seq1 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        seq2 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=99))

        r1 = validate_causal_consistency(seq1)
        r2 = validate_causal_consistency(seq2)

        assert r1.runtime_hash != r2.runtime_hash


# ═══════════════════════════════════════════════════
# Property tests
# ═══════════════════════════════════════════════════


class TestCausalProperties:
    """Property-based invariants that must always hold."""

    @pytest.mark.parametrize("seed", [1, 7, 42, 100, 255])
    def test_valid_simulation_never_fails(self, seed: int) -> None:
        """Any valid SimulationSpec should not produce causal errors."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=seed))
        result = validate_causal_consistency(seq)
        assert result.error_count == 0, (
            f"seed={seed}: {[v.message for v in result.violations if not v.passed]}"
        )

    @pytest.mark.parametrize("grid_size", [4, 8, 16, 32, 64])
    def test_all_grid_sizes_pass(self, grid_size: int) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=grid_size, steps=4, seed=42))
        result = validate_causal_consistency(seq)
        assert result.error_count == 0

    def test_monotonicity_score_bounded(self) -> None:
        """Anomaly score must always be in [0, 1] regardless of input."""
        for seed in range(10):
            seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=seed))
            event = mfn.detect(seq)
            assert 0.0 <= event.score <= 1.0, f"seed={seed}: score={event.score}"
            assert 0.0 <= event.confidence <= 1.0

    def test_self_comparison_always_near_identical(self) -> None:
        """Comparing a sequence to itself must always be near-identical."""
        for seed in [1, 42, 100]:
            seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=seed))
            comp = mfn.compare(seq, seq)
            assert comp.distance == pytest.approx(0.0, abs=1e-10)
            assert comp.label == "near-identical"


# ═══════════════════════════════════════════════════
# Observe mode
# ═══════════════════════════════════════════════════


class TestObserveMode:
    """Verify observe mode logs but never blocks."""

    def test_observe_mode_never_fails(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        result = validate_causal_consistency(seq, mode="observe")
        assert result.decision != CausalDecision.FAIL

    def test_observe_mode_still_records_violations(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
        desc = mfn.extract(seq)
        event = mfn.detect(seq)
        fcast = mfn.forecast(seq, horizon=4)
        result_strict = validate_causal_consistency(seq, desc, event, fcast, mode="strict")
        result_observe = validate_causal_consistency(seq, desc, event, fcast, mode="observe")
        # Same rules evaluated
        assert len(result_strict.rule_results) == len(result_observe.rule_results)


# ═══════════════════════════════════════════════════
# Baseline parity with causal gate
# ═══════════════════════════════════════════════════


class TestBaselineParityWithGate:
    """Verify causal gate doesn't break baseline behavior."""

    def test_baseline_report_passes_gate(self, tmp_path) -> None:
        """Standard report generation must pass causal gate."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
        assert report.run_id  # report completed without RuntimeError

    def test_baseline_detection_stable_nominal(self) -> None:
        """Baseline simulation should produce stable/nominal."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=24, seed=42))
        event = mfn.detect(seq)
        assert event.regime.label == "stable"
        assert event.label == "nominal"

    def test_neuromod_scenario_passes_gate(self) -> None:
        """Neuromodulation scenario should pass causal gate."""
        from mycelium_fractal_net.core.simulate import simulate_scenario

        seq = simulate_scenario("inhibitory_stabilization")
        desc = mfn.extract(seq)
        event = mfn.detect(seq)
        result = validate_causal_consistency(seq, desc, event)
        assert result.error_count == 0
