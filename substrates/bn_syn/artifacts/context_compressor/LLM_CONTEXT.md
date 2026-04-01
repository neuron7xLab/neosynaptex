# 1) Repo Identity + Surface Summary
- Repo: `/workspace/bnsyn-phase-controlled-emergent-dynamics`.
- Commit: `6bde36ce17d6b59c9cf01dd06e6be233bd62250b`.
- Surface: Python package/library+CLI (`bnsyn`) with scientific simulation modules, strict config schemas, and CI-heavy quality gates.
- Evidence: `file:pyproject.toml:L75-L76`, `file:src/bnsyn/cli.py:L443-L533`.

# 2) Canonical Commands (install/test/lint/type/security/docs/release)
- Install: `python -m pip install -e ".[dev,test]"` (`file:Makefile:L7-L14`).
- Test: `python -m pytest -m "not (validation or property)" -q` (`file:Makefile:L8-L8`).
- Lint: `ruff check .` + `pylint src/bnsyn` (`file:Makefile:L140-L143`).
- Typecheck: `mypy src --strict --config-file pyproject.toml` (`file:Makefile:L144-L145`).
- Build: `python -m build` (`file:Makefile:L199-L200`).
- Docs: `make docs` (`file:Makefile:L193-L194`).
- Release readiness: `python -m scripts.release_readiness` (`file:Makefile:L207-L209`).

# 3) Critical Paths (P0)
- CLI path: `pyproject script bnsyn -> bnsyn.cli:main -> command handlers` (`file:pyproject.toml:L75-L76`, `file:src/bnsyn/cli.py:L443-L533`).
- Determinism path: `seed_all -> RNGPack/split -> determinism tests` (`file:src/bnsyn/rng.py:L51-L122`, `file:tests/test_determinism.py:L1-L200`).
- CI path: `ci-pr-atomic workflow -> reusable pytest/quality gates` (`file:.github/workflows/ci-pr-atomic.yml:L1-L554`, `file:.github/workflows/_reusable_pytest.yml:L1-L257`).

# 4) Contracts Index (P0/P1 only)
- `§CFG:src/bnsyn/config.py:BaseModels#99fbf8a5537a4faf`: Pydantic parameter schemas for neuron/synapse/plasticity/criticality/temperature/energy invariants.
- `§CMD:make:build#46174ef38e397e02`: Package build artifact creation.
- `§CMD:make:lint#feb185397e880c72`: Static quality gate with ruff+pylint.
- `§CMD:make:mypy#16b7f58d110ef0fb`: Strict typecheck gate.
- `§CMD:make:test-gate#432b561eca3c3c5e`: Primary fast test gate excluding validation/property.
- `§FUN:src/bnsyn/cli.py:main()#a164a2ef0e7ba513`: Parses CLI args and dispatches subcommands for runtime operations.
- `§FUN:src/bnsyn/rng.py:seed_all(seed:int)#3d349752e0a011eb`: Creates RNGPack and seeds python/numpy streams.
- `§GAT:CI:ci-pr-atomic#bbc71bd4909c7ea9`: PR atomic CI orchestrating reusable quality/pytest/science gates.
- `§INV:determinism:seeded_rng#398b20aa24034c4f`: Simulation randomness must be seeded through bnsyn.rng to ensure replayable outputs.
- `§MOD:src/bnsyn/cli.py#3670dc50ae2fad1c`: CLI entry surface exposing demo, dtcheck, experiments, sleep-stack command paths.
- `§MOD:src/bnsyn/rng.py#a82f3dfe6131aa15`: Central deterministic RNG utilities with split support for reproducibility.

# 5) Invariants & SSOT (P0/P1 only)
- `§INV:determinism:seeded_rng#398b20aa24034c4f` seeded RNG determinism invariant.
- Bounded parameter invariants enforced in config models (PositiveFloat and explicit bounds).
- Canonical gate commands sourced from Makefile and aligned policy docs.

# 6) Gates & Required Evidence (P0/P1 only)
- Required evidence pointer formats: `file:...`, `hash:sha256:...`, `cmd:... -> log:...`.
- Gate evidence must map to Makefile/workflow lines and command logs in `proof_bundle/logs/`.
- Current risk: AGENTS test command mismatch with Makefile/docs (see RIS node).

# 7) Open Risks (P0/P1 only)
- No unresolved P0/P1 contradictions in current truth map.

# 8) EXPAND Protocol (how to rehydrate details)
- Syntax: `EXPAND <ID> [depth=N] [include={contracts|edges|evidence|snippets}] [budget=chars]`.
- Expansion source: KG.json node + evidence pointers only.
- Fail-closed: if any evidence pointer is missing, expansion is refused.
- Snippet expansion must preserve exact source line ranges from evidence pointers.
