"""
Cross-substrate γ invariant test.
CI fails if any substrate exits CRITICAL zone (|γ-1| > 0.50).
This is the core proof that intelligence is a regime property.
"""

import sys

sys.path.insert(0, ".")
from core.axioms import SUBSTRATE_GAMMA, classify_regime, verify_axiom_consistency


def test_all_substrates_not_collapsed():
    """No substrate in COLLAPSE zone. Hard requirement."""
    for name, (gamma, note) in SUBSTRATE_GAMMA.items():
        regime = classify_regime(gamma)
        assert regime != "COLLAPSE", (
            f"Substrate '{name}' collapsed: γ={gamma:.4f} "
            f"|γ-1|={abs(gamma - 1):.4f} > 0.50\nNote: {note}"
        )


def test_majority_substrates_metastable():
    """≥ 4/6 substrates in METASTABLE zone (|γ-1| < 0.15)."""
    metastable = [name for name, (gamma, _) in SUBSTRATE_GAMMA.items() if abs(gamma - 1.0) < 0.15]
    assert len(metastable) >= 4, f"Only {len(metastable)}/6 substrates metastable: {metastable}"


def test_mean_gamma_near_unity():
    """Mean γ across substrates within 0.15 of 1.0."""
    gammas = [v[0] for v in SUBSTRATE_GAMMA.values()]
    mean_g = sum(gammas) / len(gammas)
    assert abs(mean_g - 1.0) < 0.15, f"Mean γ={mean_g:.4f} outside metastable zone"


def test_axiom_consistency():
    """Full AXIOM_0 consistency check."""
    gammas = [v[0] for v in SUBSTRATE_GAMMA.values()]
    state = {
        "gamma": sum(gammas) / len(gammas),
        "substrates": list(SUBSTRATE_GAMMA.keys()),
        "convergence_slope": -0.0016,
    }
    assert verify_axiom_consistency(state), "AXIOM_0 violated"


def test_gamma_formula():
    """γ_PSD = 2H+1 verification. NEVER 2H-1."""
    from core.axioms import gamma_psd

    assert abs(gamma_psd(0.5) - 2.0) < 1e-9
    assert abs(gamma_psd(0.0) - 1.0) < 1e-9
    assert abs(gamma_psd(1.0) - 3.0) < 1e-9
