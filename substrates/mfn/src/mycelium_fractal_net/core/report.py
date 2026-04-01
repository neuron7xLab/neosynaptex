"""Pipeline report generation with signed artifact bundles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.report import AnalysisReport


def report(
    sequence: FieldSequence,
    output_root: str | Path,
    *,
    horizon: int = 8,
    comparison_sequence: FieldSequence | None = None,
) -> AnalysisReport:
    """Canonical report generation operation."""
    from mycelium_fractal_net.pipelines.reporting import build_analysis_report

    return build_analysis_report(
        sequence,
        output_root=output_root,
        horizon=horizon,
        comparison_sequence=comparison_sequence,
    )
