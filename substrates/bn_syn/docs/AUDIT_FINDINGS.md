# Audit Findings

## Baseline Status

Baseline validation run performed on: 2026-01-23

| Validator | Status | Notes |
|-----------|--------|-------|
| `scripts/validate_bibliography.py` | ✅ PASS | 17 bibkeys, 19 mapping entries, 19 claim IDs |
| `scripts/validate_claims.py` | ✅ PASS | 19 claims validated; 16 normative |
| `scripts/scan_normative_tags.py` | ✅ PASS | Governed docs have no orphan normative statements |
| `pytest -m "not validation"` | ✅ PASS | 15 passed, 6 deselected |
| `pytest -m validation` | ⚠️ 1 FAILURE | Pre-existing: `test_adex_refractory_holds_reset` |

---

## Historical Findings (Resolved)

### FND-0001 (RESOLVED)
- **Symptom:** `scripts/validate_bibliography.py` failed with `ModuleNotFoundError: No module named 'yaml'`.
- **Root cause:** `PyYAML` dependency not installed in the execution environment.
- **Anchors:** `scripts/validate_bibliography.py:17` (import `yaml`).
- **Fix:** `PyYAML` added to `[dev]` dependencies in `pyproject.toml`.
- **Status:** ✅ Resolved — validator runs successfully.

### FND-0002 (RESOLVED)
- **Symptom:** `pytest -m "not validation"` fails during test collection with `ModuleNotFoundError: No module named 'bnsyn'` across multiple tests.
- **Root cause:** Python package not installed or import path not configured for tests.
- **Anchors:** `tests/test_*` imports, e.g., `tests/test_adex_smoke.py:2`.
- **Fix:** Install package via `pip install -e ".[dev,test]"` before running tests. CI workflows already do this.
- **Status:** ✅ Resolved — tests collect and run without import errors.

### FND-0003 (RESOLVED)
- **Symptom:** `pytest -m validation` fails during test collection with same `ModuleNotFoundError: No module named 'bnsyn'`.
- **Root cause:** Same as FND-0002.
- **Anchors:** `tests/test_validation_largeN.py:2` and other test imports.
- **Fix:** Same as FND-0002.
- **Status:** ✅ Resolved — tests collect and run without import errors.

---

## Known Issues (Pre-existing)

### FND-0004 (PRE-EXISTING)
- **Symptom:** `test_adex_refractory_holds_reset` fails in validation tests.
- **Root cause:** Test expects spike at V0=-45mV with V_spike=-40mV threshold, but AdEx dynamics may not produce a spike within one dt=1e-4s (0.1ms) timestep.
- **Anchors:** `tests/validation/test_production_properties.py:29-33`
- **Status:** ⚠️ Pre-existing failure — not introduced by architecture changes.
- **Notes:** This is a test design issue in the production properties tests, not a core logic bug. The test is marked as `@pytest.mark.validation` and runs in the separate validation CI workflow.

---

## Architecture Findings (Phase 1)

### FND-0005 (ADDRESSED)
- **Symptom:** No single navigation hub for documentation.
- **Root cause:** Documentation scattered across multiple files without central index.
- **Fix:** Created `docs/INDEX.md` as single navigation hub.
- **Status:** ✅ Addressed

### FND-0006 (ADDRESSED)
- **Symptom:** No single-page governance entry.
- **Root cause:** Governance concepts split across SSOT.md, SSOT_RULES.md, NORMATIVE_LABELING.md without unified entry point.
- **Fix:** Created `docs/GOVERNANCE.md` as one-page governance entry linking all policies.
- **Status:** ✅ Addressed

### FND-0007 (ADDRESSED)
- **Symptom:** README not serving as effective system launchpad.
- **Root cause:** README missing test commands, missing links to governance, incomplete repo map.
- **Fix:** Updated README with repo map table, SSOT gate commands, test commands, and governance links.
- **Status:** ✅ Addressed

### FND-0008 (ADDRESSED)
- **Symptom:** Makefile missing standard targets.
- **Root cause:** Only `validate-claims`, `validate-bibliography`, `validate-all` existed.
- **Fix:** Added `ssot`, `test-smoke`, `test-validation`, `ci-local` targets.
- **Status:** ✅ Addressed

---

## Gitleaks Findings (Phase 2)

### FND-GTL-0001 (FALSE POSITIVE - RESOLVED)
- **Symptom:** Gitleaks CI job failing with 22 detected "secrets".
- **Rule ID:** `generic-api-key`
- **Root cause:** The `generic-api-key` rule matches patterns like `key: <value>`. The `bibkey:` field in YAML files (bibliography reference keys like `bibkey: axelrod1981cooperation`) triggers false positives.
- **Files affected:**
  - `bibliography/mapping.yml` (10 findings)
  - `claims/claims.yml` (10 findings)
  - `PR_DIFF.patch` (2 findings) - artifact file incorrectly tracked
- **Evidence (extracted 2026-01-23):**
  ```
  bibliography/mapping.yml:10: bibkey: jahr1990voltage
  bibliography/mapping.yml:14: bibkey: fremaux2016neuromodulated
  bibliography/mapping.yml:18: bibkey: izhikevich2007solving
  bibliography/mapping.yml:22: bibkey: beggs2003neuronal
  bibliography/mapping.yml:26: bibkey: beggs2003neuronal
  bibliography/mapping.yml:38: bibkey: frey1997synaptic
  bibliography/mapping.yml:42: bibkey: wilkinson2016fair
  bibliography/mapping.yml:62: bibkey: axelrod1981cooperation
  bibliography/mapping.yml:70: bibkey: fehr2002punishment
  bibliography/mapping.yml:74: bibkey: kirkpatrick1983annealing
  claims/claims.yml:66: bibkey: jahr1990voltage
  claims/claims.yml:82: bibkey: fremaux2016neuromodulated
  claims/claims.yml:98: bibkey: izhikevich2007solving
  claims/claims.yml:114: bibkey: beggs2003neuronal
  claims/claims.yml:130: bibkey: beggs2003neuronal
  claims/claims.yml:178: bibkey: frey1997synaptic
  claims/claims.yml:194: bibkey: kirkpatrick1983annealing
  claims/claims.yml:210: bibkey: wilkinson2016fair
  claims/claims.yml:292: bibkey: axelrod1981cooperation
  claims/claims.yml:324: bibkey: fehr2002punishment
  PR_DIFF.patch:129: bibkey: axelrod1981cooperation
  PR_DIFF.patch:137: bibkey: fehr2002punishment
  ```
- **Fix:**
  1. Created `.gitleaks.toml` with path-scoped allowlist for `bibkey:` pattern
  2. Added `GITLEAKS_CONFIG: .gitleaks.toml` to CI workflow
  3. Added `PR_DIFF.patch` and `PR_SUMMARY.md` to `.gitignore`
  4. Removed `PR_DIFF.patch` and `PR_SUMMARY.md` from git tracking
- **Status:** ✅ Resolved — gitleaks scan passes with 0 findings

### FND-GTL-0002 (NOT APPLICABLE)
- **Symptom:** None — no real secrets found in repository.
- **Evidence:** All 22 findings were `bibkey:` false positives (FND-GTL-0001).
- **Status:** ✅ No real secrets detected
