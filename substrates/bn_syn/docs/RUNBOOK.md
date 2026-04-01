# Runbook

## Canonical command surface

- Install: `make install`
- Lint: `make lint`
- Typecheck: `make mypy`
- Tests: `make test`
- Build: `make build`
- Security: `make security`
- Docs: `make docs`
- Perfection gate: `make perfection-gate`
- Launch gate: `make launch-gate`

## Artifact layout

- `artifacts/perfection_gate/` — verification outputs and `quality.json`.
- `artifacts/launch_gate/` — launch-readiness outputs and `quality.json`.
- `proof_bundle/logs/` — executed command logs used as evidence pointers.

## Common failure modes

- `mypy` failure in strict mode: run `make mypy` and correct type boundary mismatches.
- determinism failure: run `pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q` and compare outputs.
- release verification failure: run `python -m scripts.release_pipeline --verify-only`.

## Performance knobs

- benchmark smoke: `python -m scripts.bench_ci_smoke --repeats 1`.
- benchmark sweep: `python -m scripts.run_benchmarks`.
