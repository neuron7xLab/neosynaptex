"""Parameter definitions for BN-Syn components.

Parameters
----------
None

Returns
-------
None

Notes
-----
Defines typed parameter models used across SPEC components.

References
----------
docs/SPEC.md
docs/SSOT.md
"""

from __future__ import annotations

from pydantic import BaseModel, Field, PositiveFloat


class AdExParams(BaseModel):
    """AdEx neuron parameters (units: pF, nS, mV, ms, pA).

    Parameters
    ----------
    C_pF : float
        Membrane capacitance (pF).
    gL_nS : float
        Leak conductance (nS).
    EL_mV : float
        Leak reversal potential (mV).
    VT_mV : float
        Spike threshold (mV).
    DeltaT_mV : float
        Exponential slope factor (mV).
    tauw_ms : float
        Adaptation time constant (ms).
    a_nS : float
        Subthreshold adaptation conductance (nS).
    b_pA : float
        Spike-triggered adaptation increment (pA).
    Vreset_mV : float
        Reset voltage after spike (mV).
    Vpeak_mV : float
        Spike peak clamp voltage (mV).

    Notes
    -----
    These parameters implement the SPEC P0-1 AdEx neuron model.

    References
    ----------
    docs/SPEC.md#P0-1
    """

    # Units: pF, nS, mV, ms, pA
    C_pF: PositiveFloat = Field(default=150.0, description="Membrane capacitance (pF)")
    gL_nS: PositiveFloat = Field(default=10.0, description="Leak conductance (nS)")
    EL_mV: float = Field(default=-70.0, description="Leak reversal (mV)")
    VT_mV: float = Field(default=-55.0, description="Threshold (mV)")
    DeltaT_mV: PositiveFloat = Field(default=2.0, description="Slope factor (mV)")
    tauw_ms: PositiveFloat = Field(default=200.0, description="Adaptation time constant (ms)")
    a_nS: float = Field(default=2.0, description="Subthreshold adaptation (nS)")
    b_pA: float = Field(default=80.0, description="Spike-triggered adaptation increment (pA)")
    Vreset_mV: float = Field(default=-58.0, description="Reset voltage (mV)")
    Vpeak_mV: float = Field(default=30.0, description="Spike peak clamp (mV)")


class SynapseParams(BaseModel):
    """Synapse parameters for conductance-based synapses.

    Parameters
    ----------
    E_AMPA_mV : float
        AMPA reversal potential (mV).
    E_NMDA_mV : float
        NMDA reversal potential (mV).
    E_GABAA_mV : float
        GABA_A reversal potential (mV).
    tau_AMPA_ms : float
        AMPA decay time constant (ms).
    tau_NMDA_ms : float
        NMDA decay time constant (ms).
    tau_GABAA_ms : float
        GABA_A decay time constant (ms).
    delay_ms : float
        Synaptic transmission delay (ms).
    mg_mM : float
        Extracellular magnesium concentration (mM).

    Notes
    -----
    Parameters support conductance-based synapse dynamics in SPEC P0-2.

    References
    ----------
    docs/SPEC.md#P0-2
    """

    E_AMPA_mV: float = 0.0
    E_NMDA_mV: float = 0.0
    E_GABAA_mV: float = -70.0

    tau_AMPA_ms: PositiveFloat = 2.5
    tau_NMDA_ms: PositiveFloat = 100.0
    tau_GABAA_ms: PositiveFloat = 6.0

    delay_ms: PositiveFloat = 1.0
    mg_mM: PositiveFloat = 1.0  # extracellular Mg2+


