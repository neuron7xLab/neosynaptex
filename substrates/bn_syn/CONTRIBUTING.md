# Contributing Guide

## Quick Start

Welcome! BN-Syn follows rigorous engineering standards. This guide helps you contribute effectively.

## Anti-Drift Contract (Required)

- Canonical proof command is `bnsyn run --profile canonical --plot --export-proof`.
- Canonical artifact set is `emergence_plot.png`, `summary_metrics.json`, `run_manifest.json`.
- Changes are in-scope when they strengthen Result/Narrative/Audience vectors in README.
- Changes are drift when they obscure canonical command path or weaken reproducibility evidence.

## Development Workflow

### 1. Environment Setup

```bash
# Clone and setup
git clone https://github.com/neuron7x/bnsyn-phase-controlled-emergent-dynamics.git
cd bnsyn-phase-controlled-emergent-dynamics

# Install dev dependencies
make dev-setup

# Alternative: install a CI-compatible superset used by most jobs
python -m pip install -e ".[dev,test]"

# This installs:
# - Pre-commit hooks (ruff, mypy, pylint, pydocstyle, pytest-smoke, coverage)
# - Dev dependencies (pytest, hypothesis, bandit, pip-audit)
# - Package in editable mode
```

### 2. Make Your Changes

**Code Style Expectations:**
- **Type annotations:** All functions must have complete type hints (mypy --strict)
- **Docstrings:** NumPy-style docstrings required for all public APIs
- **Line length:** 100 characters (configured in pyproject.toml)
- **Imports:** Sorted with standard library → third-party → local
- **Error handling:** Use explicit `raise ValueError/TypeError/RuntimeError`, not bare `assert`

**Example:**
```python
def compute_variance(values: Float64Array, *, ddof: int = 1) -> float:
    """Compute sample variance.

    Parameters
    ----------
    values : Float64Array
        Input data array.
    ddof : int, optional
        Delta degrees of freedom (default: 1 for sample variance).

    Returns
    -------
    float
        Sample variance.

    Raises
    ------
    ValueError
        If values array is empty or ddof >= len(values).

    Examples
    --------
    >>> import numpy as np
    >>> compute_variance(np.array([1.0, 2.0, 3.0]))
    1.0
    """
    if len(values) == 0:
        raise ValueError("Cannot compute variance of empty array")
    if ddof >= len(values):
        raise ValueError(f"ddof={ddof} must be < len(values)={len(values)}")
    return float(np.var(values, ddof=ddof))
```

### 3. Testing

**Test Markers:**
- `@pytest.mark.smoke` — Fast tests (<1s each), run in CI
- `@pytest.mark.validation` — Slow statistical tests (>10s), run weekly

**Run tests:**
```bash
# Smoke tests (fast, CI path)
pytest -m "not validation"

# Determinism tests
pytest tests/test_determinism.py tests/test_properties_determinism.py -v

# Validation tests (slow)
pytest -m validation

# Single test file
pytest tests/test_adex_smoke.py -v

# With coverage
make coverage
```

**Test Guidelines:**
- Use `seed_all(42)` for reproducibility
- Test edge cases (empty arrays, zero values, boundary conditions)
- Property-based testing with Hypothesis for math operations
- Integration tests should be <5s on CI runners

### 4. Run Quality Checks

```bash
# Full check suite (format + lint + type check + tests + SSOT + security)
make check

# Individual checks
make format      # Auto-format with ruff
make lint        # Lint with ruff + pylint
make mypy        # Type check
make ssot        # Validate bibliography, claims, normative tags
make security    # Run gitleaks, pip-audit, bandit (JSON artifacts in artifacts/security/) using hash-locked requirements-lock.txt
make sbom        # Generate CycloneDX SBOM at artifacts/sbom/sbom.cdx.json using hash-locked requirements-sbom-lock.txt
make coverage    # Test with coverage report
```

**Pre-commit hooks run automatically on commit:**
- ruff format/lint
- mypy type checking
- pylint code quality
- pydocstyle docstring conventions
- pytest smoke tests
- coverage threshold

### 5. Claims & Evidence

**When adding scientific claims:**

1. Add citation to `bibliography/bnsyn.bib`:
   ```bibtex
   @article{AuthorYear,
     author = {Last, First and Other, Second},
     title = {Paper Title},
     journal = {Nature},
     year = {2024},
     volume = {123},
     pages = {456-789},
     doi = {10.1038/nature123456}
   }
   ```

2. Register claim in `claims/claims.yml`:
   ```yaml
   CLM-0001:
     statement: "Your scientific claim here"
     status: claimed  # or supported
     normative: true  # if this is a core design constraint
     bibkeys: [AuthorYear]
   ```

