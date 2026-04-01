"""Property-based tests for neuromodulation kinetics.

Uses Hypothesis to verify occupancy conservation holds for ALL valid
parameter combinations, not just canonical profiles.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mycelium_fractal_net.neurochem.config_types import (
    GABAAKineticsConfig,
    ObservationNoiseConfig,
    SerotonergicKineticsConfig,
)
from mycelium_fractal_net.neurochem.kinetics import step_neuromodulation_state
from mycelium_fractal_net.neurochem.state import NeuromodulationState


def _gabaa_config(
    concentration: float = 10.0,
    k_on: float = 0.22,
    k_off: float = 0.06,
    des_rate: float = 0.05,
    rec_rate: float = 0.02,
    shunt: float = 0.42,
) -> GABAAKineticsConfig:
    return GABAAKineticsConfig(
        agonist_concentration_um=concentration,
        resting_affinity_um=0.30,
        active_affinity_um=0.25,
        k_on=k_on,
        k_off=k_off,
        desensitization_rate_hz=des_rate,
        recovery_rate_hz=rec_rate,
        shunt_strength=shunt,
        tonic_inhibition_scale=1.0,
    )


class TestOccupancyConservationSingleStep:
    """Occupancy must sum to 1.0 after every step, for all valid parameters."""

    @given(
        dt=st.floats(min_value=0.001, max_value=2.0),
        concentration=st.floats(min_value=0.0, max_value=1000.0),
        k_on=st.floats(min_value=0.01, max_value=1.0),
        k_off=st.floats(min_value=0.01, max_value=1.0),
        des_rate=st.floats(min_value=0.0, max_value=0.5),
        rec_rate=st.floats(min_value=0.0, max_value=0.5),
    )
    @settings(max_examples=200, deadline=5000)
    def test_single_step_conservation(
        self,
        dt: float,
        concentration: float,
        k_on: float,
        k_off: float,
        des_rate: float,
        rec_rate: float,
    ) -> None:
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        activator = np.random.default_rng(42).uniform(0, 0.1, shape).astype(np.float64)
        field = np.random.default_rng(42).normal(-0.065, 0.005, shape).astype(np.float64)

        gabaa = _gabaa_config(
            concentration=concentration,
            k_on=k_on,
            k_off=k_off,
            des_rate=des_rate,
            rec_rate=rec_rate,
        )

        new_state = step_neuromodulation_state(
            state,
            dt_seconds=dt,
            activator=activator,
            field=field,
            gabaa=gabaa,
            serotonergic=None,
            observation_noise=None,
        )

        total = (
            new_state.occupancy_resting
            + new_state.occupancy_active
            + new_state.occupancy_desensitized
        )
        np.testing.assert_allclose(
            total,
            1.0,
            atol=1e-6,
            err_msg=f"Conservation violated: dt={dt}, conc={concentration}, k_on={k_on}",
        )

    @given(
        dt=st.floats(min_value=0.001, max_value=2.0),
        concentration=st.floats(min_value=0.0, max_value=1000.0),
        k_on=st.floats(min_value=0.01, max_value=1.0),
        k_off=st.floats(min_value=0.01, max_value=1.0),
        des_rate=st.floats(min_value=0.0, max_value=0.5),
        rec_rate=st.floats(min_value=0.0, max_value=0.5),
    )
    @settings(max_examples=200, deadline=5000)
    def test_occupancy_bounds(
        self,
        dt: float,
        concentration: float,
        k_on: float,
        k_off: float,
        des_rate: float,
        rec_rate: float,
    ) -> None:
        """Each occupancy component must be in [0, 1]."""
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        activator = np.random.default_rng(42).uniform(0, 0.1, shape).astype(np.float64)
        field = np.random.default_rng(42).normal(-0.065, 0.005, shape).astype(np.float64)

        gabaa = _gabaa_config(
            concentration=concentration,
            k_on=k_on,
            k_off=k_off,
            des_rate=des_rate,
            rec_rate=rec_rate,
        )

        new_state = step_neuromodulation_state(
            state,
            dt_seconds=dt,
            activator=activator,
            field=field,
            gabaa=gabaa,
            serotonergic=None,
            observation_noise=None,
        )

        assert np.all(new_state.occupancy_resting >= -1e-9), "resting < 0"
        assert np.all(new_state.occupancy_resting <= 1.0 + 1e-9), "resting > 1"
        assert np.all(new_state.occupancy_active >= -1e-9), "active < 0"
        assert np.all(new_state.occupancy_active <= 1.0 + 1e-9), "active > 1"
        assert np.all(new_state.occupancy_desensitized >= -1e-9), "desensitized < 0"
        assert np.all(new_state.occupancy_desensitized <= 1.0 + 1e-9), "desensitized > 1"


class TestOccupancyConservationMultiStep:
    """Conservation must hold after multiple consecutive steps."""

    @given(
        n_steps=st.integers(min_value=2, max_value=10),
        concentration=st.floats(min_value=0.1, max_value=100.0),
        dt=st.floats(min_value=0.1, max_value=1.0),
    )
    @settings(max_examples=200, deadline=10000)
    def test_multi_step_conservation(
        self,
        n_steps: int,
        concentration: float,
        dt: float,
    ) -> None:
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        activator = rng.uniform(0, 0.1, shape).astype(np.float64)
        field = rng.normal(-0.065, 0.005, shape).astype(np.float64)
        gabaa = _gabaa_config(concentration=concentration)

        for step in range(n_steps):
            state = step_neuromodulation_state(
                state,
                dt_seconds=dt,
                activator=activator,
                field=field,
                gabaa=gabaa,
                serotonergic=None,
                observation_noise=None,
            )
            total = state.occupancy_resting + state.occupancy_active + state.occupancy_desensitized
            np.testing.assert_allclose(
                total,
                1.0,
                atol=1e-6,
                err_msg=f"Conservation violated at step {step}",
            )

    def test_10_step_conservation(self) -> None:
        """Explicit 10-step conservation check."""
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        activator = rng.uniform(0, 0.1, shape).astype(np.float64)
        field = rng.normal(-0.065, 0.005, shape).astype(np.float64)
        gabaa = _gabaa_config(concentration=10.0)
        for _ in range(10):
            state = step_neuromodulation_state(
                state,
                dt_seconds=0.5,
                activator=activator,
                field=field,
                gabaa=gabaa,
                serotonergic=None,
                observation_noise=None,
            )
        assert state.occupancy_mass_error_max() < 1e-6

    def test_50_step_conservation(self) -> None:
        """50-step conservation check."""
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        activator = rng.uniform(0, 0.1, shape).astype(np.float64)
        field = rng.normal(-0.065, 0.005, shape).astype(np.float64)
        gabaa = _gabaa_config(concentration=10.0)
        for _ in range(50):
            state = step_neuromodulation_state(
                state,
                dt_seconds=0.5,
                activator=activator,
                field=field,
                gabaa=gabaa,
                serotonergic=None,
                observation_noise=None,
            )
        assert state.occupancy_mass_error_max() < 1e-6

    def test_100_step_conservation(self) -> None:
        """100-step conservation check."""
        shape = (8, 8)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        activator = rng.uniform(0, 0.1, shape).astype(np.float64)
        field = rng.normal(-0.065, 0.005, shape).astype(np.float64)
        gabaa = _gabaa_config(concentration=10.0)
        for _ in range(100):
            state = step_neuromodulation_state(
                state,
                dt_seconds=0.5,
                activator=activator,
                field=field,
                gabaa=gabaa,
                serotonergic=None,
                observation_noise=None,
            )
        assert state.occupancy_mass_error_max() < 1e-6


class TestOccupancyEdgeCases:
    """Edge cases that might break conservation."""

    def test_near_zero_dt(self) -> None:
        """Very small dt should produce minimal change but conserve mass."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(1)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1e-6,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=_gabaa_config(),
            serotonergic=None,
            observation_noise=None,
        )
        total = (
            new_state.occupancy_resting
            + new_state.occupancy_active
            + new_state.occupancy_desensitized
        )
        np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_extreme_concentration(self) -> None:
        """Very high concentration should not break conservation."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(2)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=_gabaa_config(concentration=10000.0),
            serotonergic=None,
            observation_noise=None,
        )
        total = (
            new_state.occupancy_resting
            + new_state.occupancy_active
            + new_state.occupancy_desensitized
        )
        np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_near_zero_rates(self) -> None:
        """Near-zero kinetic rates should conserve mass."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(4)
        gabaa = _gabaa_config(k_on=0.001, k_off=0.001, des_rate=0.001, rec_rate=0.001)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=gabaa,
            serotonergic=None,
            observation_noise=None,
        )
        total = (
            new_state.occupancy_resting
            + new_state.occupancy_active
            + new_state.occupancy_desensitized
        )
        np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_high_desensitization_recovery(self) -> None:
        """High desensitization + recovery rates should conserve mass."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(5)
        gabaa = _gabaa_config(des_rate=0.5, rec_rate=0.5)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=gabaa,
            serotonergic=None,
            observation_noise=None,
        )
        total = (
            new_state.occupancy_resting
            + new_state.occupancy_active
            + new_state.occupancy_desensitized
        )
        np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_no_gabaa(self) -> None:
        """Without GABA-A, occupancy should be all resting."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(3)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=None,
            serotonergic=None,
            observation_noise=None,
        )
        np.testing.assert_allclose(new_state.occupancy_resting, 1.0, atol=1e-10)
        np.testing.assert_allclose(new_state.occupancy_active, 0.0, atol=1e-10)


