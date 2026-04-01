"""Phase 3 integration tests — real MFN simulation evidence for PRR.

# EVIDENCE TYPE: real_simulation
All tests run actual MFN R-D simulations. No mocks.
Every assertion is falsifiable.

Ref: Vasylenko (2026) gamma-scaling hypothesis
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.experiments.prr_export import PRRExporter
from mycelium_fractal_net.experiments.runner import ExperimentRunner
from mycelium_fractal_net.experiments.scenarios import (
    SCENARIO_HEALTHY,
    SCENARIO_PATHOLOGICAL,
    ScenarioConfig,
)


def _quick_scenario(base: ScenarioConfig, n_runs: int = 3, n_seq: int = 10) -> ScenarioConfig:
    """Reduce run count for CI speed."""
    return ScenarioConfig(
        name=base.name,
        sim_params=base.sim_params,
        n_steps_base=base.n_steps_base,
        n_steps_increment=base.n_steps_increment,
        n_sequences=n_seq,
        n_runs=n_runs,
        expected_gamma_range=base.expected_gamma_range,
        description=base.description,
    )


@pytest.fixture(scope="module")
def runner() -> ExperimentRunner:
    return ExperimentRunner()


@pytest.fixture(scope="module")
def healthy_result(runner):
    return runner.run_scenario(_quick_scenario(SCENARIO_HEALTHY))


@pytest.fixture(scope="module")
def pathological_result(runner):
    return runner.run_scenario(_quick_scenario(SCENARIO_PATHOLOGICAL))


# ── GATE 3: Gamma scaling by condition ─────────────────────────


class TestGammaScaling:
    """# EVIDENCE TYPE: real_simulation"""

    def test_healthy_gamma_in_expected_range(self, healthy_result) -> None:
        """Healthy gamma falls in configured range [-7, -3]."""
        lo, hi = SCENARIO_HEALTHY.expected_gamma_range
        assert lo <= healthy_result.gamma_mean <= hi, (
            f"Healthy gamma {healthy_result.gamma_mean:.4f} outside [{lo}, {hi}]"
        )

    def test_healthy_has_multiple_runs(self, healthy_result) -> None:
        assert len(healthy_result.runs) == 3

    def test_pathological_gamma_weaker_scaling(self, healthy_result, pathological_result) -> None:
        """Pathological has weaker scaling (closer to 0) than healthy."""
        assert abs(pathological_result.gamma_mean) < abs(healthy_result.gamma_mean), (
            f"|patho|={abs(pathological_result.gamma_mean):.4f} >= "
            f"|healthy|={abs(healthy_result.gamma_mean):.4f}"
        )

    def test_gamma_separation_detectable(self, healthy_result, pathological_result) -> None:
        """Cohen's d > 0.5 between healthy and pathological gamma."""
        g_h = np.array([r.gamma for r in healthy_result.runs])
        g_p = np.array([r.gamma for r in pathological_result.runs])
        pooled_std = float(np.sqrt((np.var(g_h) + np.var(g_p)) / 2))
        cohens_d = float(abs(np.mean(g_h) - np.mean(g_p)) / (pooled_std + 1e-12))
        assert cohens_d > 0.5, f"Cohen's d = {cohens_d:.3f}, expected > 0.5"


# ── GATE 4: Mechanistic localization ──────────────────────────


class TestMechanistic:
    def test_deviation_origin_populated(self, healthy_result, pathological_result) -> None:
        """Every run has a valid deviation_origin classification."""
        valid_origins = {"thermodynamic", "topological", "fractal",
                         "causal_rule", "stage_transition", "emergent"}
        for r in healthy_result.runs + pathological_result.runs:
            assert r.deviation_origin in valid_origins, (
                f"Invalid deviation_origin: {r.deviation_origin}"
            )

    def test_features_extracted(self, healthy_result) -> None:
        """Feature extraction produces non-empty dicts from real data."""
        for run in healthy_result.runs:
            assert len(run.features) > 0, "No features extracted"
            for fd in run.features:
                assert "fractal" in fd or "topological" in fd, (
                    f"Missing feature groups in {list(fd.keys())}"
                )


