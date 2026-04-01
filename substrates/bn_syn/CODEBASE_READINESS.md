# CODEBASE_READINESS

This document defines the formal readiness rubric for BN-Syn.

## Scoring Model

Total readiness score is a weighted sum across five categories:

- API contract readiness: **25%**
- Stability & determinism readiness: **25%**
- Reproducibility readiness: **20%**
- Documentation readiness: **15%**
- Performance readiness: **15%**

For each category:

- `PASS` = full category weight
- `PARTIAL` = half category weight
- `FAIL` = zero category weight

Final score:

```text
readiness_percent = sum(category_weight * category_status_factor)
```

where status factor is `1.0` (PASS), `0.5` (PARTIAL), `0.0` (FAIL).

Release readiness policy:

- **Ready**: `readiness_percent >= 80`
- **Advisory gap**: `60 <= readiness_percent < 80`
- **Blocked**: `readiness_percent < 60`

## Category Rubric and Checklist

### 1) API Contract Readiness (25%)

Pass criteria:

- [ ] Stable API modules are explicitly documented in `docs/API_CONTRACT.md`.
- [ ] API surface baseline exists in `quality/api_contract_baseline.json`.
- [ ] Semver-aware API contract gate is active via `scripts/check_api_contract.py`.
- [ ] CI enforces API contract check in PR pipeline.

### 2) Stability & Determinism Readiness (25%)

Pass criteria:

- [ ] Determinism tests pass (`tests/test_determinism.py`, property determinism tests).
- [ ] Validation/smoke test partitioning is enforced by markers and pytest collection rules.
- [ ] CI determinism job executes repeated runs and RNG isolation checks.

### 3) Reproducibility Readiness (20%)

Pass criteria:

- [ ] Locked dependencies are present (`requirements-lock.txt`).
- [ ] Deterministic manifests and provenance checks exist for generated artifacts.
- [ ] Quickstart contract is executable and covered by tests.

### 4) Documentation Readiness (15%)

Pass criteria:

- [ ] Quickstart docs include deterministic runnable command and expected output shape.
- [ ] Integration examples exist for both library and CLI/tool usage.
- [ ] Release documentation includes changelog and release pipeline runbook.

### 5) Performance Readiness (15%)

Pass criteria:

- [ ] Benchmark scripts and baseline comparison tooling are present.
- [ ] Benchmark workflows are configured in CI.
- [ ] Performance checks are versioned and reproducible.

## Maturity Tagging Requirement

Public modules are tagged as one of:

- `stable`
- `experimental`
- `deprecated`

Source of truth: `docs/api_maturity.json`.
Validation command:

```bash
python -m scripts.validate_api_maturity
```

## Operational Commands

```bash
python -m scripts.validate_api_maturity
make api-contract
python -m pytest tests/test_quickstart_contract.py tests/test_integration_examples.py -q
```
