"""Recurrence Quantification Analysis — 10 tests.

Covers: _ami_tau, _embed_nd, _recurrence_matrix, _diagonal_lines,
_vertical_lines, recurrence_quantification.
"""

from __future__ import annotations

import numpy as np

from core.rqa import (
    _ami_tau,
    _diagonal_lines,
    _embed_nd,
    _recurrence_matrix,
    _vertical_lines,
    recurrence_quantification,
)


class TestAmiTau:
    def test_periodic_signal_detects_period(self):
        t = np.linspace(0, 10 * np.pi, 500)
        x = np.sin(t)
        tau = _ami_tau(x, max_tau=50)
        # AMI selects first local minimum — must be > 0
        assert 1 <= tau <= 50

    def test_white_noise_tau_small(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(500)
        tau = _ami_tau(x, max_tau=20)
        assert 1 <= tau <= 5

    def test_short_signal_returns_one(self):
        assert _ami_tau(np.array([1.0, 2.0, 3.0]), max_tau=20) == 1


class TestEmbedNd:
    def test_shape(self):
        x = np.arange(20, dtype=float)
        E = _embed_nd(x, dim=3, tau=2)
        # m = n - (dim-1)*tau = 20 - 2*2 = 16
        assert E.shape == (16, 3)

    def test_too_short(self):
        x = np.array([1.0, 2.0])
        E = _embed_nd(x, dim=3, tau=5)
        assert E.shape[0] == 0


class TestRecurrenceMatrix:
    def test_symmetric(self):
        E = np.array([[0.0], [1.0], [0.1], [1.1], [0.2]])
        R = _recurrence_matrix(E, threshold=0.5)
        assert np.array_equal(R, R.T)

    def test_diagonal_is_one(self):
        E = np.array([[0.0], [10.0], [20.0]])
        R = _recurrence_matrix(E, threshold=0.5)
        assert all(R[i, i] == 1 for i in range(len(E)))


class TestLineExtraction:
    def test_diagonal_lines_simple(self):
        R = np.array(
            [
                [1, 1, 1, 0],
                [0, 1, 1, 1],
                [0, 0, 1, 1],
                [0, 0, 0, 1],
            ]
        )
        lengths = _diagonal_lines(R, min_len=2)
        assert len(lengths) > 0
        assert all(l >= 2 for l in lengths)

    def test_vertical_lines_simple(self):
        R = np.array(
            [
                [1, 0, 0],
                [1, 0, 0],
                [1, 0, 1],
            ]
        )
        lengths = _vertical_lines(R, min_len=2)
        assert len(lengths) > 0


class TestRQA:
    def test_periodic_high_det(self):
        """Periodic signal should have high determinism."""
        t = np.linspace(0, 20 * np.pi, 300)
        x = np.sin(t)
        result = recurrence_quantification(x, embedding_dim=2, tau=5, n_surrogate=10, seed=42)
        assert result["det"] > 0.3, f"DET={result['det']}"
        assert 0 < result["rr"] < 1

    def test_white_noise_low_det(self):
        """White noise should have low determinism."""
        rng = np.random.default_rng(42)
        x = rng.standard_normal(200)
        result = recurrence_quantification(x, embedding_dim=2, tau=1, n_surrogate=10, seed=42)
        assert result["det"] < result["rr"] + 0.3  # DET should not dominate for noise

    def test_short_signal_returns_nan(self):
        result = recurrence_quantification(np.array([1.0, 2.0]))
        assert np.isnan(result["rr"])

    def test_p_value_range(self):
        rng = np.random.default_rng(42)
        x = np.sin(np.linspace(0, 10 * np.pi, 200)) + 0.1 * rng.standard_normal(200)
        result = recurrence_quantification(x, n_surrogate=20, seed=42)
        assert 0.0 < result["p_value"] <= 1.0
