# New Invariants

- Entropy determinism offenders in `entropy/current.json` must not exceed `entropy/baseline.json` for:
  - `global_np_random_offenders`
  - `python_random_offenders`
  - `time_calls_offenders`
- `tests_inventory.json` generation is deterministic across repeated executions.
- Every external GitHub Action reference in `.github/workflows/*.yml` must be pinned to a 40-hex commit SHA.
- `manifest/repo_manifest.computed.json` must expose non-empty invariants and a 64-hex `repo_ref` provenance digest.
- CI validation summary/control jobs in `ci-validation.yml` must include explicit `timeout-minutes` to reduce workflow entropy and prevent hanging jobs.
