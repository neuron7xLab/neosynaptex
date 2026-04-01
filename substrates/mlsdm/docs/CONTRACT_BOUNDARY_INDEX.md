# Contract Boundary Index

This document summarizes the contract boundaries for each MLSDM subsystem as defined in
`src/mlsdm/config/architecture_manifest.py` and enforced by the contract test suite in
`tests/contracts/`. Use it as the index for API surfaces, allowed dependencies, and
invariants that must remain stable when making changes.

## Source of truth

* Architecture manifest: `src/mlsdm/config/architecture_manifest.py`
* Contract tests: `tests/contracts/`

## Subsystem boundaries

### API (`src/mlsdm/api`)

* **API / contracts**
  * Public interfaces: `app.py`, `health.py`, `schemas.py`.
  * API schemas should remain compatible with contract models (see engine/speech contracts).
* **Allowed dependencies**
  * `engine`, `core`, `router`, `security`, `observability`, `utils`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.
  * Response contracts used by `/infer` surface: `tests/contracts/test_engine_contracts.py`,
    `tests/contracts/test_speech_contracts.py`.

### SDK (`src/mlsdm/sdk`)

* **API / contracts**
  * Public interface: `neuro_engine_client.py` (client-facing SDK).
* **Allowed dependencies**
  * `engine`, `utils`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.
  * Engine output contract compatibility: `tests/contracts/test_engine_contracts.py`.

### Engine (`src/mlsdm/engine`)

* **API / contracts**
  * Public interfaces: `neuro_cognitive_engine.py`, `factory.py`.
  * Output contract defined by `EngineResult`, `EngineTiming`, `EngineValidationStep`,
    and `EngineErrorInfo` models.
* **Allowed dependencies**
  * `core`, `memory`, `router`, `security`, `observability`, `utils`.
* **Invariants (tests/contracts)**
  * Engine output contract stability: `tests/contracts/test_engine_contracts.py`.
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.

### Core (`src/mlsdm/core`)

* **API / contracts**
  * Public interfaces: `cognitive_controller.py`, `llm_pipeline.py`, `memory_manager.py`.
  * Speech governance metadata contract defined by `AphasiaReport`, `PipelineStepResult`,
    `PipelineMetadata`, and `AphasiaMetadata`.
* **Allowed dependencies**
  * `memory`, `security`, `observability`, `utils`.
* **Invariants (tests/contracts)**
  * Speech governance output contract: `tests/contracts/test_speech_contracts.py`.
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.

### Memory (`src/mlsdm/memory`)

* **API / contracts**
  * Public interfaces: `multi_level_memory.py`, `phase_entangled_lattice_memory.py`.
* **Allowed dependencies**
  * `utils`, `observability`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.

### Router (`src/mlsdm/router`)

* **API / contracts**
  * Public interface: `llm_router.py`.
* **Allowed dependencies**
  * `adapters`, `security`, `observability`, `utils`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.
  * Engine output contract compatibility (routing metadata):
    `tests/contracts/test_engine_contracts.py`.

### Adapters (`src/mlsdm/adapters`)

* **API / contracts**
  * Public interfaces: `provider_factory.py`, `llm_provider.py`.
* **Allowed dependencies**
  * `security`, `utils`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.

### Security (`src/mlsdm/security`)

* **API / contracts**
  * Public interfaces: `policy_engine.py`, `guardrails.py`, `payload_scrubber.py`.
  * Security logging and payload scrubbing behavior must remain stable.
* **Allowed dependencies**
  * `utils`, `observability`.
* **Invariants (tests/contracts)**
  * No secrets / PII in logs: `tests/contracts/test_no_secrets_in_logs.py`.
  * Policy-workflow alignment: `tests/contracts/test_policy_workflow_alignment.py`.
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.

### Observability (`src/mlsdm/observability`)

* **API / contracts**
  * Public interfaces: `logger.py`, `metrics.py`, `tracing.py`.
* **Allowed dependencies**
  * `utils`.
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.
  * Security log scrubbing is validated in `tests/contracts/test_no_secrets_in_logs.py`.

### Utils (`src/mlsdm/utils`)

* **API / contracts**
  * Public interfaces: `config_loader.py`, `config_validator.py`, `metrics.py`.
  * Shared primitives for config, safety helpers, and metrics must be stable.
* **Allowed dependencies**
  * None (foundation layer).
* **Invariants (tests/contracts)**
  * Architecture boundary validity: `tests/contracts/test_architecture_manifest.py`.
  * Security logging and scrubbing helpers validated in
    `tests/contracts/test_no_secrets_in_logs.py`.

## Change guidance

* Update the architecture manifest when adding new subsystems or changing public interfaces.
* Run the contract tests in `tests/contracts/` when changing API contracts or security
  behavior.
* Documentation-only updates should not change runtime behavior.
