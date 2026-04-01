# BN-Syn Integration Architecture (CLI + Experiment Runner + Simulation)

This document defines the evidence-backed integration architecture for the
BN-Syn deterministic experiment runner. It is scoped to the module-level
integration between the CLI entrypoint, declarative experiment runner, schema
validation, and the simulation core.

## Components (Evidence-Backed Inventory)

| Component | Responsibility | Language/Runtime | Interfaces | Configuration |
| --- | --- | --- | --- | --- |
| `bnsyn.cli` | CLI entrypoint, subcommand dispatch, orchestration for demo/run/sleep-stack | Python 3.11+ | CLI (`bnsyn`), subcommands: `demo`, `run`, `dtcheck`, `sleep-stack` | Argparse flags; config path for `run` | 
| `bnsyn.experiments.declarative` | YAML-driven experiment runner, schema validation, result persistence | Python 3.11+ | Python API (`load_config`, `run_experiment`, `run_from_yaml`) | YAML config |
| `bnsyn.schemas.experiment` / `schemas/experiment.schema.json` | Explicit experiment config schema | JSON Schema / Pydantic | Schema validation | YAML config object |
| `bnsyn.sim.network.run_simulation` | Deterministic network simulator producing metrics | Python 3.11+ | Python API | Explicit args (steps, dt_ms, seed, N, backend) |

## Integration Architecture (Text Diagram)

```
CLI (bnsyn.cli)
  └─ "run" subcommand
       └─ run_from_yaml(config_path, output_path)
            ├─ load_config -> BNSynExperimentConfig (schema validation)
            ├─ run_experiment
            │    └─ run_simulation (per seed)
            └─ output JSON (stdout or file)
```

### Rationale
This is an in-process modular integration. Each component is a Python module
in the same package; the interfaces are explicit function calls with validated
inputs. The CLI is a thin orchestration layer that delegates to the declarative
runner. The declarative runner performs schema validation and invokes the
deterministic simulator. This aligns with existing contracts for determinism
and schema validation.

## Explicit Contracts

### Contract: Experiment Configuration (Versioned Schema)
- Schema: `schemas/experiment.schema.json` (JSON Schema draft-07).
- Versioning: `experiment.version` is required and matches `^v[0-9]+$`.
- Validation boundary: `bnsyn.experiments.declarative.load_config`.
- Ownership: configuration is owned by the experiment runner; callers supply
  the YAML payload.

### Contract: CLI `run` Subcommand
- Inputs:
  - `config`: path to YAML config.
  - `output`: optional JSON output path.
- Execution semantics:
  - Validates YAML against schema.
  - Runs deterministic simulation per seed.
  - Writes JSON to output if provided; otherwise prints to stdout.
- Failure semantics:
  - Any error returns non-zero exit code.

### Contract: Simulation API
- `run_simulation(steps, dt_ms, seed, N, backend, external_current_pA) -> metrics`
- Determinism:
  - Uses explicit seeding (`seed_all`).
  - No hidden global RNG state.
- Output:
  - `sigma_mean`, `sigma_std`, `rate_mean_hz`, `rate_std` as floats.

## Composition & Configuration

### Startup Order
1. CLI parses args and selects subcommand.
2. `run_from_yaml` loads and validates config.
3. `run_experiment` runs deterministic simulations.
4. Results are written to JSON or stdout.

### Configuration Sources
1. CLI args (highest precedence).
2. YAML config file (validated).

### Environment Separation
No implicit environment coupling is required for `run`. Optional modules
(visualization, GPU backends) are not in the `run` path.

## Integration Tests (Deterministic)

Minimum end-to-end checks:
- Validate YAML -> schema -> run_simulation -> JSON output.
- Validate failure on missing or invalid config (already covered in tests).

## Observability & Operability

### Logs
- CLI prints validation and summary outputs to stdout.
### Metrics
- Output JSON includes per-seed metrics and aggregated config details.
### Integration Broken Signals
- Non-zero CLI exit code on validation or runtime errors.
- JSON output missing expected keys.

## Local Reproduction

```
python -m bnsyn.cli run examples/configs/quickstart.yaml -o results/quickstart_v1.json
```

## Evidence Ledger

- CLI entrypoint and subcommands: `bnsyn.cli` (`demo`, `run`, `dtcheck`, `sleep-stack`). Evidence: `src/bnsyn/cli.py`.
- Declarative runner and YAML loader: `bnsyn.experiments.declarative` (`load_config`, `run_experiment`, `run_from_yaml`). Evidence: `src/bnsyn/experiments/declarative.py`.
- Experiment schema: `schemas/experiment.schema.json` (JSON Schema draft-07). Evidence: `schemas/experiment.schema.json`.
- Deterministic simulation API: `run_simulation` in `bnsyn.sim.network`. Evidence: `src/bnsyn/sim/network.py`.
- Example config used for local reproduction: `examples/configs/quickstart.yaml`. Evidence: `examples/configs/quickstart.yaml`.
- Existing CLI tests: `tests/test_cli_interactive.py`. Evidence: `tests/test_cli_interactive.py`.

## Decisions

- Integration profile: PROFILE_MIN (single runtime, in-process modular integration).
- Rationale: All components are Python modules in one package, with direct call boundaries
  and explicit schema validation. No external services or deployment orchestration exist
  in this integration path.

## Changeset

- Added this document to define integration contracts, composition, and gates.
- Added an end-to-end integration test in `tests/test_integration_experiment_flow.py`.

## Local Reproduction (Integration Gate)

```
pytest -q tests/test_integration_experiment_flow.py
```

## Acceptance Checklist

- [ ] CLI `run` path validates YAML against schema.
- [ ] `run_experiment` invokes deterministic `run_simulation` per seed.
- [ ] Output JSON contains config metadata and per-seed metrics.
- [ ] Integration test is deterministic and passes locally with dependencies installed.
- [ ] Integration flow is observable via CLI stdout and JSON output.

## Risks & Mitigations

- Risk: Missing optional test dependency (`hypothesis`) blocks running tests in some
  environments. Mitigation: ensure dev/test dependencies are installed per repo
  guidance before running pytest.
- Risk: YAML config invalid or missing fields. Mitigation: strict schema validation in
  `load_config` with explicit error messages.

## Rollback Plan

- Revert the commit that added `docs/INTEGRATION.md` and
  `tests/test_integration_experiment_flow.py`.
- No runtime behavior changes; rollback removes documentation/test only.
