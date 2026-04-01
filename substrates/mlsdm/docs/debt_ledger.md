# Technical Debt Ledger

**Last Updated:** 2026-01-19 (Wave A hardening complete)
**Related:**
- [TECHNICAL_DEBT_REGISTER.md](TECHNICAL_DEBT_REGISTER.md) - **Єдиний реєстр технічного боргу (Unified Technical Debt Register)**
- [ENGINEERING_DEFICIENCIES_REGISTER.md](ENGINEERING_DEFICIENCIES_REGISTER.md)

---

## Baseline Snapshot (main-only, "here and now")

- Scope: only `main`, last five runs per key workflow, current coverage, and active alerts/jobs.
- Key workflows (main, last 5 runs):
  - CI Smoke (`ci-smoke.yml`) — ✅ all green.
  - Other key pipelines (CI engine, property tests, SAST/security, coverage badge) — no failing jobs observed on main in latest runs.
- Coverage: **78.62%** overall from the latest available main artifact (2025-12-22); no newer coverage uploads exist since that run (see `reports/coverage/COVERAGE_REPORT_2025-12-22.md`), so this value is carried forward for the 2026-01-04 baseline.
  - Historical DL-003 milestone was recorded at 78.13%; 78.62% is the current baseline.
  - Note: coverage data is 13 days old; rerun the coverage workflow to refresh.
- Security/alerts: no active failing jobs or blocked workflows on main observed in current runs; GitHub security alert API access is restricted in this environment, so use the repo dashboard as the authoritative source.

See [TECHNICAL_DEBT_REGISTER.md](TECHNICAL_DEBT_REGISTER.md) for the **complete unified technical debt register** with all identified issues, classifications, and remediation plans.
See [ENGINEERING_DEFICIENCIES_REGISTER.md](ENGINEERING_DEFICIENCIES_REGISTER.md) for detailed engineering deficiency analysis.

---

## Wave A Progress (2026-01-19)

### TD-001: pip CVE Remediation (EXCEPTION DOCUMENTED)

- Priority: HIGH
- Status: **Exception Documented** - Infrastructure-level mitigation
- Issue: CVE-2025-8869 in pip 24.0 (tarfile path traversal)
- Risk Assessment: MEDIUM (mitigated)
  - Impact: 3 (system compromise potential)
  - Likelihood: 2 (rare - trusted sources only)
  - **Risk = 6 (MEDIUM)**
- Mitigations:
  1. All CI workflows use `pip install --upgrade pip` which gets latest pip
  2. Only trusted package sources (PyPI, GitHub) are used
  3. No sdist packages from untrusted sources
  4. Python 3.12+ already implements PEP 706 safeguards
- Remediation: See Exceptions section below
- Owner: @devops

### TD-002: Policy Drift Guard (ENHANCED)

- Priority: HIGH
- Status: **Enhanced** with structured JSON logging
- Implementation:
  - Added `src/mlsdm/policy/fingerprint.py` module implementing Section 10 requirements:
    - **Section 10.1**: Canonical fingerprint algorithm (sorted keys, stable float formatting, SHA-256)
    - **Section 10.2**: Structured JSON logging (`POLICY_FINGERPRINT` event format)
    - **Section 10.3**: Drift detection test (fingerprint A vs B comparison)
  - Components:
    - `compute_canonical_json()`: Canonical serialization with stable float formatting
    - `compute_fingerprint_hash()`: SHA-256 fingerprinting
    - `compute_policy_fingerprint()`: Full fingerprint computation with metadata
    - `emit_policy_fingerprint_event()`: Structured JSON event logging
    - `detect_policy_drift()`: Fingerprint comparison for drift detection
    - `PolicyFingerprintGuard`: Stateful guard class for baseline management
- Tests: 24 new tests in `tests/unit/test_policy_fingerprint.py` (all passing)
- Proof command: `pytest tests/unit/test_policy_fingerprint.py -v` → 24 passed
- Risk: None - additive changes only
- Owner: @copilot

### TD-003: Memory Provenance (VERIFIED)

- Priority: HIGH
- Status: **Already implemented**, verification complete
- Implementation verified in `src/mlsdm/memory/provenance.py`:
  - **Section 11.1**: Metadata schema with `source`, `created_at`, `confidence_score`
  - **Section 11.2**: AUTHORITATIVE_THRESHOLD = 0.70 implemented as `is_high_confidence`
  - **Section 11.3**: Backward compatibility tests present in `tests/unit/test_memory_provenance.py`
