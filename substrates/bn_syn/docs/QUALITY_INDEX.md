# Quality Infrastructure Index

Quick reference for running quality checks locally and understanding what each artifact proves.

## Local Commands

| Command | What it does | Blocking? |
|---------|--------------|-----------|
| `make test` | Fast unit tests (no validation/property) | PR blocking |
| `make check` | Full quality (format, lint, mypy, coverage, ssot, security) | PR blocking |
| `make coverage` | Coverage report with 85% threshold | PR blocking |
| `make mutation-baseline` | Generate mutation baseline from scratch | Manual |
| `make mutation-check` | Check mutation score against baseline (advisory mode) | Local/PR check |
| `make mutation-check-strict` | Check mutation score against baseline (strict mode, fails if uninitialized) | Nightly |
| `HYPOTHESIS_PROFILE=quick pytest -m property` | Property tests (quick, 100 examples) | Local dev |
| `HYPOTHESIS_PROFILE=thorough pytest -m property` | Property tests (thorough, 1000 examples) | Nightly |
| `pytest -m "validation and chaos"` | Chaos engineering tests | Nightly |

## Artifacts and What They Prove

| Artifact | Location | Proves |
|----------|----------|--------|
| `mutation_baseline.json` | `quality/` | Test effectiveness (mutation score) |
| `ci_truthfulness.json` | CI artifacts | No false-green patterns in workflows |
| `property_output.txt` | CI artifacts | Hypothesis statistics for property tests |
| `tlc_output.txt` | CI artifacts | TLA+ model checking results |
| `claims_coverage.json` | CI artifacts | All claims have test evidence |

## Workflow Schedule

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci-pr.yml` | PR, push to main | Fast verification |
| `quality-mutation.yml` | Nightly 3:00 UTC | Mutation testing |
| `formal-tla.yml` | Nightly 2:00 UTC | TLA+ model checking |
| `ci-validation.yml` (mode: `standard`) | Weekly Sun 3:00 UTC | SSOT + validation |
| `ci-validation.yml` (mode: `elite`) | Nightly 2:00 UTC | Validation + property |
| `ci-validation.yml` (mode: `property`) | Nightly 2:30 UTC | Property testing |
| `ci-validation.yml` (mode: `chaos`) | Nightly 4:00 UTC | Chaos engineering + property |

## Regenerating Baselines

```bash
# Mutation baseline (takes ~30 minutes)
make mutation-baseline

