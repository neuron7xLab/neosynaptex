# Repository Inventory

This document is the **authoritative list** of governed and non-governed paths in the BN-Syn repository.

## Normative language definition

Normative language in governed documents is **line-level** and is triggered by the
keywords listed below. Lines that contain any of these keywords are treated as
normative signals and are tagged with a NORMATIVE + CLM-#### tag in governed
documents.

```
must
shall
required
guarantee
```

## Governed documents (authoritative list)

The following list is consumed by `scripts/scan_governed_docs.py` and
`scripts/scan_normative_tags.py`. Only these files are scanned for normative
keywords and NORMATIVE claim bindings.

```yaml
governed_docs:
  - README.md
  - README_CLAIMS_GATE.md
  - docs/API_CONTRACT.md
  - docs/ARCHITECTURE.md
  - docs/AUDIT_LEDGER.md
  - docs/AUDIT_FINDINGS.md
  - docs/BENCHMARK_MAP.md
  - docs/BIBLIOGRAPHY.md
  - docs/CI_GATES.md
  - docs/COMPONENT_AUDIT.md
  - docs/CONSTITUTIONAL_AUDIT.md
  - docs/CRITICALITY_CONTROL_VS_MEASUREMENT.md
  - docs/EVIDENCE_COVERAGE.md
  - docs/GOVERNANCE.md
  - docs/INDEX.md
  - docs/INVENTORY.md
  - docs/NORMATIVE_LABELING.md
  - docs/PERFORMANCE.md
  - docs/PERFORMANCE_REPORT.md
  - docs/PHYSICAL_VALIDITY.md
  - docs/REPO_STRUCTURE.md
  - docs/REPRODUCIBILITY.md
  - docs/SCALABILITY_REPORT.md
  - docs/SECURITY_GITLEAKS.md
  - docs/SPEC.md
  - docs/SSOT.md
  - docs/SSOT_RULES.md
  - docs/VCG.md
  - docs/api/api_bnsyn.md
  - docs/api/index.md
  - docs/api/modules.md
  - docs/benchmarks/PROTOCOL.md
```

---

## Governed Paths

| Path | Purpose | Authority |
|------|---------|-----------|
| `docs/` | Formal specification, architecture, reproducibility, and governance docs | [SSOT.md](SSOT.md), [GOVERNANCE.md](GOVERNANCE.md) |
| `bibliography/` | SSOT bibliography (`bnsyn.bib`), mappings (`mapping.yml`), lockfile (`sources.lock`) | [SSOT.md](SSOT.md) |
| `claims/` | Evidence ledger for normative claims (`claims.yml`) | [SSOT.md](SSOT.md), [NORMATIVE_LABELING.md](NORMATIVE_LABELING.md) |
| `scripts/` | SSOT validators (`validate_bibliography.py`, `validate_claims.py`, `scan_governed_docs.py`, `scan_normative_tags.py`) | [SSOT.md](SSOT.md) |
| `.github/workflows/` | CI gates for SSOT + tests | [SSOT.md](SSOT.md) |
| `src/` | Reference implementation (`bnsyn`) | [SPEC.md](SPEC.md) |
| `tests/` | Smoke + validation tests | [SPEC.md](SPEC.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md) |

---

## Non-Governed Paths (NON-NORMATIVE)

| Path | Purpose | Notes |
|------|---------|-------|
| `docs/appendix/` | Imported working documents | Non-normative; illustrative only |
| `docs/appendix/EXECUTIVE_SUMMARY.md` | Imported executive summary | Do not cite for evidence |
| `docs/appendix/PRODUCTION_AUDIT.md` | Imported production audit | Do not cite for evidence |
| `docs/appendix/PRODUCTION_ROADMAP.md` | Imported roadmap | Do not cite for evidence |

---

## Documentation Hierarchy

```
docs/
├── INDEX.md                    # Navigation hub (start here)
├── SPEC.md                     # Formal specification (12 components)
├── ARCHITECTURE.md             # Architecture ↔ evidence crosswalk
├── GOVERNANCE.md               # Governance entry (single page)
├── SSOT.md                     # SSOT policy summary
├── SSOT_RULES.md               # Authoritative rule registry
├── REPRODUCIBILITY.md          # Determinism protocol
├── INVENTORY.md                # This file
├── BIBLIOGRAPHY.md             # Human-readable bibliography
├── EVIDENCE_COVERAGE.md        # Evidence coverage table
├── NORMATIVE_LABELING.md       # Labeling policy
├── CONSTITUTIONAL_AUDIT.md     # Constitutional constraints
├── VCG.md                      # VCG extension
├── CRITICALITY_CONTROL_VS_MEASUREMENT.md  # Criticality docs
├── AUDIT_FINDINGS.md           # Audit findings
├── AUDIT_LEDGER.md             # Audit ledger (findings → fixes)
└── appendix/                   # NON-NORMATIVE imports
    ├── EXECUTIVE_SUMMARY.md
    ├── PRODUCTION_AUDIT.md
    └── PRODUCTION_ROADMAP.md
```

---

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration + fixtures
├── test_*_smoke.py             # Smoke tests (fast, CI default)
├── test_determinism.py         # Determinism tests
├── test_dt_invariance.py       # Δt invariance tests
└── validation/                 # Validation tests (slow, statistical)
    ├── test_*_validation.py
    └── test_production_properties.py
```

---

## SSOT Artifact Closure

The following artifacts remain in sync (enforced by validators):

1. `bibliography/bnsyn.bib` — BibTeX entries
2. `bibliography/mapping.yml` — Claim ID → bibkey mappings
3. `bibliography/sources.lock` — Deterministic hash lock
4. `claims/claims.yml` — Evidence ledger

See [SSOT_RULES.md](SSOT_RULES.md) for the authoritative rule registry.
