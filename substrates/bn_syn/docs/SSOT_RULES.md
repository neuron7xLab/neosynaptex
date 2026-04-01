# SSOT Rules (Authoritative)

This document is the machine-readable SSOT rule registry. Validators read this list
and compare against their built-in rule inventory to prevent drift.

```yaml
rules:
  - id: SSR-001
    statement: Tier enum values are limited to Tier-A, Tier-S, Tier-B, Tier-C.
    scope: bibliography/, claims/
    enforcement_script:
      - scripts/validate_bibliography.py
      - scripts/validate_claims.py
    failure_code: SSOT-001
    examples:
      - "Tier-A"
      - "Tier-S"
  - id: SSR-002
    statement: Tier-A claims carry normative=true; Tier-S/B/C claims carry normative=false.
    scope: claims/, bibliography/
    enforcement_script:
      - scripts/validate_claims.py
      - scripts/validate_bibliography.py
    failure_code: SSOT-002
    examples:
      - "Tier-A + normative=true"
      - "Tier-S + normative=false"
  - id: SSR-003
    statement: Mapping entries reference existing bibkeys in bibliography/bnsyn.bib.
    scope: bibliography/
    enforcement_script:
      - scripts/validate_bibliography.py
    failure_code: SSOT-003
    examples:
      - "CLM-0001 -> brette2005adaptive"
  - id: SSR-004
    statement: Claims and mapping form a closed set with aligned tier, bibkey, and spec_section.
    scope: claims/, bibliography/
    enforcement_script:
      - scripts/validate_bibliography.py
      - scripts/validate_claims.py
    failure_code: SSOT-004
    examples:
      - "CLM-0008 tier/bibkey/spec_section match across claims/mapping"
  - id: SSR-005
    statement: Tier-A bibkeys include DOI values in bnsyn.bib and appear in sources.lock.
    scope: bibliography/
    enforcement_script:
      - scripts/validate_bibliography.py
    failure_code: SSOT-005
    examples:
      - "brette2005adaptive DOI present + lock entry exists"
  - id: SSR-006
    statement: Tier-S lock entries use NODOI and include canonical_url and retrieved_date.
    scope: bibliography/
    enforcement_script:
      - scripts/validate_bibliography.py
    failure_code: SSOT-006
    examples:
      - "pytorch2026randomness=NODOI::https://...::PyTorch::YYYY-MM-DD"
  - id: SSR-007
    statement: sources.lock SHA256 matches the computed lock string.
    scope: bibliography/
    enforcement_script:
      - scripts/validate_bibliography.py
    failure_code: SSOT-007
    examples:
      - "sha256:... matches computed lock string"
  - id: SSR-008
    statement: Claims include bibkey, spec_section, implementation_paths, and verification_paths fields.
    scope: claims/
    enforcement_script:
      - scripts/validate_claims.py
    failure_code: SSOT-008
    examples:
      - "CLM-0001 has implementation_paths + verification_paths"
  - id: SSR-009
    statement: Traceability paths exist and live under src/ or scripts/ (implementation) and tests/ or scripts/ (verification).
    scope: claims/, src/, tests/, scripts/
    enforcement_script:
      - scripts/validate_claims.py
    failure_code: SSOT-009
    examples:
      - "implementation_paths: src/bnsyn/...; verification_paths: tests/..."
  - id: SSR-010
    statement: Governed docs lines with normative signals include CLM identifiers.
    scope: docs/, README*.md
    enforcement_script:
      - scripts/scan_governed_docs.py
      - scripts/scan_normative_tags.py
    failure_code: SSOT-010
    examples:
      - "[NORMATIVE][CLM-0003] NMDA Mg²⁺ block uses canonical coefficients."
```
