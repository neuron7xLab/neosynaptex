# Deterministic Quickstart Contract

`README.md` is the single canonical quickstart surface.
This document exists only to restate the enforced contract in compact form.

## One-command first run

```bash
make quickstart-smoke
```

## Underlying canonical proof command

```bash
bnsyn run --profile canonical --plot --export-proof
```

## Human-first output contract

After execution:

1. open `artifacts/canonical_run/index.html` first;
2. treat `product_summary.json` and `proof_report.json` as the machine-readable verdict layer;
3. inspect metrics and evidence reports in the ordered sequence from [README.md](../README.md).

## Canonical references

- Canonical entry surface: [README.md](../README.md)
- Proof contract reference: [docs/CANONICAL_PROOF.md](CANONICAL_PROOF.md)
