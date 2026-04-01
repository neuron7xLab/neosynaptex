# ADR-0006: Architecture manifest covers every top-level module

**Status**: Accepted
**Date**: 2026-01-10
**Deciders**: MLSDM Architecture Working Group
**Categories**: Architecture | Testing

## Context

The architecture manifest is the primary source of truth for module boundaries, public
interfaces, and dependency constraints. It previously covered only a subset of the
`src/mlsdm/` module directories, which created drift between the real package layout
and the manifest. This drift made it harder to reason about decision loops, risk gating,
and adaptation responsibilities across modules, and increased the risk of missing
boundary violations as new packages were added.

## Decision

We will enumerate every top-level module directory under `src/mlsdm/` in
`ARCHITECTURE_MANIFEST`, and we will enforce this coverage with a contract test that
fails if any module directory is missing. Each module entry documents its layer,
responsibilities (including decision loops, risk-gating, and adaptation loops where
relevant), public interfaces, and allowed dependencies.

## Consequences

### Positive

- Manifest coverage stays aligned with the actual package structure.
- Architecture reviews have a single, complete reference for module boundaries.
- Tests catch new modules that are added without updating the manifest.

### Negative

- Adding a new top-level module now requires an explicit manifest entry.
- Manifest maintenance needs to keep pace with directory changes.

### Neutral

- No runtime behavior changes; validation remains test-only.

## Alternatives Considered

### Alternative 1: Keep a partial manifest

- **Description**: Continue tracking only the “primary” modules in the manifest.
- **Pros**: Less manifest maintenance.
- **Cons**: Drift persists, and architectural boundaries remain undocumented for newer modules.
- **Reason for rejection**: Incomplete coverage undermines the manifest’s purpose.

### Alternative 2: Auto-generate module entries

- **Description**: Generate module entries dynamically from directory scanning.
- **Pros**: Minimal manual upkeep.
- **Cons**: Loses curated responsibilities and dependency constraints.
- **Reason for rejection**: The manifest is intended to encode deliberate architectural intent.

## Implementation

- Expand `src/mlsdm/config/architecture_manifest.py` with entries for every top-level
  module directory.
- Extend `tests/contracts/test_architecture_manifest.py` to assert full coverage.

### Affected Components

- `src/mlsdm/config/architecture_manifest.py`
- `tests/contracts/test_architecture_manifest.py`

### Related Documents

- `docs/adr/0001-use-adrs.md`

## References

- N/A

---

*Template based on [Michael Nygard's ADR format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)*
