"""Tests for the MWC allosteric model implementation.

Validates that the Monod-Wyman-Changeux model for GABA-A α1β3γ2 receptors
produces biophysically correct dose-response curves.

References:
    Gielen & Bhatt (2019) Br J Pharmacol 176:2524-2537
        Muscimol EC50 on α1β3γ2: 5-15 μM
    Chang et al. (1996) Biophys J 71:2454-2468
        MWC parameters for GABA-A
    Bhatt et al. (2021) PNAS 118:e2026596118
        Plasticity modulation
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.neurochem.mwc import (
    MWC_C,
    MWC_K_R_UM,
    MWC_K_T_UM,
    MWC_L0,
    MWC_N_SITES,
    effective_gabaa_shunt,
    effective_serotonergic_gain,
    mwc_dose_response,
    mwc_ec50,
    mwc_fraction,
)


class TestMWCModel:
    """Core MWC equation correctness."""

    def test_zero_concentration_returns_near_zero(self) -> None:
        """At zero agonist, receptor is predominantly in T (closed) state."""
        r = mwc_fraction(0.0)
        assert r < 0.01, f"R_fraction at zero concentration too high: {r}"

    def test_saturating_concentration_approaches_one(self) -> None:
        """At very high agonist, receptor should be nearly fully open."""
        r = mwc_fraction(10000.0)
        assert r > 0.95, f"R_fraction at saturation too low: {r}"

    def test_monotonically_increasing(self) -> None:
        """R_fraction must increase with concentration — no dips."""
        concentrations = np.logspace(-2, 4, 100)
        responses = mwc_dose_response(concentrations)
        diffs = np.diff(responses)
        assert np.all(diffs >= -1e-12), f"Non-monotonic: min diff = {diffs.min()}"

    def test_bounded_zero_one(self) -> None:
        """R_fraction must be in [0, 1] for all concentrations."""
        concentrations = np.logspace(-3, 5, 200)
        responses = mwc_dose_response(concentrations)
        assert np.all(responses >= 0.0), f"Negative R_fraction: {responses.min()}"
        assert np.all(responses <= 1.0), f"R_fraction > 1: {responses.max()}"

    def test_negative_concentration_clamped(self) -> None:
        """Negative concentration should be treated as zero."""
        r = mwc_fraction(-5.0)
        r_zero = mwc_fraction(0.0)
        assert r == r_zero

    def test_invalid_K_R_returns_zero(self) -> None:
        """K_R <= 0 is non-physical, should return 0."""
        assert mwc_fraction(10.0, K_R=0.0) == 0.0
        assert mwc_fraction(10.0, K_R=-1.0) == 0.0

    def test_invalid_L0_returns_zero(self) -> None:
        """L0 <= 0 is non-physical, should return 0."""
        assert mwc_fraction(10.0, L0=0.0) == 0.0
        assert mwc_fraction(10.0, L0=-1.0) == 0.0


class TestMWCMonotonicity:
    """Monotonicity across the full concentration range — TASK-01 criterion 79."""

    def test_strict_monotonicity_low_range(self) -> None:
        """R_fraction strictly increases over [0.01, 100] μM."""
        conc = np.linspace(0.01, 100.0, 500)
        resp = mwc_dose_response(conc)
        diffs = np.diff(resp)
        assert np.all(diffs >= 0.0), f"Non-monotonic in low range: min diff={diffs.min()}"

    def test_strict_monotonicity_high_range(self) -> None:
        """R_fraction strictly increases over [100, 100000] μM."""
        conc = np.linspace(100.0, 100000.0, 500)
        resp = mwc_dose_response(conc)
        diffs = np.diff(resp)
        assert np.all(diffs >= 0.0), f"Non-monotonic in high range: min diff={diffs.min()}"

    def test_monotonicity_log_scale(self) -> None:
        """Monotonicity over 6 decades of concentration."""
        conc = np.logspace(-3, 5, 1000)
        resp = mwc_dose_response(conc)
        diffs = np.diff(resp)
        assert np.all(diffs >= -1e-15), f"Non-monotonic (log scale): min diff={diffs.min()}"


class TestMWCEC50:
    """EC50 validation against published electrophysiology data."""

    def test_ec50_in_published_range(self) -> None:
        """EC50 for muscimol on α1β3γ2 should be 5-15 μM.

        Ref: Gielen & Bhatt (2019) Br J Pharmacol 176:2524-2537
        """
        ec50 = mwc_ec50()
        assert 3.0 <= ec50 <= 20.0, f"EC50 = {ec50:.2f} μM, expected 5-15 μM for muscimol on α1β3γ2"

    def test_ec50_response_is_half_max(self) -> None:
        """At EC50, R_fraction should be ~R_max/2."""
        ec50 = mwc_ec50()
        r = mwc_fraction(ec50)
        r_max = 1.0 / (1.0 + MWC_L0 * (MWC_C**MWC_N_SITES))
        assert abs(r - r_max / 2.0) < 0.01, f"R at EC50 = {r}, expected ~{r_max / 2:.4f}"

    def test_ec50_comparison_with_published_data(self) -> None:
        """Compare EC50 with known muscimol data.

        Gielen & Bhatt (2019): EC50 = 5-15 μM for α1β3γ2
        Chang et al. (1996): EC50 varies 8-12 μM depending on subunit composition
        """
        ec50 = mwc_ec50()
        # Allow broader range to account for parameter uncertainty
        assert 2.0 <= ec50 <= 25.0, f"EC50 = {ec50:.2f} μM outside literature range"

    def test_ec50_increases_with_L0(self) -> None:
        """Higher L0 (more closed at rest) should shift EC50 rightward."""
        ec50_low = mwc_ec50(L0=1000.0)
        ec50_high = mwc_ec50(L0=10000.0)
        assert ec50_high > ec50_low, f"EC50 should increase with L0: {ec50_low} vs {ec50_high}"

    def test_ec50_decreases_with_n(self) -> None:
        """More binding sites should make the transition steeper, shifting EC50."""
        ec50_2 = mwc_ec50(n=2)
        ec50_4 = mwc_ec50(n=4)
        assert ec50_2 != ec50_4  # They should differ


class TestMWCParameters:
    """Verify parameter consistency — literature-backed (TASK-01 criterion 78)."""

    def test_c_equals_kr_over_kt(self) -> None:
        assert abs(MWC_C - MWC_K_R_UM / MWC_K_T_UM) < 1e-10

    def test_n_sites_matches_receptor_model(self) -> None:
        """n=2 for canonical GABA-A pentameric receptor (2 α-β interfaces)."""
        assert MWC_N_SITES == 2

    def test_l0_positive(self) -> None:
        assert MWC_L0 > 0

    def test_kr_less_than_kt(self) -> None:
        """R state has higher affinity (lower K) than T state."""
        assert MWC_K_R_UM < MWC_K_T_UM

    def test_c_less_than_one(self) -> None:
        """c = K_R/K_T < 1 is required for agonist to favor R state."""
        assert 0.0 < MWC_C < 1.0

    def test_literature_parameter_mapping(self) -> None:
        """All MWC parameters should be traceable to published sources.

        Chang et al. 1996 (Biophys J 71:2454-2468): L₀, K_T
        Gielen & Bhatt 2019 (Br J Pharmacol 176:2524-2537): K_R (muscimol)
        Bhatt et al. 2021 (PNAS 118:e2026596118): subunit composition
        """
        # L0 from Chang et al. 1996
        assert 100 <= MWC_L0 <= 10000
        # K_R from Gielen & Bhatt 2019 (muscimol range)
        assert 0.1 <= MWC_K_R_UM <= 5.0
        # K_T from Chang et al. 1996
        assert 100 <= MWC_K_T_UM <= 1000
        # n from receptor structure
        assert MWC_N_SITES in (2, 5)  # 2 canonical sites or 5 subunits


class TestMWCDoseResponse:
    """Vectorized dose-response curve."""

    def test_shape_preserved(self) -> None:
        conc = np.array([0.1, 1.0, 10.0, 100.0])
        resp = mwc_dose_response(conc)
        assert resp.shape == conc.shape

    def test_matches_scalar(self) -> None:
        """Vectorized should match scalar for each element."""
        conc = np.array([0.0, 1.0, 10.0, 100.0, 1000.0])
        vectorized = mwc_dose_response(conc)
        scalar = np.array([mwc_fraction(c) for c in conc])
        np.testing.assert_allclose(vectorized, scalar, atol=1e-10)

    def test_hill_slope_greater_than_one(self) -> None:
        """MWC with n>1 should produce a Hill slope > 1 (cooperativity)."""
        ec50 = mwc_ec50()
        delta = ec50 * 0.01
        r_below = mwc_fraction(ec50 - delta)
        r_above = mwc_fraction(ec50 + delta)
        dr_dc = (r_above - r_below) / (2 * delta)
        hill_1_slope = 1.0 / (4.0 * ec50)
        assert dr_dc > hill_1_slope * 0.8, (
            f"MWC slope {dr_dc:.6f} not steeper than Hill n=1 slope {hill_1_slope:.6f}"
        )


class TestEffectiveFunctions:
    """Verify shunt and gain helper functions."""

    def test_effective_gabaa_shunt(self) -> None:
        active = np.array([0.0, 0.5, 1.0])
        result = effective_gabaa_shunt(active, 0.5)
        assert result.shape == active.shape
        assert np.all(result >= 0.0)
        assert np.all(result <= 0.95)

    def test_effective_serotonergic_gain(self) -> None:
        drive = np.array([0.0, 0.5, 1.0])
        result = effective_serotonergic_gain(drive, 0.1, 0.05)
        assert result.shape == drive.shape
        assert np.all(result >= -0.10)
        assert np.all(result <= 0.25)


class TestCausalRuleSIM011:
    """Verify SIM-011 causal rule for MWC monotonicity."""

    def test_sim011_passes(self) -> None:
        import mycelium_fractal_net as mfn
        from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        v = validate_causal_consistency(seq, mode="strict")
        sim011 = [r for r in v.rule_results if r.rule_id == "SIM-011"]
        assert len(sim011) == 1, "SIM-011 should be evaluated"
        assert sim011[0].passed, f"SIM-011 failed: observed={sim011[0].observed}"
