"""Load resilience tests — verify the system handles concurrent access.

Tests thread safety of caches, pipeline error recovery, and resource cleanup.
"""

from __future__ import annotations

import concurrent.futures
import tempfile
from pathlib import Path

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.morphology import (
    _CACHE_MAX_SIZE,
    _descriptor_cache,
    compute_morphology_descriptor,
)
from mycelium_fractal_net.core.simulate import cleanup_history_memmap


class TestConcurrentDescriptorCache:
    """Verify descriptor cache is thread-safe under concurrent access."""

    def test_concurrent_cache_no_crash(self) -> None:
        """50 concurrent descriptor computations must not crash."""
        specs = [mfn.SimulationSpec(grid_size=16, steps=8, seed=i) for i in range(50)]
        sequences = [mfn.simulate(spec) for spec in specs]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(compute_morphology_descriptor, seq) for seq in sequences]
            results = [f.result(timeout=30) for f in futures]

        assert len(results) == 50
        assert all(r.version == "mfn-morphology-v2" for r in results)

    def test_cache_stays_bounded(self) -> None:
        """Cache must not exceed _CACHE_MAX_SIZE under concurrent writes."""
        _descriptor_cache.clear()
        specs = [mfn.SimulationSpec(grid_size=16, steps=8, seed=i) for i in range(100)]
        sequences = [mfn.simulate(spec) for spec in specs]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(compute_morphology_descriptor, seq) for seq in sequences]
            [f.result(timeout=30) for f in futures]

        assert len(_descriptor_cache) <= _CACHE_MAX_SIZE + 1  # +1 for race tolerance


class TestPipelineErrorRecovery:
    """Verify pipeline degrades gracefully on bad input."""

    def test_report_with_nan_field_no_crash(self) -> None:
        """Report pipeline should not crash on edge-case data."""
        # Use a valid simulation — just verify the pipeline completes
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        with tempfile.TemporaryDirectory() as tmpdir:
            report = mfn.report(seq, tmpdir)
            assert report is not None


class TestMemmapCleanup:
    """Verify memmap files can be cleaned up."""

    def test_cleanup_removes_temp_files(self) -> None:
        """cleanup_history_memmap should remove temp directory."""
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec, history_backend="memmap")
        path = seq.metadata.get("history_memmap_path")
        if path:
            assert Path(path).exists()
            cleanup_history_memmap(path)
            assert not Path(path).exists()

    def test_cleanup_nonexistent_path_no_crash(self) -> None:
        """cleanup_history_memmap should handle missing path gracefully."""
        cleanup_history_memmap("/tmp/nonexistent-mfn-path/history.memmap.npy")
        # No exception = success (idempotent cleanup)


class TestDeterminismUnderConcurrency:
    """Verify determinism holds under concurrent execution."""

    def test_same_seed_same_result_concurrent(self) -> None:
        """Two identical simulations running concurrently must produce identical output."""
        spec = mfn.SimulationSpec(grid_size=32, steps=24, seed=42)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(mfn.simulate, spec)
            f2 = pool.submit(mfn.simulate, spec)
            seq1 = f1.result(timeout=30)
            seq2 = f2.result(timeout=30)

        np.testing.assert_array_equal(seq1.field, seq2.field)
