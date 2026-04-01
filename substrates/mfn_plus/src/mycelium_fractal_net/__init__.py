"""MyceliumFractalNet — Morphogenetic Field Intelligence Engine.

The only open-source framework that unifies reaction-diffusion simulation,
persistent homology, causal validation, and self-healing in one package.

Quick start:
    >>> import mycelium_fractal_net as mfn
    >>> seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
    >>> print(mfn.observe(seq))       # every lens in one call
    >>> print(mfn.diagnose(seq))      # anomaly + EWS + causal gate
    >>> print(mfn.explain(seq))       # natural language
    >>> result = mfn.auto_heal(seq)   # self-repair

API tiers:
    Tier 1 — Pipeline:     simulate, extract, detect, diagnose, forecast, compare
    Tier 2 — Intelligence: observe, explain, auto_heal, invariance_report
    Tier 3 — Analytics:    InvariantOperator, ThermodynamicKernel, FractalPreservingInterpolator
    Tier 4 — Types:        SimulationSpec, FieldSequence, AnomalyEvent, DiagnosisReport
    Tier 5 — Bio (lazy):   BioExtension, LevinPipeline (loaded on first access)
"""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("mycelium-fractal-net")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .adapters import FieldAdapter
from .analytics import (
    FeatureVector,
    FractalInsightArchitect,
    Insight,
    InsufficientDataError,
    compute_basic_stats,
    compute_box_counting_dimension,
    compute_fractal_features,
)
from .analytics.invariant_operator import InvariantOperator
from .analytics.morphology import compute_morphology_descriptor
from .auto_heal import ExperienceMemory, HealResult, auto_heal, get_experience_memory

# Bio is lazy-loaded via _LAZY_ATTRS (see below)
from .cognitive import (
    benchmark_quick,
    compare_many,
    explain,
    gamma_diagnostic,
    history,
    invariance_report,
    plot_field,
    sweep,
    to_markdown,
)
from .config import (
    DatasetConfig,
    FeatureConfig,
    make_dataset_config_default,
    make_dataset_config_demo,
    make_feature_config_default,
    make_feature_config_demo,
    make_simulation_config_default,
    make_simulation_config_demo,
    validate_dataset_config,
    validate_feature_config,
    validate_simulation_config,
)
from .core import (
    FractalConfig,
    FractalGrowthEngine,
    FractalMetrics,
    MembraneConfig,
    MembraneEngine,
    MembraneMetrics,
    MyceliumField,
    NumericalInstabilityError,
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    ReactionDiffusionMetrics,
    SimulationConfig,
    SimulationResult,
    StabilityError,
    ValueOutOfRangeError,
    compute_lyapunov_exponent,
    compute_nernst_potential,
    compute_stability_metrics,
    is_stable,
    run_mycelium_simulation,
    run_mycelium_simulation_with_history,
)
from .core.detect import detect_anomaly
from .core.diagnose import diagnose, diagnose_streaming
from .core.early_warning import early_warning
from .core.ensemble import ensemble_diagnose
from .core.extract import extract as extract_operation
from .core.forecast import forecast_next
from .core.homeostasis import HomeostasisLoop, HomeostasisReport
from .core.inverse import inverse_synthesis
from .core.observatory import ObservatoryReport, observe
from .core.report import report as report_operation
from .core.scale_engine import FractalInterpolatorConfig, FractalPreservingInterpolator
from .core.simulate import (
    simulate_batch,
    simulate_final,
    simulate_history,
    simulate_null,
    simulate_scenario,
)
from .core.sovereign_gate import SovereignGate, SovereignVerdict
from .core.thermodynamic_kernel import ThermodynamicKernel, ThermodynamicKernelConfig
from .core.watch import watch
from .pipelines import (
    build_analysis_report,
    get_preset_config,
    list_presets,
    run_forecast_pipeline,
    run_scenario,
)
from .types.detection import (
    AnomalyEvent,
    RegimeState,
)
from .types.diagnosis import DiagnosisDiff, DiagnosisReport
from .types.ensemble import EnsembleDiagnosisReport
from .types.ews import CriticalTransitionWarning
from .types.features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    MorphologyDescriptor,
)
from .types.field import (
    BoundaryCondition,
    FieldHistory,
    FieldSequence,
    FieldState,
    GABAATonicSpec,
    GridShape,
    NeuromodulationSpec,
    NeuromodulationStateSnapshot,
    ObservationNoiseSpec,
    SerotonergicPlasticitySpec,
    SimulationSpec,
)
from .types.forecast import ComparisonResult, ForecastResult
from .types.inverse import InverseSynthesisResult
from .types.report import AnalysisReport
from .types.scale import FractalScaleJourney, FractalScaleReport
from .types.thermodynamics import ThermodynamicStabilityReport

