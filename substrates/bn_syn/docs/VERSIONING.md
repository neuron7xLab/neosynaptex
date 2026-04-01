# Versioning

Current package version is defined in `pyproject.toml` (`project.version`).

## Semver trigger policy
Semver action is required only when a `stable` public surface changes:
- CLI behavior/flags/default outputs.
- Schema required fields/types.
- Documented stable Python API signature/semantics.

## Current gap
- MISSING: explicit release procedure that maps surface change classes to version bump level.
  - DERIVE FROM: release workflow + maintainer policy.
  - ACTION: encode bump rules in release checklist and changelog policy.
