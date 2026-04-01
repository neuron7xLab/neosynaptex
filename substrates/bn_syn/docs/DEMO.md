# BN-Syn Offline Demo (Deterministic)

This demo runs fully offline with a fixed seed and writes reproducible artifacts.

## Canonical demo command

```bash
bnsyn run --profile canonical --plot --export-proof
```

Outputs:
- `artifacts/canonical_run/emergence_plot.png`
- `artifacts/canonical_run/summary_metrics.json`
- `artifacts/canonical_run/run_manifest.json`
- `artifacts/canonical_run/criticality_report.json`
- `artifacts/canonical_run/avalanche_report.json`
- `artifacts/canonical_run/phase_space_report.json`
- `artifacts/canonical_run/product_summary.json`
- `artifacts/canonical_run/index.html`

## Demo-completion checklist for this PR

The demo surface is only considered complete when these 10 tasks stay true together:

1. canonical run stays `bnsyn run --profile canonical --plot --export-proof`;
2. local terminal output is visually legible and theme-safe;
3. the canonical run writes both proof artifacts and the human review surface;
4. `index.html` is the first review target for new users;
5. `product_summary.json` stays available for automation;
6. `proof_report.json` remains aligned with the canonical manifest;
7. `bnsyn validate-bundle` passes on the export-proof canonical output;
8. `bnsyn proof-validate-bundle` remains available for proof-only checks;
9. README/demo docs stay synchronized with actual CLI behavior;
10. CLI/runtime tests protect the onboarding and product-report path.

## Alternate output directory

```bash
bnsyn run --profile canonical --plot --export-proof --output results/demo_smoke
```
