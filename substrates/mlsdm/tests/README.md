# MLSDM Test Suite

This directory contains the comprehensive test suite for the MLSDM (Multi-Level Synaptic Dense Memory) governed cognitive memory framework.

## Test Structure Overview

```
tests/
├── README.md              # This file - test documentation
├── conftest.py            # Shared pytest fixtures and configuration
├── __init__.py
├── utils/                 # Shared test utilities
│   ├── __init__.py
│   ├── factories.py       # Test object factories
│   ├── mocks.py           # Mock objects for LLM/embedding
│   └── fixtures.py        # Reusable test fixtures
├── unit/                  # Unit tests (~600 tests)
├── integration/           # Integration tests
├── property/              # Property-based tests (Hypothesis)
├── security/              # Security and robustness tests
├── e2e/                   # End-to-end tests
├── validation/            # Effectiveness validation tests
├── eval/                  # Evaluation suites (Sapolsky, Aphasia)
├── benchmarks/            # Performance benchmarks
├── load/                  # Load testing (Locust)
├── extensions/            # Extension-specific tests (NeuroLang)
├── observability/         # Observability and logging tests
├── speech/                # Speech governance tests
├── core/                  # Core component tests
├── scripts/               # Test script validation
└── packaging/             # Package distribution tests
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)
Fast, isolated tests for individual components:
- **Memory Systems**: `test_pelm.py`, `test_qilm_module.py`, `test_qilm_v2.py`
- **Moral Filter**: `test_moral_filter.py`
- **Cognitive Controller**: `test_cognitive_controller.py`
- **LLM Wrapper**: `test_llm_wrapper_reliability.py`, `test_llm_router.py`
- **API Components**: `test_api_health.py`, `test_input_validator.py`
- **Observability**: `test_observability_logger.py`, `test_metrics_registry.py`
- **Security**: `test_rate_limiter.py`, `test_security_logger.py`

### 2. Integration Tests (`tests/integration/`)
Tests for component interaction and real-world scenarios:
- LLM adapter integration
- API with backend integration
- Neuro cognitive engine pipelines

### 3. Property-Based Tests (`tests/property/`)
Hypothesis-based invariant verification:
- **Memory Invariants**: Capacity bounds, dimension consistency
- **Moral Filter Properties**: Threshold bounds, drift resistance
- **Engine Properties**: Response schema, timeout guarantees

### 4. Security Tests (`tests/security/`)
Security and robustness validation:
- Secure mode functionality
- Privacy in logging (no PII)
- Checkpoint security
- Configuration hardening

### 5. E2E Tests (`tests/e2e/`)
End-to-end pipeline tests with stub backends.

### 6. Validation Tests (`tests/validation/`)
Effectiveness validation with statistical analysis:
- Moral filter effectiveness
- Aphasia detection accuracy
- Wake/sleep rhythm behavior

### 7. Evaluation Suites (`tests/eval/`)
Domain-specific evaluation:
- Sapolsky validation suite
- Aphasia evaluation corpus
- A/B testing framework
- Canary deployment manager

## Running Tests

### Full Test Suite
```bash
# Run all tests (recommended for CI)
pytest tests/ -v --tb=short

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### By Category
```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Property-based tests
pytest tests/property/ -v

# Security tests
pytest tests/security/ -v -m security

# E2E tests
pytest tests/e2e/ -v
```

### By Marker
```bash
# Slow tests only
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Security-focused tests
pytest -m security

# Property tests
pytest -m property

# Integration tests
pytest -m integration
```

## Test Markers

