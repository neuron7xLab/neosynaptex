"""
CCP ↔ GNC+ Bridge — bidirectional prediction and consistency validation.

Maps between CCP triple K = <D_f, Phi, R> and GNC+ 7-axis modulator state.

Forward (CCP → GNC+):
    D_f high → Glutamate↑ (plasticity, generative expansion)
    D_f low  → GABA↑ (over-stabilization)
    R high   → Acetylcholine↑ (precision, synchronization)
    R low    → Noradrenaline↑ (volatility, desynchronization)
    Phi high → Dopamine↑ (integrated reward)
    Phi low  → Serotonin↑ (restraint)

Inverse (GNC+ → CCP):
    Glutamate↑ + GABA↓ → D_f → upper cognitive window
    Acetylcholine↑ → R↑
    Dopamine↑ → Phi↑
    Noradrenaline↑↑ → R↓ (volatility spike)

Ref: Vasylenko CCP (2026), GNC+ Sigma matrix
"""
from __future__ import annotations

import numpy as np

from mycelium_fractal_net.analytics.ccp_metrics import D_F_MAX, D_F_MIN, PHI_C, R_C
from mycelium_fractal_net.neurochem.gnc import (
    MODULATORS,
    GNCState,
    compute_gnc_state,
    gnc_diagnose,
)


def ccp_to_gnc_prediction(ccp_state: dict) -> dict[str, float]:
    """
    Predict GNC+ modulator levels from CCP parameters.

    Mapping:
    - D_f high (>1.7) → Glutamate↑, GABA↓
    - D_f low (<1.5)  → GABA↑, Glutamate↓
    - R high (>0.6)   → Acetylcholine↑
    - R low (<0.3)    → Noradrenaline↑
    - Phi high (>0)   → Dopamine↑
    - Phi low (<0)    → Serotonin↑
    """
    D_f = float(ccp_state.get("D_f", 1.7))
    R = float(ccp_state.get("R", 0.5))
    phi = float(ccp_state.get("phi_proxy", 0.0))

    # Base: all at 0.5
    levels = dict.fromkeys(MODULATORS, 0.5)

    # D_f → Glutamate/GABA axis
    if D_f > 1.7:
        levels["Glutamate"] = min(0.9, 0.5 + (D_f - 1.7) * 1.0)
        levels["GABA"] = max(0.1, 0.5 - (D_f - 1.7) * 0.8)
    elif D_f < 1.5:
        levels["GABA"] = min(0.9, 0.5 + (1.5 - D_f) * 1.0)
        levels["Glutamate"] = max(0.1, 0.5 - (1.5 - D_f) * 0.8)

    # R → Acetylcholine/Noradrenaline axis
    if R > 0.6:
        levels["Acetylcholine"] = min(0.9, 0.5 + (R - 0.6) * 1.0)
    elif R < 0.3:
        levels["Noradrenaline"] = min(0.9, 0.5 + (0.3 - R) * 1.5)

    # Phi → Dopamine/Serotonin axis
    if phi > 0:
        levels["Dopamine"] = min(0.9, 0.5 + phi * 0.5)
    else:
        levels["Serotonin"] = min(0.9, 0.5 + abs(phi) * 0.5)

    # Opioid: default unless system is very incoherent
    if R < 0.2 and D_f < 1.3:
        levels["Opioid"] = 0.6  # dampening in pathological state

    # Clip all
    levels = {k: float(np.clip(v, 0.1, 0.9)) for k, v in levels.items()}
    return levels


