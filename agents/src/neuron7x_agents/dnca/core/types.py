"""
DNCA Type System — protocols, enums, constants.

All parameters from the canonical specification with
biological calibration sources cited.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Protocol, runtime_checkable

import torch


# =============================================================================
# Constants — Biologically Calibrated
# =============================================================================

# Competition field
CAPTURE_THRESHOLD = 0.30
# Biased competition ~30% shift. Source: Reynolds, Chelazzi & Desimone 1999
# DOI: 10.1523/JNEUROSCI.19-05-01736.1999

DOMINANCE_THRESHOLD = 0.70
# Layer 1 WTA winner ~75%. Source: Adam & Serences 2020 (approximate)
# DOI: 10.1523/JNEUROSCI.2984-19.2020

SATIATION_THRESHOLD = 0.90
# Spike-rate adaptation τ >= 1s. Source: McCormick & Williamson 1989
# DOI: 10.1152/jn.1989.62.5.1149

INHIBITION_STRENGTH = 0.75
# Wilson-Cowan c_2/c_1 = 12/16. Source: Wilson & Cowan 1972
# DOI: 10.1016/S0006-3495(72)86068-5

# Oscillations
THETA_FREQ_HZ = 6.0
# Hippocampal theta 4-8 Hz, canonical 6 Hz. Source: Buzsaki 2002
# DOI: 10.1016/S0896-6273(02)00649-9

GAMMA_FREQ_HZ = 40.0
# Canonical nested gamma 30-80 Hz. Source: Lisman & Jensen 2013
# DOI: 10.1016/j.neuron.2013.03.007

N_GAMMA_SLOTS = 7             # 167ms/25ms = 6.7 ~ Miller's 7+-2
PAC_MODULATION_INDEX = 0.005  # typical significant MI (Tort et al. 2010)

# Prediction / learning
POSITIVE_RPE_GAIN = 5.5
# Dopamine burst 20-30 Hz from 3-5 Hz baseline. Source: Schultz 1997
# DOI: 10.1126/science.275.5306.1593

NEGATIVE_RPE_GAIN = 1.0
# Floor-limited dip. Source: Bayer & Glimcher 2005
# DOI: 10.1016/j.neuron.2005.09.009

ORIENTING_THRESHOLD_SD = 2.0  # MMN triggers at ~2 SD (Naatanen et al. 2007)

CEREBELLUM_LR = 0.003
# 25-40% EPSC change per 100 pairings. Source: Suvrathan et al. 2016
# DOI: 10.1016/j.neuron.2016.10.002

TEMPORAL_WINDOW_STEPS = 6     # 6 steps x 25ms = 150ms LTD window

# Regime lifecycle
MAX_REGIME_DURATION = 2400    # steps at 25ms = 60s sustained attention
MIN_REGIME_DURATION = 8       # steps = 200ms attentional dwell time
MISMATCH_COLLAPSE = 100.0     # integral collapse threshold

# Metastability
METASTABILITY_THRESHOLD = 0.10
# std(r) target floor for healthy metastable dynamics. Source: Tognoli & Kelso 2014
# DOI: 10.1016/j.neuron.2013.12.022

COLLAPSE_THRESHOLD = 0.15       # r_mean floor
RIGIDITY_THRESHOLD = 0.85       # r_mean ceiling

COUPLING_DEFAULT = 1.20
# Kuramoto K default — empirically calibrated for r_std > 0.10

# Activity
ACTIVITY_THRESHOLD = 0.05       # NMO active if A_i > this
COMPETITION_RATIO = 0.85        # overthrow threshold

# Forward model learning (orchestrator inner SGD)
FORWARD_MODEL_LR = 0.08         # inner SGD learning rate for DAC forward models
FORWARD_MODEL_INNER_STEPS = 20  # SGD iterations per DNCA step
PLASTICITY_GATE_THRESHOLD = -0.3  # cos(θ) threshold for allowing learning (INV-8)
# Rationale: cos(-0.3) opens gate for ~60% of theta cycle,
# allowing learning near both peak (LTP) and moderate trough.

# DAC dynamics
DAC_GOAL_INERTIA = 0.95          # dominant goal update smoothing (Ukhtomsky inertia)
DAC_GOAL_HINT_BLEND = 0.30       # blend ratio for external goal hint
DAC_SUMMATION_BASE = 0.15        # minimum summation boost (Ukhtomsky: all input helps)
DAC_SUMMATION_RELEVANCE = 0.35   # additional boost from input relevance
DAC_SUMMATION_DOMINANT_MULT = 1.5  # multiplier for established dominant
DAC_SATIATION_INCREMENT = 0.003  # per-step satiation accumulation in DOMINANT phase
DAC_SATIATION_LEARNING = 0.002   # satiation from low mismatch (good predictions)
DAC_RESIDUAL_SCALE = 0.1         # scale factor for residual forward model delta

# NMO natural frequencies (Hz, relative to theta=6Hz baseline)
NMO_FREQ_DA = 1.2    # dopamine: slightly faster than baseline
NMO_FREQ_ACH = 0.8   # acetylcholine: slower, sustained attention
NMO_FREQ_NE = 1.5    # norepinephrine: fast, responsive
NMO_FREQ_SHT = 0.5   # serotonin: slow, patient
NMO_FREQ_GABA = 0.7  # GABA: moderate
NMO_FREQ_GLU = 1.0   # glutamate: baseline

# Metastability bounds
COUPLING_K_MIN = 0.1   # minimum Kuramoto coupling (prevents collapse to K≈0)
COUPLING_K_MAX = 5.0   # maximum Kuramoto coupling (prevents hyper-synchronization)


# =============================================================================
# Enums
# =============================================================================

class NMOType(Enum):
    """Six neuromodulatory operator types."""
    DA = "dopamine"
    ACH = "acetylcholine"
    NE = "norepinephrine"
    SHT = "serotonin"
    GABA = "gaba"
    GLU = "glutamate"


class RegimePhase(Enum):
    """Dominant regime lifecycle phases."""
    FORMING = auto()
    ACTIVE = auto()
    SATURATING = auto()
    DISSOLVING = auto()
    COLLAPSED = auto()


class NEMode(Enum):
    """Norepinephrine operating mode (Aston-Jones & Cohen 2005)."""
    PHASIC = auto()  # high gain, exploitation
    TONIC = auto()   # low gain, exploration


# =============================================================================
# Data Contracts
# =============================================================================

@dataclass(slots=True)
class RegimeTransitionEvent:
    """Emitted on every regime transition. INV-7: must be logged."""
    step: int
    from_regime_id: Optional[int]
    to_regime_id: Optional[int]
    from_nmo: Optional[str]
    to_nmo: Optional[str]
    trigger: str  # satiation, mismatch_collapse, ne_reset, overthrow, max_duration
    coherence_at_transition: float
    from_duration: int


@dataclass(slots=True)
class DNCAAudit:
    """Per-step audit record for debugging and benchmarking."""
    step: int
    activities: Dict[str, float]
    dominant_nmo: Optional[str]
    regime_phase: str
    regime_age: int
    r_mean: float
    r_std: float
    coupling_K: float
    mismatch: float
    satiation: float
    plasticity_gate: float
    theta_phase: float


# =============================================================================
# Protocols
# =============================================================================

@runtime_checkable
class NeuromodulatoryOperatorProtocol(Protocol):
    """Contract that every NMO must satisfy."""
    nmo_type: NMOType
    activity: float

    def modulate(self, sps: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Read SPS, compute modulation, return fields to write."""
        ...

    def compute_growth_rate(self, sps: Dict[str, torch.Tensor]) -> float:
        """Compute σ_i for Lotka-Volterra competition."""
        ...

    def get_natural_frequency(self) -> float:
        """Return ω_k for Kuramoto coupling."""
        ...
