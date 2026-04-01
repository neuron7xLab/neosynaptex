#!/usr/bin/env python3
"""Regression gate for physics and kernel benchmarks.

Compares current benchmark results against committed baselines and fails when
performance regresses beyond a configured threshold.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from bnsyn.benchmarks.regime import BENCHMARK_REGIME_ID


@dataclass(frozen=True)
class MetricSpec:
    """Defines a metric's comparison direction."""

    name: str
    higher_is_better: bool


@dataclass(frozen=True)
class MetricComparison:
    """Comparison result for a single metric."""

    name: str
    baseline: float
    current: float
    change_pct: float
    higher_is_better: bool
    status: str
    note: str


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON data from a file."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_nested_value(data: dict[str, Any], path: str) -> float | None:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if isinstance(current, (int, float)):
        return float(current)
    return None


def collect_physics_metrics(data: dict[str, Any]) -> list[MetricSpec]:
    return [
        MetricSpec("performance.updates_per_sec", higher_is_better=True),
        MetricSpec("performance.spikes_per_sec", higher_is_better=True),
        MetricSpec("performance.energy_cost", higher_is_better=True),
        MetricSpec("performance.wall_time_sec", higher_is_better=False),
    ]


def collect_kernel_metrics(data: dict[str, Any]) -> list[MetricSpec]:
    kernels = data.get("kernels", {})
    specs: list[MetricSpec] = []
    if not isinstance(kernels, dict):
        return specs
    for kernel_name, metrics in kernels.items():
        if not isinstance(metrics, dict):
            continue
        for metric_key in (
            "total_time_sec",
            "avg_time_sec",
            "max_time_sec",
            "min_time_sec",
            "avg_memory_mb",
        ):
            metric_path = f"kernels.{kernel_name}.{metric_key}"
            if metric_key in metrics:
                specs.append(MetricSpec(metric_path, higher_is_better=False))
    return specs


def compare_metric(
    *,
    name: str,
    baseline: float,
    current: float,
    higher_is_better: bool,
    threshold: float,
) -> MetricComparison:
    if baseline == 0.0:
        note = "baseline is zero; comparison skipped"
        return MetricComparison(
            name=name,
            baseline=baseline,
            current=current,
            change_pct=0.0,
            higher_is_better=higher_is_better,
            status="skipped",
            note=note,
        )

    change_pct = (current - baseline) / baseline
    status = "ok"
    note = "within threshold"

    if higher_is_better:
        if change_pct < -threshold:
            status = "regression"
            note = f"throughput drop {abs(change_pct):.2%} exceeds {threshold:.2%}"
    else:
        if change_pct > threshold:
            status = "regression"
            note = f"latency increase {change_pct:.2%} exceeds {threshold:.2%}"

    return MetricComparison(
        name=name,
        baseline=baseline,
        current=current,
        change_pct=change_pct,
        higher_is_better=higher_is_better,
        status=status,
        note=note,
    )


MAX_TIME_THRESHOLD = 0.25
THRESHOLD_OVERRIDES = {
    "performance.updates_per_sec": 0.15,
    "performance.energy_cost": 0.15,
    "performance.wall_time_sec": 0.15,
    "kernels.adex_update.total_time_sec": 0.30,
    "kernels.adex_update.avg_time_sec": 0.30,
    "kernels.adex_update.min_time_sec": 0.30,
}


def _threshold_for_metric(
    name: str,
    default: float,
    overrides: dict[str, float] | None = None,
) -> float:
    if overrides is not None:
        override = overrides.get(name)
        if override is not None:
            return max(default, override)
    override = THRESHOLD_OVERRIDES.get(name)
    if override is not None:
        return max(default, override)
    if name.endswith(".max_time_sec"):
        return max(default, MAX_TIME_THRESHOLD)
    return default


def compare_datasets(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    specs: Iterable[MetricSpec],
    threshold: float,
) -> list[MetricComparison]:
    results: list[MetricComparison] = []
    threshold_overrides = baseline.get("thresholds")
    if threshold_overrides is not None and not isinstance(threshold_overrides, dict):
        raise SystemExit("Invalid benchmark thresholds format")
    for spec in specs:
        base_value = _get_nested_value(baseline, spec.name)
        curr_value = _get_nested_value(current, spec.name)
        if base_value is None or curr_value is None:
            missing = "baseline" if base_value is None else "current"
            note = f"missing {missing} metric"
            results.append(
                MetricComparison(
                    name=spec.name,
                    baseline=base_value or 0.0,
                    current=curr_value or 0.0,
                    change_pct=0.0,
                    higher_is_better=spec.higher_is_better,
                    status="regression",
                    note=note,
                )
            )
            continue
        results.append(
            compare_metric(
                name=spec.name,
                baseline=base_value,
                current=curr_value,
                higher_is_better=spec.higher_is_better,
                threshold=_threshold_for_metric(spec.name, threshold, threshold_overrides),
            )
        )
    return results


