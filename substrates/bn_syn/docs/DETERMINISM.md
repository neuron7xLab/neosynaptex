# Determinism

## Existing controls
- CLI exposes explicit `--seed` parameter for deterministic runs (`src/bnsyn/cli.py`).
- Runtime seed utility exists in `src/bnsyn/rng.py` and is used by sleep-stack flow.
- Determinism tests exist (`tests/test_determinism.py`, `tests/test_properties_determinism.py`).

## Existing ordering / reproducibility signals
- Sorted JSON output paths in CLI demo output (`json.dumps(..., sort_keys=True)` in `src/bnsyn/cli.py`).
- Reproducible artifact validation script exists (`scripts/verify_reproducible_artifacts.py`).

## Gaps
- MISSING: single SSOT document that defines all required deterministic hashes/manifests.
  - DERIVE FROM: `evidence/**` reproducibility artifacts and validation scripts.
  - ACTION: consolidate into spec-facing deterministic contract when owners approve.
