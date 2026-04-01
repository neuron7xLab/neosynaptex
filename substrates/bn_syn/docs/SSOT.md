# Single Source of Truth (SSOT)

## Canonical Commands

- install: `make install`
- lint: `make lint`
- typecheck: `make mypy`
- tests: `make test`
- build: `make build`
- docs: `make docs`
- security: `make security`
- perfection gate: `make perfection-gate`
- launch gate: `make launch-gate`

## Canonical Product Surface

- package root: `src/bnsyn`
- CLI entrypoint: `bnsyn`
- config schema: `src/bnsyn/schemas/experiment.py`
- launch artifacts root: `artifacts/launch_gate/`