# Bio extension — lazy import (scipy + sklearn are heavy)
# Access via mfn.BioExtension, mfn.BioConfig, mfn.BioReport


def full_analyze(
    seq: FieldSequence,
    target_field: Any = None,
    verbose: bool = False,
) -> object:
    """Full system analysis in one call.

    Integrates core diagnosis + bio + Levin + fractal arsenal + fractal dynamics.

    >>> report = mfn.full_analyze(seq)
    >>> print(report.summary())
    >>> print(report.interpretation())
    """
    from .core.unified_engine import UnifiedEngine

    return UnifiedEngine(verbose=verbose).analyze(seq, target_field=target_field)


def status() -> str:
    """Quick system health check. Shows version, capabilities, and readiness.

    >>> print(mfn.status())
    """
    from .core.release_contract import CONTRACT

    lines = [
        f"MyceliumFractalNet v{__version__}",
        f"  Exports:      {len(__all__)} public API symbols",
        f"  Causal rules:  {CONTRACT.causal_rules}",
        f"  Feature dims:  {CONTRACT.feature_dim}",
        f"  Bio mechanisms: {CONTRACT.bio_mechanisms}",
        f"  Invariants:    {CONTRACT.invariants} proven",
        f"  Python:        {CONTRACT.python_min}–{CONTRACT.python_max}",
        f"  Install tiers: {', '.join(CONTRACT.install_tiers)}",
        "",
        "  Ready: simulate → observe → diagnose → auto_heal → homeostasis",
    ]
    return "\n".join(lines)


def plan_intervention(
    source: FieldSequence,
    target_regime: str = "stable",
    allowed_levers: list[str] | None = None,
    budget: float = 10.0,
    objective: str = "stabilize",
    **kwargs: object,
) -> object:
    """Plan an intervention to move toward a target regime.

    >>> plan = mfn.plan_intervention(seq, target_regime="stable", budget=5.0)
    >>> print(plan.best_candidate)
    """
    from .intervention import plan_intervention as _plan

    return _plan(
        source,
        target_regime=target_regime,
        allowed_levers=allowed_levers,
        budget=budget,
        objective=objective,
        **kwargs,
    )  # type: ignore[arg-type]


def load(
    source: Any,
    *,
    normalize: bool = True,
) -> FieldSequence:
    """Load external data into the MFN pipeline.

    Accepts numpy arrays (.npy), CSV files, or raw 2D/3D arrays.
    Automatically normalizes to biophysical range if needed.

    Parameters
    ----------
    source : np.ndarray | str | Path
        - ndarray (H, W): single field frame
        - ndarray (T, H, W): field with temporal history
        - str/Path to .npy or .csv file
    normalize : bool
        Auto-rescale to biophysical range (default True).

    Returns
    -------
    FieldSequence
        Ready for: mfn.detect(seq), mfn.diagnose(seq), mfn.auto_heal(seq)

    Examples
    --------
    >>> seq = mfn.load("microscopy_data.npy")
    >>> print(mfn.diagnose(seq).summary())
    >>> result = mfn.auto_heal(seq)
    """
    return FieldAdapter.load(source, normalize=normalize)


def simulate(
    spec: SimulationSpec,
    *,
    history_backend: str = "memory",
    history_dir: str | None = None,
) -> FieldSequence:
    """Run a morphology simulation and return the field sequence.

    Parameters
    ----------
    spec : SimulationSpec
        Simulation parameters (grid size, steps, seed, neuromodulation, etc.).
    history_backend : str
        ``'memory'`` (default) or ``'memmap'`` for disk-backed history.
    history_dir : str | None
        Directory for memmap files. Only used when ``history_backend='memmap'``.

    Returns
    -------
    FieldSequence
        Simulated field with optional temporal history.

    Examples
    --------
    >>> import mycelium_fractal_net as mfn
    >>> seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=16, seed=42))
    >>> seq.field.shape
    (32, 32)
    """
    if not isinstance(spec, SimulationSpec):
        raise TypeError(f"spec must be SimulationSpec, got {type(spec).__name__}")
    return simulate_history(spec, history_backend=history_backend, history_dir=history_dir)


