# PR #62: Quality Infrastructure Audit & SSOT Compliance Fixes

## Summary

This PR fixes ALL remaining audit defects and SSOT violations in the BN-Syn quality infrastructure to achieve zero false-green, complete SSOT lifecycle for mutation testing, proper Hypothesis profile enforcement, and workflow truthfulness.

## EVIDENCE INDEX

### 1. Mutation Testing SSOT Lifecycle

**What was wrong:**
- Mutation baseline could be uninitialized (total_mutants=0) but nightly workflow would pass (false-green)
- No distinction between advisory (PR/local) and strict (nightly) checks
- Shell arithmetic bug in workflow (nested quotes breaking bash)

**What is now enforced:**
- `check_mutation_score.py` supports `--advisory` and `--strict` modes
- Strict mode FAILS (exit 1) when baseline is uninitialized or needs_regeneration
- Advisory mode WARNS (exit 0) when baseline is uninitialized
- quality-mutation.yml workflow uses strict mode to prevent false-green
- Makefile has separate targets: `mutation-check` (advisory) and `mutation-check-strict` (strict)

**Proof commands:**
```bash
# Test strict mode with uninitialized baseline (should FAIL)
python -m scripts.check_mutation_score --strict
# Expected: exit code 1, error message

# Test advisory mode with uninitialized baseline (should WARN but PASS)
python -m scripts.check_mutation_score --advisory
# Expected: exit code 0, warning message
```

**Evidence artifacts:**
- `artifacts/audit/mutation_check_strict_uninitialized.txt` - Shows strict mode exits 1
- `artifacts/audit/mutation_check_advisory.txt` - Shows advisory mode exits 0
- `.github/workflows/quality-mutation.yml` line 103-107 - Uses strict check
- `Makefile` lines 27-43 - Separate advisory/strict targets
- `scripts/check_mutation_score.py` lines 78-120 - Mode implementation

### 2. Hypothesis Profiles as SSOT

**What was wrong:**
- ci-validation.yml (mode: elite) used non-existent profile `ci-quick` (not in pyproject.toml)
- ci-validation.yml (mode: property) used CLI flag `--hypothesis-profile=quick` instead of env var
- Profile precedence not properly enforced via environment variable
- Documentation showed wrong profile values

**What is now enforced:**
- ALL workflows use `HYPOTHESIS_PROFILE` environment variable (not CLI flag)
- Profile names match pyproject.toml definitions: `quick` (100 examples), `ci` (200 examples), `thorough` (1000 examples)
- Precedence: HYPOTHESIS_PROFILE env var → profiles in pyproject.toml
- No per-test max_examples overrides found (grep verified)

**Proof commands:**
```bash
# Verify profile budgets differ
HYPOTHESIS_PROFILE=quick pytest -m property -q --hypothesis-show-statistics | grep "max_examples=100"
HYPOTHESIS_PROFILE=thorough pytest -m property -q --hypothesis-show-statistics tests/properties/test_adex_properties.py::test_adex_outputs_finite | grep "max_examples=1000"

# Verify no per-test overrides
grep -r "@settings" tests/ | grep "max_examples"
# Expected: no results (clean)
```

**Evidence artifacts:**
- `artifacts/audit/hypothesis_quick_stats.txt` - Shows max_examples=100
- `artifacts/audit/hypothesis_thorough_stats_sample.txt` - Shows max_examples=1000
- `.github/workflows/ci-validation.yml (mode: property)` lines 29-32 - Uses HYPOTHESIS_PROFILE=ci env var
- `.github/workflows/ci-validation.yml (mode: elite)` lines 82-86 - Fixed to use `quick` profile
- `.github/workflows/ci-validation.yml (mode: chaos)` line 93 - Uses HYPOTHESIS_PROFILE=thorough
- `pyproject.toml` lines 82-99 - Profile definitions
- `docs/QUALITY_INDEX.md` lines 105-116 - Updated documentation

### 3. Pytest Markers and --strict-markers

**What was wrong:**
- None - markers were already correctly registered

**What is now enforced:**
- All markers (smoke, validation, performance, integration, property, chaos) registered in pyproject.toml
- `--strict-markers` passes without errors
- Chaos tests selectable with `-m "validation and chaos"` filter

**Proof commands:**
```bash
# Verify strict markers pass
pytest -q --strict-markers --collect-only

# Verify chaos selection
pytest -m "validation and chaos" --collect-only -q

# Verify property selection
pytest -m property --collect-only -q
```

**Evidence artifacts:**
- `artifacts/audit/pytest_collect_strict_markers.txt` - Shows 264 tests collected, no errors
- `artifacts/audit/pytest_collect_chaos_selection.txt` - Shows 37 chaos tests selected
- `artifacts/audit/pytest_collect_property_selection.txt` - Shows 19 property tests selected
- `artifacts/audit/final_collect.txt` - Final verification, no marker errors
- `artifacts/audit/final_collect_chaos.txt` - Final chaos selection verification
- `pyproject.toml` lines 73-80 - Marker registry

### 4. Workflow Truthfulness and Permissions

