# Readiness Index

- Raw score: 83/110
- Normalized score: 75.45/100
- Verdict threshold (>80): FAIL

## Gate Scores
- G0_repo_inventory: 10/10
- G1_make_targets_mapped: 9/10
- G2_ci_workflows_mapped: 9/10
- G3_dependency_locks_mapped: 8/10
- G4_test_gate_exec: 8/10
- G5_lint_gate_exec: 3/10
- G6_typecheck_gate_exec: 8/10
- G7_build_gate_exec: 2/10
- G8_docs_code_ric: 9/10
- G9_evidence_logging: 8/10
- G10_sha256_anchors: 9/10

## Category Breakdown (%)
- ARCH: 95.0%
- INFRA: 86.67%
- FUNC: 80.0%
- CONFIG: 43.33%
- DOCS: 90.0%

## RIC
- RIC status: PASS
- Missing make targets in Makefile: NONE

## Evidence Logs
- make_test: proof_bundle/logs/make_test.log (exit=0)
- make_lint: proof_bundle/logs/make_lint.log (exit=2)
- make_mypy: proof_bundle/logs/make_mypy.log (exit=0)
- python_build: proof_bundle/logs/python_build.log (exit=1)
- files_inventory: proof_bundle/logs/files_inventory.log (exit=0)