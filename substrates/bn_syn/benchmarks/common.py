"""Shared helpers for deterministic benchmark execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import subprocess
import resource


@dataclass(frozen=True)
class BenchmarkContext:
    seed: int
    n_neurons: int
    dt_ms: float
    timestamp: str
    git_sha: str


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def peak_rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0


def build_context(seed: int, n_neurons: int, dt_ms: float) -> BenchmarkContext:
    return BenchmarkContext(
        seed=seed,
        n_neurons=n_neurons,
        dt_ms=dt_ms,
        timestamp=utc_timestamp(),
        git_sha=git_sha(),
    )


def metric_payload(
    ctx: BenchmarkContext,
    metric_name: str,
    value: float,
    units: str,
    benchmark: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "metric_name": metric_name,
        "N": ctx.n_neurons,
        "dt": ctx.dt_ms,
        "seed": ctx.seed,
        "value": float(value),
        "units": units,
        "timestamp": ctx.timestamp,
        "git_sha": ctx.git_sha,
        "benchmark": benchmark,
    }
    if extra:
        payload.update(extra)
    return payload