def extract(sequence: FieldSequence) -> MorphologyDescriptor:
    """Extract a morphology descriptor from a field sequence.

    Computes 50+ features across 7 groups: base statistics, temporal
    dynamics, multiscale profile, stability, complexity, connectivity,
    and neuromodulation state.

    Parameters
    ----------
    sequence : FieldSequence
        Simulated field sequence.

    Returns
    -------
    MorphologyDescriptor
        Versioned descriptor with embedding and explainable feature groups.

    Examples
    --------
    >>> desc = mfn.extract(seq)
    >>> desc.stability['instability_index']
    0.012...
    """
    if not isinstance(sequence, FieldSequence):
        raise TypeError(f"sequence must be FieldSequence, got {type(sequence).__name__}")
    return extract_operation(sequence)


def detect(sequence: FieldSequence) -> AnomalyEvent:
    """Detect anomalies and classify the regime of a field sequence.

    Returns an anomaly event with score, label (nominal/watch/anomalous),
    and a nested regime state (stable/transitional/critical/reorganized/
    pathological_noise).

    Parameters
    ----------
    sequence : FieldSequence
        Simulated field sequence.

    Returns
    -------
    AnomalyEvent
        Detection result with score, label, confidence, evidence, and regime.

    Examples
    --------
    >>> event = mfn.detect(seq)
    >>> event.label
    'nominal'
    >>> event.regime.label
    'stable'
    """
    if not isinstance(sequence, FieldSequence):
        raise TypeError(f"sequence must be FieldSequence, got {type(sequence).__name__}")
    return detect_anomaly(sequence)


def forecast(sequence: FieldSequence, horizon: int = 8) -> ForecastResult:
    """Forecast future field states using adaptive descriptor extrapolation.

    Projects the field forward by ``horizon`` steps using damped linear
    extrapolation with uncertainty quantification.

    Parameters
    ----------
    sequence : FieldSequence
        Simulated field sequence with history.
    horizon : int
        Number of future steps to predict. Default 8.

    Returns
    -------
    ForecastResult
        Predicted states, descriptor trajectory, and uncertainty envelope.

    Examples
    --------
    >>> result = mfn.forecast(seq, horizon=4)
    >>> result.to_dict()['horizon']
    4
    """
    if not isinstance(sequence, FieldSequence):
        raise TypeError(f"sequence must be FieldSequence, got {type(sequence).__name__}")
    return forecast_next(sequence, horizon=horizon)


def compare(
    a: FieldSequence | MorphologyDescriptor,
    b: FieldSequence | MorphologyDescriptor,
) -> ComparisonResult:
    """Compare two field sequences or morphology descriptors.

    Computes embedding distance, cosine similarity, topology drift,
    and structural similarity label.

    Parameters
    ----------
    a : FieldSequence | MorphologyDescriptor
        Reference sequence or descriptor.
    b : FieldSequence | MorphologyDescriptor
        Candidate sequence or descriptor.

    Returns
    -------
    ComparisonResult
        Distance, similarity label, drift summary, and topology analysis.

    Examples
    --------
    >>> result = mfn.compare(seq_a, seq_b)
    >>> result.label
    'near-identical'
    """
    from .core.compare import compare as _compare

    return _compare(a, b)


def report(sequence: FieldSequence, output_root: str, horizon: int = 8) -> AnalysisReport:
    """Generate a full analysis report with artifacts.

    Orchestrates extraction, detection, forecasting, comparison, and
    artifact generation into a single reproducible run directory.

    Parameters
    ----------
    sequence : FieldSequence
        Simulated field sequence with history.
    output_root : str
        Root directory for output artifacts.
    horizon : int
        Forecast horizon. Default 8.

    Returns
    -------
    AnalysisReport
        Complete report with all analysis results and artifact paths.

    Examples
    --------
    >>> report = mfn.report(seq, output_root='/tmp/mfn_report')
    >>> report.detection.label
    'nominal'
    """
    if not isinstance(sequence, FieldSequence):
        raise TypeError(f"sequence must be FieldSequence, got {type(sequence).__name__}")
    return report_operation(sequence, output_root=output_root, horizon=horizon)


