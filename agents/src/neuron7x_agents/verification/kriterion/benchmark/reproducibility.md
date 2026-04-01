# Reproducibility

## Synthetic demo benchmark
This benchmark is included to prove repository completeness and execution path, not to claim independent frontier-model superiority.

## Re-run
```bash
python tools/reference_runner.py examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json --output examples/worked-example/SE_WORKED_EXAMPLE_OUTPUT.json
python benchmark/benchmark_runner.py
python tools/validate_json.py schemas/evaluation-result.schema.json examples/worked-example/SE_WORKED_EXAMPLE_OUTPUT.json
```

All benchmark fixtures are synthetic and self-contained.
