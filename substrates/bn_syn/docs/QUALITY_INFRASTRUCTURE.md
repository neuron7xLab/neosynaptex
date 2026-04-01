See also: `docs/MUTATION_GATE.md` for the canonical mutation gate contract.

# Quality Infrastructure Index

This document provides a comprehensive overview of the BN-Syn quality infrastructure, including how to run each system locally, what artifacts prove correctness, and what CI jobs enforce what.

## Overview

The BN-Syn quality infrastructure consists of multiple layers:

1. **SSOT Gates** - Ensure single source of truth for bibliography, claims, and normative tags
2. **Governance Gates** - Verify CI workflows follow truthfulness principles and formal specs match code
3. **Property Testing** - Hypothesis-based testing for universal invariants
4. **Mutation Testing** - Measure test suite effectiveness
5. **Formal Verification** - TLA+ and Coq proofs for critical properties
6. **Chaos Engineering** - Fault injection for resilience testing
7. **Validation Tests** - Statistical and large-N tests for scientific claims

## Local Verification Commands

### Quick Check (Fast, PR-level)
```bash
# Pre-commit hooks
pre-commit run --all-files

# SSOT gates
python -m scripts.validate_bibliography
python -m scripts.validate_claims
python -m scripts.scan_governed_docs
python -m scripts.scan_normative_tags

# Governance gates (NEW)
python -m scripts.verify_formal_constants
python -m scripts.lint_ci_truthfulness --out artifacts/ci_truthfulness.json --md artifacts/ci_truthfulness.md

# Fast tests
pytest -m "not validation and not property" --cov=src/bnsyn --cov-fail-under=85

# Type checking
make mypy

# Linting
make lint
```

### Property Testing (Nightly)
```bash
# Quick profile (local testing)
pytest -m property --hypothesis-profile=quick --hypothesis-show-statistics

# Thorough profile (nightly CI)
HYPOTHESIS_PROFILE=thorough pytest -m property --hypothesis-show-statistics
```

### Mutation Testing (Nightly)
```bash
# Generate baseline (first time)
make mutation-baseline

# Check against baseline
make mutation-check

# Or use scripts directly
python -m scripts.generate_mutation_baseline
python -m scripts.check_mutation_score
```

### Formal Verification (Nightly)

#### TLA+ Model Checking
```bash
# Download TLC (if not cached)
cd specs/tla
wget https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar

# Verify checksum
echo "a6ece2e543c87e6e7d90d1c6e0cc04d57b1f08e6e7f4f4db08ebafdd8b39c53e  tla2tools.jar" | sha256sum -c -

# Run model checker
java -cp tla2tools.jar tlc2.TLC -config BNsyn.cfg BNsyn.tla

# Verify constants match code
python ../../scripts/verify_formal_constants.py
```

#### Coq Proofs
```bash
# Install Coq (if needed)
opam install coq.8.18.0

# Compile proofs
cd specs/coq
coqc BNsyn_Sigma.v

# Verify constants match code
python ../../scripts/verify_formal_constants.py
```

### Chaos Engineering (Nightly)
```bash
# Run all chaos tests
pytest -m "validation and chaos" -v

# Run integration chaos tests only
pytest tests/validation/test_chaos_integration.py -v

# Run specific fault type
pytest tests/validation/test_chaos_numeric.py -v
```

### Validation Tests (Nightly)
```bash
# Run all validation tests
pytest -m validation -v

# Run specific validation suite
pytest tests/validation/test_adex_validation.py -v
```

## CI Jobs and Enforcement

### PR CI (Blocking)

**Workflow**: `.github/workflows/ci-pr.yml`
**Trigger**: Every pull request and push to main
**Timeout**: 15 minutes

**Gates Enforced**:
- SSOT validation (bibliography, claims, normative tags)
- **Governance gates** (formal constants, CI truthfulness)
- Claims coverage (must be 100%)
- Fast tests (< 10 min)
- Type checking (mypy --strict)
- Linting (ruff, pylint)

**Artifacts Produced**:
- `claims_coverage.json` - Claims coverage report
- `governance-reports/ci_truthfulness.json` - CI truthfulness lint report
- `governance-reports/ci_truthfulness.md` - Human-readable lint report

**How to Debug Failures**:
```bash
# Reproduce locally
python -m scripts.validate_claims_coverage --format markdown
python -m scripts.verify_formal_constants
python -m scripts.lint_ci_truthfulness --md artifacts/ci_truthfulness.md
pytest -m "not validation and not property"
```

