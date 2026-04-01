# Integration Examples

## 1) Library integration

```bash
PYTHONPATH=src python examples/integration/library_minimal.py
```

Expected output keys:

- `example`
- `seed`
- `metrics.sigma_mean`
- `metrics.rate_mean_hz`

## 2) CLI/tool integration

```bash
PYTHONPATH=src examples/integration/cli_minimal.sh results/integration_cli_minimal.json
```

Expected file:

- JSON output with top-level `demo` field and deterministic metric keys.
