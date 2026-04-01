# Troubleshooting Guide

This guide covers common issues and their solutions when working with BN-Syn.

## Installation Issues

### `ModuleNotFoundError: No module named 'bnsyn'`

**Cause:** Package not installed or virtual environment not activated.

**Solution:**
```bash
# Install in editable mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev,test]"

# Verify installation
python -c "import bnsyn; print(bnsyn.__version__)"
```

### `ImportError: JAX is not installed`

**Cause:** Trying to use JAX backend without JAX installed.

**Solution:**
```bash
# Install JAX (CPU only)
pip install -e ".[jax]"

# Or for GPU (CUDA 12)
pip install "jax[cuda12]"
```

### `RuntimeError: PyTorch not available`

**Cause:** Using torch backend without PyTorch installed.

**Solution:**
```bash
pip install -e ".[torch]"

# Or directly
pip install torch
```

### `RuntimeError: Visualization requires matplotlib`

**Cause:** Trying to use visualization features without matplotlib.

**Solution:**
```bash
pip install -e ".[viz]"
```

## Test Failures

### Tests pass locally but fail in CI

**Common causes:**
1. **Different Python versions** — CI uses Python 3.11, check your local version
2. **Non-deterministic tests** — Ensure all RNGs are seeded via `seed_all(seed)`
3. **Platform-specific behavior** — CI runs on Ubuntu, may differ from macOS/Windows

**Debug steps:**
```bash
# Check Python version
python --version

# Run tests with same markers as CI
pytest -m "not validation" -v

# Check for determinism
pytest tests/test_determinism.py -v

# Run in Docker (matches CI environment)
docker build -t bnsyn-dev .
docker run bnsyn-dev
```

### `AssertionError` in determinism tests

**Cause:** Non-deterministic behavior or floating-point precision issues.

**Check:**
1. All random operations use `numpy.random.Generator` from `seed_all()`
2. No hidden global RNG state in external libraries
3. Environment variable `PYTHONHASHSEED=0` is set
4. NumPy operations use consistent dtypes (float64)

**Solution:**
```python
from bnsyn.rng import seed_all

# Always seed at test start
rng = seed_all(42)

# Pass rng to all functions
result = my_function(data, rng=rng)
```

### Coverage below 85%

**Cause:** New code not adequately tested.

**Solution:**
```bash
# Generate coverage report
pytest -m "not validation" --cov=src/bnsyn --cov-report=html

# Open htmlcov/index.html to see uncovered lines
# Add tests for uncovered branches
```

### `mypy` type checking errors

**Common issues:**

1. **Missing return type annotation:**
   ```python
   # WRONG
   def compute_value(x):
       return x * 2
   
   # CORRECT
   def compute_value(x: float) -> float:
       return x * 2
   ```

2. **`Any` type usage:**
   ```python
   # WRONG
   def process(data: Any) -> Any:
       ...
   
   # CORRECT
   from numpy.typing import NDArray
   import numpy as np
   
   def process(data: NDArray[np.float64]) -> NDArray[np.float64]:
       ...
   ```

3. **Optional imports:**
   ```python
   # Use type checking guards
   from typing import TYPE_CHECKING
   
   if TYPE_CHECKING:
       import matplotlib.pyplot as plt
   ```

## Runtime Issues

### `ValueError: ddof must be < len(values)`

**Cause:** Computing variance/std with too few samples.

**Solution:** Check array sizes before statistical operations:
```python
if len(values) < 2:
    raise ValueError("Need at least 2 samples for variance")
```

### `LinAlgError: SVD did not converge`

**Cause:** Numerical instability in PCA/SVD operations.

**What BN-Syn does:** Falls back to previous PCA components (see logs).

**If persistent:** Check for NaN/Inf values in input data:
```python
if not np.isfinite(data).all():
    raise ValueError("Input contains NaN or Inf values")
```

### Memory errors with large networks

**Cause:** Network too large for available RAM.

**Solutions:**
1. Use sparse connectivity:
   ```python
   from bnsyn.connectivity import SparseConnectivity
   
   W = SparseConnectivity.random_sparse(
       nE=1000, nI=200, p_conn=0.1, format="sparse"
   )
   ```

2. Enable PyTorch backend for GPU:
   ```python
   network = Network(..., use_torch=True, torch_device="cuda")
   ```

3. Reduce network size or simulation duration

### `RuntimeError: Expected csr_matrix for sparse format`

**Cause:** Internal type consistency violation in sparse matrices.

**This should not happen** — If you see this, it's a bug. Please report with:
```bash
# Minimal reproduction script
# Stack trace
# BN-Syn version: python -c "import bnsyn; print(bnsyn.__version__)"
```

