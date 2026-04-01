# CONTRACTS Index

Authoritative P0/P1 contracts extracted from critical-path modules and gates.

## §CFG:src/bnsyn/config.py:BaseModels#99fbf8a5537a4faf
- Name: `bnsyn.config models`
- Summary: Pydantic parameter schemas for neuron/synapse/plasticity/criticality/temperature/energy invariants.
- Inputs: typed numeric params
- Outputs: validated config objects
- Preconditions: constraints satisfied (PositiveFloat, bounds)
- Postconditions: validated deterministic parameter set
- Failure modes: ValidationError
- Determinism: yes
- Evidence:
  - `file:src/bnsyn/config.py:L1-L288`
  - `file:docs/SPEC.md:L1-L200`

## §CMD:make:build#46174ef38e397e02
- Name: `build`
- Summary: Package build artifact creation.
- Inputs: ∅
- Outputs: process exit code
- Preconditions: ∅
- Postconditions: ∅
- Failure modes: non-zero exit on gate failure
- Determinism: conditional
- Evidence:
  - `file:Makefile:L199-L200`
  - `file:AGENTS.md:L33-L33`

## §CMD:make:lint#feb185397e880c72
- Name: `lint`
- Summary: Static quality gate with ruff+pylint.
- Inputs: ∅
- Outputs: process exit code
- Preconditions: ∅
- Postconditions: ∅
- Failure modes: non-zero exit on gate failure
- Determinism: conditional
- Evidence:
  - `file:Makefile:L140-L143`
  - `file:AGENTS.md:L31-L31`

## §CMD:make:mypy#16b7f58d110ef0fb
- Name: `mypy`
- Summary: Strict typecheck gate.
- Inputs: ∅
- Outputs: process exit code
- Preconditions: ∅
- Postconditions: ∅
- Failure modes: non-zero exit on gate failure
- Determinism: conditional
- Evidence:
  - `file:Makefile:L144-L145`
  - `file:AGENTS.md:L32-L32`

## §CMD:make:test-gate#432b561eca3c3c5e
- Name: `test-gate`
- Summary: Primary fast test gate excluding validation/property.
- Inputs: ∅
- Outputs: process exit code
- Preconditions: ∅
- Postconditions: ∅
- Failure modes: non-zero exit on gate failure
- Determinism: conditional
- Evidence:
  - `file:Makefile:L8-L8`
  - `file:Makefile:L57-L59`
  - `file:docs/TESTING.md:L21-L25`

## §FUN:src/bnsyn/cli.py:main()#a164a2ef0e7ba513
- Name: `main`
- Summary: Parses CLI args and dispatches subcommands for runtime operations.
- Inputs: argv optional
- Outputs: int exit code
- Preconditions: CLI arguments conform to parser
- Postconditions: selected command handler executes
- Failure modes: SystemExit for invalid args
- Determinism: conditional
- Evidence:
  - `file:src/bnsyn/cli.py:L443-L533`
  - `file:pyproject.toml:L75-L76`

## §FUN:src/bnsyn/rng.py:seed_all(seed:int)#3d349752e0a011eb
- Name: `seed_all`
- Summary: Creates RNGPack and seeds python/numpy streams.
- Inputs: seed:int
- Outputs: RNGPack
- Preconditions: integer seed
- Postconditions: deterministic RNG state initialized
- Failure modes: ∅
- Determinism: yes
- Evidence:
  - `file:src/bnsyn/rng.py:L51-L92`

## §GAT:CI:ci-pr-atomic#bbc71bd4909c7ea9
- Name: `ci-pr-atomic`
- Summary: PR atomic CI orchestrating reusable quality/pytest/science gates.
- Inputs: push/pull_request events
- Outputs: status checks
- Preconditions: workflow triggers
- Postconditions: required jobs executed
- Failure modes: job failure blocks merge
- Determinism: conditional
- Evidence:
  - `file:.github/workflows/ci-pr-atomic.yml:L1-L554`
  - `file:.github/workflows/_reusable_pytest.yml:L1-L257`

## §INV:determinism:seeded_rng#398b20aa24034c4f
- Name: `seeded_rng`
- Summary: Simulation randomness must be seeded through bnsyn.rng to ensure replayable outputs.
- Inputs: seed
- Outputs: repeatable stochastic streams
- Preconditions: seed_all used
- Postconditions: same seed => same streams
- Failure modes: unseeded paths nondeterministic
- Determinism: yes
- Evidence:
  - `file:src/bnsyn/rng.py:L51-L122`
  - `file:tests/test_determinism.py:L1-L200`

## §MOD:src/bnsyn/cli.py#3670dc50ae2fad1c
- Name: `bnsyn.cli`
- Summary: CLI entry surface exposing demo, dtcheck, experiments, sleep-stack command paths.
- Inputs: argv
- Outputs: stdout JSON / status
- Preconditions: valid argparse command
- Postconditions: delegates to simulation/control modules
- Failure modes: SystemExit on argparse failures
- Determinism: conditional
- Evidence:
  - `file:src/bnsyn/cli.py:L1-L537`

## §MOD:src/bnsyn/rng.py#a82f3dfe6131aa15
- Name: `bnsyn.rng`
- Summary: Central deterministic RNG utilities with split support for reproducibility.
- Inputs: seed ints
- Outputs: RNGPack
- Preconditions: seed provided
- Postconditions: numpy and random seeded consistently
- Failure modes: ValueError for invalid split count
- Determinism: yes
- Evidence:
  - `file:src/bnsyn/rng.py:L1-L122`

## §RIS:contradiction:test-marker-contract#0cb50848744f45fb
- Name: `test-marker-contract-mismatch`
- Summary: AGENTS.md test command excludes only validation, while Makefile/docs exclude both validation and property.
- Inputs: ∅
- Outputs: risk record
- Preconditions: ∅
- Postconditions: mismatch explicit
- Failure modes: ∅
- Determinism: yes
- Evidence:
  - `file:AGENTS.md:L30-L33`
  - `file:Makefile:L8-L8`
  - `file:docs/TESTING.md:L21-L25`