**What was wrong:**
- Concern about `continue-on-error: true` being false-green
- Concern about `|| true` masking failures

**What is now enforced:**
- ALL `continue-on-error: true` patterns have proper gate steps that check exit codes and fail explicitly
- `|| true` usage is ONLY for legitimate cases (mutmut show, grep for display) where subsequent gate checks still fail
- ALL external actions are pinned to versions (@v4, @v5)
- ALL workflows have explicit minimal permissions (contents: read)
- Heavy suites (property, chaos, mutation, formal) are schedule/dispatch only

**Proof commands:**
```bash
# Scan for false-green patterns
grep -RIn "|| true\|continue-on-error:\s*true" .github/workflows

# Verify gate steps exist
grep -A 2 "Fail if" .github/workflows/_reusable_quality.yml
grep "exit 1" .github/workflows/_reusable_pytest.yml | grep "Fail if"

# Verify permissions
grep "permissions:" .github/workflows/*.yml | grep "contents: read"

# Verify action pinning
grep "uses:" .github/workflows/*.yml | grep "@v"
```

**Evidence artifacts:**
- `artifacts/audit/workflow_false_green_hits.txt` - All instances documented
- `artifacts/audit/workflow_permissions_hits.txt` - All workflows have permissions
- `.github/workflows/_reusable_pytest.yml` lines 69-70, 186-188 - continue-on-error with gate
- `.github/workflows/_reusable_quality.yml` lines 49, 88-90, 125, 154-156, 181, 207-209 - All have gate steps
- `.github/workflows/formal-tla.yml` lines 103, 218-234 - continue-on-error with gate
- `.github/workflows/quality-mutation.yml` lines 62, 66 - Legitimate || true with subsequent strict check

**Analysis of continue-on-error patterns:**

1. **_reusable_pytest.yml line 70**: Captures PYTEST_RESULT, generates summary, THEN gate step at line 186-188 fails if PYTEST_RESULT != 0. ✅ CORRECT
2. **_reusable_pytest.yml line 164**: Codecov upload with fail_ci_if_error=false. Non-blocking by design. ✅ ACCEPTABLE
3. **_reusable_quality.yml lines 49, 56**: Ruff checks capture exit codes, gate step at line 88-90 fails if either failed. ✅ CORRECT
4. **_reusable_quality.yml line 125**: Mypy captures exit code, gate step at line 154-156 fails. ✅ CORRECT
5. **_reusable_quality.yml line 181**: Pylint captures exit code, gate step at line 207-209 fails. ✅ CORRECT
6. **formal-tla.yml line 103**: TLC captures output, gate step at line 218-234 checks STATUS and fails. ✅ CORRECT

**Analysis of || true patterns:**

1. **quality-mutation.yml line 62**: `mutmut show --status survived || true` - mutmut exits non-zero when NO survivors exist (good outcome). Subsequent strict check at line 103-107 still validates baseline. ✅ ACCEPTABLE
2. **quality-mutation.yml line 66**: Similar to above, for displaying mutants. ✅ ACCEPTABLE
3. **formal-tla.yml line 228**: `grep -A 20 "Error:" ... || true` - Just for displaying error details in summary. Line 230 still exits 1 on failure. ✅ ACCEPTABLE

### 5. Documentation = Reality

**What was wrong:**
- Hypothesis profile table had wrong values (dev, quick=50, thorough=500)
- Commands showed `--hypothesis-profile` CLI flag instead of env var
- Mutation check modes not documented

**What is now enforced:**
- Profile table matches pyproject.toml exactly (quick=100, ci=200, thorough=1000)
- All commands use `HYPOTHESIS_PROFILE` environment variable
- Mutation check advisory vs strict modes documented
- Workflow triggers and commands are reproducible

**Proof commands:**
```bash
# Verify commands from docs work
HYPOTHESIS_PROFILE=quick pytest -m property
make mutation-check
make mutation-check-strict
pytest -m "validation and chaos"
```

**Evidence artifacts:**
- `docs/QUALITY_INDEX.md` lines 5-15 - Updated command table
- `docs/QUALITY_INDEX.md` lines 105-116 - Corrected profile table
- `docs/QUALITY_INDEX.md` lines 147-163 - Documented check modes
- All commands in documentation are runnable and match actual workflow usage

## ROLLBACK INSTRUCTIONS

To safely disable nightly workflows if issues arise:

### Option 1: Disable Individual Workflows (Recommended)

Edit workflow files and comment out the `schedule:` trigger, keeping `workflow_dispatch:` for manual runs:

```yaml
on:
  # schedule:
  #   - cron: '0 3 * * *'
  workflow_dispatch:
```

**Workflows to modify:**
- `.github/workflows/quality-mutation.yml` (line 4-6) - Mutation testing
- `.github/workflows/ci-validation.yml (mode: property)` (line 4-6) - Property tests
- `.github/workflows/ci-validation.yml (mode: chaos)` (line 4-6) - Chaos validation
- `.github/workflows/formal-tla.yml` - TLA+ model checking
- `.github/workflows/ci-validation.yml (mode: elite)` (line 4-6) - Scientific validation

