"""
Core Module for Hippocampal CA1

Implements core neural network components:
- CA1 network scaffold
- Two-compartment neuron model
- Laminar structure inference
- Hierarchical laminar model with MRF
- Theta-SWR state switching
- Core contracts and invariants
- Metrics for memory subsystem
- Configuration management
"""

from .ca1_network import CA1Network, SimulationResult
from .config import (
    ConfigValidationError,
    CoreConfig,
    ExperimentConfig,
    create_deterministic_config,
    get_default_config,
    load_config,
    merge_configs,
    save_config,
    validate_config,
)
from .contracts import (
    EncodeInput,
    MemoryState,
    Phase,
    RecallQuery,
    RecallResult,
    SimulationConfig,
    UpdateInput,
)
from .hierarchical_laminar import (
    CellDataHier,
    HierarchicalLaminarModel,
    build_knn_neighbors,
)
from .invariants import (
    InvariantViolation,
    check_bounded,
    check_finite,
    check_non_negative,
    check_shape_1d,
    check_shape_2d,
    check_spectral_radius,
    compute_spectral_radius,
    guards_enabled,
    set_guards_enabled,
    validate_memory_state,
)
from .laminar_structure import (
    CellData,
    SubregionClassifier,
    ZINBLayerModel,
    compute_coexpression_rate,
)
from .laminar_structure import validate_laminar_structure as validate_zinb_structure
from .metrics import (
    REPORT_KEYS,
    compute_report,
    drift_metric,
    memory_capacity_proxy,
    recall_accuracy_proxy,
    stability_metric,
    validate_report,
)
from .neuron_model import (
    CA1Population,
    NetworkMode,
    NeuronState,
    TwoCompartmentNeuron,
    extract_theta_phase,
)
from .theta_swr_switching import (
    NetworkState,
    NetworkStateController,
    ReplayDetector,
    ReplayEvent,
    StateTransitionParams,
    compute_replay_metrics,
    validate_replay_vs_template,
)

__all__ = [
    # CA1 Network
    "CA1Network",
    "SimulationResult",
    # Configuration
    "ConfigValidationError",
    "CoreConfig",
    "ExperimentConfig",
    "create_deterministic_config",
    "get_default_config",
    "load_config",
    "merge_configs",
    "save_config",
    "validate_config",
    # Contracts
    "EncodeInput",
    "MemoryState",
    "Phase",
    "RecallQuery",
    "RecallResult",
    "SimulationConfig",
    "UpdateInput",
    # Invariants
    "InvariantViolation",
    "check_bounded",
    "check_finite",
    "check_non_negative",
    "check_shape_1d",
    "check_shape_2d",
    "check_spectral_radius",
    "compute_spectral_radius",
    "guards_enabled",
    "set_guards_enabled",
    "validate_memory_state",
    # Metrics
    "REPORT_KEYS",
    "compute_report",
    "drift_metric",
    "memory_capacity_proxy",
    "recall_accuracy_proxy",
    "stability_metric",
    "validate_report",
    # Hierarchical Laminar
    "CellDataHier",
    "HierarchicalLaminarModel",
    "build_knn_neighbors",
    # Laminar Structure
    "CellData",
    "SubregionClassifier",
    "ZINBLayerModel",
    "compute_coexpression_rate",
    "validate_zinb_structure",
    # Neuron Model
    "CA1Population",
    "NetworkMode",
    "NeuronState",
    "TwoCompartmentNeuron",
    "extract_theta_phase",
    # Theta-SWR
    "NetworkState",
    "NetworkStateController",
    "ReplayDetector",
    "ReplayEvent",
    "StateTransitionParams",
    "compute_replay_metrics",
    "validate_replay_vs_template",
]
