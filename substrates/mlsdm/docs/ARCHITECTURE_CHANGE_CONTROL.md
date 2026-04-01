# Architecture Change Control

This document defines when to create an Architecture Decision Record (ADR) and when to update
architecture artifacts and contract tests. It is a process document only; it does not change
implementation behavior.

## Scope

Applies to structural, interface, and dependency changes that affect system architecture,
runtime boundaries, or external contracts. Examples include:

- New or removed services, modules, or major subsystems.
- Changes to data/control flow between components.
- New external dependencies or platform/runtime constraints.
- New, removed, or modified public APIs, schemas, or SDK surface.
- Changes to risk boundaries, security/guardrail layers, or observability topology.

## When an ADR is required

Create a new ADR when **any** of the following occur:

- A durable architectural decision with trade-offs (e.g., new subsystem, pattern, or protocol).
- A change that impacts component boundaries, contracts, or system responsibilities.
- Adoption/rejection of a major dependency, framework, or infrastructure layer.
- A change that affects safety/guardrails, risk controls, or compliance posture.
- A decision that will constrain future design choices or compatibility.

No ADR is needed for:

- Pure refactors without boundary/contract changes.
- Bug fixes or localized optimizations that do not alter architecture contracts.

ADR location: `docs/adr/`.

## When to update `docs/ARCHITECTURE_SPEC.md`

Update the architecture specification when the **documented system structure or interfaces**
change, including:

- Component boundaries, responsibilities, or interactions.
- Critical data/control flows and lifecycle states.
- External interfaces or integration points.
- Any architectural constraints, invariants, or guarantees.

If the ADR introduces new constraints or alters system structure, update
`docs/ARCHITECTURE_SPEC.md` in the same change set.

## When to update `src/mlsdm/config/architecture_manifest.py`

Update the manifest when the **implemented component inventory or wiring** changes, including:

- New or removed components, services, or modules captured by the manifest.
- Changes to component identifiers, categories, or ownership boundaries.
- Changes to documented dependencies between components.

The manifest is an implementation-facing index and must reflect reality at all times.

## When to update contract tests

Update or add contract tests whenever an external or inter-module contract changes, including:

- HTTP API request/response schemas or error formats.
- SDK client behavior tied to the API contract.
- Configuration or environment constraints that are externally observable.
- Security, policy, or governance guarantees exposed by the interface.

Relevant test locations include:

- `tests/api/test_http_contracts.py`
- `tests/sdk/`
- `tests/contracts/`

## Structural change checklist (required)

For any structural change, verify that the following artifacts are updated as applicable:

- [ ] ADR in `docs/adr/` (if the change is a durable architectural decision).
- [ ] `docs/ARCHITECTURE_SPEC.md`
- [ ] `src/mlsdm/config/architecture_manifest.py`
- [ ] Contract tests (`tests/api/test_http_contracts.py`, `tests/sdk/`, `tests/contracts/`)
- [ ] Any interface specs (`docs/API_CONTRACT.md`, `docs/API_REFERENCE.md`, SDK docs)
- [ ] Observability or risk docs if boundaries or controls changed.

