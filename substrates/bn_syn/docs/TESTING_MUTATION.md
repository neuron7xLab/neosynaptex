See also: `docs/MUTATION_GATE.md` for the canonical mutation gate contract.

# Testing Guide for BNsyn

This document describes the testing infrastructure and protocols for the BNsyn project.

## Test Categories

### 1. Unit Tests (Fast, PR-Blocking)
- **Marker**: No marker or `@pytest.mark.smoke`
- **Run with**: `make test` or `pytest -m "not validation"`
- **Coverage requirement**: ≥85%
- **Purpose**: Fast critical-path tests that run on every PR

### 2. Validation Tests (Slow, Non-Blocking)
- **Marker**: `@pytest.mark.validation`
- **Run with**: `make test-validation` or `pytest -m validation`
- **Purpose**: Slow statistical/large-N validation tests
- **Location**: `tests/validation/`
- **Schedule**: Nightly only

### 3. Property Tests (Hypothesis-Based)
- **Marker**: `@pytest.mark.property`
- **Run with**: `pytest -m property`
- **Profiles**: `quick` (100 examples), `thorough` (1000 examples), `ci-quick` (50 examples)
- **Purpose**: Exhaustive property-based testing across parameter spaces
- **Schedule**: Nightly at 2:30 AM UTC (non-blocking)

### 4. Chaos Tests (Fault Injection)
- **Marker**: `@pytest.mark.chaos` (must also have `@pytest.mark.validation`)
- **Run with**: `pytest -m "validation and chaos"`
- **Purpose**: Test system resilience under fault injection (NaN, inf, timing jitter, I/O failures)
- **Location**: `tests/validation/test_chaos_*.py`
- **Schedule**: Nightly at 4 AM UTC (non-blocking)

### 5. Determinism Tests
- **Run with**: `make test-determinism`
- **Purpose**: Verify all code paths use deterministic RNG via `bnsyn.rng.seed_all()`
- **Critical**: A1 Axiom compliance

## Mutation Testing

Mutation testing verifies that our test suite can detect intentional bugs (mutants) in the code.

### Quick Start

```bash
# Establish baseline (first time or after major changes)
# This runs mutmut and generates quality/mutation_baseline.json
make mutation-baseline

# Check against baseline
# This runs mutmut and compares score to baseline
make mutation-check
```

`make mutation-baseline` and `make mutation-check` install the test extras
(`.[test]`) alongside `mutmut==2.4.5` to ensure the test suite runs cleanly.
Mutation runs exclude tests marked `benchmark` to keep baseline generation
bounded and deterministic.

### How It Works

1. **Generate baseline**: `scripts/generate_mutation_baseline.py` runs mutmut, extracts real counts/scores, and writes factual `quality/mutation_baseline.json`
2. **Check score**: `scripts/check_mutation_score.py` compares current mutation score against baseline with tolerance
3. **CI enforcement**: `.github/workflows/quality-mutation.yml` runs nightly and fails if score drops below threshold

### Baseline Protocol

The baseline is stored in `quality/mutation_baseline.json` and includes:
- **baseline_score**: Target mutation score percentage (derived from actual mutmut run)
- **tolerance_delta**: Acceptable variance (default: ±5%)
- **config**: Tool version, Python version, commit SHA, test command
- **metrics**: Total mutants, killed, survived, timeout counts (all non-zero, factual)
- **metrics_per_module**: Per-module mutation statistics
- **history**: Historical scores for tracking trends

### Updating the Baseline

**When to update**:
1. After adding significant new tests
2. After improving test quality
3. After removing dead code

**Protocol**:
1. Run `make mutation-baseline`
2. Review the mutation report:
   ```bash
   mutmut results
   mutmut show <id>  # Inspect specific surviving mutants
   ```
3. Update `quality/mutation_baseline.json`:
   - Update `baseline_score` if score improved
   - Add entry to `history` with date, score, commit, and comment
   - Update `metrics_per_module` if available
   - Update `config.commit_sha` to current commit
4. Commit the updated baseline with a descriptive message
5. **Never lower the baseline without justification** (comment required in history)

### Interpreting Results

**Good mutants to survive** (acceptable):
- Logging/debug statements
- Error message strings
- Performance optimizations that don't change behavior

**Bad mutants to survive** (fix tests):
- Logic changes (e.g., `<` to `<=`)
- Arithmetic operations
- Boundary conditions
- Return values

### Mutation Workflow (CI)

The `.github/workflows/quality-mutation.yml` workflow:
- Runs nightly at 3 AM UTC
- Can be triggered manually via `workflow_dispatch`
- Fails if `score < baseline_score - tolerance_delta`
- Uploads mutation report artifacts