## SSOT Validation Failures

### `bibliography_gate FAILED: bibkey 'missing_ref_2026' not found`

**Cause:** Citation referenced in claims but not in bibliography.

**Solution:**
1. Add to `bibliography/bnsyn.bib`:
   ```bibtex
   @article{missing_ref_2026,
     author = {Example, Ada and Researcher, Lin},
     title = {Example Reference for Bibliography Troubleshooting},
     journal = {Journal of Example Systems},
     year = {2026},
     doi = {10.0000/example}
   }
   ```

2. Validate:
   ```bash
   python -m scripts.validate_bibliography
   ```

### `claims_gate FAILED: Claim CLM-0001 references missing bibkey`

**Cause:** Claim in `claims/claims.yml` references non-existent citation.

**Solution:**
1. Add citation to bibliography (see above)
2. OR update claim to use existing bibkey
3. Validate:
   ```bash
   python -m scripts.validate_claims
   ```

### `normative_gate FAILED: File docs/example_doc.md contains [CLM-0001] but not marked normative`

**Cause:** Document uses claim ID but lacks normative marker.

**Solution:** Add marker to document:
```markdown
<!-- NORMATIVE -->
# Document Title

Content with [CLM-0001] reference.
```

## CI/CD Issues

### Gitleaks secret detection false positive

**Cause:** Test data or commit message triggers secret pattern.

**Solution:** Add to `.gitleaks.toml`:
```toml
[[rules]]
id = "generic-api-key"
# ... existing config ...

[allowlist]
paths = [
  "tests/fixtures/test_data.json"  # Known test data
]
```

### pip-audit vulnerability in dependency

**Cause:** Known CVE in a transitive dependency.

**Solutions:**
1. **Upgrade dependency** in `pyproject.toml`
2. **Exclude if not applicable:**
   ```bash
   pip-audit --ignore-vuln GHSA-2vj6-8h5x-3v7x
   ```
3. **Open issue** to track mitigation

### Sphinx docs build failure

**Common causes:**
1. **Missing docstring** — Add NumPy-style docstring
2. **Syntax error in rst/md** — Check directive syntax
3. **Circular import** — Use `TYPE_CHECKING` guard

**Debug:**
```bash
# Build docs locally
sphinx-build docs docs/_build -v

# Check for warnings
sphinx-build docs docs/_build -W  # Treat warnings as errors
```

## Performance Issues

### Simulations are slow

**Optimizations:**
1. **Use compiled backends:**
   ```python
   # JAX backend (fastest)
   pip install -e ".[jax]"
   
   # PyTorch backend
   network = Network(..., use_torch=True)
   ```

2. **Profile hotspots:**
   ```python
   import cProfile
   cProfile.run("run_simulation(...)", "profile.stats")
   
   # Analyze
   python -m pstats profile.stats
   ```

3. **Reduce time resolution:**
   ```python
   # Instead of dt=0.1 ms
   dt = 0.5  # or 1.0 ms (verify dt-invariance tests still pass)
   ```

4. **Use sparse connectivity:**
   ```python
   W = SparseConnectivity.random_sparse(format="sparse")
   ```

### High memory usage

**Diagnostics:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory: {process.memory_info().rss / 1024**3:.2f} GB")
```

**Solutions:**
1. Reduce network size
2. Decrease simulation duration
3. Use sparse matrices
4. Clear intermediate results: `del result; gc.collect()`

## Getting Help

If none of the above solutions work:

1. **Check existing issues:** [GitHub Issues](https://github.com/neuron7x/bnsyn-phase-controlled-emergent-dynamics/issues)
2. **Search documentation:** [docs/INDEX.md](INDEX.md)
3. **Ask for help:** Open a new issue with:
   - Python version
   - BN-Syn version
   - Operating system
   - Minimal reproduction code
   - Full error traceback
   - What you've already tried

## Quick Reference

**Essential commands:**
```bash
# Setup
make dev-setup

# Run checks
make check               # All quality checks
make test                # Smoke tests only
make coverage            # Tests with coverage
make lint                # Ruff + pylint
make mypy                # Type checking
make ssot                # SSOT validation
make security            # Security scans

# Debug
pytest -v --tb=long      # Verbose test output
pytest -x                # Stop on first failure
pytest -s                # Show print statements
pytest -k "test_name"    # Run specific test

# Clean
make clean               # Remove cache files
```

**Common file locations:**
- Source: `src/bnsyn/`
- Tests: `tests/`
- Docs: `docs/`
- Config: `pyproject.toml`
- CI: `.github/workflows/`
- Bibliography: `bibliography/bnsyn.bib`
- Claims: `claims/claims.yml`
