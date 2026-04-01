# Architecture Hygiene Policy

**Document Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Active

## Purpose

This policy defines the architectural hygiene rules for MLSDM. It ensures that new modules and subsystems stay aligned with the layered architecture, keep dependencies directional, and remain discoverable.

## Scope

Applies to all new Python modules, packages, and subsystems under `src/mlsdm/` and to any documentation that describes or constrains architecture.

## Single Source for New Modules

**All new code modules MUST live under `src/mlsdm/`**.

- New modules are not permitted in `scripts/`, `tests/`, or `examples/` unless they are test harnesses or tooling that do not ship with the runtime.
- If a new capability needs to be exposed externally, add it as a package under `src/mlsdm/<layer_or_domain>/` and document it in the architecture manifest.

## No Cross-Layer Imports

**Rule:** Code may only import dependencies within the same layer or from lower layers, as defined in the architecture manifest.

- “Lower layer” means closer to foundational utilities (`utils`) and shared infrastructure (`observability`, `security`).
- Cross-layer imports that violate the manifest are prohibited.
- Enforcement: `tests/contracts/test_architecture_manifest.py` validates layer dependency rules.

## Adding a New Package or Subsystem

When introducing a new package or subsystem:

1. **Choose the layer:**
   - Place the package under `src/mlsdm/<layer_or_domain>/` aligned with the existing layer model in `docs/ARCHITECTURE_SPEC.md`.
2. **Register in the manifest:**
   - Update `src/mlsdm/config/architecture_manifest.py` with the new package, layer, and allowed dependencies.
3. **Update architecture docs:**
   - Add or update references in `docs/ARCHITECTURE_SPEC.md` and related docs so the subsystem is visible to maintainers.
4. **Validate dependency direction:**
   - Ensure the new package imports only allowed dependencies and passes the architecture manifest tests.
5. **Document public interfaces:**
   - Expose clear entry points and document the intended API in the appropriate docs (`docs/DEVELOPER_GUIDE.md` or module-specific documentation).

## Compliance Checklist

- [ ] New module under `src/mlsdm/`.
- [ ] Architecture manifest updated with layer + allowed dependencies.
- [ ] No cross-layer imports (validated by tests).
- [ ] Architecture docs updated with subsystem references.
- [ ] Public interfaces documented.

## Architecture Hygiene Register

Architectural hygiene gaps are tracked in the register below, including ownership and review cadence:

- [ARCHITECTURE_HYGIENE_REGISTER.md](ARCHITECTURE_HYGIENE_REGISTER.md)
