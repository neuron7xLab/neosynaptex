"""Tests to close coverage gaps in modules below 80%.

Target modules:
- types/scenario.py (0%)
- neurochem/calibration.py (50%)
- neurochem/state.py (71%)
- types/__init__.py (11%)
- numerics/grid_ops.py (53%)
"""

from __future__ import annotations

import numpy as np
import pytest


class TestScenarioTypes:
    """Cover types/scenario.py (0% → 100%)."""

    def test_scenario_types_importable(self) -> None:
        from mycelium_fractal_net.types.scenario import ScenarioConfig, ScenarioType

        assert ScenarioType is not None
        assert ScenarioConfig is not None


class TestCalibration:
    """Cover neurochem/calibration.py (50% → 100%)."""

    def test_list_calibration_tasks(self) -> None:
        from mycelium_fractal_net.neurochem.calibration import list_calibration_tasks

        tasks = list_calibration_tasks()
        assert len(tasks) == 3
        assert "gabaa_tonic_stabilization_fit" in tasks

    def test_get_calibration_criteria(self) -> None:
        from mycelium_fractal_net.neurochem.calibration import get_calibration_criteria

        criteria = get_calibration_criteria()
        assert "clamp_events_per_step_max" in criteria
        assert criteria["complexity_floor"] == 0.20

    def test_run_calibration_task(self) -> None:
        from mycelium_fractal_net.neurochem.calibration import run_calibration_task

        result = run_calibration_task("gabaa_tonic_stabilization_fit")
        assert result["status"] == "calibrated"
        assert "profile" in result
        assert "criteria" in result

    def test_run_calibration_task_unknown(self) -> None:
        from mycelium_fractal_net.neurochem.calibration import run_calibration_task

        with pytest.raises(KeyError, match="unknown calibration task"):
            run_calibration_task("nonexistent_task")


class TestNeuromodulationState:
    """Cover neurochem/state.py (71% → 90%+)."""

    def test_occupancy_bounds_ok(self) -> None:
        from mycelium_fractal_net.neurochem.state import NeuromodulationState

        state = NeuromodulationState.zeros((4, 4))
        assert state.occupancy_bounds_ok()

    def test_occupancy_bounds_violated(self) -> None:
        from mycelium_fractal_net.neurochem.state import NeuromodulationState

        state = NeuromodulationState.zeros((4, 4))
        state.occupancy_resting[:] = 0.5  # sum = 0.5, not 1.0
        assert not state.occupancy_bounds_ok()

    def test_to_dict(self) -> None:
        from mycelium_fractal_net.neurochem.state import NeuromodulationState

        state = NeuromodulationState.zeros((4, 4))
        d = state.to_dict()
        assert d["occupancy_bounds_ok"] is True
        assert d["occupancy_resting"] == 1.0
        assert d["occupancy_active"] == 0.0

    def test_summary(self) -> None:
        from mycelium_fractal_net.neurochem.state import NeuromodulationState

        state = NeuromodulationState.zeros((4, 4))
        s = state.summary()
        assert "occupancy_mass_error_max" in s
        assert s["occupancy_mass_error_max"] == pytest.approx(0.0)


class TestTypesInit:
    """Cover types/__init__.py lazy getattr branches (11% → 80%+)."""

    def test_lazy_simulation_config(self) -> None:
        from mycelium_fractal_net.types import SimulationConfig

        assert SimulationConfig is not None

    def test_lazy_field_types(self) -> None:
        from mycelium_fractal_net.types import (
            GridShape,
        )

        assert GridShape(rows=4, cols=4).is_square

    def test_lazy_feature_types(self) -> None:
        from mycelium_fractal_net.types import (
            FEATURE_COUNT,
            FEATURE_NAMES,
        )

        assert len(FEATURE_NAMES) == FEATURE_COUNT

    def test_lazy_detection_types(self) -> None:
        from mycelium_fractal_net.types import (
            DetectionEvidence,
        )

        e = DetectionEvidence(change_score=0.5)
        assert e.change_score == 0.5

    def test_lazy_analytics_types(self) -> None:
        from mycelium_fractal_net.types import (
            StabilityMetrics,
        )

        s = StabilityMetrics(instability_index=0.1)
        assert s.instability_index == 0.1

    def test_lazy_forecast_types(self) -> None:
        from mycelium_fractal_net.types import ForecastResult

        assert ForecastResult is not None

    def test_lazy_report_type(self) -> None:
        from mycelium_fractal_net.types import AnalysisReport

        assert AnalysisReport is not None

    def test_lazy_scenario_types(self) -> None:
        from mycelium_fractal_net.types import ScenarioType

        assert ScenarioType is not None

    def test_lazy_dataset_types(self) -> None:
        from mycelium_fractal_net.types import DatasetRow

        assert DatasetRow is not None

    def test_lazy_neuromod_snapshot(self) -> None:
        from mycelium_fractal_net.types import NeuromodulationStateSnapshot

        ns = NeuromodulationStateSnapshot()
        assert ns.occupancy_resting == 1.0


class TestGridOpsNonPeriodicBoundaries:
    """Cover numerics/grid_ops.py Neumann/Dirichlet paths (53% → 80%+)."""

    def test_laplacian_neumann(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import (
            BoundaryCondition,
            compute_laplacian,
        )

        field = np.arange(25, dtype=np.float64).reshape(5, 5) / 10.0
        lap = compute_laplacian(field, boundary=BoundaryCondition.NEUMANN)
        assert lap.shape == (5, 5)
        assert np.isfinite(lap).all()

    def test_laplacian_dirichlet(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import (
            BoundaryCondition,
            compute_laplacian,
        )

        field = np.arange(25, dtype=np.float64).reshape(5, 5) / 10.0
        lap = compute_laplacian(field, boundary=BoundaryCondition.DIRICHLET)
        assert lap.shape == (5, 5)
        assert np.isfinite(lap).all()

    def test_gradient_neumann(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import (
            BoundaryCondition,
            compute_gradient,
        )

        field = np.arange(25, dtype=np.float64).reshape(5, 5) / 10.0
        gx, _gy = compute_gradient(field, boundary=BoundaryCondition.NEUMANN)
        assert gx.shape == (5, 5)
        # Neumann: zero gradient at boundaries
        assert gx[0, :].sum() == pytest.approx(0.0)
        assert gx[-1, :].sum() == pytest.approx(0.0)

    def test_gradient_dirichlet(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import (
            BoundaryCondition,
            compute_gradient,
        )

        field = np.arange(25, dtype=np.float64).reshape(5, 5) / 10.0
        gx, _gy = compute_gradient(field, boundary=BoundaryCondition.DIRICHLET)
        assert gx.shape == (5, 5)
        assert np.isfinite(gx).all()

    def test_field_statistics(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import compute_field_statistics

        field = np.random.default_rng(42).normal(0, 1, (8, 8))
        stats = compute_field_statistics(field)
        assert "mean" in stats
        assert "std" in stats
        assert "nan_count" in stats
        assert stats["nan_count"] == 0

    def test_validate_field_bounds(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import validate_field_bounds

        field = np.array([[0.1, 0.5], [0.3, 0.9]])
        assert validate_field_bounds(field, 0.0, 1.0)
        assert not validate_field_bounds(field, 0.2, 0.8)

    def test_clamp_field(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import clamp_field

        field = np.array([[-0.2, 0.5], [1.5, 0.3]])
        clamped, count = clamp_field(field, 0.0, 1.0)
        assert count == 2
        assert float(clamped.min()) >= 0.0
        assert float(clamped.max()) <= 1.0
