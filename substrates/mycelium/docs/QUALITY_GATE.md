# Quality Gate — Definition of Done

Every PR and release must pass all gates below. No exceptions. No manual overrides.

## PR Gates (CI enforced)

| # | Gate | Command | Threshold |
|---|------|---------|-----------|
| 1 | Lint | `ruff check src/ tests/` | 0 errors |
| 2 | Format | `ruff format --check` | 0 diffs |
| 3 | Type check | `mypy --strict` (types/, security/, core/, analytics/, neurochem/, bio/) | 0 errors |
| 4 | Unit tests | `pytest tests/` | 0 failures |
| 5 | Coverage (global) | `pytest --cov --cov-fail-under=80` | ≥ 80% branch |
| 5b | Coverage (bio/) | `check_bio.sh` gate 9/9 | ≥ 90% branch |
| 6 | Import contracts | `lint-imports` | 8/8 KEPT |
| 7 | Docs drift | `scripts/docs_drift_check.py` | 0 failures |
| 8 | Security | `bandit -r src/` | 0 medium/high |

## Release Gates (release.yml enforced)

| # | Gate | Command | Threshold |
|---|------|---------|-----------|
| 9 | Scientific validation | `validation/run_validation_experiments.py` | PASS |
| 10 | Neurochem controls | `validation/neurochem_controls.py` | PASS |
| 11 | OpenAPI contract | `scripts/check_openapi_contract.py` | stable |
| 12 | Causal gate | `validate_causal_consistency(mode="strict")` | decision=pass |
| 13 | Benchmark regression | `benchmarks/benchmark_core.py` | all gates pass |
| 14 | Artifact integrity | `mfn verify-bundle` | verified |
| 15 | Dependency audit | `pip-audit --strict` | 0 critical |
| 16 | SBOM | `scripts/generate_sbom.py` | generated |
| 17 | Checksums | `sha256sum dist/*` | published |

## Merge Rules

- No direct push to `main` without PR.
- All 8 PR gates must be green.
- At least one maintainer approval.
- Squash merge preferred for feature branches.

## Release Rules

- All 17 gates must pass.
- Tag format: `v{major}.{minor}.{patch}`.
- Changelog updated before tagging.
- Release notes written.
- No `[Unreleased]` items remain without classification.

## Escalation

If a gate cannot pass due to a known issue:
1. Document the issue in `KNOWN_LIMITATIONS.md`.
2. Create a tracking issue with `P0` label.
3. Do NOT skip the gate — fix the issue or defer the release.
