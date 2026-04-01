"""Tests for FieldAdapter — external data input."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.adapters import FieldAdapter
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency


class TestFieldAdapterArray:
    """Load from numpy arrays."""

    def test_load_2d_array(self) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (16, 16))
        seq = FieldAdapter.load(arr)
        assert seq.field.shape == (16, 16)
        assert seq.history is None
        assert seq.spec is None
        assert seq.metadata["source"] == "external"

    def test_load_3d_array(self) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (8, 16, 16))
        seq = FieldAdapter.load(arr)
        assert seq.field.shape == (16, 16)
        assert seq.history is not None
        assert seq.history.shape == (8, 16, 16)

    def test_normalization(self) -> None:
        """Data outside biophysical range is rescaled."""
        arr = np.random.default_rng(42).normal(0, 100, (16, 16))
        seq = FieldAdapter.load(arr, normalize=True)
        assert float(seq.field.min()) >= -0.095 - 1e-10
        assert float(seq.field.max()) <= 0.040 + 1e-10


class TestFieldAdapterFile:
    """Load from files."""

    def test_load_npy(self, tmp_path) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (16, 16))
        path = tmp_path / "test.npy"
        np.save(path, arr)
        seq = FieldAdapter.load(str(path))
        assert seq.field.shape == (16, 16)

    def test_load_csv(self, tmp_path) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (8, 8))
        path = tmp_path / "test.csv"
        np.savetxt(path, arr, delimiter=",")
        seq = FieldAdapter.load(path)
        assert seq.field.shape == (8, 8)

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            FieldAdapter.load("/nonexistent/path.npy")

    def test_unsupported_format(self, tmp_path) -> None:
        path = tmp_path / "test.xyz"
        path.write_text("data")
        with pytest.raises(ValueError, match="Unsupported"):
            FieldAdapter.load(path)


class TestFieldAdapterValidation:
    """Reject invalid data."""

    def test_reject_nan(self) -> None:
        arr = np.ones((8, 8))
        arr[3, 3] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            FieldAdapter.load(arr)

    def test_reject_inf(self) -> None:
        arr = np.ones((8, 8))
        arr[0, 0] = np.inf
        with pytest.raises(ValueError, match="non-finite"):
            FieldAdapter.load(arr)

    def test_reject_1d(self) -> None:
        with pytest.raises(ValueError, match="at least 2D"):
            FieldAdapter.load(np.ones(10))

    def test_reject_4d(self) -> None:
        with pytest.raises(ValueError, match="2D or 3D"):
            FieldAdapter.load(np.ones((2, 3, 4, 5)))

    def test_reject_out_of_range_no_normalize(self) -> None:
        arr = np.ones((8, 8)) * 100.0
        with pytest.raises(ValueError, match="outside biophysical"):
            FieldAdapter.load(arr, normalize=False)


class TestFieldAdapterPipeline:
    """Full pipeline through adapter."""

    def test_detect_on_loaded_data(self) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (16, 16))
        seq = FieldAdapter.load(arr)
        event = seq.detect()
        assert event.label in {"nominal", "watch", "anomalous"}

    def test_causal_validation_on_loaded_data(self) -> None:
        arr = np.random.default_rng(42).normal(-0.07, 0.005, (8, 16, 16))
        seq = FieldAdapter.load(arr)
        result = validate_causal_consistency(seq)
        assert result.error_count == 0
