# EVIDENCE_INDEX

- cmd:python -m pip install -e ".[dev,test]" build bandit pytest-cov mutmut==2.4.5 cyclonedx-bom==7.1.0 -> log:artifacts/perfection_gate/logs/deps.log
- cmd:ruff check . -> log:artifacts/perfection_gate/logs/lint.log
- cmd:mypy src --strict --config-file pyproject.toml -> log:artifacts/perfection_gate/logs/mypy.log
- cmd:python -m pytest -m "not (validation or property)" -q -> log:artifacts/perfection_gate/logs/tests.log
- cmd:python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=xml:artifacts/perfection_gate/coverage/coverage.xml -q -> log:artifacts/perfection_gate/logs/coverage.log
- cmd:python -m bandit -r src/ -ll -> log:artifacts/perfection_gate/logs/bandit.log
- cmd:python -m build -> log:artifacts/perfection_gate/logs/build.log
- cmd:GITHUB_OUTPUT=artifacts/perfection_gate/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/perfection_gate/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary -> log:artifacts/perfection_gate/logs/mutation.log
- cmd:python -m scripts.bench_ci_smoke --json artifacts/perfection_gate/benchmarks/ci_smoke.json --out artifacts/perfection_gate/benchmarks/ci_smoke.csv --repeats 1 -> log:artifacts/perfection_gate/logs/benchmarks.log
- cmd:make sbom -> log:artifacts/perfection_gate/logs/sbom.log

- hash:sha256:66fb2be74f1f199985eebd1fbbd432e82c5ecad91004d7612879983df56ef0a4
- hash:sha256:09da4f45d65e9c015bec1774ec703490055d678979f3dcc9ecb1a3143cc49c57