### Property Tests (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/ci-validation.yml` (mode: `property`)
**Trigger**: Nightly at 2:30 AM UTC, manual dispatch (mode: `property`)
**Timeout**: 30 minutes

**Tests Run**:
- Property-based tests with `quick` profile (100 examples by default)
- Hypothesis statistics enabled

**Artifacts Produced**:
- `property-test-results/.hypothesis/` - Hypothesis database
- Test results and logs

**How to Reproduce**:
```bash
HYPOTHESIS_PROFILE=ci pytest -m property -v --tb=short --hypothesis-show-statistics
```

### Mutation Testing (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/quality-mutation.yml`
**Trigger**: Nightly at 3 AM UTC, manual dispatch
**Timeout**: 120 minutes

**Process**:
1. Load baseline from `quality/mutation_baseline.json`
2. Run mutmut on critical modules
3. Compare score against baseline with tolerance
4. Fail if score drops below `baseline - tolerance`

**Artifacts Produced**:
- `mutation-logs-<sha>/mutation_results.txt` - Full mutmut results
- `mutation-logs-<sha>/survived_mutants.txt` - List of survivors
- `mutation-logs-<sha>/mutation_report.txt` - Score comparison

**How to Reproduce**:
```bash
make mutation-check
# Or generate new baseline
make mutation-baseline
```

### Formal Verification - TLA+ (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/formal-tla.yml`
**Trigger**: Nightly at 2 AM UTC, manual dispatch
**Timeout**: 30 minutes

**Invariants Checked**:
- `TypeOK` - Type correctness
- `GainClamp` - Criticality gain bounds [0.2, 5.0]
- `TemperatureBounds` - Temperature bounds [Tmin, T0]
- `GateBounds` - Plasticity gate [0, 1]
- `PhaseValid` - Valid phase transitions

**Artifacts Produced**:
- `tla-model-check-report-<sha>/tlc_output.txt` - Full TLC stdout
- `tla-model-check-report-<sha>/tla_summary.md` - Summary report

**Constants Verified**: See `specs/tla/README.md` for code-to-spec mapping

**How to Reproduce**:
```bash
cd specs/tla
java -cp tla2tools.jar tlc2.TLC -config BNsyn.cfg BNsyn.tla
```

### Formal Verification - Coq (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/formal-coq.yml`
**Trigger**: Nightly at 1 AM UTC, manual dispatch
**Timeout**: 20 minutes

**Proofs Verified**:
- `gain_clamp_preserves_bounds` - Gain clamping preserves [0.2, 5.0] bounds
- `clamp_idempotent` - Clamp is idempotent

**Artifacts Produced**:
- `coq-proof-verification-<sha>/coq_output_*.txt` - Compilation logs
- `coq-proof-verification-<sha>/coq_summary.md` - Proof summary

**Constants Verified**: `gain_min=0.2`, `gain_max=5.0` (matches `CriticalityParams`)

**How to Reproduce**:
```bash
cd specs/coq
coqc BNsyn_Sigma.v
```

### Chaos Engineering (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/ci-validation.yml` (mode: `chaos`)
**Trigger**: Nightly at 4 AM UTC, manual dispatch (mode: `chaos`)
**Timeout**: 60 minutes

**Fault Types Tested**:
- Numeric faults (NaN, inf injection into AdEx state)
- Timing faults (dt jitter)
- Stochastic faults (RNG perturbation)
- I/O faults (artifact corruption)

**Expected Behaviors**:
- Fail-fast on invalid dt
- Detect NaN/inf in state and raise ValueError
- Graceful degradation on mild dt jitter
- Deterministic fault injection (same seed → same outcome)

**Artifacts Produced**:
- `chaos-results-numeric-<sha>` - Numeric fault test logs
- `chaos-results-timing-<sha>` - Timing fault test logs
- `chaos-results-stochastic-<sha>` - Stochastic fault test logs
- `chaos-results-io-<sha>` - I/O fault test logs

**How to Reproduce**:
```bash
pytest -m "validation and chaos" -v
pytest tests/validation/test_chaos_integration.py -v
```

### Validation Tests (Non-Blocking, Nightly)

**Workflow**: `.github/workflows/ci-validation.yml` (mode: `elite`)
**Trigger**: Nightly at 2 AM UTC, manual dispatch (mode: `elite`)
**Timeout**: 30 minutes

**Tests Run**:
- Scientific validation tests (large-N, statistical)
- Empirical claim verification
- Long-running integration tests

