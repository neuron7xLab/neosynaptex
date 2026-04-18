"""Performance regression gate for the Decision Bridge.

Failure of this gate means something upstream is now eating latency
that was previously free — a regression worth investigating *before*
it reaches production.

Methodology
-----------
* Fixed random seed per test — identical inputs across CI runs.
* Warm the JIT / page cache with a throw-away warm-up block so the
  first call's import / allocation cost doesn't bias percentiles.
* Measure the **median** and the **p95** over ≥ 200 samples;
  medians are stable against one-off GC pauses, p95 bounds tail
  latency.
* Assert absolute wall-clock budgets, not relative deltas. The
  budgets are set with 3-5× headroom over the current measurement
  on a CI-class single-thread box, so transient noise never fails
  the gate while a genuine 10× regression always does.

Why no pytest-benchmark?
------------------------
pytest-benchmark is excellent for sweeping parameter spaces but
introduces a new dependency, a JSON-compare step, and a binary
artefact to review. For a single regression budget, bare
``time.perf_counter_ns`` + numpy percentiles is both simpler and
less noisy.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
import pytest

from core.decision_bridge import DecisionBridge

_SEED = 7
_WARMUP = 20
_SAMPLES = 200


def _latencies_ns(fn: Callable[[int], None], ticks: int) -> np.ndarray:
    latencies = np.zeros(ticks, dtype=np.int64)
    for t in range(ticks):
        start = time.perf_counter_ns()
        fn(t)
        latencies[t] = time.perf_counter_ns() - start
    return latencies


def _percentiles(samples_ns: np.ndarray) -> tuple[float, float, float]:
    """Return (median, p95, p99) in microseconds."""
    ms = samples_ns.astype(np.float64) / 1_000.0
    return (
        float(np.median(ms)),
        float(np.percentile(ms, 95)),
        float(np.percentile(ms, 99)),
    )


@pytest.mark.slow
class TestDecisionBridgeLatency:
    """Absolute latency budgets with heavy head-room.

    Budgets are intentionally loose — any green run anywhere between
    a fast workstation and a noisy GitHub runner is acceptable. The
    gate only fires on order-of-magnitude regressions.
    """

    @pytest.mark.parametrize(
        ("history_n", "budget_p95_us"),
        [
            (20, 15_000.0),  # Typical engine output window. 15 ms p95 budget.
            (100, 40_000.0),  # Heavier window. 40 ms p95 budget.
        ],
    )
    def test_evaluate_latency_within_budget(self, history_n: int, budget_p95_us: float) -> None:
        rng = np.random.default_rng(_SEED)
        phi = rng.normal(0, 0.1, size=(history_n, 4))
        gamma = 1.0 + rng.normal(0, 0.02, size=history_n)
        bridge = DecisionBridge()

        def call(tick: int) -> None:
            bridge.evaluate(
                tick=tick,
                gamma_mean=1.0,
                gamma_std=0.02,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )

        for t in range(_WARMUP):
            call(t)

        samples_ns = _latencies_ns(lambda tick, offset=_WARMUP: call(tick + offset), _SAMPLES)
        median, p95, p99 = _percentiles(samples_ns)

        # Record for future triage — pytest will show these in -v output.
        print(
            f"[bench n={history_n}] median={median:.1f}µs "
            f"p95={p95:.1f}µs p99={p99:.1f}µs budget_p95={budget_p95_us:.0f}µs"
        )
        assert p95 < budget_p95_us, (
            f"p95 latency {p95:.1f}µs exceeds budget {budget_p95_us:.0f}µs "
            f"(median {median:.1f}µs, p99 {p99:.1f}µs). Investigate upstream."
        )

    def test_idempotent_calls_are_near_free(self) -> None:
        """Re-evaluating the same tick must be ~memoised-read-cost,
        i.e. an order of magnitude below a fresh evaluation."""
        rng = np.random.default_rng(_SEED)
        phi = rng.normal(0, 0.1, size=(20, 4))
        gamma = 1.0 + rng.normal(0, 0.02, size=20)
        bridge = DecisionBridge()

        # Cold first call.
        t0 = time.perf_counter_ns()
        bridge.evaluate(
            tick=42,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        cold_ns = time.perf_counter_ns() - t0

        # Repeated memoised reads.
        samples = np.zeros(200, dtype=np.int64)
        for i in range(200):
            t_i = time.perf_counter_ns()
            bridge.evaluate(
                tick=42,
                gamma_mean=1.0,
                gamma_std=0.02,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
            samples[i] = time.perf_counter_ns() - t_i

        median_hot = float(np.median(samples))
        # Memoised path must be at least 5× faster than the cold path.
        # Typically ~100× faster — 5× is a strict lower bound.
        assert median_hot * 5 < cold_ns, (
            f"Memoised evaluate ({median_hot:.0f}ns median) is not "
            f"meaningfully faster than cold ({cold_ns}ns). "
            "Idempotence cache may be broken."
        )