# ── GATE 5 / GATE 6: Lyapunov and identity engine ─────────────


class TestLyapunov:
    """# IMPLEMENTED TRUTH: V_x = F from ThermodynamicKernel (real R-D free energy)"""

    def test_lyapunov_stable_under_healthy(self, healthy_result) -> None:
        """Mean V trend ≤ 0.5 for healthy scenario."""
        all_v: list[float] = []
        for r in healthy_result.runs:
            all_v.extend(r.v_trajectory)
        if len(all_v) > 1:
            diffs = np.diff(all_v)
            mean_trend = float(np.mean(diffs))
            assert mean_trend <= 0.5, f"V trend = {mean_trend:.4f}, expected ≤ 0.5"

    def test_no_transformations_healthy(self, healthy_result) -> None:
        """Healthy: identity engine stays IDLE/RECOVERY, 0 transformations."""
        total = sum(r.n_transforms for r in healthy_result.runs)
        assert total == 0, f"Unexpected {total} transforms in healthy"

    def test_identity_engine_produces_valid_trajectories(self, healthy_result) -> None:
        """V trajectory from real IdentityEngine on real MFNSnapshot data."""
        for r in healthy_result.runs:
            assert len(r.v_trajectory) > 0, "Empty V trajectory"
            assert all(np.isfinite(v) for v in r.v_trajectory), "Non-finite V values"

    def test_free_energy_from_real_simulation(self, healthy_result) -> None:
        """Free energy is real F from FreeEnergyTracker, not synthetic.

        # FRISTON STATUS: PARTIAL — thermodynamic F available, not variational F
        """
        for r in healthy_result.runs:
            assert len(r.free_energy_trajectory) > 0, "No free energy data"
            assert all(np.isfinite(f) for f in r.free_energy_trajectory), "Non-finite F"


# ── GATE 7: PRR export ────────────────────────────────────────


class TestPRRExport:
    def test_prr_tables_generated(self, healthy_result, pathological_result, tmp_path) -> None:
        """All 5 PRR tables non-empty, contain numeric values."""
        exporter = PRRExporter()
        report = exporter.export(healthy_result, pathological_result,
                                 output_dir=str(tmp_path))

        for name in ("table_1", "table_2", "table_3", "table_4", "table_5"):
            table = getattr(report, name)
            assert isinstance(table, str), f"{name} is not a string"
            assert len(table) > 10, f"{name} is too short"

        assert report.evidence_type == "real_simulation"
        assert report.n_healthy_runs == len(healthy_result.runs)
        assert report.n_patho_runs == len(pathological_result.runs)

    def test_prr_file_written(self, healthy_result, pathological_result, tmp_path) -> None:
        """PRR tables are saved to disk."""
        exporter = PRRExporter()
        exporter.export(healthy_result, pathological_result,
                        output_dir=str(tmp_path))
        outfile = tmp_path / "prr_tables.txt"
        assert outfile.exists()
        content = outfile.read_text()
        assert "TABLE 1" in content
        assert "TABLE 5" in content


# ── Comparison pipeline ───────────────────────────────────────


class TestComparison:
    def test_comparison_report_valid(self, healthy_result, pathological_result) -> None:
        """InterpretabilityPipeline.compare() produces valid statistics."""
        from mycelium_fractal_net.interpretability.pipeline import InterpretabilityPipeline

        pipe = InterpretabilityPipeline()
        comp = pipe.compare(healthy_result, pathological_result)

        assert comp.cohens_d > 0, "Cohen's d should be positive"
        assert 0 <= comp.p_value <= 1, f"p_value out of range: {comp.p_value}"
        assert comp.wasserstein > 0, "Wasserstein distance should be positive"
        assert comp.friston_gap_status in ("CLOSED", "PARTIAL", "OPEN")
