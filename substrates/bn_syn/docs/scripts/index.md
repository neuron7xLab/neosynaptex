# Scripts Documentation Index

This section formalizes every executable in `scripts/` using static source inspection (module docstrings, CLI flags, and file-operation patterns).

## Inventory

| Script | Purpose | Safety level | Page |
|---|---|---|---|
| `__init__.py` | SSOT tooling package for CI and quality automation scripts. | Safe (read-only checks) | [--init--.md](./--init--.md) |
| `_audit_metrics_pr40.py` | Independent metric audit for PR #40 temperature ablation experiment. This script independently computes metrics from raw... | Writes artifacts only | [-audit-metrics-pr40.md](./-audit-metrics-pr40.md) |
| `audit_spec_implementation.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [audit-spec-implementation.md](./audit-spec-implementation.md) |
| `bench_ci_smoke.py` | CI smoke test for benchmark harness. Runs minimal benchmark scenario to validate harness functionality. Not intended for... | Safe (read-only checks) | [bench-ci-smoke.md](./bench-ci-smoke.md) |
| `benchmark_physics.py` | Ground-truth physics benchmark for BN-Syn throughput scaling. This script establishes the performance manifold baseline ... | Writes artifacts only | [benchmark-physics.md](./benchmark-physics.md) |
| `benchmark_production.py` | Local benchmark for BN-Syn production helpers. Not executed in CI. Intended for manual profiling. Run: python -m scripts... | Safe (read-only checks) | [benchmark-production.md](./benchmark-production.md) |
| `benchmark_sleep_stack_scale.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [benchmark-sleep-stack-scale.md](./benchmark-sleep-stack-scale.md) |
| `build_readiness_artifacts.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [build-readiness-artifacts.md](./build-readiness-artifacts.md) |
| `build_wheelhouse.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [build-wheelhouse.md](./build-wheelhouse.md) |
| `calculate_throughput_gain.py` | Throughput gain calculator for BN-Syn optimization. This script calculates and records throughput improvements from phys... | Writes artifacts only | [calculate-throughput-gain.md](./calculate-throughput-gain.md) |
| `check_api_contract.py` | Semver-aware API contract gate for BN-Syn public modules. | Writes artifacts only | [check-api-contract.md](./check-api-contract.md) |
| `check_benchmark_regressions.py` | Regression gate for physics and kernel benchmarks. Compares current benchmark results against committed baselines and fa... | Writes artifacts only | [check-benchmark-regressions.md](./check-benchmark-regressions.md) |
| `check_coverage_gate.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [check-coverage-gate.md](./check-coverage-gate.md) |
| `check_mutation_score.py` | Check mutation score against baseline with tolerance. | Safe (read-only checks) | [check-mutation-score.md](./check-mutation-score.md) |
| `check_quickstart_consistency.py` | Validate canonical install/quickstart commands stay consistent across docs. | Safe (read-only checks) | [check-quickstart-consistency.md](./check-quickstart-consistency.md) |
| `collect_ci_run_urls.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [collect-ci-run-urls.md](./collect-ci-run-urls.md) |
| `compare_benchmarks.py` | Compare benchmark results against golden baseline. Detects performance regressions by comparing current benchmark result... | Writes artifacts only | [compare-benchmarks.md](./compare-benchmarks.md) |
| `empirical_validation.py` | Summarize aggregate benchmark scenario records into deterministic validation metrics and calibration reports. | Writes artifacts only | [empirical-validation.md](./empirical-validation.md) |
| `generate_benchmark_baseline.py` | Generate benchmark baselines for the active regime. | Writes artifacts only | [generate-benchmark-baseline.md](./generate-benchmark-baseline.md) |
| `generate_coverage_baseline.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [generate-coverage-baseline.md](./generate-coverage-baseline.md) |
| `generate_coverage_trend.py` | Generate compact coverage trend artifacts for CI observability. | Writes artifacts only | [generate-coverage-trend.md](./generate-coverage-trend.md) |
| `generate_evidence_coverage.py` | Generate EVIDENCE_COVERAGE.md from claims.yml and bibliography. This script produces a deterministic evidence coverage t... | Writes artifacts only | [generate-evidence-coverage.md](./generate-evidence-coverage.md) |
| `generate_math_data.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [generate-math-data.md](./generate-math-data.md) |
| `generate_mutation_baseline.py` | Generate mutation testing baseline with real data. | Mutates repository state | [generate-mutation-baseline.md](./generate-mutation-baseline.md) |
| `generate_tests_inventory.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [generate-tests-inventory.md](./generate-tests-inventory.md) |
| `intelligence_cycle.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [intelligence-cycle.md](./intelligence-cycle.md) |
| `lint_ci_truthfulness.py` | Lint CI workflows for truthfulness and quality. This governance gate scans GitHub Actions workflows for anti-patterns th... | Writes artifacts only | [lint-ci-truthfulness.md](./lint-ci-truthfulness.md) |
| `math_validate.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [math-validate.md](./math-validate.md) |
| `mutation_ci_summary.py` | Emit canonical mutation CI outputs and GitHub summary. | Writes artifacts only | [mutation-ci-summary.md](./mutation-ci-summary.md) |
| `mutation_counts.py` | Canonical mutation metrics model and extraction for CI and gates. | Writes artifacts only | [mutation-counts.md](./mutation-counts.md) |
| `mutation_survivors_summary.py` | Append surviving mutants section to GitHub step summary. | Writes artifacts only | [mutation-survivors-summary.md](./mutation-survivors-summary.md) |
| `orchestrate_throughput_scaling.py` | Master orchestrator for BN-Syn throughput scaling validation. This script executes the complete 7-step physics-preservin... | Writes artifacts only | [orchestrate-throughput-scaling.md](./orchestrate-throughput-scaling.md) |
| `pre-push.sh` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [pre-push.md](./pre-push.md) |
| `profile_kernels.py` | Kernel profiler for BN-Syn throughput analysis. This script instruments and profiles major computational kernels to iden... | Writes artifacts only | [profile-kernels.md](./profile-kernels.md) |
| `rebuild_sources_lock.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [rebuild-sources-lock.md](./rebuild-sources-lock.md) |
| `release_pipeline.py` | Deterministic release pipeline helper (changelog + version + build + dry-run publish). | Writes artifacts only | [release-pipeline.md](./release-pipeline.md) |
| `release_readiness.py` | Generate a release readiness report for BN-Syn. | Writes artifacts only | [release-readiness.md](./release-readiness.md) |
| `render_workflow_policy_docs.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [render-workflow-policy-docs.md](./render-workflow-policy-docs.md) |
| `run_benchmarks.py` | Run deterministic BN-Syn performance benchmarks. | Writes artifacts only | [run-benchmarks.md](./run-benchmarks.md) |
| `run_mutation_pipeline.py` | Run mutmut with crash/survivor-aware fail-closed semantics. | Writes artifacts only | [run-mutation-pipeline.md](./run-mutation-pipeline.md) |
| `run_scaled_sleep_stack.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [run-scaled-sleep-stack.md](./run-scaled-sleep-stack.md) |
| `scan_governed_docs.py` | Scan governed docs for untagged normative language. This script reads the authoritative governed docs list from docs/INV... | Writes artifacts only | [scan-governed-docs.md](./scan-governed-docs.md) |
| `scan_normative_tags.py` | Scan governed docs for normative tags and claim compliance. | Writes artifacts only | [scan-normative-tags.md](./scan-normative-tags.md) |
| `scan_placeholders.py` | Scan code/docs trees for placeholder signals used by governance gates. | Writes artifacts only | [scan-placeholders.md](./scan-placeholders.md) |
| `scan_tierS_misuse.py` | Scan for misuse of Tier-S bibkeys in normative contexts. This script enforces the governance rule that Tier-S sources (b... | Writes artifacts only | [scan-tierS-misuse.md](./scan-tierS-misuse.md) |
| `ssot_rules.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [ssot-rules.md](./ssot-rules.md) |
| `sync_required_status_contexts.py` | UNKNOWN/TBD: missing module docstring. | Mutates repository state | [sync-required-status-contexts.md](./sync-required-status-contexts.md) |
| `track_quality.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [track-quality.md](./track-quality.md) |
| `validate_api_maturity.py` | Validate package maturity status mapping for public BN-Syn modules. | Safe (read-only checks) | [validate-api-maturity.md](./validate-api-maturity.md) |
| `validate_bibliography.py` | Validate BN-Syn bibliography SSOT: - bnsyn.bib entries include DOI for Tier-A sources - mapping.yml is well-formed and r... | Writes artifacts only | [validate-bibliography.md](./validate-bibliography.md) |
| `validate_branch_protection_governance.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-branch-protection-governance.md](./validate-branch-protection-governance.md) |
| `validate_claims.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-claims.md](./validate-claims.md) |
| `validate_claims_coverage.py` | Validate Claims→Evidence Coverage (CLM-0011 Enforcement). Ensures all claims in claims.yml have complete bibliographic t... | Writes artifacts only | [validate-claims-coverage.md](./validate-claims-coverage.md) |
| `validate_codebase_readiness_audit.py` | Validate codebase readiness audit JSON structure and scoring invariants. | Safe (read-only checks) | [validate-codebase-readiness-audit.md](./validate-codebase-readiness-audit.md) |
| `validate_long_running_triggers.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-long-running-triggers.md](./validate-long-running-triggers.md) |
| `validate_mutation_baseline.py` | Validate mutation baseline schema contract (fail-closed). | Safe (read-only checks) | [validate-mutation-baseline.md](./validate-mutation-baseline.md) |
| `validate_pr_gates.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-pr-gates.md](./validate-pr-gates.md) |
| `validate_required_checks.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-required-checks.md](./validate-required-checks.md) |
| `validate_required_status_contexts.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-required-status-contexts.md](./validate-required-status-contexts.md) |
| `validate_status_claims.py` | Validate public status and anti-overclaim policy for battle usage. | Safe (read-only checks) | [validate-status-claims.md](./validate-status-claims.md) |
| `validate_workflow_contracts.py` | UNKNOWN/TBD: missing module docstring. | Safe (read-only checks) | [validate-workflow-contracts.md](./validate-workflow-contracts.md) |
| `verify_equivalence.py` | Physical equivalence verification for BN-Syn backends. This script compares reference vs accelerated backends to ensure ... | Writes artifacts only | [verify-equivalence.md](./verify-equivalence.md) |
| `verify_formal_constants.py` | Verify formal specification constants match code reality. This governance gate ensures that formal verification models (... | Writes artifacts only | [verify-formal-constants.md](./verify-formal-constants.md) |
| `verify_reproducible_artifacts.py` | UNKNOWN/TBD: missing module docstring. | Writes artifacts only | [verify-reproducible-artifacts.md](./verify-reproducible-artifacts.md) |
| `visualize_experiment.py` | Visualize temperature ablation experiment results. This script generates publication-quality figures from experiment res... | Writes artifacts only | [visualize-experiment.md](./visualize-experiment.md) |

## Coverage Statement
- Documented files: **65 / 65**
- Source of truth: static inspection of `scripts/*` in this repository revision.