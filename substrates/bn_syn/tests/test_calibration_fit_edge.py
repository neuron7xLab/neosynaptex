"""Tests for calibration fit edge cases."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.calibration.fit import fit_line


def test_fit_line_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="same shape"):
        fit_line(np.array([1.0, 2.0]), np.array([[1.0, 2.0]]))
