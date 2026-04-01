# ADR-0011: Type Strictness Escalation Path

## Status
Accepted

## Context
mypy strict is enforced for `types/` and `security/`. The rest of the codebase (core, analytics, neurochem, pipelines, integration) has ~650 strict-mode errors. Full strict enforcement requires significant migration effort.

## Decision
Phased escalation:
1. **v4.1.x** — strict on `types/`, `security/`. Errors visible but not blocking for rest.
2. **v4.2.0** — strict on `core/detect.py`, `core/compare.py`, `core/forecast.py`, `neurochem/`.
3. **v5.0.0** — strict on entire `core/` and `analytics/`.

Each phase removes `disallow_untyped_defs = false` for target modules and fixes all errors before merge.

## Consequences
- Type safety improves incrementally without blocking releases.
- Each phase has clear scope and acceptance criteria.
- `# type: ignore` count tracked per release as quality metric.