**Artifacts Produced**:
- `validation-logs-<sha>/validation.log` - Full test output
- `validation-logs-<sha>/validation-junit.xml` - JUnit XML report
- `property-logs-<sha>/property.log` - Property test output with ci-quick profile

**How to Reproduce**:
```bash
pytest -m validation -v
```

## Governance Principles

### Truthful Verification
- **Never** use `|| true` to mask test failures
- Use `if: always()` on artifact upload steps instead
- Hard-coded success messages must be derived from actual outputs
- Workflow summaries computed from real test results

### PR CI Integrity
- PR checks must be fast (<15 min total)
- Heavy suites (validation, property, mutation, formal) run on schedule/dispatch
- Runtime budgets enforced and audited

### Fork-Safety & Least Privilege
- All workflows have explicit `permissions: contents: read` at minimum
- No secrets required for most workflows
- Write permissions guarded and minimized

### Supply Chain Integrity
- External tools pinned with SHA256 verification (TLA+ tools)
- Container images pinned by digest (Coq toolchain)
- Dependencies installed from locked requirements

### Determinism
- All randomness uses seeded RNG (`bnsyn.rng.seed_all()`)
- Chaos and property tests are deterministic
- Explicit reproducibility commands provided

### Evidence Traceability
- All claims backed by artifacts
- Docs contain reproducible commands
- Artifact uploads always enabled (`if: always()`)

## Maintenance

### Updating Baselines

**Mutation Baseline**:
```bash
# After improving tests
make mutation-baseline
git add quality/mutation_baseline.json
git commit -m "Update mutation baseline after test improvements"
```

**Property Test Examples**:
- Profiles control runtime (don't override `max_examples` in decorators)
- Update profiles in `pyproject.toml` if needed

### Adding New Invariants

**TLA+ Invariants**:
1. Add state predicate to `specs/tla/BNsyn.tla`
2. Add to `INVARIANTS` section in `specs/tla/BNsyn.cfg`
3. Document code mapping in `specs/tla/README.md`
4. Verify with `python -m scripts.verify_formal_constants`

**Coq Proofs**:
1. Add lemma/theorem to `specs/coq/BNsyn_Sigma.v`
2. Document code mapping in `specs/coq/README.md`
3. Compile: `coqc BNsyn_Sigma.v`
4. Verify constants: `python -m scripts.verify_formal_constants`

### Workflow Changes

**After modifying workflows**:
```bash
# Lint for truthfulness
python -m scripts.lint_ci_truthfulness --md artifacts/ci_truthfulness.md

# Check for violations
cat artifacts/ci_truthfulness.md

# Fix any errors (|| true, hard-coded summaries, unused inputs)
# Then re-lint to verify
```

## References

- **SSOT Rules**: `docs/SSOT_RULES.md`
- **CI Gates Policy**: `docs/CI_GATES.md`
- **Testing Guide**: `docs/TESTING_MUTATION.md`
- **TLA+ Spec**: `specs/tla/README.md`
- **Coq Spec**: `specs/coq/README.md`
- **Governance Gates**: This document (governance gate scripts in `scripts/`)

## Troubleshooting

### Formal Constants Mismatch
```bash
python -m scripts.verify_formal_constants
# Fix constants in TLA+/Coq to match src/bnsyn/config.py
```

### CI Truthfulness Violations
```bash
python -m scripts.lint_ci_truthfulness --md artifacts/ci_truthfulness.md
# Fix workflows: remove || true, add explicit permissions, remove unused inputs
```

### Mutation Score Drop
```bash
make mutation-check
# Review survivors: mutmut show --status survived
# Add tests to kill mutants
# Regenerate baseline if appropriate: make mutation-baseline
```

### Property Test Failures
```bash
# Check profile
pytest -m property --hypothesis-show-statistics
# Review hypothesis database: .hypothesis/
# Add examples or constraints to fix failures
```

### Chaos Test Failures
```bash
# Run with verbose output
pytest tests/validation/test_chaos_integration.py -vv -s
# Check for non-determinism (run multiple times with same seed)
# Verify expected behaviors are correctly documented
```

## Status

**Last Updated**: 2026-01-28

**Governance Gates Status**:
- ✅ CI Truthfulness Linter: Operational
- ✅ Formal Constants Verifier: Operational
- ✅ All workflows have explicit permissions
- ✅ All constants verified to match code

**Open Items**:
- None (all governance gates passing)
