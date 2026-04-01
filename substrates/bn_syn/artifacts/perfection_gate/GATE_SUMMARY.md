{
  "commands": [
    {
      "command": "python -m pip install -e \".[dev,test]\" build bandit pytest-cov mutmut==2.4.5 cyclonedx-bom==7.1.0",
      "log": "artifacts/perfection_gate/logs/deps.log",
      "returncode": 1
    },
    {
      "command": "ruff check .",
      "log": "artifacts/perfection_gate/logs/lint.log",
      "returncode": 1
    },
    {
      "command": "mypy src --strict --config-file pyproject.toml",
      "log": "artifacts/perfection_gate/logs/mypy.log",
      "returncode": 1
    },
    {
      "command": "python -m pytest -m \"not (validation or property)\" -q",
      "log": "artifacts/perfection_gate/logs/tests.log",
      "returncode": 0
    },
    {
      "command": "python -m pytest -m \"not (validation or property)\" --cov=bnsyn --cov-report=xml:artifacts/perfection_gate/coverage/coverage.xml -q",
      "log": "artifacts/perfection_gate/logs/coverage.log",
      "returncode": 1
    },
    {
      "command": "python -m bandit -r src/ -ll",
      "log": "artifacts/perfection_gate/logs/bandit.log",
      "returncode": 1
    },
    {
      "command": "python -m build",
      "log": "artifacts/perfection_gate/logs/build.log",
      "returncode": 0
    },
    {
      "command": "GITHUB_OUTPUT=artifacts/perfection_gate/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/perfection_gate/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary",
      "log": "artifacts/perfection_gate/logs/mutation.log",
      "returncode": 0
    },
    {
      "command": "python -m scripts.bench_ci_smoke --json artifacts/perfection_gate/benchmarks/ci_smoke.json --out artifacts/perfection_gate/benchmarks/ci_smoke.csv --repeats 1",
      "log": "artifacts/perfection_gate/logs/benchmarks.log",
      "returncode": 0
    },
    {
      "command": "make sbom",
      "log": "artifacts/perfection_gate/logs/sbom.log",
      "returncode": 0
    }
  ],
  "contradictions": [],
  "quality": {
    "broken_refs": 0,
    "contradictions": 0,
    "coverage": {
      "branch_pct": 0.0,
      "line_pct": 0.0,
      "thresholds_met": false
    },
    "determinism": "PASS",
    "lint": "FAIL",
    "missing_evidence": 0,
    "mutation": {
      "killed_pct": 0.0,
      "thresholds_met": true
    },
    "performance": {
      "bench_regressions": 0,
      "thresholds_met": true
    },
    "reproducibility": "PASS",
    "sbom": "PASS",
    "security": "FAIL",
    "tests": "PASS",
    "typecheck": "FAIL",
    "verdict": "FAIL"
  }
}
