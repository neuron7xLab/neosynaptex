# Developer Guide

**Document Version:** 1.0.0
**Project Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Production

---

## Table of Contents

- [Purpose](#purpose)
- [Project Layout](#project-layout)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Architecture Quick Reference](#architecture-quick-reference)
- [Key Patterns and Conventions](#key-patterns-and-conventions)
- [Running and Testing](#running-and-testing)
- [Adding New Features](#adding-new-features)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)
- [PR Expectations](#pr-expectations)

---

## Purpose

This guide enables engineers to:

1. **Bootstrap** the development environment in <10 minutes
2. **Understand** the codebase structure without guessing
3. **Modify** existing components safely, honoring memory and retrieval patterns derived from synaptic and RAG literature [@benna2016_synaptic; @lewis2020_rag]
4. **Extend** the system with new features following established patterns
5. **Debug** issues efficiently using built-in observability

**Audience:** Core developers, contributors, and engineers integrating MLSDM into their systems.

---

## Project Layout

```text
mlsdm/
├── src/mlsdm/                    # Main source code
│   ├── adapters/                 # LLM provider integrations
│   │   ├── llm_provider.py       # LLMProvider protocol definition
│   │   ├── openai_adapter.py     # OpenAI API adapter
│   │   ├── local_stub_adapter.py # Local testing stub
│   │   └── provider_factory.py   # Factory for adapter instantiation
│   │
│   ├── api/                      # FastAPI HTTP layer
│   │   ├── app.py                # Main FastAPI application
│   │   ├── health.py             # Health check endpoints
│   │   ├── lifecycle.py          # Startup/shutdown hooks
│   │   ├── middleware.py         # Rate limiting, auth, observability
│   │   └── schemas.py            # Pydantic request/response models
│   │
│   ├── cognition/                # Cognitive subsystems
│   │   ├── moral_filter_v2.py    # Adaptive moral threshold (primary)
│   │   ├── moral_filter.py       # Legacy moral filter (deprecated)
│   │   ├── ontology_matcher.py   # Semantic classification
│   │   └── synergy_experience.py # Synergy patterns
│   │
│   ├── core/                     # Core orchestration
│   │   ├── llm_wrapper.py        # Universal LLM wrapper
│   │   ├── llm_pipeline.py       # Pre/post filter pipeline
│   │   ├── cognitive_controller.py # Thread-safe orchestrator
│   │   ├── cognitive_state.py    # State management
│   │   └── memory_manager.py     # Memory lifecycle
│   │
│   ├── engine/                   # High-level engine
│   │   ├── neuro_cognitive_engine.py # Timeout/circuit breaker wrapper
│   │   └── factory.py            # Engine instantiation
│   │
│   ├── entrypoints/              # Runtime entry points
│   │   ├── dev/                  # Development mode entry
│   │   ├── cloud/                # Cloud production mode
│   │   ├── agent/                # Agent/API mode
│   │   └── health.py             # Health check CLI
│   │
│   ├── extensions/               # Optional extensions
│   │   └── neuro_lang_extension.py # NeuroLang + Aphasia detection
│   │
│   ├── memory/                   # Memory subsystems
│   │   ├── phase_entangled_lattice_memory.py # PELM (primary)
│   │   ├── multi_level_memory.py # L1/L2/L3 synaptic memory
│   │   ├── qilm_v2.py            # Legacy QILM (deprecated)
│   │   └── experimental/         # Research modules
│   │
│   ├── observability/            # Metrics and logging
│   │   ├── metrics.py            # Prometheus metrics
│   │   ├── logger.py             # Structured JSON logging
│   │   ├── exporters.py          # Metric export utilities
│   │   └── aphasia_logging.py    # Domain-specific logging
│   │
│   ├── rhythm/                   # Cognitive rhythm
│   │   └── cognitive_rhythm.py   # Wake/sleep cycle manager
│   │
│   ├── router/                   # LLM routing
│   │   └── llm_router.py         # Multi-provider routing
│   │
│   ├── sdk/                      # Client SDK
│   │   └── neuro_engine_client.py # HTTP client for remote access
│   │
│   ├── security/                 # Security layer
│   │   ├── rate_limit.py         # Token bucket rate limiter
│   │   └── payload_scrubber.py   # PII removal
│   │
│   ├── service/                  # Service layer
│   │   └── neuro_engine_service.py # FastAPI service wrapper
│   │
│   ├── speech/                   # Speech governance
│   │   └── governance.py         # Aphasia speech policy
│   │
│   └── utils/                    # Utilities
│       ├── config_loader.py      # YAML configuration
│       ├── config_validator.py   # Schema enforcement
│       ├── input_validator.py    # Input validation
│       └── data_serializer.py    # Event serialization
│
├── tests/                        # Test suites
│   ├── unit/                     # Component-level tests
│   ├── integration/              # Cross-component tests
│   ├── e2e/                      # End-to-end tests
│   ├── property/                 # Hypothesis property tests
│   ├── validation/               # Effectiveness validation
│   ├── eval/                     # Scientific evaluation
│   ├── security/                 # Security tests
│   └── load/                     # Performance/load tests
│
├── examples/                     # Working code examples
│   ├── llm_wrapper_example.py    # Basic wrapper usage
│   ├── production_chatbot_example.py # Production patterns
│   └── observability_*.py        # Metrics/logging examples
│
├── scripts/                      # Utility scripts
│   ├── run_aphasia_eval.py       # Aphasia evaluation runner
│   ├── security_audit.py         # Security posture check
│   └── verify_core_implementation.sh # Implementation validation
│
├── config/                       # Configuration profiles
├── deploy/                       # Deployment manifests
│   ├── k8s/                      # Kubernetes manifests
│   └── grafana/                  # Grafana dashboards
│
├── docs/                         # Extended documentation
│   ├── LLM_PIPELINE.md           # Pipeline specification
│   ├── NEURO_FOUNDATIONS.md      # Neuroscience foundations
│   └── SCIENTIFIC_RATIONALE.md   # Scientific basis
│
└── pyproject.toml                # Project configuration
```

### Key Files by Purpose

| Purpose | Primary File | Secondary Files |
|---------|--------------|-----------------|
| **LLM Wrapping** | `src/mlsdm/core/llm_wrapper.py` | `llm_pipeline.py`, `cognitive_controller.py` |
| **Moral Filtering** | `src/mlsdm/cognition/moral_filter_v2.py` | - |
| **Memory Storage** | `src/mlsdm/memory/phase_entangled_lattice_memory.py` | `multi_level_memory.py` |
| **Wake/Sleep Cycle** | `src/mlsdm/rhythm/cognitive_rhythm.py` | - |
| **Aphasia Detection** | `src/mlsdm/extensions/neuro_lang_extension.py` | `src/mlsdm/speech/governance.py` |
| **HTTP API** | `src/mlsdm/api/app.py` | `health.py`, `middleware.py` |
| **Metrics** | `src/mlsdm/observability/metrics.py` | `logger.py`, `exporters.py` |

---

## Development Setup

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Git
- Make (optional, for convenience commands)

### Quick Setup (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/neuron7xLab/mlsdm.git
cd mlsdm

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install with dev dependencies
pip install -e ".[dev,test]"

# 4. Verify installation
make test
# Or: pytest --ignore=tests/load -x -q
```

### Optional: NeuroLang/Aphasia Support

```bash
# Install PyTorch-based NeuroLang extension
pip install -e ".[neurolang]"
```

### Optional: Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

This enables automatic linting and formatting on each commit.

### Environment Variables (Optional)

Create `.env` file or export variables:

```bash
# LLM providers (only if testing with real LLMs)
export OPENAI_API_KEY=your-key-here

# Runtime mode
export MLSDM_ENV=development
export LOG_LEVEL=DEBUG
```

---

## Development Workflow

### Standard Development Cycle

```text
1. Create branch   → git checkout -b feature/your-feature
2. Make changes    → Edit files in src/mlsdm/
3. Write tests     → Add tests in tests/
4. Run tests       → make test
5. Run linter      → make lint
6. Run types       → make type
7. Commit          → git commit -m "feat: your change"
8. Push + PR       → git push origin feature/your-feature
```

### Available Make Commands

```bash
# Testing & Linting
make test     # Run all tests (ignores load tests)
make lint     # Run ruff linter on src and tests
make type     # Run mypy type checker on src/mlsdm
make cov      # Run tests with coverage report

# Runtime Modes
make run-dev        # Start development server (hot reload, debug logging)
make run-cloud-local # Start local production server (multiple workers)
make run-agent      # Start agent/API server (for LLM integration)
make health-check   # Run health check

# Evaluations
make eval-moral_filter # Run moral filter evaluation suite
```

### Direct Commands (Without Make)

```bash
# Tests
pytest --ignore=tests/load -v

# Specific test file
pytest tests/unit/test_llm_wrapper.py -v

# Specific test function
pytest tests/unit/test_llm_wrapper.py::test_basic_generation -v

# With coverage
pytest --ignore=tests/load --cov=src --cov-report=html --cov-report=term-missing

# Linting
ruff check src tests
ruff check src tests --fix  # Auto-fix issues

# Type checking
mypy src/mlsdm

# Format code
ruff format src tests
```

### Test Organization

| Test Type | Location | Purpose | Run Command |
|-----------|----------|---------|-------------|
| **Unit** | `tests/unit/` | Component isolation | `pytest tests/unit/ -v` |
| **Integration** | `tests/integration/` | Cross-component | `pytest tests/integration/ -v` |
| **E2E** | `tests/e2e/` | Full system | `pytest tests/e2e/ -v` |
| **Property** | `tests/property/` | Invariant verification | `pytest tests/property/ -v` |
| **Validation** | `tests/validation/` | Effectiveness | `pytest tests/validation/ -v` |
| **Security** | `tests/security/` | Security features | `pytest tests/security/ -v` |
| **Load** | `tests/load/` | Performance | `pytest tests/load/ -v` (separate) |

---

## Architecture Quick Reference

### Core Data Flow

```text
User Prompt (str)
     │
     ▼
┌─────────────────────────────────────────┐
│           LLMWrapper.generate()          │
│  • Creates embedding via embedding_fn    │
│  • Retrieves context from PELM           │
│  • Calls CognitiveController             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│        CognitiveController               │
│  • MoralFilterV2.evaluate()             │
│  • CognitiveRhythm.advance()            │
│  • MultiLevelMemory.update()            │
│  • PELM.store()                         │
└─────────────────┬───────────────────────┘
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
 Rejected                  Accepted
     │                         │
     ▼                         ▼
 Return empty           Call llm_generate_fn()
 + rejection note              │
                               ▼
                         Return response
                         + governance metadata
```

### Key Invariants

| Invariant | Value | Enforcement |
|-----------|-------|-------------|
| **Moral Threshold Bounds** | [0.30, 0.90] | `MoralFilterV2._adapt_threshold()` |
| **Memory Capacity** | 20,000 vectors | `PELM.__init__()` circular buffer |
| **Memory Footprint** | ≤ 29.37 MB | Pre-allocated, zero-growth |
| **Non-Aphasic Output** | avg_sentence_len ≥ 6 | `AphasiaBrocaDetector.analyze()` |
| **Function Word Ratio** | ≥ 0.15 | `AphasiaBrocaDetector.analyze()` |

### Thread Safety Model

All shared state is protected by `threading.Lock` in `CognitiveController`:

```python
# Thread-safe pattern used throughout
with self._lock:
    # Read/modify shared state
    self._step += 1
    self._memory.store(vector)
```

**Concurrency**: O(1) lock acquisition, ~2ms P50 critical section, no deadlocks.

---

## Key Patterns and Conventions

### 1. Protocol-Based Adapters

Use protocols (not abstract base classes) for LLM integrations:

```python
# src/mlsdm/adapters/llm_provider.py
from typing import Protocol

class LLMProvider(Protocol):
    def generate(self, prompt: str, max_tokens: int) -> str: ...
    def get_provider_name(self) -> str: ...

# Implement by satisfying the protocol
class MyCustomAdapter:
    def generate(self, prompt: str, max_tokens: int) -> str:
        return my_llm_call(prompt, max_tokens)

    def get_provider_name(self) -> str:
        return "my_custom"
```

### 2. Dependency Injection

Pass functions, not instances:

```python
# Correct: Pass callable functions
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,      # Callable[[str, int], str]
    embedding_fn=my_embedder,    # Callable[[str], np.ndarray]
    dim=384
)

# Incorrect: Don't create dependencies internally
# wrapper = LLMWrapper()  # Where does LLM come from?
```

### 3. Immutable State Returns

Return copies, not references:

```python
def get_state(self) -> dict:
    """Return system state (thread-safe copy)."""
    with self._lock:
        return {
            "step": self._step,
            "phase": self._phase,
            "threshold": self._threshold,
            # Never return: "memory": self._memory  # Mutable!
        }
```

### 4. Structured Logging

Use observability logger for production:

```python
from mlsdm.observability.logger import get_logger

logger = get_logger(__name__)

# Structured context
logger.info("event_processed", extra={
    "step": step,
    "phase": phase,
    "moral_value": moral_value,
    "accepted": accepted
})
```

### 5. Type Hints Required

All public functions must have type hints:

```python
# Required for all public APIs
def process_event(
    event_vector: np.ndarray,
    moral_value: float,
    *,  # Force keyword-only after this
    context_top_k: int = 5
) -> dict:
    """Process cognitive event with moral evaluation.

    Args:
        event_vector: Input embedding (dim,)
        moral_value: Moral score 0.0-1.0
        context_top_k: Number of context items

    Returns:
        Dict with accepted, phase, threshold, etc.

    Raises:
        ValueError: If moral_value outside [0, 1]
    """
```

### 6. Google-Style Docstrings

```python
class MoralFilterV2:
    """Adaptive moral filtering with homeostatic threshold.

    The filter maintains a dynamic threshold that adapts based on
    acceptance rates to achieve approximately 50% acceptance.

    Attributes:
        threshold: Current moral threshold value (0.30-0.90)
        ema: Exponential moving average of acceptance rate

    Example:
        >>> filter = MoralFilterV2(initial_threshold=0.5)
        >>> accepted = filter.evaluate(moral_value=0.8)
        >>> filter.adapt(accepted)
    """
```

---

## Running and Testing

### Run Development Server

```bash
# Method 1: Make target
make run-dev

# Method 2: Direct Python
python -m mlsdm.entrypoints.dev

# Method 3: Uvicorn directly
uvicorn mlsdm.api.app:app --reload --host 0.0.0.0 --port 8000
```

Server starts at `http://localhost:8000`. Swagger UI at `/docs`.

### Health Check

```bash
curl http://localhost:8000/health

# Expected response:
# {"status": "ok", "version": "1.2.0", "phase": "wake", "step": 0}
```

### Test a Generation Request

```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "moral_value": 0.8}'
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Property-based tests (invariant verification)
pytest tests/property/ -v

# Aphasia/NeuroLang tests
pytest tests/validation/test_aphasia_detection.py -v
pytest tests/eval/test_aphasia_eval_suite.py -v

# Security tests
pytest tests/security/ -v

# Skip slow tests
pytest -m "not slow" -v
```

### Coverage Report

```bash
make cov
# Opens HTML report in coverage_html_report/index.html
```

---

## Adding New Features

### Adding a New LLM Adapter

1. Create adapter file:

```python
# src/mlsdm/adapters/anthropic_adapter.py
import anthropic

class AnthropicAdapter:
    """Anthropic Claude API adapter."""

    def __init__(self, api_key: str, model: str = "claude-3-opus"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def get_provider_name(self) -> str:
        return "anthropic"
```

2. Register in factory:

```python
# src/mlsdm/adapters/provider_factory.py
class ProviderFactory:
    @staticmethod
    def create_provider(backend: str, **kwargs) -> LLMProvider:
        if backend == "anthropic":
            from .anthropic_adapter import AnthropicAdapter
            return AnthropicAdapter(**kwargs)
        # ... existing providers
```

3. Add tests:

```python
# tests/unit/test_anthropic_adapter.py
def test_anthropic_adapter_creation():
    adapter = AnthropicAdapter(api_key="test", model="claude-3")
    assert adapter.get_provider_name() == "anthropic"
```

### Adding a New Pre-Filter

1. Implement filter protocol:

```python
# src/mlsdm/core/my_filter.py
from mlsdm.core.llm_pipeline import FilterResult, FilterDecision

class MyPreFilter:
    """Custom pre-filter for specific validation."""

    def evaluate(self, prompt: str, context: dict) -> FilterResult:
        if self._is_blocked(prompt):
            return FilterResult(
                decision=FilterDecision.BLOCK,
                reason="custom_block",
                metadata={"matched": "reason"}
            )
        return FilterResult(
            decision=FilterDecision.ALLOW,
            reason="allowed"
        )

    def _is_blocked(self, prompt: str) -> bool:
        # Custom logic
        return False
```

2. Register in pipeline:

```python
# In your pipeline configuration
pipeline._pre_filters.append(("my_filter", MyPreFilter()))
```

### Adding New Metrics

1. Define metric in observability:

```python
# src/mlsdm/observability/metrics.py
from prometheus_client import Counter, Histogram

my_counter = Counter(
    'mlsdm_my_events_total',
    'Total my events',
    ['event_type']
)

my_latency = Histogram(
    'mlsdm_my_latency_seconds',
    'My operation latency'
)
```

2. Use in code:

```python
from mlsdm.observability.metrics import my_counter, my_latency

my_counter.labels(event_type='processed').inc()
with my_latency.time():
    result = do_operation()
```

---

## Debugging and Troubleshooting

### Common Issues

#### Issue: High Rejection Rate

**Symptoms:** Most requests rejected by moral filter.

**Debug:**

```python
wrapper = LLMWrapper(...)
state = wrapper.get_state()
print(f"Threshold: {state['moral_threshold']}")
print(f"Rejected: {state['rejected_count']}/{state['step']}")
```

**Solutions:**

- Lower `initial_moral_threshold` (default 0.50)
- Check moral_value scoring function
- Verify moral values are in [0.0, 1.0]

#### Issue: Sleep Phase Rejections

**Symptoms:** Requests rejected during sleep phase.

**Debug:**

```python
state = wrapper.get_state()
print(f"Phase: {state['phase']}, Step: {state['step']}")
```

**Solution:** Wait for wake phase or adjust `wake_duration`/`sleep_duration`.

#### Issue: Memory Not Growing

**Symptoms:** PELM reports 0 entries after many requests.

**Debug:**

```python
state = wrapper.get_state()
print(f"PELM used: {state['qilm_stats']['used']}")
print(f"PELM capacity: {state['qilm_stats']['capacity']}")
```

**Solutions:**

- Verify embedding function returns valid `np.ndarray`
- Check embedding dimension matches `dim` parameter

#### Issue: Aphasia Detection Triggering Unexpectedly

**Symptoms:** Valid responses flagged as aphasic.

**Debug:**

```python
from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector

detector = AphasiaBrocaDetector()
analysis = detector.analyze(response_text)
print(analysis)
```

**Check:**

- `avg_sentence_len` ≥ 6
- `function_word_ratio` ≥ 0.15
- `fragment_ratio` ≤ 0.5

### Enabling Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LOG_LEVEL=DEBUG
```

### Inspecting Full State

```python
import json

wrapper = LLMWrapper(...)
result = wrapper.generate(prompt, moral_value)

# Full state snapshot
state = wrapper.get_state()
print(json.dumps(state, indent=2, default=str))

# Response metadata
print(json.dumps(result, indent=2, default=str))
```

### Running Single Tests with Verbose Output

```bash
pytest tests/unit/test_llm_wrapper.py::test_basic_generation -v -s --tb=long
```

---

## PR Expectations

### Before Submitting

**Checklist:**

- [ ] Tests pass: `make test`
- [ ] Linting passes: `make lint`
- [ ] Type checking passes: `make type`
- [ ] Coverage ≥ 90% for new code
- [ ] Documentation updated if public API changed
- [ ] CHANGELOG.md updated for user-facing changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- Describe testing performed
- List any new tests added

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Changes are backwards compatible (or documented)
```

### Commit Message Format

```text
<type>: <short summary>

<detailed description if needed>

<issue reference if applicable>
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

**Example:**

```text
feat: Add Anthropic adapter for Claude models

Implements AnthropicAdapter supporting Claude 3 family.
Includes rate limiting and retry logic.

Closes #42
```

### Review Criteria

| Criterion | Expectation |
|-----------|-------------|
| **Correctness** | Code works as intended, handles edge cases |
| **Tests** | New code has tests, critical paths 100% covered |
| **Design** | Follows established patterns, no unnecessary complexity |
| **Documentation** | Public APIs documented, inline comments for complex logic |
| **Performance** | No regressions, measured if performance-critical |
| **Security** | Input validation, no secrets in code, reviewed for injection |

---

## Related Documentation

- [ARCHITECTURE_SPEC.md](../ARCHITECTURE_SPEC.md) — Full system architecture
- [ARCHITECTURE_HYGIENE_POLICY.md](ARCHITECTURE_HYGIENE_POLICY.md) — Rules for module placement and layer dependencies
- [docs/LLM_PIPELINE.md](LLM_PIPELINE.md) — LLM pipeline specification
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contribution guidelines
- [TESTING_GUIDE.md](../TESTING_GUIDE.md) — Comprehensive testing guide
- [API_REFERENCE.md](../API_REFERENCE.md) — Complete API documentation

---

**Document Status:** Production
**Review Cycle:** Per minor version
**Last Reviewed:** December 2025
**Next Review:** Version 1.3.0 release