def render_report(results: list[MetricComparison]) -> str:
    lines = ["Benchmark Regression Report", "=" * 28]
    for result in results:
        status_icon = "✅" if result.status == "ok" else "⚠️" if result.status == "skipped" else "❌"
        direction = "higher" if result.higher_is_better else "lower"
        lines.append(
            f"{status_icon} {result.name}: baseline={result.baseline:.6g}, "
            f"current={result.current:.6g}, change={result.change_pct:+.2%}, "
            f"{direction} better ({result.note})"
        )
    return "\n".join(lines)


def render_markdown(results: list[MetricComparison]) -> str:
    lines = [
        "| Metric | Baseline | Current | Change | Direction | Status | Note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        direction = "higher" if result.higher_is_better else "lower"
        status = result.status
        lines.append(
            f"| {result.name} | {result.baseline:.6g} | {result.current:.6g} | "
            f"{result.change_pct:+.2%} | {direction} | {status} | {result.note} |"
        )
    return "\n".join(lines)


def render_json(results: list[MetricComparison]) -> str:
    payload = [
        {
            "metric": result.name,
            "baseline": result.baseline,
            "current": result.current,
            "change_pct": result.change_pct,
            "higher_is_better": result.higher_is_better,
            "status": result.status,
            "note": result.note,
        }
        for result in results
    ]
    return json.dumps(payload, indent=2)


def compare_benchmarks(
    *,
    physics_baseline: Path,
    physics_current: Path,
    kernel_baseline: Path,
    kernel_current: Path,
    threshold: float,
) -> tuple[list[MetricComparison], bool]:
    physics_base = load_json(physics_baseline)
    physics_curr = load_json(physics_current)
    kernel_base = load_json(kernel_baseline)
    kernel_curr = load_json(kernel_current)

    for label, baseline_data, current_data in (
        ("physics", physics_base, physics_curr),
        ("kernels", kernel_base, kernel_curr),
    ):
        baseline_regime = baseline_data.get("regime_id")
        current_regime = current_data.get("regime_id")
        if baseline_regime is None or current_regime is None:
            raise SystemExit(f"Missing benchmark regime_id for {label}")
        if baseline_regime != current_regime or baseline_regime != BENCHMARK_REGIME_ID:
            raise SystemExit(
                f"Benchmark regime mismatch for {label}: "
                f"baseline={baseline_regime}, current={current_regime}, "
                f"expected={BENCHMARK_REGIME_ID}"
            )
        baseline_config = baseline_data.get("configuration")
        current_config = current_data.get("configuration")
        if not isinstance(baseline_config, dict) or not isinstance(current_config, dict):
            raise SystemExit(f"Missing configuration for {label}")
        for key in ("neurons", "dt_ms", "steps"):
            if baseline_config.get(key) != current_config.get(key):
                raise SystemExit(
                    f"Benchmark configuration mismatch for {label}: "
                    f"{key} baseline={baseline_config.get(key)} current={current_config.get(key)}"
                )

    results = []
    results.extend(
        compare_datasets(
            baseline=physics_base,
            current=physics_curr,
            specs=collect_physics_metrics(physics_base),
            threshold=threshold,
        )
    )
    results.extend(
        compare_datasets(
            baseline=kernel_base,
            current=kernel_curr,
            specs=collect_kernel_metrics(kernel_base),
            threshold=threshold,
        )
    )

    has_regression = any(result.status == "regression" for result in results)
    return results, has_regression


def main() -> None:
    parser = argparse.ArgumentParser(description="Check benchmark regressions")
    parser.add_argument(
        "--physics-baseline",
        type=Path,
        default=Path("benchmarks/baselines/physics_baseline.json"),
    )
    parser.add_argument(
        "--physics-current",
        type=Path,
        default=Path("benchmarks/physics_baseline.json"),
    )
    parser.add_argument(
        "--kernel-baseline",
        type=Path,
        default=Path("benchmarks/baselines/kernel_profile.json"),
    )
    parser.add_argument(
        "--kernel-current",
        type=Path,
        default=Path("benchmarks/kernel_profile.json"),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="Regression threshold (default: 0.10 = 10%%)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
    )

    args = parser.parse_args()

    results, has_regression = compare_benchmarks(
        physics_baseline=args.physics_baseline,
        physics_current=args.physics_current,
        kernel_baseline=args.kernel_baseline,
        kernel_current=args.kernel_current,
        threshold=args.threshold,
    )

    if args.format == "markdown":
        report = render_markdown(results)
    elif args.format == "json":
        report = render_json(results)
    else:
        report = render_report(results)

    print(report)

    if has_regression:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
