"""
Functional contracts for biomimetic modules.

These contracts are lightweight, testable descriptions that capture the
computational role, inputs/outputs, safety constraints, and fallback modes for
each neuro-inspired component. They are used by the Neuro-AI adapters and the
documentation in docs/neuro_ai/CONTRACTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass(frozen=True)
class ContractSpec:
    """Declarative contract for a biomimetic module."""

    name: str
    role: str
    inputs: Sequence[str]
    outputs: Sequence[str]
    constraints: Sequence[str]
    failure_modes: Sequence[str]
    hybrid_improvements: Sequence[str]
    references: Sequence[str]


# Canonical contracts used by docs and tests
NEURO_CONTRACTS: Mapping[str, ContractSpec] = {
    "MultiLevelSynapticMemory": ContractSpec(
        name="MultiLevelSynapticMemory",
        role="Multi-timescale synaptic buffer and consolidation gate",
        inputs=[
            "event: np.ndarray",
            "lambda_l1/l2/l3 decay rates",
            "theta_l1/theta_l2 consolidation thresholds",
        ],
        outputs=["updated L1/L2/L3 traces", "consolidation flags"],
        constraints=[
            "Decay rates in (0,1], thresholds > 0",
            "No NaNs/inf in traces",
            "Memory usage must stay bounded by dimension",
        ],
        failure_modes=[
            "Fallback to zeroed traces on invalid input shape",
            "No consolidation when thresholds are not met",
        ],
        hybrid_improvements=[
            "Observability hook for latency and consolidation",
            "Bounded decay and gating to prevent runaway growth",
        ],
        references=[
            "src/mlsdm/memory/multi_level_memory.py",
            "docs/NEURO_FOUNDATIONS.md#multi-timescale-synaptic-memory",
        ],
    ),
    "PhaseEntangledLatticeMemory": ContractSpec(
        name="PhaseEntangledLatticeMemory",
        role="Phase-coded associative memory for bidirectional retrieval",
        inputs=[
            "keys/values embeddings",
            "phase weights for associative retrieval",
        ],
        outputs=["top-k associative results", "phase coherence score"],
        constraints=[
            "Capacity bound respected via eviction policy",
            "Similarity thresholds avoid degenerate matches",
        ],
        failure_modes=[
            "Returns empty result when similarity below threshold",
            "Keeps prior state unchanged on invalid phase input",
        ],
        hybrid_improvements=[
            "Deterministic eviction ordering for testability",
            "Bounded similarity thresholds to avoid oscillations",
        ],
        references=[
            "src/mlsdm/memory/phase_entangled_lattice_memory.py",
            "docs/NEURO_FOUNDATIONS.md#phase-entangled-lattice-memory-pelm",
        ],
    ),
    "CognitiveRhythm": ContractSpec(
        name="CognitiveRhythm",
        role="Wake/sleep phase pacing with regime-aware time constants",
        inputs=["wake_duration", "sleep_duration", "step() ticks", "optional risk signal"],
        outputs=["current phase label", "phase counter"],
        constraints=[
            "Durations must be positive",
            "Phase transitions bounded by hysteresis/cooldown",
        ],
        failure_modes=[
            "Stays in last stable phase if invalid duration provided",
            "Counter resets to duration on transition",
        ],
        hybrid_improvements=[
            "Boolean fast-path for hot checks (is_wake/is_sleep)",
            "Optional regime modulation for faster defensive adaptation",
        ],
        references=[
            "src/mlsdm/rhythm/cognitive_rhythm.py",
            "docs/NEURO_FOUNDATIONS.md#circadian-rhythms-and-sleep",
        ],
    ),
    "SynergyExperienceMemory": ContractSpec(
        name="SynergyExperienceMemory",
        role="Prediction-error-driven combo selection with ε-greedy balance",
        inputs=[
            "state_signature",
            "combo_id",
            "delta_eoi (observed-predicted objective index)",
            "epsilon exploration rate",
        ],
        outputs=["ComboStats (ema_delta_eoi, attempts, mean_delta_eoi)", "selected combo id"],
        constraints=[
            "epsilon in [0,1]",
            "delta_eoi sanitized to avoid NaN/inf",
            "bounded EMA smoothing factor",
        ],
        failure_modes=[
            "Defaults to neutral stats when insufficient trials",
            "Falls back to exploration when no stats exist",
        ],
        hybrid_improvements=[
            "Thread-safe updates via locks",
            "EMA smoothing for stability under noisy deltas",
        ],
        references=[
            "src/mlsdm/cognition/synergy_experience.py",
            "tests/unit/test_synergy_experience.py",
        ],
    ),
}


@dataclass(frozen=True)
class FunctionalCoverageRecord:
    """Functional coverage link between biomimetic names and concrete functions."""

    module: str
    bio_system: str
    function: str
    category: Literal["biological", "engineering_abstraction"]
    function_tags: Sequence[str]
    tests: Sequence[str]
    contract: str | None = None


FUNCTIONAL_COVERAGE_MATRIX: tuple[FunctionalCoverageRecord, ...] = (
    FunctionalCoverageRecord(
        module="mlsdm.memory.multi_level_memory.MultiLevelSynapticMemory",
        bio_system="Hippocampal-cortical multi-timescale buffer",
        function="Consolidation across L1/L2/L3 with decay and gating",
        category="biological",
        function_tags=("prediction_error", "inhibition"),
        tests=(
            "tests/unit/test_multi_level_memory_calibration.py",
            "tests/observability/test_memory_observability.py",
            "tests/neuro_ai/test_neuro_ai_contract_layer.py",
        ),
        contract="MultiLevelSynapticMemory",
    ),
    FunctionalCoverageRecord(
        module="mlsdm.memory.phase_entangled_lattice_memory.PhaseEntangledLatticeMemory",
        bio_system="Phase-coded associative lattice (PELM)",
        function="Phase-weighted retrieval with bounded similarity and capacity",
        category="biological",
        function_tags=("action_selection",),
        tests=("tests/unit/test_pelm.py", "tests/unit/test_pelm_batch.py"),
        contract="PhaseEntangledLatticeMemory",
    ),
    FunctionalCoverageRecord(
        module="mlsdm.rhythm.cognitive_rhythm.CognitiveRhythm",
        bio_system="Wake/sleep pacing with hysteresis",
        function="Phase pacing and inhibition timing",
        category="biological",
        function_tags=("regime_switching", "inhibition"),
        tests=(
            "tests/unit/test_cognitive_rhythm.py",
            "tests/validation/test_wake_sleep_effectiveness.py",
        ),
        contract="CognitiveRhythm",
    ),
    FunctionalCoverageRecord(
        module="mlsdm.cognition.synergy_experience.SynergyExperienceMemory",
        bio_system="Basal-ganglia-inspired action selection",
        function="Prediction-error-driven combo selection with ε-greedy",
        category="biological",
        function_tags=("action_selection", "prediction_error"),
        tests=("tests/unit/test_synergy_experience.py",),
        contract="SynergyExperienceMemory",
    ),
    FunctionalCoverageRecord(
        module="mlsdm.neuro_ai.adapters.SynapticMemoryAdapter",
        bio_system="Threat-driven inhibition wrapper",
        function="Regime-aware scaling of synaptic updates",
        category="engineering_abstraction",
        function_tags=("inhibition", "regime_switching"),
        tests=("tests/neuro_ai/test_neuro_ai_contract_layer.py",),
        contract=None,
    ),
    FunctionalCoverageRecord(
        module="mlsdm.core.iteration_loop.IterationLoop",
        bio_system="Prediction-error control loop",
        function="Stability-envelope-governed regime switching and updates",
        category="engineering_abstraction",
        function_tags=("prediction_error", "regime_switching", "inhibition"),
        tests=("tests/unit/test_iteration_loop.py",),
        contract=None,
    ),
)

__all__ = [
    "ContractSpec",
    "FunctionalCoverageRecord",
    "FUNCTIONAL_COVERAGE_MATRIX",
    "NEURO_CONTRACTS",
]
