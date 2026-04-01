# Genesis Run Plan

Post-merge operator protocol for initializing the canonical proof baseline on `main`.

## 1. Invalidate legacy caches

Run:

```bash
gh cache delete --all --repo neuron7x/bnsyn-phase-controlled-emergent-dynamics
```

This forces the next canonical proof execution to rebuild from zero cache state and validates the determinism of `scripts/bootstrap.sh`.

## 2. Trigger the canonical workflow on `main`

Use GitHub Actions `workflow_dispatch` for `.github/workflows/canonical-proof-spine.yml` immediately after merge.

## 3. Archive the Baseline Bundle

Preserve:

- `canonical_run_bundle.tgz`
- the generated attestation from `attest-canonical-bundle`
- `artifacts/agent_feedback/context.json`
- `artifacts/remediation/remediation_plan.json`

These become the first canonical baseline bundle for future PR comparisons.

## 4. Required follow-up validation

Confirm these merge-blocking checks are registered and green:

- `canonical-proof-spine / canonical-proof-spine`
- `canonical-proof-spine / cross-commit-analytics`
- `canonical-proof-spine / attest-canonical-bundle`

## 5. Future PR comparison rule

Treat the Baseline Bundle from this run as the reference artifact for all future `compare_canonical_runs.py` drift analysis.
