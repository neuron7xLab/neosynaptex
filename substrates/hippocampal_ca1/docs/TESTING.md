# Testing Guide

Complete testing documentation for CA1 Hippocampus Framework.

## Security Gates (required for merge)

- **Unicode scan**: `python scripts/unicode_scan.py`
- **Secrets scan (gitleaks)**: `gitleaks detect --config .gitleaks.toml --report-format sarif --report-path gitleaks.sarif`
- **Dependency audit (pip-audit)**: `pip install pip-audit==2.7.3 && pip-audit -r requirements.txt && pip-audit -r requirements-dev.txt`
- **Pre-commit PEP8 & lint**: `pre-commit install && pre-commit run --all-files` (black, flake8, unicode scan, gitleaks)
- **Actionlint**: Download actionlint v1.7.9 and run `actionlint .github/workflows/*.yml` (ensure the binary is on your PATH or reference its full location)
- **Config validation**: `pip install PyYAML==6.0.2 && python scripts/validate_configs.py .`
- **CI policy check**: `pip install PyYAML==6.0.2 && python scripts/ci_policy_check.py`
- **PR metadata check**: Ensure the PR body includes either `Phase: X.Y` or `Closes #123`, and also contains a `Verification:` section with commands executed (use the PR template).

## Test Suite Overview

```
tests/
├── test_ca1_network_api.py      # Public API smoke tests
├── test_golden_suite.py         # Imports validation/golden_tests (6 checks)
├── test_hierarchical_laminar.py # Unit tests for inference
├── test_memory_module.py        # Unit tests for AI integration
├── test_theta_swr_switching.py  # Unit tests for state switching/replay
└── test_unified_weights.py      # Plasticity unit tests
```

## Quick Start

### Run All Tests

```bash
# Golden tests (must pass)
python test_golden_standalone.py

# Unit tests (including golden suite)
python -m pytest -q
```

## Golden Tests (Seed=42)

**Critical**: These tests MUST pass with exact numerical values.

### Test 1: Network Stability

```python
def test_network_stability():
    # Create UnifiedWeightMatrix
    W = UnifiedWeightMatrix(connectivity, weights, sources, params)
    
    # Simulate
    for _ in range(50):
        W.update_stp(spikes_pre, spikes_post)
        W.update_calcium(spikes_pre, spikes_post, V_dend)
    
    # Enforce stability
    W.enforce_spectral_constraint(rho_target=0.95)
    
    # Validate
    assert stats['spectral_radius'] < 1.0  # MUST PASS
```

**Expected output** (seed=42):
```
ρ(W) = 0.950 < 1.0  ✓
W_eff mean = 0.181
Ca mean = 2.069 μM
```

### Test 2: Ca²⁺ Plasticity

```python
def test_calcium_plasticity():
    # High Ca → LTP
    W.Ca[0, 1] = 2.5  # > θ_p = 2.0
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))
    assert delta_ltp > 0.0001  # MUST INCREASE
    
    # Medium Ca → LTD
    W.Ca[0, 1] = 1.5  # θ_d < Ca < θ_p
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))
    assert delta_ltd < 0  # MUST DECREASE
```

**Expected output** (seed=42):
```
LTP: ΔW = +0.0895  ✓
LTD: ΔW = -0.0050  ✓
```

### Test 3: Input-Specific Plasticity

```python
def test_input_specific():
    # Same Ca at CA3 and EC synapses
    W.Ca[0, 1] = 2.5  # CA3
    W.Ca[0, 2] = 2.5  # EC
    
    # Run plasticity
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))
    
    # EC should change 10x less
    ratio = delta_ca3 / (delta_ec + 1e-10)
    assert ratio > 5.0  # MUST PASS
```

**Expected output** (seed=42):
```
CA3: ΔW = 0.0895
EC:  ΔW = 0.0089
Ratio: 10.06  ✓
```

### Test 4: Theta-SWR Switching

```python
def test_theta_swr():
    controller = NetworkStateController(params)
    
    # Simulate 10 seconds
    for _ in range(100000):
        state, _ = controller.step()
        # Track time in each state
    
    # Validate
    assert 0.7 <= theta_frac <= 0.95  # Theta dominant
    assert controller.get_inhibition_factor() < 1.0  # SWR reduces inh
    assert controller.get_recurrence_factor() > 1.0  # SWR boosts rec
```

**Expected output** (seed=42):
```
Theta: 90.6%  ✓
SWR inhibition: 0.50  ✓
SWR recurrence: 2.00  ✓
```

### Test 5: Reproducibility

```python
def test_reproducibility():
    W1 = run_simulation(seed=42)
    W2 = run_simulation(seed=42)
    
    diff = np.max(np.abs(W1 - W2))
    assert diff < 1e-10  # EXACT MATCH
```

**Expected output**:
```
Max diff: 0.0000e+00  ✓
```

## Unit Tests

### Testing UnifiedWeightMatrix

