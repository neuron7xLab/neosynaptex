# Claims Ledger (SSOT)

This folder is the single source of truth (SSOT) for quantitative and falsifiable statements used in **normative** sections of BN‑Syn docs.

## Rules
- Any statement labeled **[NORMATIVE]** in docs MUST map to a `claim_id` in `claims.yml`.
- A **NORMATIVE** claim MUST have:
  - `status: PROVEN`
  - `tier: A` (or `tier: B` only if explicitly allowed in the doc section)
  - `source` + `locator` (precise pointer: DOI/section/table/figure)
- If evidence is missing/weak, mark `status: UNPROVEN` and set `action: REMOVE` or `DOWNGRADE`.

## Files
- `claims.yml` — machine-checked ledger
- `overrides.yml` — optional local policy overrides (e.g., allow Tier‑B in NON‑NORMATIVE appendices)

## CI
GitHub Actions workflow `claims-gate.yml` runs `scripts/validate_claims.py` and fails PRs that introduce invalid NORMATIVE claims.
