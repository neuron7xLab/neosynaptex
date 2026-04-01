# Architectural Debt Register

Updated: 2026-03-27

## Resolved

| Item | Was | Now | Commit |
|------|-----|-----|--------|
| model.py monolith | 1329 LOC | 13 LOC wrapper + 4 modules | `e11d005` |
| config.py monolith | 810 LOC | 318 LOC + config_validation.py | `e11d005` |
| api.py monolith | 1062 LOC | 937 + api_v1.py (153) | `e11d005` |
| Flat fitness function | f≈0.045 all configs | Additive 5-component discriminating | `41dd323` |
| Memory query rebuild | Full rebuild every query | Pre-allocated matrix + append path | `78b059a` |
| Physarum sparse rebuild | 28.9ms/step lil_matrix loop | 3.0ms precomputed indices + splu | `845cce2` |
| NaN propagation | Silent leak to BioConfig | np.where(isfinite) guard | `58bb8c9` |
| HDV overflow | cos(extreme) → NaN | nan_to_num + clip(±1e6) | `e3060c8` |
| Version drift | 22 stale "4.1.0" refs | All "4.5.0" + golden hashes regenerated | `917f739` |
| Benchmark flaky gates | Hardcoded ms thresholds | Calibrated baselines + adaptive multiplier | `current` |
| Regression/gate metric split | Different measurement methods | Unified: regression=correctness, gate=performance | `current` |
| HDV degenerate encoding | All-+1 for small fields | z-score patch normalization | `23b1631` |
| pandas eager import | Base import crashes without [data] | Lazy import in run_scenario() | `c11703b` |
| sklearn missing from deps | morphospace ImportError on clean install | Added scikit-learn to bio extras | `c11703b` |
| Levin Three modules | Not implemented | morphospace + memory_anonymization + persuasion + pipeline | `dc6abc9` |
| ComputeBudget | No adaptive compute | Glycogen reserve: 8280× eigen speedup under load | `e1e9c65` |
| Stress test coverage | No hardware stress test | 32/32 operations, 0 leaks, sub-quadratic scaling | `1ac3602` |
| Vectorized HDV/Laplacian | Python loops in encode + build_laplacian | stride_tricks + mgrid, 1.9× speedup | `1ac3602` |
| Version drift 4.2.0→4.5.0 | 22 stale version refs across source | All synced via check_contract_version_sync.py | `a265886` |
| 512×512 scale support | OOM profiling incomplete | FractalPreservingInterpolator + MemoryBudgetGuard | `26ea774` |
| 1024×1024 policy | Undefined | FractalBudgetExceededError + allow_experimental_1024 | `26ea774` |
| Optional deps on import | scipy(475)+torch(668) loaded eagerly | Lazy numba/scipy/torch — 0 optional on import | `a265886` |
| MMS convergence tests | No manufactured solution tests | 10 tests: O(h²) spatial, O(dt) temporal, mass, CFL | `ac88d49` |
| Contract version sync | Manual, error-prone | check_contract_version_sync.py CI gate | `ac88d49` |
| README claims drift | Manual badge updates | Every example verified to produce exact shown output | `b946c4f` |

## Active

| Item | Symptom | Root cause | Closure condition |
|------|---------|------------|-------------------|
| causal_validation.py 1021 LOC | Exceeds 800 LOC standard | Living spec pattern — 46 rules need proximity | Accept: justified by architecture |
| api.py 937 LOC | Near 950 cap | WS handlers inline | v5.0: extract to separate service |
| Frozen surface ~2300 LOC | crypto/ + federated + stdp + turing | Deprecated, removal planned | v5.0 |
| CI benchmark calibration | Local baselines only | No CI runner calibration yet | CI workflow with calibrate_bio.py |

## Rules

1. No module > 800 LOC without exemption + documented justification
2. Baseline updates require before/after numbers in commit message
3. Performance gates: adaptive multiplier (50x sub-ms, 5x ms, 3x >5ms)
4. Regression tests: correctness only, no timing assertions
5. Benchmark gates: calibrated baseline × multiplier, with warmup + gc.collect
6. hypothesis mandatory in dev dependencies
7. All bio gates must pass `scripts/check_bio.sh` on clean environment