class PlasticityParams(BaseModel):
    """Three-factor plasticity parameters.

    Parameters
    ----------
    tau_e_ms : float
        Eligibility trace decay time constant (ms).
    tau_plus_ms : float
        STDP potentiation trace time constant (ms).
    tau_minus_ms : float
        STDP depression trace time constant (ms).
    A_plus : float
        Potentiation amplitude.
    A_minus : float
        Depression amplitude.
    eta : float
        Learning rate for three-factor updates.
    w_min : float
        Minimum synaptic weight.
    w_max : float
        Maximum synaptic weight.

    Notes
    -----
    Implements the SPEC P0-3 three-factor plasticity rule.

    References
    ----------
    docs/SPEC.md#P0-3
    """

    tau_e_ms: PositiveFloat = 500.0
    tau_plus_ms: PositiveFloat = 20.0
    tau_minus_ms: PositiveFloat = 20.0
    A_plus: PositiveFloat = 1.0
    A_minus: PositiveFloat = 1.05
    eta: PositiveFloat = 5e-3
    w_min: float = 0.0
    w_max: float = 200.0


class CriticalityParams(BaseModel):
    """Criticality control parameters for sigma tracking.

    Parameters
    ----------
    sigma_target : float
        Target branching ratio.
    eta_sigma : float
        Gain update rate for sigma control.
    gain_min : float
        Lower bound on gain.
    gain_max : float
        Upper bound on gain.

    Notes
    -----
    Used by the SPEC P0-4 sigma tracking control loop.

    References
    ----------
    docs/SPEC.md#P0-4
    """

    sigma_target: float = 1.0
    eta_sigma: PositiveFloat = 1e-3
    gain_min: PositiveFloat = 0.2
    gain_max: PositiveFloat = 5.0


class TemperatureParams(BaseModel):
    """Temperature schedule and gate parameters.

    Parameters
    ----------
    T0 : float
        Initial temperature.
    Tmin : float
        Minimum temperature floor.
    alpha : float
        Cooling factor per update.
    Tc : float
        Critical temperature for gating.
    gate_tau : float
        Sigmoid sharpness for temperature gating.

    Notes
    -----
    Parameters drive the SPEC P1-2 temperature schedule.

    References
    ----------
    docs/SPEC.md#P1-2
    """

    T0: PositiveFloat = 1.0
    Tmin: PositiveFloat = 1e-3
    alpha: float = Field(default=0.95, ge=0.0, le=1.0)
    Tc: PositiveFloat = 0.1
    gate_tau: float = Field(
        default=0.02,
        ge=0.015,
        le=0.08,
        description=(
            "Validated temperature-gate slope window from ablation studies; "
            "narrow bounds prevent near-binary gating at low tau and over-flat gating at high tau."
        ),
    )


class DualWeightParams(BaseModel):
    """Dual-weight consolidation parameters.

    Parameters
    ----------
    tau_f_s : float
        Fast weight decay time constant (s).
    tau_tag_s : float
        Synaptic tag decay time constant (s).
    tau_p_s : float
        Protein pool decay time constant (s).
    theta_tag : float
        Tagging threshold.
    eta_f : float
        Fast weight learning rate.
    eta_c : float
        Consolidation learning rate.

    Notes
    -----
    Parameters implement the SPEC P1-6 dual-weight consolidation dynamics.

    References
    ----------
    docs/SPEC.md#P1-6
    """

    tau_f_s: PositiveFloat = 1800.0  # 30 min
    tau_tag_s: PositiveFloat = 5400.0  # 90 min
    tau_p_s: PositiveFloat = 7200.0  # 2 h
    theta_tag: PositiveFloat = 0.25
    eta_f: PositiveFloat = 0.05
    eta_c: PositiveFloat = 0.005


class EnergyParams(BaseModel):
    """Energy regularization parameters.

    Parameters
    ----------
    lambda_rate : float
        Quadratic penalty weight for firing rates.
    lambda_weight : float
        Quadratic penalty weight for synaptic weights.
    lambda_energy : float
        Penalty weight for total energy expenditure.
    r_min_hz : float
        Minimum firing rate floor for reward shaping.

    Notes
    -----
    Used by the energy regularization and reward shaping utilities.

    References
    ----------
    docs/SPEC.md
    """

    lambda_rate: PositiveFloat = 1e-3
    lambda_weight: PositiveFloat = 5e-4
    lambda_energy: PositiveFloat = 1e-2
    r_min_hz: PositiveFloat = 0.05