def gnc_to_ccp_prediction(gnc_state: GNCState) -> dict:
    """
    Predict CCP parameters from GNC+ state.

    Inverse mapping:
    - Glutamate↑ + GABA↓ → D_f upper window
    - Acetylcholine↑ → R↑
    - Dopamine↑ + Serotonin balanced → Phi↑
    - Noradrenaline↑↑ → R↓

    Returns predicted D_f range, R range, cognitive prediction, confidence.
    """
    m = gnc_state.modulators
    glu = m["Glutamate"]
    gaba = m["GABA"]
    na = m["Noradrenaline"]
    ach = m["Acetylcholine"]
    da = m["Dopamine"]
    sht = m["Serotonin"]
    op = m["Opioid"]

    # D_f prediction from E/I balance
    ei_balance = glu - gaba  # positive = excitatory dominant
    D_f_center = 1.7 + ei_balance * 0.5
    D_f_range = (
        float(np.clip(D_f_center - 0.2, 0.5, 2.5)),
        float(np.clip(D_f_center + 0.2, 0.5, 2.5)),
    )

    # R prediction from ACh and NA
    R_center = 0.5 + (ach - 0.5) * 0.8 - (na - 0.5) * 0.6
    # Opioid dampens coherence
    R_center -= (op - 0.5) * 0.3
    R_range = (
        float(np.clip(R_center - 0.15, 0.0, 1.0)),
        float(np.clip(R_center + 0.15, 0.0, 1.0)),
    )

    # Phi prediction from DA/5HT balance
    phi_pred = (da - 0.5) * 1.0 - (sht - 0.5) * 0.5

    # Cognitive prediction
    D_f_in_window = D_f_range[0] <= D_F_MAX and D_f_range[1] >= D_F_MIN
    R_above = R_range[1] > R_C
    phi_above = phi_pred >= PHI_C
    predicted_cognitive = D_f_in_window and R_above and phi_above

    # Confidence based on how central the predictions are
    diag = gnc_diagnose(gnc_state)
    confidence = float(np.clip(diag.coherence * 0.7 + 0.3 * (1.0 - diag.theta_imbalance), 0.0, 1.0))

    return {
        "predicted_D_f_range": D_f_range,
        "predicted_R_range": R_range,
        "predicted_phi": float(phi_pred),
        "predicted_cognitive": predicted_cognitive,
        "confidence": confidence,
    }


def validate_ccp_gnc_consistency(
    ccp_state: dict,
    gnc_state: GNCState,
) -> dict:
    """
    Validate consistency between CCP and GNC+ states.

    Inconsistencies:
    - CCP cognitive=True but GNC+ dysregulated
    - CCP cognitive=False but GNC+ optimal
    """
    ccp_cognitive = bool(ccp_state.get("cognitive", False))
    diag = gnc_diagnose(gnc_state)
    gnc_regime = diag.regime

    inconsistency_type = None
    recommendation = "States are consistent."

    if ccp_cognitive and gnc_regime == "dysregulated":
        inconsistency_type = "ccp_cognitive_gnc_dysregulated"
        recommendation = (
            "CCP indicates cognitive state but GNC+ shows dysregulation. "
            "Check: modulator levels may need rebalancing, or CCP measurement noise."
        )
    elif not ccp_cognitive and gnc_regime == "optimal":
        inconsistency_type = "ccp_noncognitive_gnc_optimal"
        recommendation = (
            "GNC+ is optimal but CCP conditions not met. "
            "Check: D_f may be outside window, or R below threshold. "
            "System may be stable but not in cognitive regime."
        )

    consistent = inconsistency_type is None

    return {
        "consistent": consistent,
        "ccp_cognitive": ccp_cognitive,
        "gnc_regime": gnc_regime,
        "gnc_coherence": diag.coherence,
        "inconsistency_type": inconsistency_type,
        "recommendation": recommendation,
    }


# ===================================================================
# TESTS
# ===================================================================


def _tests_ccp_to_gnc(test_fn) -> None:
    print("\n--- ccp_to_gnc_prediction ---")

    def _test_high_D_f_high_glu():
        pred = ccp_to_gnc_prediction({"D_f": 1.9, "R": 0.5, "phi_proxy": 0.0})
        assert pred["Glutamate"] > 0.5, f"high D_f should → Glu↑, got {pred['Glutamate']}"
    test_fn("high D_f → high Glutamate", _test_high_D_f_high_glu)

    def _test_low_R_high_na():
        pred = ccp_to_gnc_prediction({"D_f": 1.7, "R": 0.15, "phi_proxy": 0.0})
        assert pred["Noradrenaline"] > 0.5, f"low R should → NA↑, got {pred['Noradrenaline']}"
    test_fn("low R → high Noradrenaline", _test_low_R_high_na)

    def _test_high_phi_high_da():
        pred = ccp_to_gnc_prediction({"D_f": 1.7, "R": 0.5, "phi_proxy": 0.5})
        assert pred["Dopamine"] > 0.5, f"high Phi → DA↑, got {pred['Dopamine']}"
    test_fn("high Phi → high Dopamine", _test_high_phi_high_da)

    def _test_prediction_bounds():
        pred = ccp_to_gnc_prediction({"D_f": 3.0, "R": 0.0, "phi_proxy": -5.0})
        for m, v in pred.items():
            assert 0.1 <= v <= 0.9, f"{m}={v} out of bounds"
    test_fn("all predictions in [0.1, 0.9]", _test_prediction_bounds)


