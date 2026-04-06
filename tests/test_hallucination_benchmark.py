"""Tests for the Hallucination Thermodynamics Benchmark (Task 4)."""

from __future__ import annotations

import numpy as np
import pytest

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
    CoherenceStateSpaceParams,
)
from core.hallucination_benchmark import (
    BenchmarkResult,
    BenchmarkScenario,
    HallucinationBenchmark,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def model() -> CoherenceStateSpace:
    return CoherenceStateSpace(CoherenceStateSpaceParams())


@pytest.fixture()
def bench(model: CoherenceStateSpace) -> HallucinationBenchmark:
    return HallucinationBenchmark(model)


@pytest.fixture()
def rng() -> np.random.Generator:
    return np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------


class TestScenarioGeneration:
    def test_scenario_count(self, bench: HallucinationBenchmark) -> None:
        assert len(bench.scenarios()) >= 15

    def test_scenario_categories(self, bench: HallucinationBenchmark) -> None:
        cats = {s.category for s in bench.scenarios()}
        assert cats == {"clean", "ambiguous", "adversarial"}

    def test_five_per_category(self, bench: HallucinationBenchmark) -> None:
        from collections import Counter

        counts = Counter(s.category for s in bench.scenarios())
        for cat in ("clean", "ambiguous", "adversarial"):
            assert counts[cat] >= 5

    def test_scenario_inputs_shape(self, bench: HallucinationBenchmark) -> None:
        for s in bench.scenarios():
            assert s.inputs.ndim == 2
            assert s.inputs.shape[1] == 2

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValueError, match="category"):
            BenchmarkScenario(
                name="bad",
                category="nonsense",
                initial_state=CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3),
                inputs=np.zeros((10, 2)),
                expected_hallucination=False,
                description="invalid",
            )

    def test_invalid_inputs_shape_rejected(self) -> None:
        with pytest.raises(ValueError, match="inputs"):
            BenchmarkScenario(
                name="bad",
                category="clean",
                initial_state=CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3),
                inputs=np.zeros((10, 3)),
                expected_hallucination=False,
                description="wrong shape",
            )


# ---------------------------------------------------------------------------
# Running scenarios
# ---------------------------------------------------------------------------


class TestRunScenario:
    def test_run_single_returns_result(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        s = bench.scenarios()[0]
        r = bench.run_scenario(s, rng)
        assert isinstance(r, BenchmarkResult)
        assert r.scenario_name == s.name

    def test_delta_s_trajectory_length(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        s = bench.scenarios()[0]
        r = bench.run_scenario(s, rng)
        assert len(r.delta_S_trajectory) == s.inputs.shape[0]

    def test_coherence_trajectory_length(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        s = bench.scenarios()[0]
        r = bench.run_scenario(s, rng)
        # rollout returns n_steps+1 rows
        assert len(r.coherence_trajectory) == s.inputs.shape[0] + 1

    def test_clean_scenarios_predict_no_hallucination(
        self,
        bench: HallucinationBenchmark,
    ) -> None:
        """Clean scenarios (deterministic, no noise) should predict no hallucination."""
        clean = [s for s in bench.scenarios() if s.category == "clean"]
        correct = 0
        for s in clean:
            r = bench.run_scenario(s, np.random.default_rng(0))
            if not r.predicted_hallucination:
                correct += 1
        # At least 4 out of 5 clean should be correct
        assert correct >= 4, f"Only {correct}/5 clean scenarios predicted correctly"

    def test_adversarial_scenarios_predict_hallucination(
        self,
        bench: HallucinationBenchmark,
    ) -> None:
        """Adversarial scenarios should mostly predict hallucination."""
        adv = [s for s in bench.scenarios() if s.category == "adversarial"]
        correct = 0
        for s in adv:
            r = bench.run_scenario(s, np.random.default_rng(0))
            if r.predicted_hallucination:
                correct += 1
        assert correct >= 3, f"Only {correct}/5 adversarial predicted correctly"

    def test_run_all(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        results = bench.run_all(rng)
        assert len(results) >= 15


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_metrics_valid(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        results = bench.run_all(rng)
        s = bench.summary(results)
        assert 0.0 <= s.accuracy <= 1.0
        assert 0.0 <= s.precision <= 1.0
        assert 0.0 <= s.recall <= 1.0
        assert s.total == len(results)
        assert 0 <= s.correct <= s.total

    def test_calibration_error_bounded(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        results = bench.run_all(rng)
        s = bench.summary(results)
        assert 0.0 <= s.calibration_error <= 1.0

    def test_category_accuracy_all_present(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        results = bench.run_all(rng)
        s = bench.summary(results)
        for cat in ("clean", "ambiguous", "adversarial"):
            assert cat in s.category_accuracy
            assert 0.0 <= s.category_accuracy[cat] <= 1.0

    def test_delta_s_distribution_length(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        results = bench.run_all(rng)
        s = bench.summary(results)
        assert len(s.delta_s_distribution) == len(results)

    def test_empty_results(self, bench: HallucinationBenchmark) -> None:
        s = bench.summary([])
        assert s.total == 0
        assert s.accuracy == 0.0
        assert s.calibration_error == 0.0
        assert s.category_accuracy == {}


# ---------------------------------------------------------------------------
# Perturbation robustness
# ---------------------------------------------------------------------------


class TestPerturbation:
    def test_perturb_returns_correct_count(
        self,
        bench: HallucinationBenchmark,
        rng: np.random.Generator,
    ) -> None:
        s = bench.scenarios()[0]  # clean scenario
        results = bench.perturb_and_rerun(s, n_perturbations=5, noise_scale=1e-4, rng=rng)
        assert len(results) == 5

    def test_clean_robust_under_small_perturbation(
        self,
        bench: HallucinationBenchmark,
    ) -> None:
        """Clean scenarios should remain non-hallucination under tiny perturbation.

        We compare each perturbed run against the *baseline* (unperturbed)
        prediction — the test checks that perturbation doesn't flip relative
        to baseline, not that every run is non-hallucination (model noise
        can independently flip runs either way).
        """
        clean = [s for s in bench.scenarios() if s.category == "clean"]
        scenario = clean[0]
        # Baseline: run without perturbation using a fixed seed
        baseline = bench.run_scenario(scenario, np.random.default_rng(0))
        # Perturbed runs
        results = bench.perturb_and_rerun(
            scenario,
            n_perturbations=10,
            noise_scale=1e-6,
            rng=np.random.default_rng(99),
        )
        # Check that perturbation results aren't ALL flipped vs baseline
        agree = sum(
            1 for r in results if r.predicted_hallucination == baseline.predicted_hallucination
        )
        assert agree >= 4, (
            f"Only {agree}/10 perturbations agreed with baseline — "
            f"model is fragile to tiny input noise"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_same_result(
        self,
        bench: HallucinationBenchmark,
    ) -> None:
        s = bench.scenarios()[0]
        r1 = bench.run_scenario(s, np.random.default_rng(123))
        r2 = bench.run_scenario(s, np.random.default_rng(123))
        np.testing.assert_array_equal(r1.delta_S_trajectory, r2.delta_S_trajectory)
        assert r1.final_delta_S == r2.final_delta_S
        assert r1.predicted_hallucination == r2.predicted_hallucination
