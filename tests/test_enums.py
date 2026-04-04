"""Tests for core.enums — type-safe operational states and verdicts."""

from core.enums import (
    CoherenceVerdict,
    FalsificationVerdict,
    GammaVerdict,
    Phase,
    Regime,
    TruthVerdict,
    ValueGate,
)


def test_phase_is_str_compatible():
    """Phase enum values should be usable as plain strings via == comparison."""
    assert Phase.METASTABLE == "METASTABLE"
    assert Phase.INITIALIZING == "INITIALIZING"
    assert Phase.CONVERGING.value == "CONVERGING"


def test_gamma_verdict_str_compatible():
    assert GammaVerdict.METASTABLE == "METASTABLE"
    assert GammaVerdict.INSUFFICIENT_DATA == "INSUFFICIENT_DATA"


def test_regime_str_compatible():
    assert Regime.METASTABLE == "METASTABLE"
    assert Regime.COLLAPSE == "COLLAPSE"


def test_value_gate_str_compatible():
    assert ValueGate.PROCEED == "proceed"
    assert ValueGate.CAUTION == "caution"
    assert ValueGate.REDIRECT == "redirect"


def test_truth_verdict_values():
    verdicts = {v.value for v in TruthVerdict}
    assert verdicts == {"VERIFIED", "CONSTRUCTED", "FRAGILE", "INCONCLUSIVE"}


def test_falsification_verdict_values():
    verdicts = {v.value for v in FalsificationVerdict}
    assert verdicts == {"ROBUST", "FRAGILE", "INCONCLUSIVE"}


def test_coherence_verdict_values():
    verdicts = {v.value for v in CoherenceVerdict}
    assert verdicts == {"COHERENT", "INCOHERENT", "PARTIAL"}


def test_phase_all_values():
    phases = {p.value for p in Phase}
    expected = {
        "INITIALIZING", "METASTABLE", "CONVERGING", "DRIFTING",
        "DIVERGING", "COLLAPSING", "DEGENERATE",
    }
    assert phases == expected


def test_enums_in_dict_keys():
    """Enum members should work as dict keys (str-compatible)."""
    d = {Phase.METASTABLE: 1.0, Phase.DIVERGING: 0.0}
    assert d["METASTABLE"] == 1.0
    assert d[Phase.METASTABLE] == 1.0