# Verify it worked
cat quality/mutation_baseline.json | jq '.metrics'
# Should show total_mutants > 0
```

## Understanding the Quality Stack

### Guard Tests (Formal Invariants)

- `tests/test_tla_invariants_guard.py` exercises production temperature schedule and criticality gain updates.
- `tests/test_vcg_invariants_guard.py` exercises pure VCG update/allocation functions only.
  - No core simulation integration exists in production for VCG; guard tests do **not** claim core side-effect proofs.

### Layer 1: Fast Feedback (PR Blocking)

**Unit Tests** (`make test`)
- Runtime: ~30 seconds
- Coverage threshold: 85%
- Excludes validation and property tests
- Must pass before merge

**Static Analysis** (`make check`)
- Black formatting
- Ruff linting
- mypy type checking (strict mode)
- pylint with 7.5+ threshold
- All must pass before merge

**SSOT Validation**
- Bibliography references
- Claims coverage (100% required)
- Governed docs consistency
- Normative tag usage
- TierS annotation correctness

**Security Summary (A6: CI Safety)**
- PR gates block on gitleaks, pip-audit, and bandit findings.
- pip-audit outputs `artifacts/pip-audit.json` for traceability across CI runs.

### Guard Tests

- Invariant mappings are protected by `tests/test_spec_mapping_guard.py`.
- SSOT for invariants lives in `specs/tla/BNsyn.tla` and `docs/VCG.md`.
- Guard tests must align with those SSOT sources.

### Layer 2: Nightly Deep Verification

**Property-Based Testing** (`ci-validation.yml` mode `elite`/`property`/`chaos`)
- Hypothesis framework with quick/thorough profiles
- Tests universal invariants (determinism, finiteness, boundedness)
- Captures statistics for empirical validation
- Non-blocking but signals serious issues

**Mutation Testing** (`quality-mutation.yml`)
- mutmut framework targeting critical modules
- Baseline score tracked in `quality/mutation_baseline.json`
- Tolerance: ±5% of baseline
- Detects weak test assertions

**Chaos Engineering** (`ci-validation.yml`, mode `chaos`)
- Fault injection (numeric, timing, stochastic, I/O)
- Tests resilience and fail-fast behavior
- Validates error detection mechanisms
- All tests marked with both `@pytest.mark.validation` and `@pytest.mark.chaos`

### Layer 3: Formal Methods

**TLA+ Model Checking** (`formal-tla.yml`)
- Temporal logic specifications
- Exhaustive state space exploration
- Proves impossibility of certain bugs
- Results in `tlc_output.txt` artifact

**Coq Proofs** (`formal-coq.yml`)
- Mathematical correctness proofs
- Guarantees about critical algorithms
- Verified against paper claims

## Hypothesis Profiles

Defined in `tests/properties/conftest.py`, controlled via `HYPOTHESIS_PROFILE` environment variable for property contour:

| Profile | Examples | Deadline | Use Case |
|---------|----------|----------|----------|
| `quick` | 100 | 5000ms | Local development |
| `ci` | 50 | 5000ms | CI property tests |
| `thorough` | 1000 | 20000ms | Nightly deep testing |

**IMPORTANT**: 
- Property tests should NOT hard-code `max_examples` in `@settings()` decorators. The profile is the single source of truth.
- Set profile via environment variable: `HYPOTHESIS_PROFILE=thorough pytest -m property`
- Do NOT use `--hypothesis-profile` CLI flag; use env var for proper precedence.

## Test Markers

| Marker | Purpose | CI Workflow |
|--------|---------|-------------|
| `property` | Hypothesis property tests | `ci-validation.yml` (elite/property/chaos) |
| `validation` | Extended validation tests | `ci-validation.yml` (standard/elite/chaos) |
| `chaos` | Chaos engineering tests | `ci-validation.yml` (chaos) |

**Chaos tests MUST have both `@pytest.mark.validation` AND `@pytest.mark.chaos`** to be selected by the chaos workflow's `-m "validation and chaos"` filter.

## Mutation Testing Details

### Scope

Critical modules under mutation coverage:
- `src/bnsyn/neuron/adex.py` - AdEx neuron dynamics
- `src/bnsyn/plasticity/stdp.py` - STDP learning rule
- `src/bnsyn/plasticity/three_factor.py` - Neuromodulated plasticity
- `src/bnsyn/temperature/schedule.py` - Temperature scheduling

### Baseline Status

**INVARIANT I4 (Mutation Integrity) Compliance**:

The `quality/mutation_baseline.json` file tracks:
- **Baseline score**: Target mutation score percentage
- **Tolerance**: Acceptable deviation (±5%)
- **Status**: `needs_regeneration` if not populated
- **Metrics**: Total mutants, killed, survived, timeout

**Current Status**: The baseline is in `needs_regeneration` state with `total_mutants == 0`.

**Invariant I4 Requirements**:
- If `total_mutants == 0`: status MUST be "needs_regeneration", score MUST be 0.0 ✅
- Otherwise: metrics MUST match real mutmut output ✅

**To populate baseline**: Run `make mutation-baseline` to generate real metrics (~30 minutes).

**Verification**: The baseline will be populated during scheduled nightly runs via `quality-mutation.yml`.

### Check Behavior

`scripts/check_mutation_score.py` supports two modes:

**Advisory Mode** (`--advisory` or default):
- If `status == "needs_regeneration"` or `total_mutants == 0`: Print warning, exit 0 (non-blocking)
- Otherwise: Compare current score to baseline ± tolerance, fail if below threshold
- Use for PR checks and local development

**Strict Mode** (`--strict`):
- If `status == "needs_regeneration"` or `total_mutants == 0`: Print error, exit 1 (FAIL)
- Otherwise: Compare current score to baseline ± tolerance, fail if below threshold
- Use for nightly/scheduled CI runs to ensure baseline is always initialized

## CI Truthfulness Linting

`scripts/lint_ci_truthfulness.py` detects common false-green patterns:

❌ **Anti-patterns detected**:
- Tests that run but don't fail the build
- Coverage reports without enforcement
- Linters that don't block on violations
- Commands with `|| true` that hide failures

✅ **What it validates**:
- Exit codes properly propagated
- Assertions that block on failure
- No silent test skipping
- Commands in conditionals have proper error handling

Reports saved to:
- `artifacts/ci_truthfulness.json` (machine-readable)
- `artifacts/ci_truthfulness.md` (human-readable, appended to PR summary)

## Security Scanning

### Gitleaks
- Scans for secrets in code and commit history
- Config: `.gitleaks.toml`
- Runs on every PR via `ci-pr.yml`

### pip-audit
- Checks Python dependencies for known vulnerabilities
- Runs on every PR
- Reports saved to artifacts

### CodeQL
- Static analysis for security vulnerabilities
- Language-specific queries
- Weekly full scans

## Coverage Requirements

**Unit Test Coverage**: 85% minimum
- Enforced via `pytest --cov --cov-fail-under=85`
- Reports uploaded to Codecov
- Excludes test files, validation tests, property tests

**Claims Coverage**: 100% required
- Every claim in `claims/*.yml` must have test evidence
- Validated by `scripts/validate_claims_coverage.py`
- PR blocking

## Adding New Quality Checks

When adding a new quality check:

1. **Make it PR-blocking or clearly non-blocking**
   - Blocking: Add to `ci-pr.yml` or `_reusable_quality.yml`
   - Non-blocking: Add to nightly workflows with clear signaling

2. **Ensure truthfulness**
   - Check must fail the build on violation
   - No `|| true` or silent failures
   - Use proper exit codes

3. **Document it here**
   - Add command to "Local Commands" table
   - Add artifact to "Artifacts" table if applicable
   - Add to workflow schedule if nightly

4. **Verify with CI truthfulness lint**
   - Run `python -m scripts.lint_ci_truthfulness`
   - Fix any violations before merging

## Troubleshooting

### "Mutation baseline not initialized"

```bash
# Generate baseline (takes ~30 minutes)
make mutation-baseline

# Verify it worked
cat quality/mutation_baseline.json | jq '.metrics.total_mutants'
# Should be > 0
```

### "Property tests using wrong profile"

Check that tests don't override `max_examples` in `@settings()`:

```bash
# Find violations
grep -r "max_examples" tests/

# Fix: Remove max_examples, keep deadline if needed
# Before:  @settings(max_examples=50, deadline=None)
# After:   @settings(deadline=None)
```

### "Chaos tests not collected"

Ensure tests have BOTH markers:

```python
@pytest.mark.validation
@pytest.mark.chaos
def test_my_chaos_test():
    pass
```

Verify with:
```bash
pytest -m "validation and chaos" --collect-only
```

### "CI truthfulness violations"

Read the report:
```bash
python -m scripts.lint_ci_truthfulness --md output.md
cat output.md
```

Common fixes:
- Remove `|| true` from test commands
- Add `exit 1` to failure branches
- Check exit codes in conditionals
- Use `set -e` in shell scripts

## References

- **Testing Strategy**: `docs/TESTING_MUTATION.md`
- **Hypothesis Guide**: `docs/HYPOTHESIS.md`
- **SSOT Rules**: `docs/SSOT_RULES.md`
- **CI Gates**: `docs/CI_GATES.md`
- **Architecture**: `docs/ARCHITECTURE.md`
