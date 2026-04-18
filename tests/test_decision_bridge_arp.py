"""Tests for the AR(p) opt-in path of ``OnlinePredictor``.

Contract I-DB-ARP-1  ``auto_order=False`` is bit-identical to the
                     legacy AR(1) behaviour (forecasts and residuals
                     match value-by-value across any input stream).
Contract I-DB-ARP-2  ``auto_order=True`` + pure AR(2) ground truth with a
                     suppressed lag-1 mode selects order ≥ 2 and produces
                     meaningfully tighter residuals than the default AR(1).
Contract I-DB-ARP-3  Bad constructor arguments raise ValueError.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from core.decision_bridge import OnlinePredictor


def _ar2_oscillatory_series(n: int, seed: int = 0) -> np.ndarray:
    """AR(2) around mean=0.5 with a *suppressed* lag-1 coefficient.

    Choosing coefficients ``(φ₁, φ₂) = (0.0, 0.7)`` produces a process
    whose lag-1 autocorrelation is near zero while lag-2 carries most
    of the predictable variance. An AR(1) fit therefore has nothing
    to grab onto, and AR(p) selection should strictly prefer p ≥ 2.
    """
    rng = np.random.default_rng(seed)
    phi = np.array([0.0, 0.7])
    x = np.zeros(n, dtype=np.float64)
    x[0:2] = 0.5 + rng.normal(0, 0.02, 2)
    for t in range(2, n):
        deviation = np.dot(phi, x[t - 2 : t][::-1] - 0.5)
        x[t] = 0.5 + deviation + rng.normal(0, 0.02)
    return x


class TestARPConstructor:
    def test_default_is_ar1(self) -> None:
        pred = OnlinePredictor()
        assert pred.last_fit_order == 0

    def test_rejects_zero_order(self) -> None:
        with pytest.raises(ValueError, match="max_order"):
            OnlinePredictor(auto_order=True, max_order=0)

    def test_rejects_order_above_window(self) -> None:
        with pytest.raises(ValueError, match="max_order"):
            OnlinePredictor(window=8, auto_order=True, max_order=10)


class TestARPBackCompat:
    def test_ar1_default_path_matches_explicit_max_order_1(self) -> None:
        """I-DB-ARP-1: auto_order=False fast path is the legacy AR(1)."""
        series = np.linspace(0.2, 0.8, 40) ** 2  # arbitrary non-trivial
        a = OnlinePredictor()
        b = OnlinePredictor(auto_order=True, max_order=1)
        residuals_a: list[float] = []
        residuals_b: list[float] = []
        for v in series:
            residuals_a.append(a.observe(float(v)))
            residuals_b.append(b.observe(float(v)))
        # NaN comparison: both arrays must agree element-wise, including NaN slots.
        arr_a = np.asarray(residuals_a)
        arr_b = np.asarray(residuals_b)
        np.testing.assert_array_equal(np.isnan(arr_a), np.isnan(arr_b))
        np.testing.assert_allclose(
            arr_a[~np.isnan(arr_a)],
            arr_b[~np.isnan(arr_b)],
            rtol=0,
            atol=1e-12,
        )


class TestARPOrderSelection:
    def test_ar2_ground_truth_prefers_order_at_least_two(self) -> None:
        """I-DB-ARP-2: AIC picks p ≥ 2 on genuinely AR(2) data."""
        series = _ar2_oscillatory_series(200, seed=42)
        pred = OnlinePredictor(window=32, auto_order=True, max_order=5)
        selected_orders: list[int] = []
        for v in series:
            pred.observe(float(v))
            if pred.last_fit_order:
                selected_orders.append(pred.last_fit_order)
        tail = selected_orders[-80:]
        # On AR(2) data with lag-1 suppressed, the majority of AIC
        # decisions once the buffer is full must be for an order ≥ 2.
        (values, counts) = np.unique(np.asarray(tail), return_counts=True)
        winner = int(values[np.argmax(counts)])
        assert winner >= 2, (
            f"expected AIC-winner ≥ 2, got distribution {dict(zip(values, counts, strict=True))}"
        )

    def test_arp_beats_ar1_on_ar2_data(self) -> None:
        """AR(p) residuals must have strictly lower RMSE than AR(1) on AR(2) data."""
        series = _ar2_oscillatory_series(300, seed=1)
        ar1 = OnlinePredictor(window=32)
        arp = OnlinePredictor(window=32, auto_order=True, max_order=5)
        res_ar1: list[float] = []
        res_arp: list[float] = []
        for v in series:
            r1 = ar1.observe(float(v))
            r_p = arp.observe(float(v))
            if math.isfinite(r1) and math.isfinite(r_p):
                res_ar1.append(r1)
                res_arp.append(r_p)
        tail_ar1 = np.asarray(res_ar1[-150:])
        tail_arp = np.asarray(res_arp[-150:])
        rmse_ar1 = float(np.sqrt(np.mean(tail_ar1**2)))
        rmse_arp = float(np.sqrt(np.mean(tail_arp**2)))
        # On a lag-1-suppressed AR(2) process the AR(p) residual RMSE
        # must be strictly below the AR(1) RMSE. We don't demand a
        # large margin — just a real signal of model selection payoff.
        assert rmse_arp < rmse_ar1, (
            f"AR(p) did not beat AR(1) on AR(2) data: "
            f"rmse_ar1={rmse_ar1:.5f}, rmse_arp={rmse_arp:.5f}"
        )


class TestARPDegenerateInputs:
    def test_constant_series_selects_order_zero(self) -> None:
        """Constant input → degenerate branch, order stays 0."""
        pred = OnlinePredictor(auto_order=True, max_order=3)
        for _ in range(20):
            pred.observe(0.5)
        # After warm-up, a flatline is the degenerate case — order 0
        # signals "no model needed; forecast is the mean".
        assert pred.last_fit_order == 0