- Tests: 22 existing tests (all passing)
- Proof command: `pytest tests/unit/test_memory_provenance.py -v` → 22 passed

### TD-005: NumPy Compatibility Decision (RESOLVED)

- Priority: HIGH
- Status: **Resolved** via ADR-0008
- Decision: Maintain `numpy>=2.0.0` as minimum version requirement
- Rationale:
  - NumPy 2.0 stable for over a year
  - All major ecosystem libraries support NumPy 2.0
  - NumPy 2.0 type stubs essential for strict mypy
  - No production issues reported
- Documentation: [docs/adr/0008-numpy-version-compatibility.md](adr/0008-numpy-version-compatibility.md)
- Owner: @engineering

---

## Exceptions

### EXC-001: pip CVE-2025-8869

- **Date UTC:** 2026-01-19T18:00:00Z
- **Reason:** System pip 24.0 has CVE-2025-8869, but:
  - CI automatically upgrades pip
  - Python 3.12 implements PEP 706 safeguards
  - Only trusted sources used
- **Scope:** CI/CD infrastructure and local development
- **Owner:** @devops
- **Expiry Date:** 2026-04-19 (90 days)
- **Removal Plan:** 
  1. Monitor GitHub Actions runner images for pip >=25.3
  2. Verify pip upgrade in CI logs
  3. Close exception once system pip is >=25.3
- **Link:** TD-001 in TECHNICAL_DEBT_REGISTER.md

---

## DL-001 (RESOLVED)

- Priority: P3
- Gate: test
- Symptom: RuntimeWarning about overflow encountered in dot during TestMemoryContentSafety::test_extreme_magnitude_vectors.
- Evidence: artifacts/baseline/test.log (numpy/linalg/_linalg.py:2792 RuntimeWarning: overflow encountered in dot, triggered by tests/safety/test_memory_leakage.py::TestMemoryContentSafety::test_extreme_magnitude_vectors).
- Likely root cause: Test inputs use extremely large vectors causing numpy.linalg dot product to overflow.
- Fix applied: Implemented safe_norm() function in src/mlsdm/utils/math_constants.py that uses scaled norm computation to prevent overflow. Updated phase_entangled_lattice_memory.py and multi_level_memory.py to use safe_norm() instead of np.linalg.norm().
- Proof command: source .venv/bin/activate && make test
- Risk: None - safe_norm() produces identical results for normal vectors and handles extreme magnitudes safely.
- Date: 2025-12-15
- Fixed: 2025-12-17
- Owner: @copilot
- Status: resolved
- Next action: None - issue is resolved.

---

## DL-002 (RESOLVED)

- Priority: P4 (Low)
- Gate: type-check
- Symptom: 37 mypy errors when running `mypy src/mlsdm`
- Evidence: mypy output showed errors including:
  - 9x "Class cannot subclass 'BaseHTTPMiddleware' (has type 'Any')"
  - 15x "Untyped decorator makes function untyped"
  - 6x "Returning Any from function"
  - 2x "Library stubs not installed"
- Likely root cause: FastAPI/Starlette typing limitations and missing type stubs
- Fix applied: types-PyYAML and types-requests properly configured in pyproject.toml dev dependencies. mypy configuration correctly handles optional modules.
- Proof command: `pip install -e ".[dev]" && mypy src/mlsdm` → "Success: no issues found in 109 source files"
- Risk: None
- Date: 2025-12-19
- Fixed: 2025-12-19
- Owner: @copilot
- Status: resolved
- Next action: None - issue is resolved.

---

## DL-003 (RESOLVED)

- Priority: P3 (Medium)
- Gate: coverage
- Symptom: Test coverage at 70.85%, below target of 75%
- Evidence: COVERAGE_REPORT_2025.md showed 70.85% overall coverage
- Likely root cause: Insufficient tests for api/, security/, observability/ modules
- Fix applied: Coverage verified at 78.13% (above 75% target) after including state tests. Unit tests passing: 1932 passed, 12 skipped.
- Proof command: `pytest tests/unit/ tests/state/ --cov=src/mlsdm` → "Required test coverage of 75.0% reached. Total coverage: 78.13%"
- Risk: None
- Date: 2025-12-19
- Fixed: 2025-12-19
- Owner: @copilot
- Status: resolved
- Next action: None - issue is resolved.