```python
# tests/test_unified_weights.py
import pytest
import numpy as np
from plasticity.unified_weights import UnifiedWeightMatrix

class TestUnifiedWeights:
    def setup_method(self):
        self.N = 10
        self.connectivity = np.eye(self.N, k=1, dtype=bool)
        # ... setup
    
    def test_effective_weights_shape(self):
        W = UnifiedWeightMatrix(...)
        W_eff = W.get_effective_weights()
        assert W_eff.shape == (self.N, self.N)
    
    def test_stp_bounds(self):
        W = UnifiedWeightMatrix(...)
        W.update_stp(spikes_pre, spikes_post)
        assert np.all(0 <= W.u) and np.all(W.u <= 1)
        assert np.all(0 <= W.R) and np.all(W.R <= 1)
    
    def test_calcium_nonnegative(self):
        W = UnifiedWeightMatrix(...)
        W.update_calcium(spikes_pre, spikes_post, V_dend)
        assert np.all(W.Ca >= 0)
```

### Testing HierarchicalLaminar

```python
# tests/test_hierarchical_laminar.py
def test_layer_assignment_valid():
    model = HierarchicalLaminarModel()
    q = model.fit_em_vectorized(cells, max_iter=10)
    assignments = model.assign_layers(cells, q)
    
    assert len(assignments) == len(cells)
    assert np.all((0 <= assignments) & (assignments < 4))

def test_mrf_improves_coherence():
    model_mrf = HierarchicalLaminarModel(lambda_mrf=0.5)
    model_no_mrf = HierarchicalLaminarModel(lambda_mrf=0.0)
    
    coherence_mrf = compute_coherence(...)
    coherence_no_mrf = compute_coherence(...)
    
    assert coherence_mrf > coherence_no_mrf
```

## Integration Tests

```python
# tests/test_integration.py
def test_full_pipeline():
    # 1. Create network
    params = get_default_parameters()
    W = UnifiedWeightMatrix(...)
    pop = CA1Population(...)
    controller = NetworkStateController(...)
    
    # 2. Simulate 1000ms
    for step in range(10000):
        state, _ = controller.step()
        spikes = pop.step(...)
        W.update_stp(...)
        W.update_calcium(...)
        if step % 10 == 0:
            W.update_plasticity_ca_based(...)
    
    # 3. Validate
    assert controller state machine worked
    assert spikes generated
    assert weights changed appropriately
```

## Coverage Requirements

Minimum coverage: **95%** across the core packages (`core`, `plasticity`, `ai_integration`, `validation`); critical paths must remain at 100%.

```bash
python -m pytest tests/ \
  --cov=core --cov=plasticity --cov=ai_integration --cov=validation \
  --cov-report=term-missing --cov-fail-under=95
```

**Note**: Current legacy baseline coverage is ~39%; reaching the 95% target will require additional test authoring beyond the existing suite.

**Critical paths** (must have 100% coverage):
- `UnifiedWeightMatrix.update_plasticity_ca_based`
- `NetworkStateController.step`
- `HierarchicalLaminarModel.fit_em_vectorized`

## Continuous Integration

Tests run automatically on:
- Every push to main
- Every pull request
- Nightly builds

See `.github/workflows/tests.yml`

## Performance Testing

```bash
python scripts/benchmark.py                 # Default reference benchmarks
python scripts/benchmark.py --stress-neurons 100000 --stress-steps 5 --stress-conn-prob 1e-4
```

Expected performance (reference machine):
```
Laminar EM (1000 cells): < 2.5s
Weight update (10K synapses): < 60ms
Full simulation (100 neurons, 1s): < 6s
Sparse stress test (100K neurons, p=1e-4, 5 steps): < 15s, < 200 MB
```

## Debugging Failed Tests

### Golden Test Fails

1. **Check seed**: Must be 42
2. **Check dependencies**: `pip install -r requirements.txt`
3. **Check NumPy version**: Should be ≥ 1.24
4. **Platform differences**: Run on Linux for exact match

### Unit Test Fails

1. **Check error message**: Often indicates parameter mismatch
2. **Run single test**: `pytest tests/test_file.py::test_name -v`
3. **Add print statements**: Temporary debugging
4. **Check golden tests first**: If those fail, fix first

## Writing New Tests

### Template

```python
import pytest
import numpy as np

def test_my_feature():
    """
    Test description.
    
    Expected behavior: ...
    Reference: DOI if applicable
    """
    # Setup
    np.random.seed(42)
    
    # Execute
    result = my_function(params)
    
    # Validate
    assert result meets expectations
    assert no side effects
```

### Best Practices

1. **Always set seed**: `np.random.seed(42)`
2. **Test edge cases**: Zero, negative, boundary values
3. **Test invariants**: e.g., W ∈ [W_min, W_max]
4. **Clear assertions**: Use meaningful error messages
5. **Docstrings**: Explain what is being tested

## Test Data

Test data is **generated programmatically** (no external files needed).

Example:
```python
def generate_test_cells(N=1000, seed=42):
    np.random.seed(seed)
    cells = []
    for i in range(N):
        z = np.random.rand()
        layer = min(int(z * 4), 3)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)
        cells.append(CellDataHier(...))
    return cells
```

## Troubleshooting

### Common Issues

**Issue**: Tests pass locally but fail in CI  
**Solution**: Check Python version, dependencies, random seed

**Issue**: Numerical differences across platforms  
**Solution**: Use tolerance in assertions (but golden tests must match exactly)

**Issue**: Tests are slow  
**Solution**: Use smaller N for unit tests, reserve large N for integration

---

**Last updated**: December 14, 2025
