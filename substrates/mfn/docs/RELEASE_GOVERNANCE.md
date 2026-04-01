# Release Governance

## Release Criteria

A release is authorized only when ALL of the following gates pass:

| # | Gate | Tool | Fail action |
|---|------|------|-------------|
| 1 | Full test suite green | `pytest tests/` | Block release |
| 2 | Coverage >= 78% branch | `pytest --cov-fail-under=78` | Block release |
| 3 | Import contracts 7/7 | `lint-imports` | Block release |
| 4 | Causal gate PASS | `validate_causal_consistency(mode="strict")` | Block release |
| 5 | OpenAPI contract stable | `scripts/check_openapi_contract.py` | Block release |
| 6 | Docs drift clean | `scripts/docs_drift_check.py` | Block release |
| 7 | Scientific validation | `validation/run_validation_experiments.py` | Block release |
| 8 | Neurochem controls | `validation/neurochem_controls.py` | Block release |
| 9 | Benchmark no regression | `benchmarks/benchmark_quality.py` | Block release |
| 10 | Security scan clean | `bandit + pip-audit` | Block release |
| 11 | Artifact integrity | `mfn verify-bundle` | Block release |
| 12 | Lockfile consistent | `uv lock --check` | Block release |

## Change Classification

| Classification | Criteria | Release type | Benchmark required |
|---------------|----------|-------------|-------------------|
| **patch** | Bug fix, no behavior change | Patch (4.1.x) | No |
| **minor** | New feature, backward-compatible | Minor (4.x.0) | Yes |
| **scientific-impacting** | Changes to detection thresholds, causal rules, or biophysical constants | Minor + scientific validation | Yes + validation experiments |
| **release-blocking** | Breaks causal gate, artifact integrity, or test suite | Cannot merge | N/A |

## Scientific-Impacting Changes

Any change that modifies:
- Detection threshold constants in `configs/detection_thresholds_v1.json`
- Causal rule definitions in `core/causal_validation.py`
- Biophysical constants (Nernst, GABA-A, Turing parameters)
- Feature extraction formulas in `analytics/`
- Regime classification logic in `core/detect.py`

Must include:
1. Rationale with scientific reference
2. Before/after benchmark comparison
3. Updated golden regression tests
4. Updated causal rule manifest
5. Explicit CHANGELOG entry classified as `scientific-impacting`

## Reproducibility Sheet

Every release tag must include:

| Field | Source |
|-------|--------|
| Git commit SHA | `git rev-parse HEAD` |
| Engine version | `pyproject.toml [project] version` |
| Python version | `python --version` |
| Lock hash | `sha256sum uv.lock` |
| Config hash | Detection thresholds + causal validation config SHA256 |
| Test count | `pytest` output |
| Coverage | `pytest --cov` output |
| Causal decision | `validate_causal_consistency` output |
| Benchmark baseline | `benchmarks/results/benchmark_core.json` |
| Artifact checksums | `SHA256SUMS` in release bundle |

## Release Process

```bash
# 1. Verify all gates
make fullcheck
make validate
make benchmark

# 2. Tag
git tag -a v4.x.y -m "Release v4.x.y"

# 3. Build + sign
make sbom
python -m build
cd dist && sha256sum * > SHA256SUMS

# 4. Push tag (triggers release.yml workflow)
git push origin v4.x.y
```

## Performance Budget

| Metric | Budget | Fail threshold |
|--------|--------|---------------|
| Full pipeline (64x64, 32 steps) | < 100 ms | > 150 ms |
| Simulate (64x64, 32 steps) | < 25 ms | > 40 ms |
| Causal validation | < 5 ms | > 10 ms |
| Report generation | < 200 ms | > 500 ms |
| Artifact bundle size | < 2 MB | > 5 MB |

## Benchmark History

Each release archives benchmark results in `benchmarks/results/` with the format:
```
benchmark_core_v{version}.json
benchmark_quality_v{version}.json
```

Regression is detected when any metric exceeds baseline + 20% margin.

## Audit Trail

Every release artifact includes:
- `causal_validation.json` — causal gate verdict with provenance hash
- `attestation.json` — Ed25519 signature
- `SHA256SUMS` — file checksums
- `sbom.json` — dependency manifest
