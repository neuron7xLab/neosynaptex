"""Unit tests for emergence_plot.py using headless matplotlib backend."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def _write_minimal_valid_npz(path: Path) -> None:
    """Write a minimal valid emergence NPZ fixture."""
    np.savez(
        path,
        format_version=np.asarray("1.1.0"),
        spike_steps=np.asarray([1, 3, 5], dtype=np.int64),
        spike_neurons=np.asarray([0, 1, 2], dtype=np.int64),
        sigma_trace=np.asarray([0.9, 1.0, 1.1, 1.0, 0.95, 1.02], dtype=np.float32),
        rate_trace_hz=np.asarray([5.0, 6.0, 5.5, 6.2, 5.8, 6.1], dtype=np.float32),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(6, dtype=np.int64),
        N=np.asarray(10, dtype=np.int64),
        seed=np.asarray(42, dtype=np.int64),
        external_current_pA=np.asarray(120.0, dtype=np.float32),
    )


def test_plot_emergence_npz_creates_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")
    pytest.importorskip("matplotlib")
    from bnsyn.viz.emergence_plot import plot_emergence_npz

    npz_path = tmp_path / "traces.npz"
    out_path = tmp_path / "emergence_plot.png"
    _write_minimal_valid_npz(npz_path)

    plot_emergence_npz(str(npz_path), str(out_path))
    assert out_path.is_file()
    assert out_path.stat().st_size > 0


def test_plot_emergence_npz_rejects_missing_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")
    pytest.importorskip("matplotlib")
    from bnsyn.viz.emergence_plot import plot_emergence_npz

    with pytest.raises((FileNotFoundError, ValueError, Exception)):
        plot_emergence_npz(
            str(tmp_path / "nonexistent.npz"),
            str(tmp_path / "out.png"),
        )


def test_plot_emergence_npz_rejects_wrong_format_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")
    pytest.importorskip("matplotlib")
    from bnsyn.viz.emergence_plot import plot_emergence_npz

    npz_path = tmp_path / "bad_version.npz"
    np.savez(
        npz_path,
        format_version=np.asarray("1.0.0"),
        spike_steps=np.asarray([1], dtype=np.int64),
        spike_neurons=np.asarray([0], dtype=np.int64),
        sigma_trace=np.asarray([1.0], dtype=np.float32),
        rate_trace_hz=np.asarray([5.0], dtype=np.float32),
        dt_ms=np.asarray(0.1),
        steps=np.asarray(1, dtype=np.int64),
        N=np.asarray(1, dtype=np.int64),
        seed=np.asarray(1, dtype=np.int64),
        external_current_pA=np.asarray(100.0, dtype=np.float32),
    )
    out_path = tmp_path / "out.png"

    with pytest.raises((ValueError, KeyError, Exception)):
        plot_emergence_npz(str(npz_path), str(out_path))
