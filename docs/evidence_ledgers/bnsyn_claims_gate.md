# Drop-in Claims Gate Bundle

## What this adds
- `claims/claims.yml` — SSOT ledger of quantitative claims
- `scripts/validate_claims.py` — CI validator (no external deps)
- `.github/workflows/ci-smoke.yml` — PR/Push enforcement (SSOT + smoke tests)
- `.github/workflows/ci-validation.yml` — scheduled/manual validation tests
- `docs/*` — policy + criticality separation docs
- `Makefile` target: `make validate-claims`

## How to integrate
1) Copy these files into the **root** of your repo (preserve paths).
2) In docs, mark quantitative requirements as:
   ```
   [NORMATIVE][CLM-####] ...
   ```
3) Add or update claim entries in `claims/claims.yml`.
4) Open PR; CI will fail if any NORMATIVE claim lacks evidence-grade SSOT metadata.

## Policy
- NORMATIVE is Tier‑A + PROVEN (enforced).
- Tier‑B allowed only for NON‑NORMATIVE appendices.
