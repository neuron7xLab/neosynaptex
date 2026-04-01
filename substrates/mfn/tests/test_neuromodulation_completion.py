from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from mycelium_fractal_net.core.compare import compare
from mycelium_fractal_net.core.detect import detect_anomaly, detect_regime_shift
from mycelium_fractal_net.core.forecast import counterfactual, forecast_next
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.integration.api_server import create_app
from mycelium_fractal_net.types.field import (
    GABAATonicSpec,
    NeuromodulationSpec,
    ObservationNoiseSpec,
    SerotonergicPlasticitySpec,
    SimulationSpec,
)


def _gabaa_spec() -> NeuromodulationSpec:
    return NeuromodulationSpec(
        profile="gabaa_tonic_muscimol_alpha1beta3",
        enabled=True,
        dt_seconds=1.0,
        gabaa_tonic=GABAATonicSpec(
            profile="gabaa_tonic_muscimol_alpha1beta3",
            agonist_concentration_um=0.85,
            resting_affinity_um=0.45,
            active_affinity_um=0.35,
            desensitization_rate_hz=0.05,
            recovery_rate_hz=0.02,
            shunt_strength=0.42,
        ),
    )


def test_baseline_parity_gate_neuromodulation_none() -> None:
    spec_a = SimulationSpec(grid_size=16, steps=8, seed=42)
    spec_b = SimulationSpec.from_dict({**spec_a.to_dict(), "neuromodulation": None})
    left = simulate_history(spec_a)
    right = simulate_history(spec_b)
    assert np.array_equal(left.field, right.field)
    assert np.array_equal(left.history, right.history)
    assert left.to_dict().keys() == right.to_dict().keys()


def test_neuromodulation_spec_roundtrip() -> None:
    spec = SimulationSpec(
        grid_size=16,
        steps=8,
        seed=42,
        neuromodulation=NeuromodulationSpec(
            profile="balanced_criticality_candidate",
            enabled=True,
            dt_seconds=0.5,
            intrinsic_field_jitter=True,
            intrinsic_field_jitter_var=0.0002,
            gabaa_tonic=GABAATonicSpec(
                profile="balanced_criticality_candidate",
                agonist_concentration_um=0.2,
                resting_affinity_um=0.25,
                active_affinity_um=0.22,
                desensitization_rate_hz=0.015,
                recovery_rate_hz=0.03,
                shunt_strength=0.18,
            ),
            serotonergic=SerotonergicPlasticitySpec(
                profile="balanced_criticality_candidate",
                gain_fluidity_coeff=0.05,
                reorganization_drive=0.05,
                coherence_bias=0.01,
            ),
            observation_noise=ObservationNoiseSpec(
                profile="observation_noise_gaussian_temporal",
                std=0.0012,
                temporal_smoothing=0.35,
            ),
        ),
    )
    recovered = SimulationSpec.from_dict(spec.to_dict())
    assert recovered.neuromodulation is not None
    assert recovered.neuromodulation.profile == "balanced_criticality_candidate"
    assert recovered.neuromodulation.gabaa_tonic is not None
    assert recovered.neuromodulation.serotonergic is not None
    assert recovered.neuromodulation.observation_noise is not None


def test_plasticity_aware_detect_compare_forecast() -> None:
    base = simulate_history(SimulationSpec(grid_size=16, steps=8, seed=42))
    reorganized = simulate_history(
        SimulationSpec(
            grid_size=16,
            steps=8,
            seed=42,
            neuromodulation=NeuromodulationSpec(
                profile="serotonergic_reorganization_candidate",
                enabled=True,
                serotonergic=SerotonergicPlasticitySpec(
                    profile="serotonergic_reorganization_candidate",
                    gain_fluidity_coeff=0.08,
                    reorganization_drive=0.12,
                    coherence_bias=0.02,
                ),
            ),
        )
    )
    anomaly = detect_anomaly(reorganized)
    regime = detect_regime_shift(reorganized)
    result = compare(base, reorganized)
    forecast = forecast_next(reorganized, horizon=4)
    cf = counterfactual(
        reorganized,
        SimulationSpec(grid_size=16, steps=8, seed=42, neuromodulation=_gabaa_spec()),
    )
    assert regime.label in {
        "stable",
        "transitional",
        "critical",
        "reorganized",
        "pathological_noise",
    }
    assert anomaly.regime is not None
    assert "connectivity_divergence" in result.drift_summary
    assert result.reorganization_label in {
        "stable",
        "transitional",
        "critical",
        "reorganized",
        "pathological_noise",
    }
    assert 0.85 <= forecast.benchmark_metrics["adaptive_damping"] <= 0.92
    assert cf.metadata["counterfactual_mode"] == "gabaa-tonic"


def test_api_neuromodulation_surface() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/simulate",
        json={
            "seed": 42,
            "grid_size": 16,
            "steps": 8,
            "with_history": True,
            "neuromodulation": {
                "profile": "observation_noise_gaussian_temporal",
                "enabled": True,
                "dt_seconds": 1.0,
                "observation_noise": {
                    "profile": "observation_noise_gaussian_temporal",
                    "std": 0.0012,
                    "temporal_smoothing": 0.35,
                },
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["spec"]["neuromodulation"]["profile"] == "observation_noise_gaussian_temporal"


def test_neuromodulation_state_machine_bounds_and_local_offset() -> None:
    seq = simulate_history(
        SimulationSpec(
            grid_size=16,
            steps=12,
            seed=7,
            neuromodulation=NeuromodulationSpec(
                profile="gabaa_tonic_extrasynaptic_delta_high_affinity",
                enabled=True,
                dt_seconds=1.0,
                gabaa_tonic=GABAATonicSpec(
                    profile="gabaa_tonic_extrasynaptic_delta_high_affinity",
                    agonist_concentration_um=0.35,
                    resting_affinity_um=0.10,
                    active_affinity_um=0.08,
                    desensitization_rate_hz=0.02,
                    recovery_rate_hz=0.06,
                    shunt_strength=0.50,
                    rest_offset_mv=-0.40,
                    baseline_activation_offset_mv=-0.15,
                    tonic_inhibition_scale=1.25,
                    k_on=0.30,
                    k_off=0.04,
                    K_R=0.10,
                    c=0.95,
                    Q=0.88,
                    L=1.45,
                    binding_sites=3,
                    k_leak_reduction_fraction=0.24,
                ),
            ),
        )
    )
    assert seq.metadata["occupancy_bounds_ok"] is True
    assert seq.metadata["occupancy_mass_error_max"] <= 1e-6
    assert 0.0 <= seq.metadata["occupancy_active_mean"] <= 1.0
    assert seq.metadata["excitability_offset_mean_v"] < 0.0
