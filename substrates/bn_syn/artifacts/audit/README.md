# Audit CI run evidence

Regenerate immutable workflow run evidence for the current HEAD SHA:

```bash
python -m scripts.collect_ci_run_urls \
  --repo neuron7x/bnsyn-phase-controlled-emergent-dynamics \
  --sha "$(git rev-parse HEAD)" \
  --out artifacts/audit/runs_for_head.json \
  --required
```

Authentication:
- optional for public metadata, but recommended to avoid rate limits.
- set `GITHUB_TOKEN` (preferred) or `GH_TOKEN`.

Output file:
- `artifacts/audit/runs_for_head.json`