3. Reference in code/docs:
   ```python
   # docs/SPEC.md
   AdEx neuron model uses exponential spike mechanism [CLM-0001].
   ```

4. Validate:
   ```bash
   python -m scripts.validate_bibliography
   python -m scripts.validate_claims
   ```

## Before Creating a PR

1. Install dev environment:
   ```bash
   make dev-setup
   ```

2. Make your changes (following code style above)

3. Run all checks:
   ```bash
   make check
   ```

4. Verify coverage:
   ```bash
   make coverage
   ```

5. Test locally with Docker:
   ```bash
   docker build -t bnsyn-dev .
   docker run bnsyn-dev
   ```

## PR Checklist

See `.github/pull_request_template.md` — all items are REQUIRED.

## CI/CD Pipeline

All PRs must pass:
- **ssot**: bibliography, claims, normative tags, governed docs validation
- **dependency-consistency**: pyproject.toml validation, dependency resolution
- **quality**: ruff format/lint, mypy type checking
- **build**: package build + import check
- **docs-build**: Sphinx documentation build
- **tests-smoke**: pytest -m "not validation" with ≥85% coverage
- **benchmarks.yml** (tier=standard, profile=ci): determinism, dt-invariance, criticality benchmarks
- **gitleaks**: secret scanning
- **pip-audit**: dependency vulnerability scanning

See [CI_GATES.md](docs/CI_GATES.md) for exact commands.

## CI/CD Quality Gates

### Coverage Requirements
- **Minimum:** 85% line coverage (enforced by `--cov-fail-under=85`)
- **Reporting:** Codecov (authenticated upload with fallback artifacts)
- **Failure Mode:** If Codecov is unavailable, the local coverage threshold still enforces the gate

### Known CI Failure Modes
1. **Codecov Rate Limit (HTTP 429)**
   - **Root Cause:** Anonymous upload without token
   - **Resolution:** Ensure `CODECOV_TOKEN` secret is configured
   - **Fallback:** Coverage artifacts still uploaded to GitHub Actions

2. **Determinism Test Flakiness**
   - **Detection:** Multiple runs with different results
   - **Mitigation:** `PYTHONHASHSEED=0` and RNG isolation tests

## Common Tasks

### Adding a New Module

1. Create module in `src/bnsyn/`
2. Add `__init__.py` with public API exports
3. Write tests in `tests/test_<module>_smoke.py`
4. Add docstrings (NumPy style)
5. Update docs if user-facing
6. Run `make check`

### Updating Dependencies

```bash
# Add to pyproject.toml [project.dependencies] or [project.optional-dependencies]
# Then:
pip install -e ".[dev]"
make check
```

### Debugging Test Failures

```bash
# Verbose output
pytest tests/test_foo.py -v --tb=long

# Stop on first failure
pytest tests/test_foo.py -x

# Print statements (disable capture)
pytest tests/test_foo.py -s

# Run specific test
pytest tests/test_foo.py::test_bar -v
```

## Architecture Guidelines

**Component Boundaries (SPEC.md):**
- P0-1: RNG system (bnsyn.rng)
- P1-1: AdEx neuron (bnsyn.neuron.adex)
- P1-2: Conductance synapses (bnsyn.synapse.conductance)
- P1-3: Three-factor plasticity (bnsyn.plasticity.three_factor)
- P2-4: Criticality control (bnsyn.criticality)
- P2-5: Temperature scheduling (bnsyn.temperature)
- P2-6: Synaptic consolidation (bnsyn.consolidation)
- P2-7: Energy accounting (bnsyn.energy)
- P2-8: Numerics (bnsyn.numerics)
- P2-9: Calibration (bnsyn.calibration)
- P2-10: Reference simulator (bnsyn.simulation)
- P2-11: Network simulator (bnsyn.sim.network)
- P2-12: CLI (bnsyn.cli)

**Design Principles:**
- **Determinism-first:** All randomness through explicit RNG injection
- **Immutability:** Use frozen dataclasses for configuration
- **Type safety:** mypy strict mode, no `Any` unless necessary
- **Modularity:** Clear component boundaries per SPEC.md
- **Testability:** Pure functions where possible, dependency injection

## Questions?

- **Documentation:** [docs/INDEX.md](docs/INDEX.md)
- **Specification:** [docs/SPEC.md](docs/SPEC.md)
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Issues:** [GitHub Issues](https://github.com/neuron7x/bnsyn-phase-controlled-emergent-dynamics/issues)
