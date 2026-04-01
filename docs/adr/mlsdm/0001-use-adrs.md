# ADR-0001: Use Architecture Decision Records

**Status**: Accepted
**Date**: 2025-11-30
**Deciders**: MLSDM Core Team
**Categories**: Architecture, Documentation

## Context

MLSDM is a neurobiologically-grounded cognitive architecture with moral governance; readiness is tracked in [status/READINESS.md](../status/READINESS.md). The system makes numerous non-obvious architectural decisions derived from neuroscience research, AI safety principles, and production reliability requirements.

Current challenges:
- **Knowledge silos**: New contributors struggle to understand *why* specific design choices were made
- **Decision drift**: Without documented rationale, decisions may be unknowingly reversed
- **Onboarding friction**: Principal engineers evaluating the system need to understand the reasoning behind the architecture
- **Maintenance burden**: Without context, future maintainers may make incompatible changes

The project already has comprehensive documentation:
- `ARCHITECTURE_SPEC.md` - describes *what* the system does
- `docs/NEURO_FOUNDATIONS.md` - explains the neuroscience basis
- `docs/FORMAL_INVARIANTS.md` - defines system invariants

However, none of these documents capture *why* specific architectural choices were made among alternatives.

## Decision

We will adopt Architecture Decision Records (ADRs) to document significant architectural decisions.

ADR characteristics:
1. **Immutable once accepted**: ADRs are not deleted; they are superseded
2. **Lightweight**: Each ADR focuses on one decision
3. **Contextual**: Include forces, constraints, and alternatives considered
4. **Discoverable**: Stored in `docs/adr/` with sequential numbering
5. **Version controlled**: ADRs evolve with the codebase

Initial ADRs will cover:
- ADR-0001: This decision (meta-ADR)
- ADR-0002: Phase-Entangled Lattice Memory (PELM) design
- ADR-0003: Moral Filter algorithm with adaptive threshold
- ADR-0004: Memory bounds (CORE-04 invariant)

## Consequences

### Positive

- **Preserved knowledge**: Rationale is captured at decision time
- **Faster onboarding**: New contributors understand *why* not just *what*
- **Better decisions**: Writing ADRs forces rigorous analysis of alternatives
- **Audit trail**: History of architectural evolution is preserved
- **Reduced re-litigation**: Decisions aren't constantly revisited

### Negative

- **Maintenance overhead**: ADRs need to be written and kept discoverable
- **Learning curve**: Contributors need to learn ADR format and process
- **Possible staleness**: ADRs may become outdated if not maintained

### Neutral

- ADRs are supplementary to existing documentation, not a replacement
- The template provides structure but should not constrain expression

## Alternatives Considered

### Alternative 1: Inline Code Comments

- **Description**: Document decisions in code comments near implementation
- **Pros**: Co-located with code, always visible during development
- **Cons**: Scattered, hard to discover, lacks structure, doesn't capture alternatives
- **Reason for rejection**: Insufficient for complex architectural decisions

### Alternative 2: Wiki Documentation

- **Description**: Use GitHub Wiki or external wiki for decision documentation
- **Pros**: Easy to edit, supports rich formatting
- **Cons**: Not version-controlled with code, can diverge from implementation
- **Reason for rejection**: Documentation should live with the code

### Alternative 3: RFC Process

- **Description**: Formal Request for Comments process for all changes
- **Pros**: Rigorous review process, community input
- **Cons**: High overhead for smaller decisions, slower velocity
- **Reason for rejection**: Too heavyweight for most architectural decisions

## Implementation

### Directory Structure

```
docs/adr/
├── 0000-adr-template.md     # Template for new ADRs
├── 0001-use-adrs.md         # This document
├── 0002-pelm-design.md      # PELM architecture
├── 0003-moral-filter.md     # Moral filter algorithm
└── 0004-memory-bounds.md    # Memory bounds invariant
```

### Naming Convention

- Format: `NNNN-short-title.md`
- Numbers are sequential, zero-padded to 4 digits
- Titles are lowercase, hyphenated

### ADR Lifecycle

1. **Proposed**: Initial draft for review
2. **Accepted**: Approved and implemented
3. **Deprecated**: No longer applies (e.g., feature removed)
4. **Superseded**: Replaced by a new ADR (link to successor)

### Related Documents

- `docs/adr/0000-adr-template.md` - Template for new ADRs
- `CONTRIBUTING.md` - Should reference ADR process for significant changes
- `ARCHITECTURE_SPEC.md` - High-level architecture overview

## References

- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (2011)
- GitHub, [Using Architecture Decision Records](https://adr.github.io/)
- Joel Parker Henderson, [ADR GitHub Organization](https://github.com/joelparkerhenderson/architecture-decision-record)

---

*This ADR was created as part of DOC-001 from PROD_GAPS.md*
