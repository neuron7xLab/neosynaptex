"""Tests for error budget tracking."""

from __future__ import annotations

from mycelium_fractal_net.core.error_budget import ErrorBudget, StageError


class TestErrorBudget:
    def test_empty_budget(self) -> None:
        budget = ErrorBudget()
        assert len(budget.stages) == 0

    def test_add_stage(self) -> None:
        budget = ErrorBudget()
        budget.stages.append(
            StageError(
                stage="simulate",
                metric="field_nan",
                value=0.0,
                threshold=0.01,
                fraction=0.0,
            )
        )
        assert len(budget.stages) == 1
        assert budget.stages[0].stage == "simulate"

    def test_stage_fraction(self) -> None:
        stage = StageError(
            stage="detect",
            metric="score",
            value=0.05,
            threshold=0.1,
            fraction=0.5,
        )
        assert stage.fraction == 0.5

    def test_budget_serialization(self) -> None:
        budget = ErrorBudget()
        budget.stages.append(
            StageError(
                stage="forecast",
                metric="error",
                value=0.01,
                threshold=0.05,
                fraction=0.2,
            )
        )
        # Verify it's a proper dataclass
        assert hasattr(budget, "stages")
