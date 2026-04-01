# Architecture Specification

**Document Version:** 1.2.0
**Project Version:** 1.2.0
**Last Updated:** December 2025
**Status:** Beta

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Component Interactions](#component-interactions)
- [Data Flow](#data-flow)
- [Memory Architecture](#memory-architecture)
- [API Architecture](#api-architecture)
- [Performance Characteristics](#performance-characteristics)
- [Design Principles](#design-principles)

---

## Overview

MLSDM (Multi-Level Synaptic Dynamic Memory) Governed Cognitive Memory is a neurobiologically-grounded cognitive architecture that provides universal LLM wrapping with moral governance, phase-based memory, cognitive rhythm enforcement, and language pathology detection via the Aphasia-Broca model [@benna2016_synaptic; @fusi2005_cascade; @gabriel2020_alignment].

### Architecture Goals

1. **Biological Fidelity**: Ground cognitive processes in neurobiological principles
2. **Moral Governance**: Enforce adaptive moral thresholds without external training
3. **Bounded Resources**: Maintain strict memory and computational bounds
4. **Thread Safety**: Support concurrent access with zero data races
5. **Phase-Based Processing**: Implement wake/sleep cycles with distinct behaviors

### System Properties

- **Memory Bound**: Fixed 29.37 MB footprint with hard capacity limits
- **Thread-Safe**: Lock-free concurrent access for high-throughput workloads
- **Adaptive**: Dynamic moral threshold adjustment based on observed patterns [@gabriel2020_alignment]
- **Phase-Aware**: Different retrieval strategies for wake vs. sleep phases
- **Observable**: Comprehensive metrics and state introspection

---

## System Architecture

### Full System Architecture

MLSDM is a multi-layered system spanning from low-level cognitive primitives to HTTP services, client SDKs, and operational infrastructure [@davies2018_loihi; @touvron2023_llama]; readiness is tracked in [status/READINESS.md](status/READINESS.md) and all layers are currently implemented and operational.

```
┌───────────────────────────────────────────────────────────────────┐
│                    Client & Integration Layer                      │
│  • SDK Client (src/mlsdm/sdk/neuro_engine_client.py)             │
│  • Direct Python Integration (LLMWrapper, NeuroLangWrapper)       │
│  • LLM Provider Adapters (OpenAI, Local Stub via Factory)         │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│                      Service & API Layer                           │
│  • FastAPI Application (src/mlsdm/api/app.py)                     │
│  • Health Endpoints (health, lifecycle)                           │
│  • Neuro Engine Service (src/mlsdm/service/)                      │
│  • API Middleware (rate limiting, security, observability)        │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│                   Engine & Routing Layer                           │
│  • NeuroCognitiveEngine (src/mlsdm/engine/neuro_cognitive_engine.py) │
│  • LLM Router (src/mlsdm/router/llm_router.py)                    │
│  • Engine Factory (src/mlsdm/engine/factory.py)                   │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│              Application/Wrapper Layer (Cognitive Interface)       │
│  • LLMWrapper (src/mlsdm/core/llm_wrapper.py) - base wrapper     │
│  • NeuroLangWrapper (src/mlsdm/extensions/neuro_lang_extension.py) │
│  • Speech Governance (src/mlsdm/speech/governance.py)             │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────┐
│              Orchestration Layer (Cognitive Controller)            │
│  • CognitiveController (src/mlsdm/core/cognitive_controller.py)  │
│    - Thread-safe coordination of all cognitive subsystems         │
│    - State management and metrics aggregation                     │
│  • Memory Manager (src/mlsdm/core/memory_manager.py)             │
└───┬─────────┬──────────┬──────────┬──────────┬────────────────────┘
    │         │          │          │          │
┌───▼────┐ ┌─▼─────┐ ┌──▼─────┐ ┌──▼──────┐ ┌▼────────┐
│ Moral  │ │Rhythm │ │ Memory │ │Ontology │ │ Speech  │
│Filter  │ │Manager│ │ System │ │ Matcher │ │Governor │
│  V2    │ │       │ │        │ │         │ │         │
└────────┘ └───────┘ └────┬───┘ └─────────┘ └─────────┘
                          │
           ┌──────────────┴──────────────┐
           │                             │
    ┌──────▼────────┐           ┌────────▼──────────┐
    │ Phase-Entangled│           │  Multi-Level      │
    │ Lattice Memory │           │  Synaptic Memory  │
    │ (PELM)         │           │  (L1/L2/L3)       │
    └────────────────┘           └───────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│            Cross-Cutting Infrastructure Layers                     │
│                                                                    │
│  Observability (src/mlsdm/observability/):                        │
│    • Metrics export (Prometheus)                                  │
│    • Structured logging                                           │
│    • Aphasia-specific logging                                     │
│                                                                    │
│  Risk Control (src/mlsdm/risk/):                                   │
│    • Threat-model gating and risk fusion                           │
│    • Mode switching and degradations                               │
│    • Emergency fallback directives                                 │
│                                                                    │
│  Security (src/mlsdm/security/):                                  │
│    • Rate limiting                                                │
│    • Payload scrubbing                                            │
│    • Input validation (src/mlsdm/utils/input_validator.py)       │
│    • Security logging                                             │
│                                                                    │
│  Configuration & Utilities (src/mlsdm/utils/):                    │
│    • Config loader & validator                                    │
│    • Config schema enforcement                                    │
│    • Data serialization                                           │
│    • Coherence/safety metrics                                     │
│                                                                    │
│  Deployment (src/mlsdm/deploy/, config/, docker/):               │
│    • Canary manager                                               │
│    • Docker images                                                │
│    • Production configs                                           │
└───────────────────────────────────────────────────────────────────┘
```

### Architecture Governance Manifest

- **Source of truth:** `src/mlsdm/config/architecture_manifest.py`
- **Enforcement:** `tests/contracts/test_architecture_manifest.py` validates paths, public interfaces, and dependency declarations.

| Module | Layer | Responsibility Focus | Allowed Dependencies |
| --- | --- | --- | --- |
| api | interface | FastAPI surface, lifecycle, middleware | engine, core, router, security, observability, utils |
| sdk | interface | Client SDK for embedding MLSDM | engine, utils |
| engine | engine | Compose cognitive subsystems and factories | core, memory, router, security, observability, utils |
| core | cognitive-core | Cognitive controller and pipeline | memory, security, observability, utils |
| memory | memory | Multi-level memory and phase lattice | utils, observability |
| router | service | Provider routing and failover | adapters, security, observability, utils |
| adapters | integration | Provider-specific adapters | security, utils |
| security | cross-cutting | Policy engine, guardrails, scrubbing | utils, observability |
| risk | cross-cutting | Threat gating, mode switching, fallback control | security, cognition, observability, config, contracts, utils |
| observability | cross-cutting | Metrics, logging, tracing | utils |
| utils | foundation | Config, primitives, shared helpers | — |

### Component Hierarchy

1. **Client & Integration Layer**
   - **SDK Client** (`src/mlsdm/sdk/neuro_engine_client.py`): HTTP client for remote engine access
   - **LLM Adapters** (`src/mlsdm/adapters/`): Pluggable LLM providers
     - `openai_adapter.py`: OpenAI integration
     - `local_stub_adapter.py`: Local testing stub
     - `provider_factory.py`: Factory pattern for adapter selection
   - **Direct Integration**: Import LLMWrapper or NeuroLangWrapper directly in Python apps

2. **Service & API Layer** (`src/mlsdm/api/`, `src/mlsdm/service/`)
   - **FastAPI Application** (`app.py`): HTTP/JSON REST API
   - **Health Endpoints** (`health.py`): Liveness, readiness, detailed health checks
   - **Lifecycle Management** (`lifecycle.py`): Startup/shutdown hooks
   - **Middleware** (`middleware.py`): Rate limiting, authentication, observability
   - **Neuro Engine Service** (`service/neuro_engine_service.py`): Service wrapper

3. **Engine & Routing Layer** (`src/mlsdm/engine/`, `src/mlsdm/router/`)
   - **NeuroCognitiveEngine** (`engine/neuro_cognitive_engine.py`): High-level cognitive API
   - **LLM Router** (`router/llm_router.py`): Multi-provider routing logic
   - **Engine Factory** (`engine/factory.py`): Engine instantiation patterns

4. **Application/Wrapper Layer** (`src/mlsdm/core/`, `src/mlsdm/extensions/`, `src/mlsdm/speech/`)
   - **LLMWrapper** (`core/llm_wrapper.py`): Universal LLM wrapper with cognitive governance
     - Accepts user-provided LLM and embedding functions
     - Enforces biological constraints (memory, rhythm, moral)
     - Manages context retrieval and injection
   - **NeuroLangWrapper** (`extensions/neuro_lang_extension.py`): Extended wrapper with language processing
     - Adds NeuroLang grammar enrichment
     - Includes Aphasia-Broca detection and repair
     - Supports configurable detection/repair modes
   - **Speech Governance** (`speech/governance.py`): Pluggable linguistic policy framework
     - Base `SpeechGovernanceResult` protocol
     - Enables custom output control policies

5. **Orchestration Layer** (`src/mlsdm/core/`)
   - **CognitiveController** (`cognitive_controller.py`): Thread-safe orchestrator
     - Coordinates moral filtering, rhythm, memory, ontology
     - Ensures atomic state transitions
     - Aggregates metrics from all subsystems
   - **Memory Manager** (`memory_manager.py`): Memory lifecycle management

6. **Cognitive Subsystems** (`src/mlsdm/cognition/`, `src/mlsdm/rhythm/`, `src/mlsdm/memory/`, `src/mlsdm/speech/`)
   - **Moral Filter V2** (`cognition/moral_filter_v2.py`): Adaptive moral threshold with EMA
   - **Cognitive Rhythm** (`rhythm/cognitive_rhythm.py`): Wake/sleep cycle state machine
   - **Memory System**: Dual-memory architecture
     - **PELM** (`memory/phase_entangled_lattice_memory.py`): Phase-aware retrieval
     - **MultiLevelMemory** (`memory/multi_level_memory.py`): L1/L2/L3 decay cascade
   - **Ontology Matcher** (`cognition/ontology_matcher.py`): Semantic classification
   - **Speech Governor**: Pluggable output control (used by Aphasia-Broca)

7. **LLM Integration** (`src/mlsdm/adapters/`, `src/mlsdm/extensions/`)
   - **Provider Adapters**: OpenAI, local stub, extensible factory
   - **NeuroLang Extension**: Bio-inspired language processing with:
     - `InnateGrammarModule`: Recursive grammar templates
     - `CriticalPeriodTrainer`: Language acquisition modeling
     - `ModularLanguageProcessor`: Production/comprehension separation
     - `SocialIntegrator`: Pragmatic intent simulation
     - `AphasiaBrocaDetector`: Telegraphic speech detection

8. **Observability Infrastructure** (`src/mlsdm/observability/`)
   - **Metrics** (`metrics.py`): Prometheus-compatible metric export
   - **Structured Logging** (`logger.py`): JSON-formatted logs with context
   - **Aphasia Logging** (`aphasia_logging.py`): Domain-specific observability
   - **Exporters** (`exporters.py`): Metric aggregation and export

9. **Security Infrastructure** (`src/mlsdm/security/`, `src/mlsdm/utils/`)
    - **Rate Limiting** (`security/rate_limit.py`): Token bucket rate limiter
    - **Payload Scrubbing** (`security/payload_scrubber.py`): PII removal
    - **Input Validation** (`utils/input_validator.py`): Schema-based validation
    - **Security Logging** (`utils/security_logger.py`): Audit trail

10. **Risk & Safety Control Contour** (`src/mlsdm/risk/`)
    - **Safety Control Contour** (`risk/safety_control.py`): CNS-inspired gating loop
      - **Threat-model gating**: fuse security flags with cognitive risk signals
      - **Mode switching**: normal → guarded → degraded → emergency
      - **Degradation controls**: token caps, rate limiting, safe-response defaults
      - **Emergency fallback**: abort or safe-return with audit tags
    - **API Contract**:
      - **Inputs**: security policy outcomes, cognition risk scores, observability anomalies
      - **Outputs**: `RiskDirective` for core/engine enforcement
    - **Integration Points**:
      - **Inbound signals**: `security.guardrails`, `cognition` filters, `observability` anomaly telemetry
      - **Outbound actions**: engine/core gating, fallback selection, and response shaping

11. **Configuration & Utilities** (`src/mlsdm/utils/`)
    - **Config Loader** (`config_loader.py`): YAML-based configuration
    - **Config Validator** (`config_validator.py`): Schema enforcement
    - **Config Schema** (`config_schema.py`): Pydantic models for validation
    - **Data Serialization** (`data_serializer.py`): Event serialization
    - **Coherence/Safety Metrics** (`coherence_safety_metrics.py`): Domain metrics

12. **Deployment Infrastructure** (`src/mlsdm/deploy/`, `config/`, `docker/`, `deploy/`)
    - **Canary Manager** (`deploy/canary_manager.py`): Gradual rollout logic
    - **Docker Images**: Production containerization (Dockerfile.neuro-engine-service)
    - **Configuration Profiles**: dev, staging, production YAML configs
    - **Deployment Manifests**: Kubernetes, docker-compose examples

13. **Testing Infrastructure** (`tests/`)
    - **Unit Tests** (`tests/unit/`): Component-level tests (90%+ coverage)
    - **Integration Tests** (`tests/integration/`): Cross-component integration scenarios
    - **End-to-End Tests** (`tests/e2e/`): Full system behavior with stub backends
    - **Property Tests** (`tests/property/`): Hypothesis-based invariant verification
      - `test_invariants_neuro_engine.py`: Safety, liveness, metamorphic properties
      - `test_invariants_memory.py`: Memory system invariants
      - `counterexamples/`: Known edge cases and failure modes
    - **Validation Tests** (`tests/validation/`): Effectiveness validation suites
      - `test_wake_sleep_effectiveness.py`: Cognitive rhythm efficiency
      - `test_moral_filter_effectiveness.py`: Moral filtering accuracy
      - `test_aphasia_detection.py`: Speech pathology detection
    - **Evaluation Tests** (`tests/eval/`): Scientific validation
      - `aphasia_eval_suite.py`: Comprehensive aphasia test battery
      - `sapolsky_validation_suite.py`: Schizophasia detection tests
      - `test_llm_ab_testing.py`: A/B testing framework
      - `test_canary_manager.py`: Deployment rollout tests
    - **Security Tests** (`tests/security/`): Security feature validation
    - **Speech Tests** (`tests/speech/`): Speech governance validation
    - **Load Tests** (`tests/load/`): Performance and scalability tests
    - **Benchmarks** (`tests/benchmarks/`): Performance baseline comparisons
    - **Observability Tests** (`tests/observability/`): Metrics and logging validation
    - **Extension Tests** (`tests/extensions/`): NeuroLang and extension validation

14. **Scripts & Tooling** (`scripts/`)
    - **Effectiveness Charts** (`generate_effectiveness_charts.py`): Visualization generation
    - **Aphasia Evaluation** (`run_aphasia_eval.py`): Aphasia detection runner
    - **Security Audit** (`security_audit.py`): Security posture assessment
    - **NeuroLang Training** (`train_neurolang_grammar.py`): Grammar model training
    - **Core Verification** (`verify_core_implementation.sh`): Implementation validation
    - **Security Features Test** (`test_security_features.py`): Security integration tests

15. **CI/CD Infrastructure** (`.github/workflows/`)
    - **Neuro Cognitive Engine CI** (`ci-neuro-cognitive-engine.yml`): Core test suite
      - Unit, integration, e2e tests
      - Performance benchmarks
      - Effectiveness validation
      - Coverage reporting
    - **Property-Based Tests** (`property-tests.yml`): Invariant verification
      - Hypothesis-based property tests
      - Counterexamples regression testing
      - Invariant coverage checks
    - **Aphasia/NeuroLang CI** (`aphasia-ci.yml`): Language processing tests
      - NeuroLang module tests
      - Aphasia detection validation
      - Speech governance tests
    - **Release Workflow** (`release.yml`): Automated releases
      - Multi-platform Docker builds
      - GitHub Container Registry publishing
      - Release notes generation
      - Optional TestPyPI publishing

---

## Core Components

### 1. LLMWrapper

**Location:** `src/mlsdm/core/llm_wrapper.py`
**Purpose:** Universal wrapper providing cognitive governance for any LLM

**Key Responsibilities:**
- Accept user-provided LLM and embedding functions
- Enforce biological constraints (memory, rhythm, moral)
- Manage context retrieval and injection
- Adapt max tokens based on cognitive phase
- Return structured results with governance metadata

**Interface:**
```python
class LLMWrapper:
    def __init__(
        llm_generate_fn: Callable[[str, int], str],
        embedding_fn: Callable[[str], np.ndarray],
        dim: int = 384,
        capacity: int = 20_000,
        wake_duration: int = 8,
        sleep_duration: int = 3,
        initial_moral_threshold: float = 0.50
    ) -> None

    def generate(
        prompt: str,
        moral_value: float,
        max_tokens: Optional[int] = None,
        context_top_k: int = 5
    ) -> dict
```

**State Management:**
- Maintains CognitiveController instance
- Tracks processing history
- Manages phase-dependent behavior

---

### 2. CognitiveController

**Location:** `src/mlsdm/core/cognitive_controller.py`
**Purpose:** Thread-safe orchestrator of all cognitive subsystems

**Key Responsibilities:**
- Coordinate moral filtering, rhythm management, and memory operations
- Ensure atomic state transitions
- Collect and aggregate metrics
- Provide state introspection

**Interface:**
```python
class CognitiveController:
    def __init__(
        dim: int,
        capacity: int = 20_000,
        wake_duration: int = 8,
        sleep_duration: int = 3,
        initial_moral_threshold: float = 0.50
    ) -> None

    def process_event(
        event_vector: np.ndarray,
        moral_value: float
    ) -> dict

    def get_state() -> dict

    def get_context(
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[np.ndarray]
```

**Thread Safety:**
- Uses threading.Lock for critical sections
- Ensures atomic reads/writes to shared state
- Prevents race conditions in concurrent access

---

### 3. MoralFilterV2

**Location:** `src/mlsdm/cognition/moral_filter_v2.py`
**Purpose:** Adaptive moral threshold evaluation and homeostasis

**Key Responsibilities:**
- Evaluate moral acceptability of events
- Adapt threshold based on observed patterns (EMA-based)
- Maintain threshold within bounds [0.30, 0.90]
- Converge to min/max under sustained patterns

**Algorithm:**
```python
# Evaluation
accept = moral_value >= threshold

# EMA update (α = 0.1)
ema = α * signal + (1 - α) * ema_prev

# Threshold adaptation
error = ema - target  # target = 0.5
adjustment = 0.05 * sign(error)
threshold = clip(threshold + adjustment, 0.30, 0.90)
```

**Convergence Properties:**
- Converges to 0.30 under sustained low-morality inputs (< 0.1)
- Converges to 0.90 under sustained high-morality inputs (> 0.9)
- Stable equilibrium around 0.50 for balanced inputs
- Drift bounded to ±0.05 per adaptation step

---

### 4. CognitiveRhythm

**Location:** `src/mlsdm/rhythm/cognitive_rhythm.py`
**Purpose:** Manage wake/sleep cycles with distinct processing behaviors

**Key Responsibilities:**
- Track current phase (wake or sleep)
- Advance phase based on step count
- Provide phase information for downstream systems
- Enforce phase-specific constraints

**Cycle Behavior:**
```
Wake Phase (8 steps):
  - Full token generation (up to max_tokens)
  - Fresh memory retrieval emphasized
  - Normal processing speed

Sleep Phase (3 steps):
  - Reduced tokens (max_tokens // 2)
  - Consolidated memory retrieval emphasized
  - Introspection and memory consolidation
```

**State Transitions:**
```
Initial → Wake (step 0-7) → Sleep (step 8-10) → Wake (step 11-18) → ...
```

---

### 5. Phase-Entangled Lattice Memory (PELM)

**Location:** `src/mlsdm/memory/phase_entangled_lattice_memory.py` (formerly `qilm_v2.py`)
**Purpose:** Bounded phase-entangled lattice in embedding space with phase-based retrieval

PELM is a geometrically-structured memory system that stores vectors with associated phase values, enabling phase-proximity-based retrieval. The design is mathematically inspired by quantum concepts but operates entirely in classical embedding space—not related to quantum hardware.

**Key Responsibilities:**
- Store vectors with phase entanglement
- Provide phase-aware retrieval
- Maintain capacity bounds (fixed size)
- Support efficient similarity search

**Data Structure:**
```python
memory: List[Vector]  # Circular buffer with fixed capacity
phases: List[str]     # Corresponding phase labels
size: int             # Current occupancy (≤ capacity)
write_index: int      # Next write position
```

**Retrieval Strategy:**
```python
def retrieve(query: np.ndarray, phase: str, tolerance: float) -> List[np.ndarray]:
    # 1. Filter by phase with tolerance
    candidates = [v for v, p in zip(vectors, phases) if phase_match(p, phase, tolerance)]

    # 2. Compute cosine similarity
    similarities = [cosine(query, v) for v in candidates]

    # 3. Return top-k by similarity
    return sorted_by_similarity(candidates, similarities)[:k]
```

**Capacity Management:**
- Fixed capacity (default: 20,000 vectors)
- Circular buffer eviction (FIFO)
- Zero allocation after initialization
- O(1) insertion, O(n) retrieval

---

### 6. MultiLevelSynapticMemory

**Location:** `src/mlsdm/memory/multi_level_memory.py`
**Purpose:** Three-level memory with decay and gated transfer

**Memory Levels:**

1. **L1 (Short-Term)**: λ = 0.95 (fast decay)
   - Holds immediate context (last few events)
   - High temporal resolution
   - Rapid forgetting

2. **L2 (Medium-Term)**: λ = 0.98 (moderate decay)
   - Holds recent significant events
   - Balanced retention
   - Gated transfer from L1

3. **L3 (Long-Term)**: λ = 0.99 (slow decay)
   - Holds consolidated memories
   - Low temporal resolution
   - Gated transfer from L2

**Update Mechanism:**
```python
def update(event: np.ndarray) -> None:
    # Decay existing levels
    L1 = λ1 * L1_prev
    L2 = λ2 * L2_prev
    L3 = λ3 * L3_prev

    # Add new event to L1
    L1 += event

    # Gated transfer L1 → L2 (if threshold exceeded)
    if norm(L1) > threshold_12:
        L2 += gate_12 * L1

    # Gated transfer L2 → L3 (if threshold exceeded)
    if norm(L2) > threshold_23:
        L3 += gate_23 * L2
```

---

### 7. OntologyMatcher

**Location:** `src/mlsdm/cognition/ontology_matcher.py`
**Purpose:** Semantic classification and concept matching

**Key Responsibilities:**
- Match event vectors to ontology concepts
- Compute similarity scores
- Support multiple distance metrics
- Provide semantic labels

**Interface:**
```python
class OntologyMatcher:
    def __init__(ontology: Dict[str, np.ndarray]) -> None

    def match(
        event_vector: np.ndarray,
        metric: str = "cosine"
    ) -> Tuple[str, float]
```

**Supported Metrics:**
- `cosine`: Cosine similarity (default)
- `euclidean`: Euclidean distance
- `dot`: Dot product

---

### 8. NeuroLangWrapper

**Location:** `src/mlsdm/extensions/neuro_lang_extension.py`
**Status:** ✅ Implemented
**Purpose:** Enhanced LLM wrapper with NeuroLang language processing and Aphasia-Broca detection

**Key Responsibilities:**
- Extend base LLMWrapper with language-specific processing
- Apply NeuroLang grammar enrichment to prompts
- Detect aphasic speech patterns in LLM outputs
- Trigger regeneration when telegraphic responses detected
- Return structured metadata about language processing

**Interface:**
```python
class NeuroLangWrapper(LLMWrapper):
    def __init__(
        llm_generate_fn: Callable[[str, int], str],
        embedding_fn: Callable[[str], np.ndarray],
        dim: int = 384,
        capacity: int = 20_000,
        wake_duration: int = 8,
        sleep_duration: int = 3,
        initial_moral_threshold: float = 0.50
    ) -> None

    def generate(
        prompt: str,
        moral_value: float,
        max_tokens: Optional[int] = None,
        context_top_k: int = 5
    ) -> dict  # Includes aphasia_flags and neuro_enhancement
```

**Components:**
- `InnateGrammarModule`: Provides recursive grammar templates
- `CriticalPeriodTrainer`: Models language acquisition windows
- `ModularLanguageProcessor`: Separates production/comprehension
- `SocialIntegrator`: Simulates pragmatic intent
- `AphasiaBrocaDetector`: Analyzes speech quality

---

### 9. AphasiaBrocaDetector

**Location:** `src/mlsdm/extensions/neuro_lang_extension.py`
**Status:** ✅ Implemented
**Purpose:** Detect and quantify telegraphic speech patterns in LLM outputs

**Key Responsibilities:**
- Analyze text for Broca-like aphasia characteristics
- Measure sentence length, function word ratio, fragmentation
- Calculate severity score (0.0 = healthy, 1.0 = severe)
- Provide structured diagnostic output
- Support regeneration decisions

**Interface:**
```python
class AphasiaBrocaDetector:
    def __init__() -> None  # Stateless

    def analyze(text: str) -> dict:
        return {
            "is_aphasic": bool,
            "severity": float,
            "avg_sentence_len": float,
            "function_word_ratio": float,
            "fragment_ratio": float,
            "flags": List[str]
        }
```

**Detection Criteria:**
- **Non-Aphasic**: avg_sentence_len ≥ 6, function_word_ratio ≥ 0.15, fragment_ratio ≤ 0.5
- **Aphasic**: Any threshold violated

**Algorithm:**
```python
# Severity calculation
σ = min(1.0, (
    (MIN_LEN - avg_len) / MIN_LEN +
    (MIN_FUNC - func_ratio) / MIN_FUNC +
    (frag_ratio - MAX_FRAG) / MAX_FRAG
) / 3)
```

**Performance:**
- Latency: ~1-2ms for 100-word text
- Thread-safe (stateless, pure functional)
- O(n) time complexity

For detailed specification, see [APHASIA_SPEC.md](APHASIA_SPEC.md).

---

### 10. AphasiaSpeechGovernor

**Location:** `src/mlsdm/extensions/neuro_lang_extension.py`
**Status:** ✅ Implemented
**Purpose:** Pluggable speech governor implementing aphasia detection and repair

**Key Responsibilities:**
- Implement `SpeechGovernanceResult` protocol from `speech.governance`
- Integrate `AphasiaBrocaDetector` for analysis
- Optionally trigger LLM-based repair for telegraphic speech
- Return metadata about detection and repair operations

**Interface:**
```python
class AphasiaSpeechGovernor:
    def __init__(
        detector: AphasiaBrocaDetector,
        repair_enabled: bool = True,
        severity_threshold: float = 0.3,
        llm_generate_fn: Callable[[str, int], str] = None
    ) -> None

    def __call__(
        *,
        prompt: str,
        draft: str,
        max_tokens: int
    ) -> SpeechGovernanceResult
```

**Integration:**
- Used by `LLMWrapper` and `NeuroLangWrapper` as pluggable speech policy
- Enables separation of detection (stateless analysis) from repair (LLM-based correction)
- Supports monitoring-only mode (`repair_enabled=False`)

---

### 11. NeuroCognitiveEngine

**Location:** `src/mlsdm/engine/neuro_cognitive_engine.py`
**Status:** ✅ Implemented
**Purpose:** High-level cognitive API with timeout enforcement and circuit breaker

**Key Responsibilities:**
- Provide simplified interface for cognitive processing
- Enforce timeouts on LLM calls to prevent hangs
- Implement circuit breaker pattern for failure isolation
- Manage LLM provider routing via `LLMRouter`
- Return structured responses with timing metadata

**Interface:**
```python
class NeuroCognitiveEngine:
    def __init__(
        config: NeuroEngineConfig,
        llm_router: LLMRouter,
        embedding_fn: Callable[[str], np.ndarray]
    ) -> None

    def generate(
        prompt: str,
        moral_value: float,
        timeout_seconds: float = 30.0
    ) -> dict  # Includes response, metadata, timing
```

**Features:**
- Timeout enforcement with `TimingContext`
- Circuit breaker with configurable thresholds
- Multiple LLM backend support via routing
- Comprehensive error handling (`MLSDMRejectionError`, `EmptyResponseError`)
- Timing instrumentation for observability

---

### 12. NeuroEngineService

**Location:** `src/mlsdm/service/neuro_engine_service.py`
**Status:** ✅ Implemented
**Purpose:** Service-layer wrapper for NeuroCognitiveEngine with FastAPI integration

**Key Responsibilities:**
- Define Pydantic request/response models
- Integrate with FastAPI application
- Provide health check endpoints
- Handle service lifecycle (startup/shutdown)

**Models:**
```python
class GenerateRequest(BaseModel):
    prompt: str
    moral_value: float
    timeout_seconds: float = 30.0

class GenerateResponse(BaseModel):
    response: str
    accepted: bool
    phase: str
    metadata: dict
    timing: dict

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
```

---

### 13. NeuroCognitiveClient (SDK)

**Location:** `src/mlsdm/sdk/neuro_engine_client.py`
**Status:** ✅ Implemented
**Purpose:** Python SDK for remote NeuroCognitiveEngine access via HTTP

**Key Responsibilities:**
- HTTP client for `/generate` and `/health` endpoints
- Request/response serialization
- Connection pooling and retry logic
- Timeout enforcement at client level
- Error handling and exception translation

**Interface:**
```python
class NeuroCognitiveClient:
    def __init__(
        base_url: str,
        api_key: str = None,
        timeout: float = 30.0
    ) -> None

    def generate(
        prompt: str,
        moral_value: float,
        timeout_seconds: float = None
    ) -> dict

    def health_check() -> dict
```

**Usage Example:**
```python
client = NeuroCognitiveClient("http://localhost:8000")
result = client.generate("Hello", moral_value=0.8)
print(result["response"])
```

---

### 14. LLM Adapters and Factory

**Location:** `src/mlsdm/adapters/`
**Status:** ✅ Implemented
**Purpose:** Pluggable LLM provider integrations with unified interface

**Components:**

**LLMProvider Protocol** (`llm_provider.py`):
```python
class LLMProvider(Protocol):
    def generate(prompt: str, max_tokens: int) -> str
    def get_provider_name() -> str
```

**Implementations:**
- **OpenAIAdapter** (`openai_adapter.py`): OpenAI API integration with configurable models
- **LocalStubAdapter** (`local_stub_adapter.py`): Testing stub with configurable behavior

**ProviderFactory** (`provider_factory.py`):
```python
class ProviderFactory:
    @staticmethod
    def create_provider(
        backend: str,
        api_key: str = None,
        model: str = None
    ) -> LLMProvider
```

**Supported Backends:**
- `openai`: OpenAI GPT models (requires API key)
- `local_stub`: Local testing stub (no external dependencies)
- Extensible: Add new providers by implementing `LLMProvider` protocol

---

For detailed specification, see [APHASIA_SPEC.md](APHASIA_SPEC.md).

---

## Component Interactions

### Event Processing Flow (Base LLMWrapper)

```
1. User calls wrapper.generate(prompt, moral_value)
   │
2. Wrapper creates embedding of prompt
   │
3. Controller receives process_event(embedding, moral_value)
   │
4. MoralFilter evaluates moral_value
   │   ├─ Accept: continue processing
   │   └─ Reject: return early with rejection metadata
   │
5. CognitiveRhythm advances phase
   │
6. MultiLevelMemory updates with event vector
   │
7. PELM stores event with current phase
   │
8. OntologyMatcher classifies event
   │
9. Controller retrieves context for prompt enrichment
   │
10. Wrapper calls LLM with enriched prompt + phase-adjusted tokens
    │
11. Response returned with governance metadata
```

### NeuroLang Processing Flow (NeuroLangWrapper)

```
1. User calls wrapper.generate(prompt, moral_value)
   │
2. NeuroLang enrichment
   │   ├─ InnateGrammarModule processes prompt
   │   ├─ ModularLanguageProcessor adds structure
   │   └─ SocialIntegrator adds pragmatic context
   │
3. Wrapper creates embedding of enriched prompt
   │
4. Controller receives process_event(embedding, moral_value)
   │   ├─ MoralFilter evaluation
   │   ├─ CognitiveRhythm phase management
   │   └─ Memory storage (PELM + MultiLevelMemory)
   │
5. If accepted: LLM generates base_response
   │
6. AphasiaBrocaDetector analyzes base_response
   │   ├─ Check: avg_sentence_len ≥ 6?
   │   ├─ Check: function_word_ratio ≥ 0.15?
   │   └─ Check: fragment_ratio ≤ 0.5?
   │
7. If aphasic detected:
   │   ├─ Construct correction prompt
   │   ├─ Regenerate with grammar requirements
   │   └─ Re-analyze until healthy
   │
8. Response returned with extended metadata:
   │   ├─ response (corrected if needed)
   │   ├─ phase, accepted
   │   ├─ neuro_enhancement (NeuroLang additions)
   │   └─ aphasia_flags (detection results)
```

### End-to-End HTTP API Flow

```
1. HTTP Client (SDK or curl) → POST /generate
   │
2. FastAPI (src/mlsdm/api/app.py)
   │   ├─ Middleware: Rate limiting check (5 RPS default)
   │   ├─ Middleware: Authentication (Bearer token)
   │   ├─ Middleware: Request validation (Pydantic)
   │   └─ Route to NeuroEngineService
   │
3. NeuroEngineService (src/mlsdm/service/neuro_engine_service.py)
   │   ├─ Parse GenerateRequest
   │   └─ Delegate to NeuroCognitiveEngine
   │
4. NeuroCognitiveEngine (src/mlsdm/engine/neuro_cognitive_engine.py)
   │   ├─ Start timeout enforcement (TimingContext)
   │   ├─ Check circuit breaker state
   │   ├─ Route to LLM via LLMRouter
   │   └─ Delegate to LLMWrapper/NeuroLangWrapper
   │
5. LLMWrapper or NeuroLangWrapper
   │   ├─ Create embedding of prompt
   │   ├─ Retrieve context from CognitiveController
   │   ├─ Call CognitiveController.process_event()
   │   │   ├─ MoralFilter evaluation
   │   │   ├─ CognitiveRhythm phase management
   │   │   ├─ Memory storage (PELM + MultiLevelMemory)
   │   │   └─ Ontology matching
   │   ├─ If accepted: Call LLM provider (OpenAI/Stub)
   │   ├─ If NeuroLangWrapper: Apply AphasiaSpeechGovernor
   │   └─ Return structured response
   │
6. Response flows back up through layers:
   │   ├─ NeuroCognitiveEngine: Add timing metadata
   │   ├─ NeuroEngineService: Serialize to GenerateResponse
   │   ├─ FastAPI: Add response headers, log metrics
   │   └─ HTTP response to client
   │
7. Observability (parallel):
   │   ├─ Metrics export to Prometheus (src/mlsdm/observability/metrics.py)
   │   ├─ Structured logging (src/mlsdm/observability/logger.py)
   │   └─ Aphasia-specific events (src/mlsdm/observability/aphasia_logging.py)
```

### Direct Integration Flow (No HTTP)

```
1. Application code directly imports LLMWrapper or NeuroLangWrapper
   │
2. Initialize with user-provided functions:
   │   ├─ llm_generate_fn: Custom LLM integration
   │   └─ embedding_fn: Custom embedding model
   │
3. Call wrapper.generate(prompt, moral_value)
   │   ├─ Follows same cognitive flow as HTTP API
   │   └─ No HTTP overhead, no middleware layers
   │
4. Returns dict with response and metadata directly to caller
```

### Concurrent Access Pattern

```
Thread 1: generate("prompt A", 0.8) ──┐
                                       ├──► Lock ──► Controller ──► Unlock
Thread 2: generate("prompt B", 0.6) ──┘

Thread 3: get_state() ──► Lock ──► Controller ──► Unlock
```

**Concurrency Properties:**
- Lock acquisition: O(1) expected, bounded waiting
- Critical section: ~2ms P50, ~10ms P95
- No deadlocks (single lock, no nested acquisition)
- No race conditions (all shared state protected)

### Multi-Provider Routing Flow

```
1. NeuroCognitiveEngine receives generate request
   │
2. LLMRouter.route() selects provider based on:
   │   ├─ Provider availability (circuit breaker state)
   │   ├─ Load balancing strategy (round-robin, weighted)
   │   └─ Request characteristics (prompt length, moral value)
   │
3. Selected provider (OpenAI / Local Stub / Custom):
   │   ├─ OpenAIAdapter: Calls OpenAI API with retry logic
   │   ├─ LocalStubAdapter: Returns deterministic test response
   │   └─ Custom: User-provided LLMProvider implementation
   │
4. Response flows back through NeuroCognitiveEngine
   │   ├─ Add provider metadata (provider_name, latency)
   │   ├─ Update circuit breaker metrics
   │   └─ Return to caller
```

---

## Data Flow

### Input Data Flow

```
User Prompt (str)
    │
    ├──► Embedding Function
    │        │
    │        └──► Event Vector (np.ndarray, dim=384)
    │
    └──► Moral Value (float ∈ [0, 1])
         │
         └──► MoralFilter ──► Accept/Reject Decision
```

### Memory Data Flow

```
Event Vector
    │
    ├──► MultiLevelMemory (L1 → L2 → L3 decay)
    │
    └──► Phase-Entangled Lattice Memory (PELM, formerly QILM_v2) (phase-entangled storage)
         │
         └──► Retrieval ──► Context Vectors ──► Prompt Enrichment
```

### Response Data Flow

```
Enriched Prompt
    │
    └──► LLM Generate Function
         │
         └──► Response Text (str)
              │
              ├──► Accept: Return response
              │
              └──► Reject: Return empty + metadata
```

---

## Memory Architecture

### Memory Capacity Management

**Total Memory Bound:** 29.37 MB (verified empirically)

**Component Breakdown:**
- Phase-Entangled Lattice Memory (PELM, formerly QILM_v2): 20,000 vectors × 384 dims × 4 bytes = 30,720,000 bytes ≈ 29.30 MB (pre-allocated)
- MultiLevelMemory: 3 levels × 384 dims × 4 bytes = 4,608 bytes ≈ 4.5 KB
- MoralFilter: ~100 bytes (threshold + EMA state)
- CognitiveRhythm: ~50 bytes (phase + step counter)
- Controller metadata: ~50 KB (overhead and tracking)

**Note:** Total measured footprint is 29.37 MB, which includes Python object overhead and runtime structures.

**Zero-Allocation Property:**
- All memory pre-allocated at initialization
- Circular buffer reuse (no dynamic allocation)
- Fixed-size data structures
- No heap growth during operation

### Memory Retrieval Strategies

**Wake Phase Strategy:**
```python
# Emphasize fresh, recent memories
tolerance = 0.3  # Stricter phase matching
weight_recent = 0.7
weight_consolidated = 0.3
```

**Sleep Phase Strategy:**
```python
# Emphasize consolidated, long-term memories
tolerance = 0.7  # Looser phase matching
weight_recent = 0.3
weight_consolidated = 0.7
```

---

## API Architecture

### FastAPI Integration

**Location:** `src/mlsdm/api/app.py`
**Purpose:** HTTP/JSON interface for remote access

**Endpoints:**

1. **POST /v1/process_event**
   - Process cognitive event with moral evaluation
   - Request: `{event: List[float], moral_value: float}`
   - Response: `{accepted: bool, phase: str, ...}`

2. **GET /v1/state**
   - Retrieve current system state
   - Response: `{step: int, phase: str, threshold: float, ...}`

3. **GET /health**
   - Health check endpoint
   - Response: `{status: "ok"}`

**Security:**
- Bearer token authentication
- Rate limiting (5 RPS per client)
- Input validation (strict type checking)
- Structured logging (no PII)

---

## Performance Characteristics

### Latency Profiles

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| process_event (no retrieval) | 2ms | 5ms | 8ms |
| process_event (with retrieval) | 8ms | 10ms | 15ms |
| get_state | <1ms | 2ms | 3ms |
| get_context | 5ms | 8ms | 12ms |

### Throughput

- **Single-threaded:** ~500 ops/sec
- **Multi-threaded (4 cores):** ~1,800 ops/sec
- **Maximum verified:** 5,500 ops/sec (load test)
- **Concurrent requests:** 1,000+ simultaneous (verified)

### Resource Usage

- **Memory:** 29.37 MB (fixed)
- **CPU:** ~5% at 100 RPS (single core)
- **I/O:** Minimal (in-memory operations)

---

## Design Principles

### 1. Neurobiological Grounding

All components derive from established neuroscience principles (see [docs/NEURO_FOUNDATIONS.md](docs/NEURO_FOUNDATIONS.md) for detailed scientific foundations):

- **Circadian Rhythm:** Wake/sleep cycles inspired by suprachiasmatic nucleus (SCN) rhythm generation [Hastings et al., 2018] and distributed brain clocks [Mendoza & Challet, 2009]
- **Synaptic Decay:** Multi-level memory with cascade consolidation models [Fusi et al., 2005; Benna & Fusi, 2016]
- **Moral Homeostasis:** Adaptive threshold regulation inspired by value alignment theory [Gabriel, 2020] and constitutional AI principles [Bai et al., 2022]
- **Phase Entanglement:** Quantum-inspired associative memory [Masuyama et al., 2014, 2018] with hippocampal replay mechanisms [Foster & Wilson, 2006; Carr et al., 2011]
- **Broca's Area Model:** Speech production and grammar processing for aphasia detection (see [APHASIA_SPEC.md](APHASIA_SPEC.md))
- **Modular Language Processing:** Separate comprehension and production pathways inspired by dual-stream language models

### 2. Bounded Resources

System designed for production environments with strict limits:
- **Fixed Memory:** No unbounded growth
- **Deterministic Latency:** Bounded worst-case performance
- **Graceful Degradation:** Capacity eviction, not failure

### 3. Safety and Governance

Moral governance and language quality without external training:
- **Adaptive Thresholds:** Self-regulating based on patterns
- **No RLHF Required:** Built-in moral evaluation
- **Speech Pathology Detection:** Automatic identification of telegraphic responses
- **Self-Correction:** Regeneration when quality thresholds violated
- **Transparent Decisions:** Observable threshold and reasoning
- **Drift Resistance:** Bounded adaptation steps

### 4. Composability

System designed for flexible integration:
- **Universal LLM Support:** Works with any generation function
- **Custom Embeddings:** User-provided embedding models
- **Standalone or Service:** Direct integration or API deployment
- **Observable State:** Complete introspection capabilities

### 5. Production Readiness

Enterprise-grade operational characteristics:
- **Thread-Safe:** Zero race conditions
- **High Throughput:** 1,000+ RPS verified
- **Observable:** Prometheus metrics, structured logs
- **Testable:** 90%+ coverage, property-based tests
- **Documented:** Comprehensive API and architecture docs

---

## References

### Scientific Foundation
- [docs/SCIENTIFIC_RATIONALE.md](docs/SCIENTIFIC_RATIONALE.md) - Core scientific rationale and hypothesis
- [docs/NEURO_FOUNDATIONS.md](docs/NEURO_FOUNDATIONS.md) - Neuroscience foundations for each module
- [docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md](docs/ALIGNMENT_AND_SAFETY_FOUNDATIONS.md) - AI safety and governance foundations
- [BIBLIOGRAPHY.md](bibliography/README.md) - Complete bibliography with peer-reviewed sources

### Technical Documentation
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Implementation details
- [EFFECTIVENESS_VALIDATION_REPORT.md](EFFECTIVENESS_VALIDATION_REPORT.md) - Empirical validation
- [APHASIA_SPEC.md](APHASIA_SPEC.md) - Aphasia-Broca Model specification
- [docs/FORMAL_INVARIANTS.md](docs/FORMAL_INVARIANTS.md) - Formal properties and verification

---

**Document Status:** Beta
**Review Cycle:** Per minor version
**Last Reviewed:** November 22, 2025
**Next Review:** Version 1.2.0 release