The following pytest markers are available:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.slow` | Tests that take >5 seconds |
| `@pytest.mark.integration` | Integration tests requiring multiple components |
| `@pytest.mark.unit` | Fast, isolated unit tests |
| `@pytest.mark.property` | Property-based tests using Hypothesis |
| `@pytest.mark.security` | Security and robustness tests |
| `@pytest.mark.benchmark` | Performance benchmark tests |

## Coverage Requirements

- **Minimum coverage**: 90% (enforced in CI)
- **Critical paths**: 95%+ coverage expected
- **Coverage report**: Generated in `htmlcov/` directory

## Key Components Tested

### Critical Core Components
| Component | Test Files | Coverage |
|-----------|------------|----------|
| PhaseEntangledLatticeMemory (PELM) | `test_pelm.py`, `test_invariants_memory.py` | ✅ Full |
| MoralFilter/MoralFilterV2 | `test_moral_filter.py`, `test_moral_filter_properties.py` | ✅ Full |
| CognitiveController | `test_cognitive_controller.py`, `test_cognitive_controller_integration.py` | ✅ Full |
| CognitiveRhythm | `test_rhythm_state_machine.py` | ✅ Full |
| NeuroCognitiveEngine | `test_neuro_cognitive_engine.py`, `test_invariants_neuro_engine.py` | ✅ Full |
| LLMWrapper/Router | `test_llm_wrapper_reliability.py`, `test_llm_router.py` | ✅ Full |
| HTTP API | `test_api_health.py`, `test_neuro_engine_http_api.py` | ✅ Full |
| Adapters | `test_provider_factory.py`, `test_api_with_adapters.py` | ✅ Full |

### Safety Components
| Component | Test Files | Coverage |
|-----------|------------|----------|
| Moral Threshold Stability | `test_moral_filter_properties.py` | ✅ Full |
| Aphasia Detection | `test_aphasia_detection.py`, `test_aphasia_edge_cases.py` | ✅ Full |
| Secure Mode | `test_secure_mode.py` | ✅ Full |
| Privacy Logging | `test_aphasia_logging_privacy.py` | ✅ Full |
| Rate Limiting | `test_rate_limiter.py` | ✅ Full |

## CI/CD Integration

### Mandatory Gates (merge blockers)
1. All unit tests pass
2. All integration tests pass
3. All property tests pass
4. All security tests pass
5. Coverage ≥ 90%

### Quality Gates
1. Linting (ruff)
2. Type checking (mypy)
3. Security scanning

## Writing New Tests

### Style Guidelines
1. Use pytest-style tests (functions or classes)
2. Use descriptive test names: `test_<what>_<scenario>_<expected>`
3. Use fixtures from `conftest.py` for common setup
4. Add docstrings explaining test purpose
5. Use fixed random seeds for reproducibility

### Example Test Structure
```python
"""
Tests for ComponentName functionality.
"""
import pytest
from mlsdm.module import Component

class TestComponentBasic:
    """Basic functionality tests."""

    def test_initialization_with_defaults(self):
        """Test component initializes with default parameters."""
        comp = Component()
        assert comp.param == expected_default

    def test_operation_normal_case(self, sample_fixture):
        """Test normal operation with valid input."""
        result = comp.operation(sample_fixture)
        assert result is not None

class TestComponentEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_input_handling(self):
        """Test component handles empty input gracefully."""
        comp = Component()
        result = comp.operation([])
        assert result == expected_empty_result
```

### Using Shared Utilities
```python
from tests.utils.factories import create_test_vector, create_mock_llm
from tests.utils.fixtures import deterministic_seed

def test_with_utilities(deterministic_seed):
    """Test using shared utilities."""
    vector = create_test_vector(dim=384)
    llm = create_mock_llm(response="test")
    # ... test logic
```

## Troubleshooting

### Common Issues

1. **Flaky tests**: Ensure deterministic seeds are used
2. **Slow tests**: Mark with `@pytest.mark.slow`
3. **Import errors**: Check that `src/` is in PYTHONPATH
4. **Coverage misses**: Ensure tests exercise all branches

### Debug Mode
```bash
# Run with verbose output
pytest tests/path/to/test.py -v -s

# Run single test
pytest tests/path/to/test.py::TestClass::test_method -v

# With debugger on failure
pytest tests/path/to/test.py --pdb
```

## Maintainers

- Repository: `neuron7xLab/mlsdm`
- Test Architecture: Principal Test Architect

## Document History

- **2025-11-25**: Initial comprehensive test documentation
- See `TESTING_STRATEGY.md` for detailed methodology
