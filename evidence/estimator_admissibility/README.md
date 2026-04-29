# Estimator Admissibility Trial — evidence directory

This directory holds JSON outputs from the Phase 3 estimator admissibility
trial. The trial answers a single metrological question: is the canonical
Theil–Sen γ estimator (or one of four alternatives) admissible as a ruler
before any null-screen p-value, verdict label, or substrate claim is
allowed downstream?

## Output schema

Each JSON file (`smoke_*.json`, `canonical_*.json`) is the artefact of a
single CI matrix leg — one estimator's full sweep over the
(γ_true × N × σ) grid at the chosen replicate count M.

Top-level keys:

| key                   | content                                                                                  |
|-----------------------|------------------------------------------------------------------------------------------|
| `schema_version`      | semver string; bumped on schema-breaking changes                                         |
| `verdict`             | dict with the six contractual fields (see protocol doc) plus `per_estimator` diagnostics |
| `verdict_block`       | rendered six-field verdict block, identical to what the CLI prints                       |
| `results`             | full grid: `cells[estimator][γ_true][N][σ]` with the 8 per-cell metrics                  |
| `result_hash`         | sha256 of canonicalised payload (sorted keys, no spaces, no NaN/Inf)                     |
| `generated_at_utc`    | wall-clock start (NOT in hash)                                                           |
| `completed_at_utc`    | wall-clock finish (NOT in hash)                                                          |
| `runtime_seconds`     | measured runtime (NOT in hash)                                                           |

## Reproducibility

Two runs with the same `--M`, `--estimators`, `--gamma-grid`, `--n-grid`,
`--noise-sigma`, `--seed-base`, and `--n-window-replicates` produce a
**byte-identical** `result_hash`. This is enforced by the test
`test_cli_smoke_reproducible_hash` in `tests/test_estimator_admissibility.py`.

## Authoritative protocol

`docs/audit/ESTIMATOR_ADMISSIBILITY_PROTOCOL.md` — the frozen prose
explanation of why this trial is upstream of the null-screen runner and
what each of the six verdict fields means.

## .gitignore

The JSON outputs themselves are **not** committed — they regenerate
deterministically on every CI run. This README is the only file kept
under version control inside this directory.

## Reference smoke verdict — 2026-04-29

Locally-reproduced M=100 canonical smoke on the full grid
(7 γ_true × 6 N × 4 σ × 5 estimators × 100 replicates), single-threaded,
74 min wall-clock on a 16-core / Linux 6.8 machine:

```
ESTIMATOR_ADMISSIBILITY:
  PASSED

MINIMUM_TRAJECTORY_LENGTH:
  128

CANONICAL_ESTIMATOR:
  accepted

REPLACEMENT_ESTIMATOR:
  NONE

HYPOTHESIS_TEST_STATUS:
  READY (at N >= 128)

FINAL_VERDICT:
  ADMISSIBLE_AT_N_MIN_128
```

`result_hash`: `ed619996a738d2db3664ac98448c330a2dfbbd387918a3941a998d91e2c35cf2`

Reproduce:

```
python -m tools.phase_3.admissibility.run_admissibility_trial \
  --M 100 --smoke \
  --out evidence/estimator_admissibility/smoke.json \
  --print-block
```

All five estimators (`canonical_theil_sen`, `subwindow_bagged_theil_sen`,
`quantile_pivoted_slope`, `bootstrap_median_slope`, `odr_log_log`) reach
A1–A4 at `N ≥ 128` on σ=0.1; canonical is accepted by RMSE tie-break.
This is *the reference verdict* the CI smoke matrix should reproduce on
every PR; CI's per-estimator-leg artefacts converge to the same
`result_hash` when run with the same seed and bootstrap-B.

### Downstream consequence

Phase 3 null-screen verdicts on substrates with trajectory length
`N < 128` are **not** scientifically grounded — they sit below the
admissibility floor. `serotonergic_kuramoto`'s `_N_SWEEP=20` adapter
therefore cannot ground a Phase 3 verdict; that substrate's
`ESTIMATOR_ARTIFACT_SUSPECTED` was a substrate-side gap, not an
estimator gap. Phase 4 must rerun the adapter at `N ≥ 128`, or change
the observable.