## Chaos Engineering Tests

Located in `tests/validation/test_chaos_*.py`, these tests inject controlled faults to verify resilience:

1. **Numeric Faults** (`test_chaos_numeric.py`): NaN/inf injection
2. **Timing Faults** (`test_chaos_timing.py`): dt jitter
3. **Stochastic Faults** (`test_chaos_stochastic.py`): RNG perturbation
4. **I/O Faults** (`test_chaos_io.py`): Simulated I/O failures

All chaos tests are:
- **Deterministic**: Use explicit seeding via `FaultConfig`
- **Non-blocking**: Run nightly only
- **Marked** with `@pytest.mark.validation`

### Chaos Workflow

The `.github/workflows/ci-validation.yml` workflow (mode: `chaos`):
- Runs nightly at 4 AM UTC
- Can run specific fault types via `chaos_subset` input
- Includes property-based tests with thorough profile (1000 examples)

## Formal Verification

### TLA+ Model Checking

Located in `specs/tla/`, the TLA+ specification verifies critical invariants:

1. **TempMonotone**: Temperature decreases during cooling
2. **GateSoundness**: Plasticity gate correlates with temperature
3. **SigmaClamp**: Criticality σ stays within bounds
4. **PhaseConsistency**: Valid state machine transitions
5. **GateTemperatureCorrelation**: Gate open during consolidation

**Run locally**:
```bash
cd specs/tla
wget https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar
java -jar tla2tools.jar -config BNsyn.cfg BNsyn.tla
```

**Workflow**: `.github/workflows/formal-tla.yml`
- Runs nightly at 2 AM UTC
- Verifies SHA256 of TLA+ tools (supply chain security)
- Uses `max_steps` input parameter for model checking depth
- Status: `VERIFIED`, `VIOLATED`, `NOT_PROVEN`, `NOT_CHECKED`

### Coq Proofs

Located in `specs/coq/`, the Coq specification provides theorem proving:
- **Status**: Scaffold with proof obligations documented
- **Future work**: Implement formal proofs

## Running Tests Locally

```bash
# All fast tests (PR blocking)
make test

# Specific test types
pytest tests/test_adex_smoke.py -v
pytest -m property --hypothesis-profile=quick
pytest -m validation -k "chaos"

# Determinism verification
make test-determinism

# Coverage
make coverage

# Full quality check (includes linting, typing, security)
make check
```

## Hypothesis Profiles

Configured in `tests/conftest.py`:

- **quick**: 100 examples, 5s deadline (default for local)
- **thorough**: 1000 examples, 20s deadline (nightly property tests)
- **ci-quick**: 50 examples, 5s deadline (CI, if needed)

**Priority**: Explicit `HYPOTHESIS_PROFILE` env var overrides CI mode.

Set via environment variable:
```bash
# Use thorough profile (1000 examples)
HYPOTHESIS_PROFILE=thorough pytest -m property

# CI mode (if HYPOTHESIS_PROFILE not set)
CI=1 pytest -m property  # Uses ci-quick profile
```

**Property test decorators**: Do NOT override `max_examples` in `@settings()` - let profiles control runtime.

## Best Practices

1. **Always use `bnsyn.rng.seed_all()`** for any randomness
2. **Mark validation tests** with `@pytest.mark.validation`
3. **Mark chaos tests** with both `@pytest.mark.validation` and `@pytest.mark.chaos`
4. **Keep unit tests fast** (<10 minutes total)
5. **Write property tests** for universal invariants (no `max_examples` overrides)
6. **Write chaos tests** that test real BN-Syn runtime, not just fault injectors
7. **Document mutation survivors** that are acceptable
8. **Update baselines** only after regenerating with `make mutation-baseline`
7. **Review chaos test failures** carefully (may indicate real bugs)

## Troubleshooting

### Mutation Testing Hangs
- Increase timeout in baseline config
- Check for infinite loops in mutated code
- Use `mutmut run --no-progress` for debugging

### Property Tests Fail Non-Deterministically
- Ensure using `bnsyn.rng` not `random` or `np.random`
- Check `derandomize=True` in Hypothesis settings
- Verify seed propagation in test fixtures

### Chaos Tests Flake
- All chaos tests should use explicit `FaultConfig(seed=X)`
- Report flakes immediately (violates determinism requirement)
- Check for global state mutation

## References

- **A1 Axiom (Determinism)**: All tests must be deterministic
- **SPEC.md**: System specification
- **SSOT.md**: Single Source of Truth documentation
- **REPRODUCIBILITY.md**: Reproducibility protocol
