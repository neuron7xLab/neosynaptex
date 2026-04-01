from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bnsyn.experiments.declarative import (
    _build_raster_image,
    _build_rate_image,
    _write_grayscale_png,
)


def test_write_grayscale_png_rejects_non_uint8(tmp_path: Path) -> None:
    image = np.zeros((2, 2), dtype=np.float64)
    with pytest.raises(ValueError, match="image must be uint8"):
        _write_grayscale_png(image, tmp_path / "x.png")


def test_write_grayscale_png_rejects_non_2d(tmp_path: Path) -> None:
    image = np.zeros((2, 2, 1), dtype=np.uint8)
    with pytest.raises(ValueError, match="image must be 2-D"):
        _write_grayscale_png(image, tmp_path / "x.png")


def test_write_grayscale_png_writes_valid_signature(tmp_path: Path) -> None:
    out = tmp_path / "ok.png"
    _write_grayscale_png(np.array([[255, 0], [0, 255]], dtype=np.uint8), out)
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_build_raster_image_min_dims_and_in_bounds_pixel() -> None:
    image = _build_raster_image(
        spike_steps=np.array([0], dtype=np.int64),
        spike_neurons=np.array([0], dtype=np.int64),
        steps=1,
        n_neurons=1,
    )
    assert image.shape == (2, 2)
    assert image[1, 0] == 0


def test_build_raster_image_ignores_out_of_bounds() -> None:
    image = _build_raster_image(
        spike_steps=np.array([5, -1, 0], dtype=np.int64),
        spike_neurons=np.array([0, 1, 5], dtype=np.int64),
        steps=2,
        n_neurons=2,
    )
    assert np.all(image == 255)


def test_build_rate_image_empty_trace_is_blank() -> None:
    image = _build_rate_image(np.array([], dtype=np.float64), width=8, height=4)
    assert image.shape == (4, 8)
    assert np.all(image == 255)


def test_build_rate_image_all_zero_trace_draws_baseline() -> None:
    image = _build_rate_image(np.zeros(8, dtype=np.float64), width=8, height=4)
    assert np.all(image[-1, :] == 0)


def test_build_rate_image_non_zero_draws_above_baseline() -> None:
    image = _build_rate_image(np.array([0.0, 1.0, 2.0, 4.0], dtype=np.float64), width=10, height=6)
    assert np.any(image[:-1, :] < 255)
