# Canonical Demo Surface Review

## Executive goal

Turn the canonical emergence proof path into a **production-ready local demo surface** that:

1. preserves the one-command scientific proof contract;
2. opens with a clear human-facing review surface;
3. remains machine-validated and reproducible; and
4. is merge-safe for the existing BN-Syn architecture.

## Architecture review summary

### Main-branch constraints

- The repo already treats `bnsyn run --profile canonical --plot --export-proof` as the non-negotiable canonical proof path.
- `README.md` and `docs/CANONICAL_PROOF.md` describe `index.html` as the first human review surface.
- `validate-bundle` is the human/product validator, while `proof-validate-bundle` is the narrower proof-bundle validator.

### Previous PR gap

The prior iteration improved terminal cosmetics, but the branch still had an integration gap:

- the raw export-proof run produced proof artifacts without always guaranteeing the documented human review surface;
- validator coverage for the product surface was weaker than the proof surface;
- documentation, UX, and merge-readiness expectations were not fully consolidated into a single prioritized review artifact.

## Final integration objective

The PR is only successful if the canonical export-proof run now behaves as a complete local review loop:

`run canonical bundle -> open index.html -> inspect product_summary.json/proof_report.json -> validate-bundle -> proof-validate-bundle`

## Prioritized critical tasks

| Priority | Task | Why it is critical | Status in this PR |
|---|---|---|---|
| P0 | Preserve the canonical proof command | Prevents drift from the repository’s core contract | Closed |
| P0 | Emit `index.html` and `product_summary.json` on canonical export-proof runs | Without this, the documented first-review surface is broken | Closed |
| P0 | Keep `validate-bundle` passing on raw canonical export-proof output | Required for real operator trust and merge readiness | Closed |
| P0 | Keep `proof-validate-bundle` intact for proof-only verification | Required to preserve the narrower scientific validation path | Closed |
| P1 | Move terminal presentation out of the CLI orchestration core | Lowers coupling and keeps architecture maintainable | Closed |
| P1 | Strengthen product-surface validation beyond file existence | Prevents silent regressions in `product_summary.json` and `index.html` | Closed |
| P1 | Improve the HTML report into a true demo/control surface | Needed for reviewer usability and community-facing demos | Closed |
| P1 | Synchronize README / canonical proof / demo docs | Prevents onboarding contradictions | Closed |
| P2 | Add regression tests for product-surface generation and docs sync | Protects future changes from breaking the demo path | Closed |
| P2 | Capture the completed review in a durable repo artifact | Makes merge-readiness and architectural intent inspectable | Closed |

## Merge-readiness conclusion

The canonical demo surface is merge-ready when all of the following are true together:

- canonical export-proof runs emit both proof artifacts and the human review surface;
- `validate-bundle` passes on that output;
- docs tell the truth about that behavior;
- terminal guidance and HTML surface point to commands that actually succeed;
- regression coverage locks the path in place.

## Machine-readable companion

The exact same review model is also published as `docs/demo_review_contract.json` so CI/tests can assert:

- the task set remains exactly 10;
- priorities stay ordered by correctness → stability → integration → merge readiness;
- every task has an explicit closure status.
