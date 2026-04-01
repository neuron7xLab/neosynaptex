from __future__ import annotations

import pytest

from bnsyn.biodigital import (
    BioSignalState,
    ThermostatState,
    al_update,
    evaluate_neuro_consistency,
    landauer_thermostat,
    normalized_shannon_entropy,
    update_5ht_impulse_control,
    update_ach_uncertainty,
    update_oxt_coherence,
)


def test_entropy_coupler_and_signal_updates_are_bounded() -> None:
    h_q_norm = normalized_shannon_entropy([2.0, 2.0, 2.0, 2.0])
    assert 0.99 <= h_q_norm <= 1.0

    u = update_ach_uncertainty(u_base=0.2, k_u=0.9, h_q_norm=h_q_norm)
    o = update_oxt_coherence(o_base=0.5, k_o=0.4, coherence_score=0.9, conflict_score=0.1)
    t = update_5ht_impulse_control(
        t_base=0.3,
        k_t=0.7,
        stability_need=0.8,
        immediate_gain_pressure=0.1,
    )

    assert 0.0 <= u <= 1.0
    assert 0.0 <= o <= 1.0
    assert 0.0 <= t <= 1.0


def test_allostasis_update_is_deterministic_and_bounded() -> None:
    state_a = al_update(
        metrics=(0.1, 0.3, 0.5),
        budgets=(0.9, 0.8),
        history=(0.7, 0.4, 0.6),
        horizon_steps=2,
    )
    state_b = al_update(
        metrics=(0.1, 0.3, 0.5),
        budgets=(0.9, 0.8),
        history=(0.7, 0.4, 0.6),
        horizon_steps=2,
    )

    assert state_a == state_b
    assert len(state_a.forecast_vector) == 2
    assert all(target >= 0.0 for target in state_a.target_vector)


def test_landauer_thermostat_triggers_verify_mode() -> None:
    report = landauer_thermostat(
        ThermostatState(erased_bits_proxy=120.0, entropy_budget=100.0, t_max=0.95)
    )

    assert report.triggered is True
    assert report.stress_guard == 1.0
    assert report.mode == "verify"
    assert report.candidate_expansion_blocked is True


def test_neuro_consistency_gate_reports_violations() -> None:
    signals = BioSignalState(u=0.9, a=0.7, r=0.8, s=0.95, o=0.1, t=0.9)
    result = evaluate_neuro_consistency(
        signals=signals,
        mode="explore",
        allow_external_sources=True,
        require_extra_certificates=False,
    )

    assert result.pass_gate is False
    assert result.r_effective == 0.0
    assert "mode_incompatible_with_stress_guard" in result.violations
    assert "high_impulse_requires_extra_certificates" in result.violations
    assert "low_coherence_forbids_untrusted_external_sources" in result.violations


def test_input_validation_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="distribution must not be empty"):
        normalized_shannon_entropy([])

    with pytest.raises(ValueError, match="distribution must not contain negative"):
        normalized_shannon_entropy([0.1, -0.1, 0.4])

    with pytest.raises(ValueError, match="mode must be one of"):
        evaluate_neuro_consistency(
            signals=BioSignalState(u=0.2, a=0.4, r=0.1, s=0.2, o=0.8, t=0.3),
            mode="invalid",  # type: ignore[arg-type]
            allow_external_sources=False,
            require_extra_certificates=True,
        )

    with pytest.raises(ValueError, match="entropy_budget must be > 0"):
        landauer_thermostat(ThermostatState(erased_bits_proxy=0.0, entropy_budget=0.0, t_max=0.7))


def test_al_update_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="metrics must not be empty"):
        al_update(metrics=(), budgets=(1.0,), history=(1.0,), horizon_steps=1)

    with pytest.raises(ValueError, match="budgets must not be empty"):
        al_update(metrics=(1.0,), budgets=(), history=(1.0,), horizon_steps=1)

    with pytest.raises(ValueError, match="history must not be empty"):
        al_update(metrics=(1.0,), budgets=(1.0,), history=(), horizon_steps=1)
