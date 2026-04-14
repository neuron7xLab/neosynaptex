# Analysis split contract — cardiac γ-program

This document defines the immutable subject-level split between the
**development** set (used to calibrate every threshold, feature fit,
and null-separability verdict) and the **external validation** set
(touched only after thresholds are frozen).

## Source of truth

| artefact | role |
|---|---|
| `config/analysis_split.yaml` | the split membership, as committed bytes |
| `tools/data/analysis_split.py::ANALYSIS_SPLIT_SHA256` | the review gate |
| `tools/data/analysis_split.py::load_split()` | the verified loader |
| `docs/protocols/ANALYSIS_SPLIT.md` (this file) | the human contract |

The YAML and the SHA-256 constant must travel together in a single PR.
A mismatch at load time raises `ImmutabilityError` and blocks the
pipeline before any feature can be computed.

## Split

| split | cohorts | n_subjects |
|---|---|---|
| development | nsr2db (54), chfdb (15) | 69 |
| external validation | chf2db (29), nsrdb (18) | 47 |

- **Unit of analysis.** Subject. Windows are nested observations
  inside a subject. A subject lives in exactly one split.
- **Pathology balance.** Each split has one healthy cohort and one
  pathology cohort, so NSR-vs-CHF contrasts can be performed on
  either side without leaving its boundary.
- **Sampling frequency.** Development mixes 128 Hz and 250 Hz
  (chfdb). External validation is uniform 128 Hz. This is a real
  confound — Task 4 (canonical extraction stack) handles it via
  fixed-rate RR resampling; Task 2 only surfaces it in the
  distribution summary and never hides it.

## Dev-only discipline

Calibration code paths must wrap threshold fitting in
`enforce_dev_only()`. Any attempt to read an external-split subject
inside that context raises `SplitLeakError`. Downstream tasks
(Task 6 null-suite calibration, Task 8 threshold freeze) are the
primary users.

```python
from tools.data.analysis_split import enforce_dev_only, load_split

split = load_split()
with enforce_dev_only():
    thresholds = fit_thresholds(split.development)  # OK

# After enforce_dev_only() has exited, external is readable for the
# frozen-threshold application step:
external_scores = score(split.external, thresholds)
```

## What changes trigger what

| change | allowed | protocol step |
|---|---|---|
| Typo fix in a `#`-comment | no | requires a SHA-rotation PR reviewed as a protocol event |
| Add a new cohort | no — Task 1 reopens | mint a new cohort in `physionet_cohort.py`, then a SHA-rotation PR |
| Move a subject between splits | no | forbidden without superseding the entire γ-run; see CLAIM_BOUNDARY §E-02 |
| Re-hash after intentional edit | yes | update `ANALYSIS_SPLIT_SHA256` in the same PR, document the reason in the PR body |

## Cross-references

- `docs/protocols/MEASUREMENT_CONTRACT.md` §8 (interpretation_boundary)
- `CLAIM_BOUNDARY.md` §E-02 / §E-03 (blind external validation)
- `SYSTEM_PROTOCOL.md` §Remediation Queue Binding (S-02, E-02, E-03)
