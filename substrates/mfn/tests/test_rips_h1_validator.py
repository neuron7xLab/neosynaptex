"""Tests for Rips H1 validator. Pre-val: Stripe=0.541, Noise=1.082."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.validation.zebrafish.rips_h1_validator import (
    DEFAULT_EPS,
    H1ControlGenerator,
    H1_ORGANIZED_THRESHOLD,
    H1_PRE_VALIDATED,
    NORMALIZE_SCALE,
    RipsH1Computer,
    RipsH1Validator,
)


def _stripe(N=300, seed=42):
    rng = np.random.default_rng(seed)
    return np.column_stack([
        rng.uniform(0, 100, N),
        np.round(rng.uniform(0, 4, N)) * 20 + rng.normal(0, 3.0, N),
    ])


@pytest.fixture(scope="module")
def stripe_cloud():
    return _stripe()


@pytest.fixture(scope="module")
def noise_cloud():
    return np.random.default_rng(99).random((300, 2)) * 100


@pytest.fixture(scope="module")
def stripe_series():
    return [_stripe(250, seed=s) for s in range(8)]


class TestNormalization:
    def test_scale(self):
        c = RipsH1Computer()
        n = c._normalize(np.array([[0, 0], [100, 200], [50, 100.0]]))
        assert n.max() <= NORMALIZE_SCALE + 1e-6 and n.min() >= -1e-6


class TestRipsH1Computer:
    def test_has_h1_features(self, stripe_cloud):
        assert RipsH1Computer().compute(stripe_cloud, "s").n_h1_features > 0

    def test_stripe_near_preval(self, stripe_cloud):
        r = RipsH1Computer().compute(stripe_cloud, "s")
        assert abs(r.h1_median - H1_PRE_VALIDATED["stripe_h1_mhl_mean"]) < 0.30

    def test_stripe_lt_noise(self, stripe_cloud, noise_cloud):
        c = RipsH1Computer()
        assert c.compute(stripe_cloud, "s").h1_median < c.compute(noise_cloud, "n").h1_median

    def test_stripe_organized(self, stripe_cloud):
        assert RipsH1Computer().compute(stripe_cloud, "s").is_organized is True

    def test_noise_not_organized(self, noise_cloud):
        assert RipsH1Computer().compute(noise_cloud, "n").is_organized is False

    def test_series(self, stripe_series):
        assert RipsH1Computer().compute_series(stripe_series, "ss").n_h1_features >= 5


class TestH1ControlGenerator:
    def test_in_bbox(self, stripe_cloud):
        p = H1ControlGenerator().generate(stripe_cloud)
        assert np.all(p >= stripe_cloud.min(0) - 1e-8)
        assert np.all(p <= stripe_cloud.max(0) + 1e-8)


class TestRipsH1Validator:
    def test_verdict(self, stripe_series):
        r = RipsH1Validator(verbose=True).validate(stripe_series)
        assert r.verdict in ("SUPPORTED", "FALSIFIED", "INCONCLUSIVE")

    def test_wt_organized(self, stripe_series):
        assert RipsH1Validator().validate(stripe_series).wild_type.is_organized is True

    def test_g6_false_synthetic(self, stripe_series):
        assert RipsH1Validator().validate(stripe_series, label_real=False).g6_closed is False

    def test_primary_in_report(self, stripe_series):
        assert "1.043" in RipsH1Validator().validate(stripe_series).primary_evidence

    def test_summary(self, stripe_series):
        s = RipsH1Validator().validate(stripe_series).summary()
        assert "H1_MHL" in s and "VERDICT" in s and "G6" in s
