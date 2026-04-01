# Entropy Ledger

## Scope
- Repository: `bnsyn-phase-controlled-emergent-dynamics`
- PR themes: `process_evidence_bundle`, `guarded_entropy_artifacts`
- Selected batches: 1 (process entropy)

## Cycle 0 — Baseline Snapshot

### Canonical commands discovered
- TEST_CMD: `pytest -q` (from `.github/workflows/_reusable_pytest.yml` / CI jobs)
- LINT_CMD: `ruff check .` (from `.github/workflows/_reusable_quality.yml`)
- BUILD_CMD: `python -m build` (from `.github/workflows/ci-pr-atomic.yml`)
- SCAN_CMD: `python -m scripts.scan_governed_docs` (from `.github/workflows/ci-pr-atomic.yml`)

### Baseline metrics

| Metric ID | Definition | Baseline | Threshold | Status | Evidence |
|---|---|---:|---:|---|---|
| M1 | Dependency pin ratio (`==`) in `pyproject.toml` dependency surfaces | 0.9459 | >= 0.94 | pass | `entropy/metrics.json` |
| M1b | SHA-pinned GitHub Actions ratio in `.github/workflows` | 0.0 | informational | risk | `entropy/metrics.json` |
| M2 | Determinism controls (`hypothesis.derandomize`, `PYTHONHASHSEED`) | 2 | >= 2 | pass | `entropy/metrics.json` |
| M3 | Contract validation signals (typed validation boundary modules present) | 2 | >= 2 | pass | `entropy/metrics.json` |
| M4 | Entropy guard test count | 0 | >= 1 | fail | `evidence/entropy/baseline.json` |
| M5 | Entropy evidence bundle completeness | 0 | >= 1 | fail | `evidence/entropy/baseline.json` |

## Entropy Top-10 List (baseline)

1. Missing canonical entropy ledger artifact (`docs/ENTROPY_LEDGER.md`) — process entropy.
2. Missing machine-readable entropy metrics (`entropy/metrics.json`) — process entropy.
3. Missing command evidence log (`entropy/commands.log`) — audit entropy.
4. Missing acceptance mapping (`entropy/acceptance_map.yaml`) — gate ambiguity.
5. Missing regression guard for entropy artifacts — no relapse prevention.
6. No entropy-specific evidence snapshots (`evidence/entropy/*.json`) — weak traceability.
7. No dedicated test asserting entropy artifact validity.
8. CI actions are version-tag pinned, not SHA pinned (informational).
9. Determinism checks exist, but no unified entropy gate script.
10. Baseline/final delta not encoded in canonical location before this PR.

## Cycle 1 — Plan

### Selected entropy themes
1. Build/process evidence determinism (artifact bundle standardization).
2. Regression guard for entropy artifacts and thresholds.

### Fix + guard map
- Fix: add canonical entropy artifacts (`A-F`) with baseline/final metrics and acceptance map.
- Guard: `entropy/guards/check_entropy_artifacts.py` + `tests/test_entropy_artifacts_guard.py`.
- Evidence: `entropy/metrics.json`, `entropy/commands.log`, `evidence/entropy/per_cycle/CYCLE_1.json`.

## Cycle 3/4 — Implementation and guards

- Added canonical artifacts required for entropy accounting.
- Added guard script validating required artifact presence and acceptance threshold compliance.
- Added pytest regression test that executes guard logic in CI test runs.

## Cycle 6 — Final snapshot

| Metric ID | Baseline | Final | Delta |
|---|---:|---:|---:|
| M1 dependency pin ratio | 0.9459 | 0.9459 | +0.0000 |
| M2 determinism controls | 2 | 2 | +0 |
| M4 entropy guard tests | 0 | 1 | +1 |
| M5 evidence bundle completeness | 0 | 1 | +1 |

## Acceptance verdict
- AC1: pass
- AC2: pass
- AC3: pass
- AC4: pass

**MERGE_OK** (local gate evidence satisfied).
