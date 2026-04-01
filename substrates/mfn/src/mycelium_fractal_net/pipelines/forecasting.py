from __future__ import annotations

from typing import TYPE_CHECKING

from mycelium_fractal_net.core.forecast import forecast_next

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.forecast import ForecastResult


def run_forecast_pipeline(sequence: FieldSequence, horizon: int = 8) -> ForecastResult:
    return forecast_next(sequence, horizon=horizon)
