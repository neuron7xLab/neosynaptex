"""Tests for Rips point cloud G6 validator.

Pre-validated: Stripe MHL=2.530, Noise MHL=3.541, Cohen d=5.06.
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.validation.zebrafish.rips_validator import (
    ORGANIZED_THRESHOLD_MHL,
    PRE_VALIDATED,
    RipsControlGenerator,
    RipsMHLComputer,
    RipsValidator,
)


def _stripe_cloud(N: int = 300, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.column_stack([
        rng.uniform(0, 100, N),
        np.round(rng.uniform(0, 4, N)) * 20 + rng.normal(0, 2.5, N),
    ])


def _noise_cloud(stripe: np.ndarray, seed: int = 99) -> np.ndarray:
    rng = np.random.default_rng(seed)
    lo, hi = stripe.min(axis=0), stripe.max(axis=0)
    return rng.random((len(stripe), 2)) * (hi - lo) + lo


@pytest.fixture(scope="module")
def stripe_cloud():
    return _stripe_cloud()


@pytest.fixture(scope="module")
def noise_cloud(stripe_cloud):
    return _noise_cloud(stripe_cloud)


@pytest.fixture(scope="module")
def stripe_series():
    return [_stripe_cloud(300, seed=s) for s in range(10)]


class TestRipsControlGenerator:
    def test_same_shape(self, stripe_cloud):
        assert RipsControlGenerator(0).full_permutation(stripe_cloud).shape == stripe_cloud.shape

    def test_in_bbox(self, stripe_cloud):
        p = RipsControlGenerator(0).full_permutation(stripe_cloud)
        assert np.all(p >= stripe_cloud.min(axis=0) - 1e-10)
        assert np.all(p <= stripe_cloud.max(axis=0) + 1e-10)

    def test_series_length(self, stripe_series):
        assert len(RipsControlGenerator(0).full_permutation_series(stripe_series)) == len(stripe_series)


class TestRipsMHLComputer:
    def test_returns_result(self, stripe_cloud):
        r = RipsMHLComputer().compute(stripe_cloud, "stripe")
        assert r.n_h0_features > 0 and r.median_lifetime > 0

    def test_stripe_near_prevalidated(self, stripe_cloud):
        r = RipsMHLComputer().compute(stripe_cloud, "stripe")
        assert abs(r.median_lifetime - PRE_VALIDATED["stripe_mhl_mean"]) < 0.5

    def test_stripe_lt_noise(self, stripe_cloud, noise_cloud):
        c = RipsMHLComputer()
        assert c.compute(stripe_cloud, "s").median_lifetime < c.compute(noise_cloud, "n").median_lifetime

    def test_stripe_organized(self, stripe_cloud):
        assert RipsMHLComputer().compute(stripe_cloud, "s").is_organized is True

    def test_noise_not_organized(self, noise_cloud):
        assert RipsMHLComputer().compute(noise_cloud, "n").is_organized is False

    def test_series(self, stripe_series):
        r = RipsMHLComputer().compute_series(stripe_series, "ss")
        assert r.n_h0_features > 0

    def test_label_real(self, stripe_cloud):
        r = RipsMHLComputer().compute(stripe_cloud, "t", label_real=True)
        assert r.label_real is True and r.evidence_type == "real"


class TestRipsValidator:
    def test_validate_verdict(self, stripe_series):
        r = RipsValidator(verbose=True).validate(stripe_series, label_real=False)
        assert r.verdict in ("SUPPORTED", "FALSIFIED", "INCONCLUSIVE")

    def test_wt_organized(self, stripe_series):
        assert RipsValidator().validate(stripe_series).wild_type.is_organized is True

    def test_g6_not_closed_synthetic(self, stripe_series):
        assert RipsValidator().validate(stripe_series, label_real=False).g6_closed is False

    def test_summary_fields(self, stripe_series):
        s = RipsValidator().validate(stripe_series).summary()
        assert "MHL=" in s and "VERDICT" in s and "G6" in s

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            RipsValidator().from_mat_directory(tmp_path / "nope")
