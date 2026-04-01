"""Tests for FieldAdapter — external data loading into MFN pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

import mycelium_fractal_net as mfn


def test_load_2d_array() -> None:
    """Single 2D array → FieldSequence with no history."""
    field = np.random.default_rng(42).standard_normal((32, 32))
    seq = mfn.load(field)
    assert seq.field.shape == (32, 32)
    assert seq.history is None
    assert np.isfinite(seq.field).all()


def test_load_3d_array() -> None:
    """3D array (T, H, W) → FieldSequence with history."""
    history = np.random.default_rng(42).standard_normal((20, 16, 16))
    seq = mfn.load(history)
    assert seq.field.shape == (16, 16)
    assert seq.history is not None
    assert seq.history.shape == (20, 16, 16)


def test_load_normalizes_to_biophysical_range() -> None:
    """Data outside [-0.095, 0.040] is rescaled."""
    field = np.random.default_rng(42).standard_normal((32, 32)) * 100
    seq = mfn.load(field, normalize=True)
    assert seq.field.min() >= -0.095 - 1e-6
    assert seq.field.max() <= 0.040 + 1e-6


def test_load_rejects_non_finite() -> None:
    """NaN/Inf data raises ValueError."""
    field = np.ones((16, 16))
    field[5, 5] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        mfn.load(field)


def test_load_npy_file() -> None:
    """Load from .npy file."""
    field = np.random.default_rng(42).standard_normal((16, 16))
    with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
        np.save(f, field)
        path = f.name
    seq = mfn.load(path)
    assert seq.field.shape == (16, 16)
    Path(path).unlink()


def test_load_csv_file() -> None:
    """Load from .csv file."""
    field = np.random.default_rng(42).standard_normal((16, 16))
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        np.savetxt(f, field, delimiter=",")
        path = f.name
    seq = mfn.load(path)
    assert seq.field.shape == (16, 16)
    Path(path).unlink()


def test_full_pipeline_on_loaded_data() -> None:
    """Loaded data works through detect → extract → diagnose."""
    history = np.random.default_rng(42).standard_normal((30, 16, 16)) * 0.03
    seq = mfn.load(history)

    det = mfn.detect(seq)
    assert det.label in ("nominal", "watch", "anomalous")

    desc = mfn.extract(seq)
    assert len(desc.embedding) > 0

    diag = mfn.diagnose(seq)
    assert diag.severity in ("stable", "info", "warning", "critical")

    json.dumps(det.to_dict())
    json.dumps(desc.to_dict())
    json.dumps(diag.to_dict())


def test_load_in_all() -> None:
    """mfn.load is in __all__. FieldAdapter is internal (use mfn.load instead)."""
    assert "load" in mfn.__all__
    # FieldAdapter is accessible but not in curated __all__
    assert hasattr(mfn, "FieldAdapter")
