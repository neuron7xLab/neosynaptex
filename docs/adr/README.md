# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the
`neosynaptex` project. Each ADR captures a significant design decision,
its context, the options considered, and the rationale for the choice.

ADRs are immutable once accepted. Superseded ADRs are marked with a
`Superseded by` note at the top rather than deleted.

---

## Index

| ID | Title | Status |
|----|-------|--------|
| [ADR-001](ADR-001-single-file-engine.md) | Single-file engine (`neosynaptex.py`) | Accepted |
| [ADR-002](ADR-002-agpl-license.md) | AGPL-3.0 license | Accepted |
| [ADR-003](ADR-003-theil-sen-estimator.md) | Theil-Sen estimator for gamma | Accepted |

---

## Format

Each ADR follows this template:

```
# ADR-NNN — Title

**Status:** Proposed / Accepted / Deprecated / Superseded by ADR-NNN

## Context
## Decision
## Consequences
## Alternatives considered
```

---

## Adding a New ADR

1. Copy the template above.
2. Assign the next sequential number.
3. Open a PR — the ADR must be reviewed before merging.
4. Accepted ADRs are locked (no substantive edits after merge).
