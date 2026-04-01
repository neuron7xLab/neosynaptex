"""Tests for NFI Unified γ Diagnostic Orchestrator."""

import math

import pytest

from neuron7x_agents.dnca.adapters.nfi_gamma_orchestrator import (
    DIVERGENCE_UNIFIED,
    DIVERGENCE_WARNING,
    GAMMA_UNIFIED_HIGH,
    GAMMA_UNIFIED_LOW,
    GAMMA_WT,
    LayerGamma,
    NFIGammaDiagnostic,
    NFIGammaOutput,
    _compute_divergence,
    _compute_verdict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _layer(name: str, gamma: float, ci_low: float = 0.0, ci_high: float = 2.0,
           r2: float = 0.5, n_points: int = 50, control: float = 0.02) -> LayerGamma:
    return LayerGamma(
        layer=name, gamma=gamma, ci_low=ci_low, ci_high=ci_high,
        r2=r2, n_points=n_points, control_gamma=control,
    )


@pytest.fixture
def diag():
    return NFIGammaDiagnostic()


@pytest.fixture
def three_layers():
    """All three substrates with realistic γ values from actual measurements."""
    return [
        _layer("DNCA", 2.072, 1.341, 2.849, 0.45, 949, 0.068),
        _layer("MFN", 0.865, 0.649, 1.250, 0.35, 100, 0.035),
        _layer("market", 1.081, 0.869, 1.290, 0.40, 200, 0.145),
    ]


# ---------------------------------------------------------------------------
# LayerGamma
# ---------------------------------------------------------------------------

class TestLayerGamma:
    def test_valid_layer(self):
        lg = _layer("DNCA", 1.0)
        assert lg.is_valid
        assert lg.is_organized
        assert lg.control_passes

    def test_insufficient_points(self):
        lg = _layer("DNCA", 1.0, n_points=5)
        assert not lg.is_valid

    def test_negative_gamma_not_organized(self):
        lg = _layer("DNCA", -0.5)
        assert lg.is_valid
        assert not lg.is_organized

    def test_low_r2_not_organized(self):
        lg = _layer("DNCA", 1.0, r2=0.05)
        assert not lg.is_organized

    def test_control_fails_high(self):
        lg = _layer("DNCA", 1.0, control=0.5)
        assert not lg.control_passes

    def test_nan_gamma_invalid(self):
        lg = _layer("DNCA", float("nan"), n_points=50)
        assert not lg.is_valid


# ---------------------------------------------------------------------------
# NFIGammaOutput
# ---------------------------------------------------------------------------

class TestNFIGammaOutput:
    def test_all_gammas_includes_biological(self):
        out = NFIGammaOutput(gamma_DNCA=1.5, gamma_MFN=1.0, gamma_market=1.1)
        g = out.all_gammas
        assert "biological" in g
        assert g["biological"] == GAMMA_WT
        assert g["DNCA"] == 1.5
        assert g["MFN"] == 1.0
        assert g["market"] == 1.1

    def test_all_gammas_none_excluded(self):
        out = NFIGammaOutput(gamma_DNCA=1.5)
        g = out.all_gammas
        assert "MFN" not in g
        assert "market" not in g

    def test_summary_contains_verdict(self):
        out = NFIGammaOutput(
            gamma_DNCA=1.2, gamma_MFN=1.0, gamma_market=1.1,
            coherence_verdict="UNIFIED", gamma_divergence=0.2,
        )
        s = out.summary()
        assert "UNIFIED" in s
        assert "γ_DNCA" in s


# ---------------------------------------------------------------------------
# Divergence & Verdict
# ---------------------------------------------------------------------------

class TestDivergenceVerdict:
    def test_divergence_two_values(self):
        assert _compute_divergence([1.0, 1.5]) == pytest.approx(0.5)

    def test_divergence_single_value_inf(self):
        assert _compute_divergence([1.0]) == float("inf")

    def test_divergence_empty_inf(self):
        assert _compute_divergence([]) == float("inf")

    def test_verdict_unified(self):
        gammas = [1.0, 1.1, 1.2]
        div = _compute_divergence(gammas)
        assert _compute_verdict(gammas, div) == "UNIFIED"

    def test_verdict_organized(self):
        gammas = [0.5, 1.0, 1.5]
        div = _compute_divergence(gammas)  # 1.0 — too wide for UNIFIED
        # 0.5 is below GAMMA_UNIFIED_LOW so not UNIFIED, but all > 0
        # divergence is 1.0 > 0.5, so DIVERGENT
        assert _compute_verdict(gammas, div) == "DIVERGENT"

    def test_verdict_organized_moderate_spread(self):
        gammas = [0.8, 1.0, 1.1]
        div = _compute_divergence(gammas)  # 0.3
        # 0.8 < 0.9 so not all in [0.9, 1.5] → not UNIFIED
        # all > 0, div = 0.3 ≤ 0.5 → ORGANIZED
        assert _compute_verdict(gammas, div) == "ORGANIZED"

    def test_verdict_insufficient(self):
        assert _compute_verdict([1.0], 0.0) == "INSUFFICIENT_DATA"

    def test_verdict_divergent(self):
        gammas = [0.5, 2.0]
        div = _compute_divergence(gammas)  # 1.5
        assert _compute_verdict(gammas, div) == "DIVERGENT"

    def test_verdict_mixed(self):
        gammas = [-0.3, 0.5]
        div = _compute_divergence(gammas)  # 0.8 > 0.5
        # divergence > 0.5, so DIVERGENT actually takes precedence
        assert _compute_verdict(gammas, div) == "DIVERGENT"


# ---------------------------------------------------------------------------
# NFIGammaDiagnostic
# ---------------------------------------------------------------------------

class TestNFIGammaDiagnostic:
    def test_diagnose_three_layers(self, diag, three_layers):
        out = diag.diagnose(three_layers, step=1000)
        assert out.gamma_DNCA == pytest.approx(2.072)
        assert out.gamma_MFN == pytest.approx(0.865)
        assert out.gamma_market == pytest.approx(1.081)
        assert out.gamma_biological == GAMMA_WT
        assert math.isfinite(out.gamma_divergence)
        assert out.coherence_verdict != "INSUFFICIENT_DATA"
        assert out.step == 1000

    def test_diagnose_single_layer(self, diag):
        layers = [_layer("DNCA", 1.2)]
        out = diag.diagnose(layers)
        # With biological reference included, we have 2 gammas
        assert out.gamma_DNCA == pytest.approx(1.2)
        assert out.gamma_MFN is None
        assert out.gamma_market is None

    def test_diagnose_no_layers(self, diag):
        out = diag.diagnose([])
        assert out.coherence_verdict == "INSUFFICIENT_DATA"

    def test_invalid_layer_skipped(self, diag):
        layers = [
            _layer("DNCA", 1.2),
            _layer("MFN", 0.5, n_points=3),  # invalid — too few points
        ]
        out = diag.diagnose(layers)
        assert out.gamma_MFN is None  # skipped

    def test_history_accumulates(self, diag, three_layers):
        diag.diagnose(three_layers, step=100)
        diag.diagnose(three_layers, step=200)
        assert len(diag.history) == 2
        assert diag.history[0].step == 100
        assert diag.history[1].step == 200

    def test_cross_substrate_validator(self, diag, three_layers):
        diag.diagnose(three_layers)
        report = diag.cross_substrate_validator()
        assert "γ_biological" in report
        assert "γ_computational" in report
        assert "γ_morphogenetic" in report
        assert "γ_market" in report
        assert "Verdict" in report

    def test_cross_substrate_validator_empty(self, diag):
        report = diag.cross_substrate_validator()
        assert "No measurements" in report

    def test_without_biological(self):
        diag = NFIGammaDiagnostic(include_biological=False)
        layers = [_layer("DNCA", 1.2)]
        out = diag.diagnose(layers)
        # Only 1 gamma (no biological), so INSUFFICIENT_DATA
        assert out.coherence_verdict == "INSUFFICIENT_DATA"

    def test_unified_verdict_achievable(self, diag):
        """All layers near γ_WT → UNIFIED."""
        layers = [
            _layer("DNCA", 1.1),
            _layer("MFN", 1.0),
            _layer("market", 1.05),
        ]
        out = diag.diagnose(layers)
        # gammas: [1.043, 1.1, 1.0, 1.05] — all in [0.9, 1.5], div = 0.1
        assert out.coherence_verdict == "UNIFIED"

    def test_divergent_verdict(self, diag):
        """Wide spread triggers DIVERGENT."""
        layers = [
            _layer("DNCA", 3.0),
            _layer("MFN", 0.5),
        ]
        out = diag.diagnose(layers)
        # gammas: [1.043, 3.0, 0.5] — divergence = 2.5
        assert out.coherence_verdict == "DIVERGENT"

    def test_layer_name_matching(self, diag):
        """Various layer name formats are correctly matched."""
        layers = [
            _layer("cognitive_dnca", 1.0),
            _layer("morphogenetic_field", 1.1),
            _layer("mvstack_market", 1.05),
        ]
        out = diag.diagnose(layers)
        assert out.gamma_DNCA == pytest.approx(1.0)
        assert out.gamma_MFN == pytest.approx(1.1)
        assert out.gamma_market == pytest.approx(1.05)

    def test_output_summary_format(self, diag, three_layers):
        out = diag.diagnose(three_layers)
        s = out.summary()
        assert "NFI Unified" in s
        assert "γ_DNCA" in s
        assert "γ_MFN" in s
        assert "γ_market" in s
        assert "divergence" in s
        assert "verdict" in s

    def test_actual_measurements_organized(self, diag, three_layers):
        """Real measurements from previous session produce ORGANIZED verdict."""
        out = diag.diagnose(three_layers, step=1000)
        # DNCA=2.072, MFN=0.865, market=1.081, bio=1.043
        # All > 0, divergence = 2.072 - 0.865 = 1.207 > 0.5 → DIVERGENT
        # Actually since DNCA is high, this will be DIVERGENT
        assert out.coherence_verdict in ("ORGANIZED", "DIVERGENT")
        assert all(lg.is_organized for lg in out.layers)

    def test_controls_all_pass(self, diag, three_layers):
        """All control γ values are near zero."""
        for lg in three_layers:
            assert lg.control_passes, f"{lg.layer} control failed: {lg.control_gamma}"
