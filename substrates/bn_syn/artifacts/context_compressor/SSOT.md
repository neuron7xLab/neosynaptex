# SSOT Registry

## Canonical Commands
- `§CMD:make:test-gate#432b561eca3c3c5e`: `python -m pytest -m "not (validation or property)" -q` (file:Makefile:L8-L8).
- `§CMD:make:lint#feb185397e880c72`: `ruff check .` + `pylint src/bnsyn` (file:Makefile:L140-L143).
- `§CMD:make:mypy#16b7f58d110ef0fb`: `mypy src --strict --config-file pyproject.toml` (file:Makefile:L144-L145).
- `§CMD:make:build#46174ef38e397e02`: `python -m build` (file:Makefile:L199-L200).

## Invariants
- `§INV:determinism:seeded_rng#398b20aa24034c4f`: seeded RNG path is deterministic (file:src/bnsyn/rng.py:L51-L122).
- `§INV:config:bounded_params#6a6369457458f293`: Pydantic bounds enforce safe param domains (file:src/bnsyn/config.py:L26-L288).

## Gates
- `§GAT:CI:ci-pr-atomic#bbc71bd4909c7ea9` required CI workflow (file:.github/workflows/ci-pr-atomic.yml:L1-L554).

## Recorded Contradictions
- `§RIS:contradiction:test-marker-contract#0cb50848744f45fb` unresolved policy-vs-runtime test marker mismatch (file:AGENTS.md:L30-L33 / file:Makefile:L8-L8).
