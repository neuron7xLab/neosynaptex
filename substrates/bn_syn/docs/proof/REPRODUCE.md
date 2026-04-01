# Proof: Reproduce

Primary visual proof command:

```bash
bnsyn run --profile canonical --plot --export-proof
```

Base-mode artifacts (`bnsyn run --profile canonical --plot`):

- `artifacts/canonical_run/emergence_plot.png`
- `artifacts/canonical_run/summary_metrics.json`
- `artifacts/canonical_run/run_manifest.json`
- `artifacts/canonical_run/criticality_report.json`
- `artifacts/canonical_run/avalanche_report.json`
- `artifacts/canonical_run/phase_space_report.json`

Export-proof additional artifact (`bnsyn run --profile canonical --plot --export-proof`):

- `artifacts/canonical_run/proof_report.json`

---

Canonical command:

```bash
make reproduce
```

This command must produce:

- `artifacts/demo.json`
- `artifacts/demo.sha256`
- `artifacts/reproduce_manifest.json`
- `artifacts/reproducibility_report.json`

Validation rule:
- `artifacts/reproducibility_report.json` must contain `"status": "pass"` for the configured artifact checks.
- `artifacts/demo.sha256` must match the `sha256` value in `artifacts/reproduce_manifest.json`.