_LAZY_MODULES = {
    name: f"{__name__}.{name}"
    for name in [
        "analytics",
        "core",
        "experiments",
        "integration",
        "numerics",
        "pipelines",
        "security",
        "signal",
        "types",
        "interpretability",
        "self_reading",
        "tau_control",
    ]
}

_LAZY_ATTRS = {
    "HierarchicalKrumAggregator": (
        "mycelium_fractal_net.core.federated",
        "HierarchicalKrumAggregator",
    ),
    "aggregate_gradients_krum": (
        "mycelium_fractal_net.core.federated",
        "aggregate_gradients_krum",
    ),
    "STDPPlasticity": ("mycelium_fractal_net.core.stdp", "STDPPlasticity"),
    "estimate_fractal_dimension": (
        "mycelium_fractal_net.core.fractal",
        "estimate_fractal_dimension",
    ),
    "generate_fractal_ifs": (
        "mycelium_fractal_net.core.fractal",
        "generate_fractal_ifs",
    ),
    "simulate_mycelium_field": (
        "mycelium_fractal_net.core.turing",
        "simulate_mycelium_field",
    ),
    # Pure constants — sourced from CPU-only modules (no torch dependency)
    "BODY_TEMPERATURE_K": (
        "mycelium_fractal_net.core.membrane_engine",
        "BODY_TEMPERATURE_K",
    ),
    "FARADAY_CONSTANT": (
        "mycelium_fractal_net.core.membrane_engine",
        "FARADAY_CONSTANT",
    ),
    "ION_CLAMP_MIN": ("mycelium_fractal_net.core.membrane_engine", "ION_CLAMP_MIN"),
    "R_GAS_CONSTANT": ("mycelium_fractal_net.core.membrane_engine", "R_GAS_CONSTANT"),
    "TURING_THRESHOLD": ("mycelium_fractal_net.core.turing", "TURING_THRESHOLD"),
    "QUANTUM_JITTER_VAR": ("mycelium_fractal_net.core.turing", "QUANTUM_JITTER_VAR"),
    "NERNST_RTFZ_MV": ("mycelium_fractal_net.core.nernst", "NERNST_RTFZ_MV"),
    # ML-dependent surfaces — torch required at access time
    "MyceliumFractalNet": ("mycelium_fractal_net.model", "MyceliumFractalNet"),
    "SPARSE_TOPK": ("mycelium_fractal_net.model", "SPARSE_TOPK"),
    "STDP_A_MINUS": ("mycelium_fractal_net.model", "STDP_A_MINUS"),
    "STDP_A_PLUS": ("mycelium_fractal_net.model", "STDP_A_PLUS"),
    "STDP_TAU_MINUS": ("mycelium_fractal_net.model", "STDP_TAU_MINUS"),
    "STDP_TAU_PLUS": ("mycelium_fractal_net.model", "STDP_TAU_PLUS"),
    "SparseAttention": ("mycelium_fractal_net.model", "SparseAttention"),
    "ValidationConfig": ("mycelium_fractal_net.model", "ValidationConfig"),
    "run_validation": ("mycelium_fractal_net.model", "run_validation"),
    "run_validation_cli": ("mycelium_fractal_net.model", "run_validation_cli"),
    # Bio (heavy: scipy + sklearn)
    "BioExtension": ("mycelium_fractal_net.bio", "BioExtension"),
    "BioConfig": ("mycelium_fractal_net.bio", "BioConfig"),
    "BioReport": ("mycelium_fractal_net.bio", "BioReport"),
    # Meta-Core — Reality pipeline (lazy: imports GNC+)
    # Note: HealResult is eagerly imported (line 45), no lazy entry needed
    "compute_reality": ("mycelium_fractal_net.meta_core", "compute_reality"),
    "resolve_reality": ("mycelium_fractal_net.meta_core", "resolve_reality"),
    "AgentState": ("mycelium_fractal_net.meta_core", "AgentState"),
    "RealityFrame": ("mycelium_fractal_net.meta_core", "RealityFrame"),
    # Choice Operator A_C (lazy: imports thermodynamic kernel)
    "choice_operator": ("mycelium_fractal_net.core.choice_operator", "choice_operator"),
    "ChoiceResult": ("mycelium_fractal_net.core.choice_operator", "ChoiceResult"),
    # Axiomatic Choice (lazy: imports GNC+)
    "AxiomaticChoiceOperator": (
        "mycelium_fractal_net.neurochem.axiomatic_choice",
        "AxiomaticChoiceOperator",
    ),
    "SelectionStrategy": (
        "mycelium_fractal_net.neurochem.axiomatic_choice",
        "SelectionStrategy",
    ),
    # ── Interpretability (lazy: read-only auditor) ───────────────
    "AttributionGraph": ("mycelium_fractal_net.interpretability", "AttributionGraph"),
    "AttributionGraphBuilder": ("mycelium_fractal_net.interpretability", "AttributionGraphBuilder"),
    "CausalTracer": ("mycelium_fractal_net.interpretability", "CausalTracer"),
    "GammaDiagnosticReport": ("mycelium_fractal_net.interpretability", "GammaDiagnosticReport"),
    "GammaDiagnostics": ("mycelium_fractal_net.interpretability", "GammaDiagnostics"),
    "LinearStateProbe": ("mycelium_fractal_net.interpretability", "LinearStateProbe"),
    "MFNFeatureExtractor": ("mycelium_fractal_net.interpretability", "MFNFeatureExtractor"),
    "MFNInterpretabilityReport": ("mycelium_fractal_net.interpretability", "MFNInterpretabilityReport"),
    # ── Self-Reading (lazy: 5-layer introspection) ───────────────
    "CoherenceMonitor": ("mycelium_fractal_net.self_reading", "CoherenceMonitor"),
    "CoherenceReport": ("mycelium_fractal_net.self_reading", "CoherenceReport"),
    "MFNPhase": ("mycelium_fractal_net.self_reading", "MFNPhase"),
    "PhaseValidator": ("mycelium_fractal_net.self_reading", "PhaseValidator"),
    "RecoveryProtocol": ("mycelium_fractal_net.self_reading", "RecoveryProtocol"),
    "SelfModel": ("mycelium_fractal_net.self_reading", "SelfModel"),
    "SelfReadingConfig": ("mycelium_fractal_net.self_reading", "SelfReadingConfig"),
    "SelfReadingLoop": ("mycelium_fractal_net.self_reading", "SelfReadingLoop"),
    "SelfReadingReport": ("mycelium_fractal_net.self_reading", "SelfReadingReport"),
    # ── NFI (lazy: neuromodulatory field intelligence) ────────────
    "NFIAdaptiveLoop": ("mycelium_fractal_net.nfi", "NFIAdaptiveLoop"),
    "NFIClosureLoop": ("mycelium_fractal_net.nfi", "NFIClosureLoop"),
    "NFIStateContract": ("mycelium_fractal_net.nfi", "NFIStateContract"),
    "GammaEmergenceProbe": ("mycelium_fractal_net.nfi", "GammaEmergenceProbe"),
    "EmergentValidationSuite": ("mycelium_fractal_net.nfi", "EmergentValidationSuite"),
    "AdaptiveRunResult": ("mycelium_fractal_net.nfi", "AdaptiveRunResult"),
    "ThetaMapping": ("mycelium_fractal_net.nfi", "ThetaMapping"),
    # ── tau-Control (lazy: identity preservation engine) ─────────
    "IdentityEngine": ("mycelium_fractal_net.tau_control", "IdentityEngine"),
    "IdentityReport": ("mycelium_fractal_net.tau_control", "IdentityReport"),
    "LyapunovMonitor": ("mycelium_fractal_net.tau_control", "LyapunovMonitor"),
    "NormSpace": ("mycelium_fractal_net.tau_control", "NormSpace"),
    "TauController": ("mycelium_fractal_net.tau_control", "TauController"),
    "CertifiedEllipsoid": ("mycelium_fractal_net.tau_control", "CertifiedEllipsoid"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MODULES:
        module = import_module(_LAZY_MODULES[name])
        globals()[name] = module
        return module
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(name)


V1_SURFACE = (
    "simulate",
    "extract",
    "detect",
    "forecast",
    "compare",
    "report",
    "plan_intervention",
    "diagnose",
    "diagnose_streaming",
    "full_analyze",
    "early_warning",
    "watch",
    "SimulationSpec",
    "NeuromodulationSpec",
    "GABAATonicSpec",
    "SerotonergicPlasticitySpec",
    "ObservationNoiseSpec",
    "FieldSequence",
    "MorphologyDescriptor",
    "AnomalyEvent",
    "RegimeState",
    "ForecastResult",
    "ComparisonResult",
    "AnalysisReport",
    "__version__",
)

# Frozen surfaces: maintained for backward compatibility but not actively
# developed. Import triggers a DeprecationWarning. Will be removed in v5.0.
# Use canonical alternatives:
#   crypto → artifact_bundle (Ed25519 signing via importlib)
#   core.federated → external federated learning framework
#   integration.ws_* → standard WebSocket libraries
FROZEN_SURFACES = (
    "crypto",
    "core.federated",
    "k8s.yaml",
    "integration.ws_*",
    "load_tests",
    "notebooks",
    "planning",
)
DEPRECATED_SURFACES = {
    "crypto": "Use artifact_bundle for signing. crypto/ will be removed in v5.0.",
    "core.federated": "Federated learning is frozen. Use external frameworks.",
}


# ═══════════════════════════════════════════════════════════════
# PUBLIC API — organized by tier
# ═══════════════════════════════════════════════════════════════

__all__ = [
    "AgentState",
    "AnalysisReport",
    "AnomalyEvent",
    # ── Tier 8: Interpretability (read-only auditor) ─────────────
    "AttributionGraph",
    "AttributionGraphBuilder",
    "AxiomaticChoiceOperator",
    "BoundaryCondition",
    "CausalTracer",
    # ── Tier 10: tau-Control (identity preservation) ─────────────
    "CertifiedEllipsoid",
    # ── Tier 11: NFI (neuromodulatory field intelligence) ────────
    "AdaptiveRunResult",
    "EmergentValidationSuite",
    "GammaEmergenceProbe",
    "NFIAdaptiveLoop",
    "NFIClosureLoop",
    "NFIStateContract",
    "ThetaMapping",
    "ChoiceResult",
    # ── Tier 9: Self-Reading (5-layer introspection) ─────────────
    "CoherenceMonitor",
    "CoherenceReport",
    "ComparisonResult",
    "DiagnosisReport",
    "FieldSequence",
    "ForecastResult",
    "FractalInterpolatorConfig",
    "FractalPreservingInterpolator",
    "FractalScaleJourney",
    "GABAATonicSpec",
    "GammaDiagnosticReport",
    "GammaDiagnostics",
    "HealResult",
    "IdentityEngine",
    "IdentityReport",
    # ── Tier 4: Engines & operators ───────────────────────────
    "InvariantOperator",
    "LinearStateProbe",
    "LyapunovMonitor",
    "MFNFeatureExtractor",
    "MFNInterpretabilityReport",
    "MFNPhase",
    "MorphologyDescriptor",
    # ── Tier 6: Spec types (simulation config) ────────────────
    "NeuromodulationSpec",
    "NormSpace",
    "ObservationNoiseSpec",
    "ObservatoryReport",
    "PhaseValidator",
    "RealityFrame",
    "RecoveryProtocol",
    "SelectionStrategy",
    "SelfModel",
    "SelfReadingConfig",
    "SelfReadingLoop",
    "SelfReadingReport",
    "SerotonergicPlasticitySpec",
    # ── Tier 5: Core types ────────────────────────────────────
    "SimulationSpec",
    "SovereignGate",
    "SovereignVerdict",
    "TauController",
    "ThermodynamicKernel",
    "ThermodynamicKernelConfig",
    "ThermodynamicStabilityReport",
    # ── Version ───────────────────────────────────────────────
    "__version__",
    "auto_heal",
    "benchmark_quick",
    "choice_operator",
    "compare",
    "compare_many",
    # ── Tier 3: Cognitive extensions ──────────────────────────
    "compute_reality",
    "detect",
    "diagnose",
    "early_warning",
    "explain",
    "extract",
    "forecast",
    "full_analyze",
    "gamma_diagnostic",
    "history",
    "invariance_report",
    "load",
    # ── Tier 2: Intelligence ──────────────────────────────────
    "observe",
    "plan_intervention",
    "plot_field",
    "report",
    "resolve_reality",
    # ── Tier 1: Pipeline (the 7 verbs) ────────────────────────
    "simulate",
    "simulate_null",
    "status",
    "sweep",
    "to_markdown",
]
