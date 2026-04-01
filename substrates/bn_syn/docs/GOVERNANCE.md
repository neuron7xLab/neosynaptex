# BN-Syn Governance

This document is the **one-page governance entry** for the BN-Syn repository.
It links to all authoritative governance artifacts without duplicating their content.

---

## Governance Overview

BN-Syn uses a **Single-Source-of-Truth (SSOT)** governance model where:

- Scientific claims are traceable to peer-reviewed sources
- Documentation and validators are kept in sync (isomorphic)
- Changes are validated by automated CI gates

---

## Authority Chain

| Layer | Document | Purpose |
|-------|----------|---------|
| **Rules** | [SSOT_RULES.md](SSOT_RULES.md) | Machine-readable rule registry (authoritative) |
| **Policy** | [SSOT.md](SSOT.md) | Human-readable SSOT policy summary |
| **Data** | <a href="../bibliography/bnsyn.bib">bibliography/bnsyn.bib</a>, <a href="../bibliography/mapping.yml">bibliography/mapping.yml</a>, <a href="../claims/claims.yml">claims/claims.yml</a> | SSOT data artifacts |
| **Validators** | <a href="../scripts/validate_bibliography.py">scripts/validate_bibliography.py</a>, <a href="../scripts/validate_claims.py">scripts/validate_claims.py</a>, <a href="../scripts/scan_normative_tags.py">scripts/scan_normative_tags.py</a> | Enforcement scripts |
| **Labels** | [NORMATIVE_LABELING.md](NORMATIVE_LABELING.md) | Normative vs non-normative labeling |
| **Audit** | [CONSTITUTIONAL_AUDIT.md](CONSTITUTIONAL_AUDIT.md) | Constitutional constraints |

---

## Key Governance Concepts

### Tier System

| Tier | Description | Normative |
|------|-------------|-----------|
| **Tier-A** | Peer-reviewed sources with DOI | Yes |
| **Tier-S** | Standards/documentation (no DOI) | No |
| **Tier-B** | Conference/workshop papers | No |
| **Tier-C** | Other sources | No |

### Claim Binding

- Normative quantitative statements include identifiers such as `CLM-0001`
- Claim IDs are authoritative in [claims/claims.yml](../claims/claims.yml)
- Mappings are defined in [bibliography/mapping.yml](../bibliography/mapping.yml)

### Evidence Closure

- Claims, mappings, and bibliography form a **closed set**
- [sources.lock](../bibliography/sources.lock) carries deterministic hashes
- Validators enforce alignment between all SSOT artifacts

---

## Enforcement

### Validators

| Script | Purpose |
|--------|---------|
| `scripts/validate_bibliography.py` | Validates bibliography SSOT closure |
| `scripts/validate_claims.py` | Validates claims ledger |
| `scripts/scan_normative_tags.py` | Scans for orphan normative statements |

### CI Gates

| Workflow | Triggers | Gates |
|----------|----------|-------|
| [ci-smoke.yml](../.github/workflows/ci-smoke.yml) | Every PR | SSOT + smoke tests |
| [ci-validation.yml](../.github/workflows/ci-validation.yml) | Weekly + manual | SSOT + validation tests |

---

## Quick Commands

```bash
# Run all SSOT validators
python -m scripts.validate_bibliography
python -m scripts.validate_claims
python -m scripts.scan_normative_tags

# Or use Makefile
make ssot
```

---

## Related Documents

- [INDEX.md](INDEX.md) — Full documentation index
- [INVENTORY.md](INVENTORY.md) — Governed path inventory
- [REPRODUCIBILITY.md](REPRODUCIBILITY.md) — Determinism protocol
- [ARCHITECTURE.md](ARCHITECTURE.md) — Architecture crosswalk