class TestTypedConfigValidation:
    """Tests for typed config acceptance and invalid type rejection."""

    def test_valid_typed_gabaa_config(self) -> None:
        """Valid GABAAKineticsConfig should be accepted."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        gabaa = GABAAKineticsConfig(
            agonist_concentration_um=10.0,
            resting_affinity_um=0.30,
            active_affinity_um=0.25,
            k_on=0.22,
            k_off=0.06,
        )
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=gabaa,
            serotonergic=None,
            observation_noise=None,
        )
        assert new_state.occupancy_mass_error_max() < 1e-6

    def test_valid_typed_serotonergic_config(self) -> None:
        """Valid SerotonergicKineticsConfig should be accepted."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        sero = SerotonergicKineticsConfig(
            plasticity_scale=1.3,
            reorganization_drive=0.12,
            gain_fluidity_coeff=0.08,
            coherence_bias=0.02,
        )
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=None,
            serotonergic=sero,
            observation_noise=None,
        )
        assert np.all(np.isfinite(new_state.effective_gain))

    def test_valid_typed_observation_noise_config(self) -> None:
        """Valid ObservationNoiseConfig should be accepted."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        obs = ObservationNoiseConfig(std=0.001, temporal_smoothing=0.35)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=None,
            serotonergic=None,
            observation_noise=obs,
        )
        assert np.all(new_state.observation_noise_gain >= 0)

    def test_missing_optional_config(self) -> None:
        """All optional configs as None should work."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        new_state = step_neuromodulation_state(
            state,
            dt_seconds=1.0,
            activator=rng.uniform(0, 0.1, shape).astype(np.float64),
            field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
            gabaa=None,
            serotonergic=None,
            observation_noise=None,
        )
        np.testing.assert_allclose(new_state.occupancy_resting, 1.0, atol=1e-10)

    def test_invalid_type_rejection_gabaa(self) -> None:
        """Passing a raw dict should raise AttributeError (dict has no attributes)."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        with pytest.raises(AttributeError):
            step_neuromodulation_state(
                state,
                dt_seconds=1.0,
                activator=rng.uniform(0, 0.1, shape).astype(np.float64),
                field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
                gabaa={"agonist_concentration_um": 10.0},  # type: ignore[arg-type]
                serotonergic=None,
                observation_noise=None,
            )

    def test_invalid_type_rejection_serotonergic(self) -> None:
        """Passing a raw dict for serotonergic should raise AttributeError."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        with pytest.raises(AttributeError):
            step_neuromodulation_state(
                state,
                dt_seconds=1.0,
                activator=rng.uniform(0, 0.1, shape).astype(np.float64),
                field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
                gabaa=None,
                serotonergic={"plasticity_scale": 1.3},  # type: ignore[arg-type]
                observation_noise=None,
            )

    def test_invalid_type_rejection_observation_noise(self) -> None:
        """Passing a raw dict for observation_noise should raise AttributeError."""
        shape = (4, 4)
        state = NeuromodulationState.zeros(shape)
        rng = np.random.default_rng(42)
        with pytest.raises(AttributeError):
            step_neuromodulation_state(
                state,
                dt_seconds=1.0,
                activator=rng.uniform(0, 0.1, shape).astype(np.float64),
                field=rng.normal(-0.065, 0.005, shape).astype(np.float64),
                gabaa=None,
                serotonergic=None,
                observation_noise={"std": 0.001},  # type: ignore[arg-type]
            )

    def test_gabaa_from_dict(self) -> None:
        """GABAAKineticsConfig.from_dict should work."""
        config = GABAAKineticsConfig.from_dict(
            {
                "agonist_concentration_um": 10.0,
                "k_on": 0.22,
                "unknown_key": "ignored",
            }
        )
        assert config.agonist_concentration_um == 10.0
        assert config.k_on == 0.22
        assert config.k_off == DEFAULT_K_OFF_HZ  # default


from mycelium_fractal_net.neurochem.constants import DEFAULT_K_OFF_HZ
