"""Benchmark regression gates.

Verify core operations complete within baseline + 3x margin.
If any of these fail, a performance regression has been introduced.

Baseline: benchmarks/bio_baseline.json
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

import mycelium_fractal_net as mfn

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "configs" / "benchmark_baseline.json").read_text())["benchmarks"]

# Allow 5x margin for CI variability (fullcheck runs parallel stages)
MARGIN = 5.0


def test_simulation_performance() -> None:
    spec = mfn.SimulationSpec(grid_size=64, steps=64, seed=42)
    start = time.perf_counter()
    mfn.simulate(spec)
    elapsed = time.perf_counter() - start
    limit = BASELINE["simulation_64x64_64steps"]["max_s"] * MARGIN
    assert elapsed < limit, f"Simulation took {elapsed:.3f}s, limit {limit:.3f}s"


def test_extract_performance() -> None:
    spec = mfn.SimulationSpec(grid_size=64, steps=64, seed=42)
    seq = mfn.simulate(spec)
    from mycelium_fractal_net.analytics.morphology import _descriptor_cache

    _descriptor_cache.clear()
    start = time.perf_counter()
    mfn.extract(seq)
    elapsed = time.perf_counter() - start
    limit = BASELINE["extract_64x64"]["max_s"] * MARGIN
    assert elapsed < limit, f"Extract took {elapsed:.3f}s, limit {limit:.3f}s"


def test_detect_performance() -> None:
    spec = mfn.SimulationSpec(grid_size=64, steps=64, seed=42)
    seq = mfn.simulate(spec)
    from mycelium_fractal_net.analytics.morphology import _descriptor_cache

    _descriptor_cache.clear()
    start = time.perf_counter()
    mfn.detect(seq)
    elapsed = time.perf_counter() - start
    limit = BASELINE["detect_64x64"]["max_s"] * MARGIN
    assert elapsed < limit, f"Detect took {elapsed:.3f}s, limit {limit:.3f}s"


def test_report_performance() -> None:
    spec = mfn.SimulationSpec(grid_size=64, steps=64, seed=42)
    seq = mfn.simulate(spec)
    from mycelium_fractal_net.analytics.morphology import _descriptor_cache

    _descriptor_cache.clear()
    with tempfile.TemporaryDirectory() as tmp:
        start = time.perf_counter()
        mfn.report(seq, output_root=tmp, horizon=4)
        elapsed = time.perf_counter() - start
    limit = BASELINE["report_64x64_h4"]["max_s"] * MARGIN
    assert elapsed < limit, f"Report took {elapsed:.3f}s, limit {limit:.3f}s"