### Option 2: Revert Mutation Strict Mode

If mutation strict mode is too aggressive:

1. Edit `.github/workflows/quality-mutation.yml` line 107
   - Change: `python -m scripts.check_mutation_score --strict`
   - To: `python -m scripts.check_mutation_score --advisory`

2. This allows nightly runs to pass even with uninitialized baseline (warning only)

### Option 3: Full PR Revert

To completely revert all changes:

```bash
git revert <commit-sha-from-this-pr>
git push origin copilot/fix-quality-infrastructure-defects
```

Then merge the revert to restore previous behavior.

## FILES CHANGED

### Scripts
- `scripts/check_mutation_score.py` - Added --advisory and --strict modes with proper argparse
- `scripts/generate_mutation_baseline.py` - No changes (already correct)

### Workflows
- `.github/workflows/quality-mutation.yml` - Fixed shell arithmetic, added strict check
- `.github/workflows/ci-validation.yml (mode: property)` - Use HYPOTHESIS_PROFILE env var
- `.github/workflows/ci-validation.yml (mode: elite)` - Fixed profile name ci-quick → quick
- `.github/workflows/ci-validation.yml (mode: chaos)` - No changes (already correct)
- `.github/workflows/_reusable_pytest.yml` - No changes (patterns already correct)
- `.github/workflows/_reusable_quality.yml` - No changes (patterns already correct)
- `.github/workflows/formal-tla.yml` - No changes (patterns already correct)

### Build/Config
- `Makefile` - Added mutation-check-strict target

### Documentation
- `docs/QUALITY_INDEX.md` - Updated profiles, commands, and check mode documentation

### Evidence
- `artifacts/audit/*.txt` - 17 evidence files documenting all verifications

## VERIFICATION RESULTS

All acceptance criteria PASS:

✅ `grep` finds ONLY justified `|| true` / `continue-on-error:true` with proper gate steps
✅ `pytest --strict-markers --collect-only` passes (264 tests)
✅ `pytest -m "validation and chaos" --collect-only` selects 37 chaos tests without errors
✅ Hypothesis budgets controlled by profiles (100 quick vs 1000 thorough, verified in artifacts)
✅ Mutation baseline strict check fails when uninitialized (exit code 1)
✅ Nightly mutation workflow uses strict mode (will fail if baseline missing)
✅ Workflows have explicit minimal permissions (contents: read)
✅ All external actions pinned to versions (@v4, @v5)
✅ Docs match actual workflow triggers and commands are reproducible

## IMPACT ASSESSMENT

**Zero Breaking Changes:**
- All changes are to infrastructure, not core scientific code
- Tests remain unchanged
- Baseline files remain compatible
- Workflows remain fork-safe (no secrets required)

**Quality Improvements:**
- Eliminates false-green in mutation testing
- Enforces SSOT for Hypothesis profiles
- Documents all verification procedures
- Makes quality gates verifiable and auditable

**Performance:**
- No impact on test runtime
- No additional CI jobs added
- Heavy suites remain nightly/dispatch only

## NEXT STEPS

After merge:
1. Monitor first nightly mutation run - if baseline uninitialized, generate with `make mutation-baseline` (~30 min)
2. Monitor property tests to verify profiles are working correctly
3. If any workflow issues arise, use rollback instructions above

## CodeQL Workflow Evidence (Current Default-Branch State)

### codeql.yml (pre-fix snapshot)
```yaml
name: codeql

on:
  push:
    branches: ["main"]
  pull_request:
  schedule:
    - cron: "0 4 * * 0"

jobs:
  analyze:
    name: analyze
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ["python"]
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      - name: Analyze
        uses: github/codeql-action/analyze@v3
```

---

## PR Agent Evidence Run (Protocol BNSYN_PR_EXEC_v2026.02)

STATUS: NEEDS_EVIDENCE

### What changed
- Added reproducible local evidence logs under `artifacts/pr_agent/` for inventory, baseline, PR gates, manifest determinism, test slice, and refactor slice checkpoints.
- Re-ran inventory, PR gate parsing, manifest generation/validation, and targeted deterministic test suites.

### Why
- Enforces audit-grade traceability for required PR protocol steps.
- Confirms the baseline failure mode is environmental/toolchain-security-gate related (`pip-audit` vulnerability in the runtime pip version), not source regressions.

### Evidence pointers
- `artifacts/pr_agent/00_inventory.txt`
- `artifacts/pr_agent/01_baseline.txt`
- `artifacts/pr_agent/02_pr_gates.txt`
- `artifacts/pr_agent/03_manifest.txt`
- `artifacts/pr_agent/04_tests.txt`
- `artifacts/pr_agent/05_refactor.txt`

### Missing proof to reach PASS
- Canonical `make check` must pass without failing `pip-audit` security gate.
- Required remediation command sequence (exact):
  1. `python -m pip install --upgrade pip`
  2. `export PATH="$HOME/go/bin:$PATH"`
  3. `make check`
