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
