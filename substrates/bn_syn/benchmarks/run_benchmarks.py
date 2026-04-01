#!/usr/bin/env python3
"""Benchmark harness for BN-Syn benchmarking and validation."""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.scenarios import get_scenarios

try:
    import torch
    from torch.utils.bottleneck import bottleneck
except Exception:  # pragma: no cover - optional GPU tooling
    torch = None
    bottleneck = None


def get_git_sha() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def get_python_version() -> str:
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def run_scenario_subprocess(scenario_dict: dict[str, Any]) -> dict[str, Any] | None:
    """Run a benchmark scenario in a subprocess for isolation."""
    repo_root = Path.cwd()
    repo_src = repo_root / "src"
    script = f"""
import atexit
import shutil
import tempfile
import resource
import sys
import json
sys.path.insert(0, {repr(str(repo_root))})
sys.path.insert(0, {repr(str(repo_src))})

from benchmarks.metrics import metrics_to_dict, run_benchmark
from benchmarks.scenarios.base import BenchmarkScenario

tmpdir = tempfile.mkdtemp(prefix="bnsyn-bench-")
atexit.register(lambda: shutil.rmtree(tmpdir, ignore_errors=True))

limit_bytes = 1024 * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

scenario = BenchmarkScenario(**{repr(scenario_dict)})
result = run_benchmark(scenario)
print(json.dumps(metrics_to_dict(result)))
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=600,
            check=True,
        )
        return json.loads(result.stdout.strip())
    except subprocess.TimeoutExpired:
        print("  WARNING: scenario timed out", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  WARNING: scenario failed: {exc}", file=sys.stderr)
        return None


def aggregate_metrics(runs: list[dict[str, Any]]) -> dict[str, float | None]:
    """Aggregate metrics across multiple runs using mean/std/p5/p50/p95."""
    import numpy as np
    from scipy.stats import zscore

    if not runs:
        return {}

    keys = list(runs[0].keys())
    aggregated: dict[str, float | None] = {}
    for key in keys:
        raw_values = [run.get(key) for run in runs]
        values = np.asarray(
            [float(value) for value in raw_values if value is not None],
            dtype=np.float64,
        )
        values = values[np.isfinite(values)]
        if values.size >= 3:
            z = np.abs(zscore(values, nan_policy="omit"))
            values = values[z <= 2.0]
        if values.size == 0:
            aggregated[f"{key}_mean"] = None
            aggregated[f"{key}_std"] = None
            aggregated[f"{key}_p5"] = None
            aggregated[f"{key}_p50"] = None
            aggregated[f"{key}_p95"] = None
            continue
        aggregated[f"{key}_mean"] = float(np.mean(values))
        aggregated[f"{key}_std"] = float(np.std(values))
        aggregated[f"{key}_p5"] = float(np.percentile(values, 5))
        aggregated[f"{key}_p50"] = float(np.percentile(values, 50))
        aggregated[f"{key}_p95"] = float(np.percentile(values, 95))
    return aggregated


def _sanitize_for_json(payload: Any) -> Any:
    if isinstance(payload, float):
        if math.isfinite(payload):
            return payload
        return None
    if isinstance(payload, list):
        return [_sanitize_for_json(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _sanitize_for_json(value) for key, value in payload.items()}
    return payload


def run_benchmarks(
    scenario_set: str,
    repeats: int,
    output_json: str | None,
    output_csv: str | None,
    warmup: int,
) -> list[dict[str, Any]]:
    """Run benchmark scenarios and return results."""
    scenarios = get_scenarios(scenario_set)
    git_sha = get_git_sha()
    python_ver = get_python_version()
    timestamp = datetime.now().astimezone().isoformat()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler("bench.log", mode="w"), logging.StreamHandler(sys.stdout)],
    )
    logging.info("Running %d scenarios with %d repeats each", len(scenarios), repeats)
    logging.info("Warmup runs per scenario: %d", warmup)
    logging.info("Git SHA: %s", git_sha)
    logging.info("Python: %s", python_ver)
    logging.info("Timestamp: %s", timestamp)

    device = None
    if torch is not None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        torch.manual_seed(42)
        logging.info("Torch device: %s", device)
        os.environ["BNSYN_USE_TORCH"] = "1"
        os.environ["BNSYN_DEVICE"] = str(device)

    all_results: list[dict[str, Any]] = []

    for idx, scenario in enumerate(scenarios):
        logging.info(
            f"[{idx + 1}/{len(scenarios)}] {scenario.name}: "
            f"N={scenario.N_neurons}, steps={scenario.steps}, dt={scenario.dt_ms}ms"
        )
        scenario_dict = scenario.to_dict()

        for warmup_idx in range(warmup):
            logging.info("  Warmup %d/%d...", warmup_idx + 1, warmup)
            _ = run_scenario_subprocess(scenario_dict)

        runs: list[dict[str, Any]] = []
        for repeat in range(repeats):
            logging.info("  Repeat %d/%d...", repeat + 1, repeats)
            metrics = run_scenario_subprocess(scenario_dict)
            if metrics is None:
                logging.info("  FAILED")
                continue
            runs.append(metrics)
            logging.info(
                "  wall_time=%.3fs, rss=%.1fMB, sigma=%.3f",
                metrics["performance_wall_time_sec"],
                metrics["performance_peak_rss_mb"],
                metrics["physics_sigma"],
            )

        if not runs:
            logging.info("  ERROR: All runs failed, skipping scenario")
            continue

        aggregated = aggregate_metrics(runs)
        all_results.append(
            {
                "scenario": scenario.name,
                "git_sha": git_sha,
                "python_version": python_ver,
                "timestamp": timestamp,
                **scenario_dict,
                "warmup": warmup,
                "repeats": len(runs),
                **aggregated,
            }
        )
        summary_wall_time = aggregated.get("performance_wall_time_sec_mean")
        summary_sigma = aggregated.get("physics_sigma_mean")
        summary_nan_rate = aggregated.get("stability_nan_rate_mean")
        summary_wall_time_p50 = aggregated.get("performance_wall_time_sec_p50")
        summary_wall_time_p95 = aggregated.get("performance_wall_time_sec_p95")
        summary_rss_p95 = aggregated.get("performance_peak_rss_mb_p95")
        if summary_wall_time is None:
            logging.info("  Summary: wall_time_mean=n/a")
        else:
            logging.info("  Summary: wall_time_mean=%.3fs", summary_wall_time)
        if summary_sigma is not None and summary_nan_rate is not None:
            logging.info(
                "  Summary: sigma_mean=%.3f, nan_rate=%.6f",
                summary_sigma,
                summary_nan_rate,
            )
        if (
            summary_wall_time_p50 is not None
            and summary_wall_time_p95 is not None
            and summary_rss_p95 is not None
        ):
            logging.info(
                "  Summary: wall_time_p50=%.3fs, wall_time_p95=%.3fs, rss_p95=%.1fMB",
                summary_wall_time_p50,
                summary_wall_time_p95,
                summary_rss_p95,
            )

    if output_json and all_results:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(_sanitize_for_json(all_results), f, indent=2, allow_nan=False)
        logging.info("Wrote JSON: %s", output_json)

    if output_csv and all_results:
        import csv

        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(all_results[0].keys())
        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in _sanitize_for_json(all_results):
                writer.writerow(row)
        logging.info("Wrote CSV: %s", output_csv)

    if bottleneck is not None and device is not None and device.type == "cuda":
        bottleneck()

    return all_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BN-Syn benchmarks")
    parser.add_argument(
        "--scenario",
        default="small_network",
        choices=[
            "ci_smoke",
            "small_network",
            "medium_network",
            "large_network",
            "criticality_sweep",
            "temperature_sweep",
            "dt_sweep",
            "full",
        ],
        help="Scenario set to run",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Number of repeats per scenario")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup runs per scenario")
    parser.add_argument("--json", help="Output JSON file path")
    parser.add_argument("--csv", help="Output CSV file path")

    args = parser.parse_args()

    if args.repeats <= 0:
        raise SystemExit("repeats must be positive")
    if args.warmup < 0:
        raise SystemExit("warmup must be non-negative")

    run_benchmarks(
        scenario_set=args.scenario,
        repeats=args.repeats,
        output_json=args.json,
        output_csv=args.csv,
        warmup=args.warmup,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