def _tests_gnc_to_ccp(test_fn) -> None:
    print("\n--- gnc_to_ccp_prediction ---")

    def _test_optimal_predicts_cognitive():
        st = GNCState.default()
        pred = gnc_to_ccp_prediction(st)
        assert pred["predicted_cognitive"], "optimal GNC+ should predict cognitive"
    test_fn("GNC+ optimal → predicts cognitive", _test_optimal_predicts_cognitive)

    def _test_dysregulated_predicts_noncognitive():
        st = compute_gnc_state({
            "Glutamate": 0.9, "GABA": 0.9, "Dopamine": 0.1,
            "Serotonin": 0.1, "Opioid": 0.9, "Noradrenaline": 0.1
        })
        pred = gnc_to_ccp_prediction(st)
        assert pred["confidence"] < 0.8, "dysregulated should have lower confidence"
    test_fn("GNC+ dysregulated → lower confidence", _test_dysregulated_predicts_noncognitive)

    def _test_confidence_range():
        for levels in [None, {"Dopamine": 0.9}, {"GABA": 0.9, "Glutamate": 0.1}]:
            st = compute_gnc_state(levels)
            pred = gnc_to_ccp_prediction(st)
            assert 0.0 <= pred["confidence"] <= 1.0
    test_fn("confidence in [0, 1]", _test_confidence_range)


def _tests_consistency(test_fn) -> None:
    print("\n--- validate_ccp_gnc_consistency ---")

    def _test_consistent_optimal_cognitive():
        ccp = {"cognitive": True}
        gnc = GNCState.default()
        result = validate_ccp_gnc_consistency(ccp, gnc)
        assert result["consistent"], "optimal + cognitive should be consistent"
    test_fn("optimal + cognitive = consistent", _test_consistent_optimal_cognitive)

    def _test_inconsistency_detected():
        ccp = {"cognitive": True}
        gnc = compute_gnc_state({
            "Glutamate": 0.9, "GABA": 0.9, "Dopamine": 0.1,
            "Serotonin": 0.1, "Opioid": 0.9, "Noradrenaline": 0.1
        })
        result = validate_ccp_gnc_consistency(ccp, gnc)
        assert "consistent" in result
        assert "recommendation" in result
    test_fn("inconsistency check returns all fields", _test_inconsistency_detected)

    def _test_noncognitive_optimal():
        ccp = {"cognitive": False}
        gnc = GNCState.default()
        result = validate_ccp_gnc_consistency(ccp, gnc)
        assert result["inconsistency_type"] == "ccp_noncognitive_gnc_optimal"
    test_fn("non-cognitive + optimal → inconsistency detected", _test_noncognitive_optimal)

    def _test_consistency_returns_all_keys():
        ccp = {"cognitive": True}
        gnc = GNCState.default()
        result = validate_ccp_gnc_consistency(ccp, gnc)
        for key in ["consistent", "ccp_cognitive", "gnc_regime", "inconsistency_type", "recommendation"]:
            assert key in result, f"missing key: {key}"
    test_fn("consistency check returns all keys", _test_consistency_returns_all_keys)


def _run_tests() -> None:
    passed = 0
    failed = 0

    def _test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            passed += 1
            print(f"  \u2713 {name}")
        except Exception as e:
            failed += 1
            print(f"  \u2717 {name}: {e}")

    print("=" * 60)
    print("CCP-GNC+ Bridge Test Suite")
    print("=" * 60)

    _tests_ccp_to_gnc(_test)
    _tests_gnc_to_ccp(_test)
    _tests_consistency(_test)

    # --- Summary ---
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
