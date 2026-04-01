# Scripts Reference

This registry documents every Python file under `scripts/` as discovered in the repository. Claims are evidence-backed from module docstrings and executable `--help` probes. Unknown behavior is labeled explicitly.

## Coverage

Total files documented: **63**.

## Registry Table

| Script | Purpose (module docstring summary) | `--help` probe |
|---|---|---|
| `__init__.py` | SSOT tooling package for CI and quality automation scripts. | module package initializer |
| `_audit_metrics_pr40.py` | Independent metric audit for PR #40 temperature ablation experiment. This script independently computes metrics from raw trial data to verify the aggregated results reported in the PR. | unavailable (exit 1) |
| `audit_spec_implementation.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `bench_ci_smoke.py` | CI smoke test for benchmark harness. Runs minimal benchmark scenario to validate harness functionality. Not intended for performance measurement. | available |
| `benchmark_physics.py` | Ground-truth physics benchmark for BN-Syn throughput scaling. This script establishes the performance manifold baseline that all optimizations must preserve. It measures biophysical throughput under fixed deterministic conditions. Parameters ---------- --backend : str Execution backend: 'reference' (default) or 'accelerated' --output : str Path to output JSON file (default: benchmarks/physics_baseline.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with ground-truth metrics to file or stdout Notes ----- This benchmark is the SSOT (Single Source of Truth) for physics-preserving optimization. All acceleration must match these results within tolerance. References ---------- docs/SPEC.md#P2-11 Problem statement STEP 1 | unavailable (exit 1) |
| `benchmark_production.py` | Local benchmark for BN-Syn production helpers. Not executed in CI. Intended for manual profiling. Run: python -m scripts.benchmark_production | unavailable (exit 1) |
| `benchmark_sleep_stack_scale.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `build_readiness_artifacts.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 0) |
| `build_wheelhouse.py` | UNKNOWN/TBD: no module docstring. | available |
| `calculate_throughput_gain.py` | Throughput gain calculator for BN-Syn optimization. This script calculates and records throughput improvements from physics-preserving transformations, creating an audit trail of performance gains. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output throughput gain JSON (default: benchmarks/throughput_gain.json) Returns ------- None Writes JSON with throughput metrics to file Notes ----- This creates the performance audit trail required for STEP 6. References ---------- Problem statement STEP 6 | available |
| `check_api_contract.py` | Semver-aware API contract gate for BN-Syn public modules. | available |
| `check_benchmark_regressions.py` | Regression gate for physics and kernel benchmarks. Compares current benchmark results against committed baselines and fails when performance regresses beyond a configured threshold. | unavailable (exit 1) |
| `check_coverage_gate.py` | UNKNOWN/TBD: no module docstring. | available |
| `check_mutation_score.py` | Check mutation score against baseline with tolerance. | available |
| `check_quickstart_consistency.py` | Validate canonical install/quickstart commands stay consistent across docs. | available |
| `collect_ci_run_urls.py` | UNKNOWN/TBD: no module docstring. | available |
| `compare_benchmarks.py` | Compare benchmark results against golden baseline. Detects performance regressions by comparing current benchmark results against the golden baseline stored in benchmarks/baselines/golden_baseline.yml. Exit codes: - 0: No significant regressions detected - 1: Regressions detected (>threshold%) Usage: python -m scripts.compare_benchmarks --baseline benchmarks/baselines/golden_baseline.yml \ --current benchmarks/baseline.json \ --format markdown | unavailable (exit 1) |
| `generate_benchmark_baseline.py` | Generate benchmark baselines for the active regime. | unavailable (exit 1) |
| `generate_coverage_baseline.py` | UNKNOWN/TBD: no module docstring. | available |
| `generate_coverage_trend.py` | Generate compact coverage trend artifacts for CI observability. | available |
| `generate_evidence_coverage.py` | Generate EVIDENCE_COVERAGE.md from claims.yml and bibliography. This script produces a deterministic evidence coverage table showing traceability for each claim in the registry. Output: docs/EVIDENCE_COVERAGE.md | unavailable (exit 1) |
| `generate_math_data.py` | UNKNOWN/TBD: no module docstring. | available |
| `generate_mutation_baseline.py` | Generate mutation testing baseline with real data. | available |
| `generate_tests_inventory.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 0) |
| `intelligence_cycle.py` | UNKNOWN/TBD: no module docstring. | available |
| `lint_ci_truthfulness.py` | Lint CI workflows for truthfulness and quality. This governance gate scans GitHub Actions workflows for anti-patterns that could lead to false-green CI or policy drift: 1. Test/verification commands followed by `|| true` (masks failures) 2. Hard-coded "success" summaries not derived from actual outputs 3. Workflow inputs declared but never used 4. Missing permissions declarations (should be explicit and minimal) Usage: python -m scripts.lint_ci_truthfulness --out artifacts/ci_truthfulness.json --md artifacts/ci_truthfulness.md Exit codes: 0: All checks passed 1: Critical violations found 2: Warnings found (can be promoted to errors) | unavailable (exit 1) |
| `math_validate.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 0) |
| `mutation_ci_summary.py` | Emit canonical mutation CI outputs and GitHub summary. | available |
| `mutation_counts.py` | Canonical mutation metrics model and extraction for CI and gates. | unavailable (exit 0) |
| `mutation_survivors_summary.py` | Append surviving mutants section to GitHub step summary. | unavailable (exit 1) |
| `orchestrate_throughput_scaling.py` | Master orchestrator for BN-Syn throughput scaling validation. This script executes the complete 7-step physics-preserving optimization workflow: 1. Generate ground-truth baseline 2. Profile kernels 3. Analyze scaling surfaces (already documented in scaling_plan.md) 4. Run accelerated backend 5. Verify physics equivalence 6. Calculate throughput gains 7. Generate comprehensive report Parameters ---------- --steps : int Number of simulation steps (default: 1000) --neurons : int Number of neurons (default: 200) --tolerance : float Physics equivalence tolerance (default: 0.01 = 1%) --output-dir : str Output directory for all reports (default: benchmarks/) Returns ------- None Generates complete validation suite Notes ----- This is the master orchestrator for physics-preserving throughput scaling. References ---------- Problem statement: All 7 steps | unavailable (exit 1) |
| `profile_kernels.py` | Kernel profiler for BN-Syn throughput analysis. This script instruments and profiles major computational kernels to identify bottlenecks and scaling surfaces for optimization. Parameters ---------- --output : str Path to output JSON file (default: benchmarks/kernel_profile.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with kernel metrics to file or stdout Notes ----- This creates the "Performance Jacobian" - the gradient of computational cost with respect to each kernel operation. References ---------- Problem statement STEP 2 | unavailable (exit 1) |
| `rebuild_sources_lock.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `release_pipeline.py` | Deterministic release pipeline helper (changelog + version + build + dry-run publish). | available |
| `release_readiness.py` | Generate a release readiness report for BN-Syn. | available |
| `render_workflow_policy_docs.py` | UNKNOWN/TBD: no module docstring. | available |
| `run_benchmarks.py` | Run deterministic BN-Syn performance benchmarks. | unavailable (exit 1) |
| `run_mutation_pipeline.py` | Run mutmut with crash/survivor-aware fail-closed semantics. | available |
| `run_scaled_sleep_stack.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `scan_governed_docs.py` | Scan governed docs for untagged normative language. This script reads the authoritative governed docs list from docs/INVENTORY.md and scans for normative keywords and [NORMATIVE] tags. Rules: - Lines containing normative keywords must include [NORMATIVE][CLM-####] - Lines containing [NORMATIVE] must include a CLM-#### identifier Exit codes: - 0: All checks pass - 1: Governed docs could not be parsed or listed files missing - 2: Orphan normative statements found (missing [NORMATIVE][CLM-####]) | unavailable (exit 1) |
| `scan_normative_tags.py` | Scan governed docs for normative tags and claim compliance. | unavailable (exit 1) |
| `scan_placeholders.py` | Scan code/docs trees for placeholder signals used by governance gates. | available |
| `scan_tierS_misuse.py` | Scan for misuse of Tier-S bibkeys in normative contexts. This script enforces the governance rule that Tier-S sources (bibkeys starting with 'tierS_') MUST NOT be used in normative contexts: - Lines tagged with [NORMATIVE] - Claims with normative=true in claims.yml Tier-S sources are for non-normative context/inspiration only. | unavailable (exit 1) |
| `ssot_rules.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `sync_required_status_contexts.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `track_quality.py` | UNKNOWN/TBD: no module docstring. | available |
| `validate_api_maturity.py` | Validate package maturity status mapping for public BN-Syn modules. | available |
| `validate_bibliography.py` | Validate BN-Syn bibliography SSOT: - bnsyn.bib entries include DOI for Tier-A sources - mapping.yml is well-formed and references existing bibkeys - sources.lock lines are syntactically valid and SHA256 matches LOCK_STRING - tiers and claim mappings are consistent across claims/mapping | unavailable (exit 1) |
| `validate_branch_protection_governance.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_claims.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_claims_coverage.py` | Validate Claims→Evidence Coverage (CLM-0011 Enforcement). Ensures all claims in claims.yml have complete bibliographic traceability: - bibkey (reference key) - locator (specific page/section in source) - verification_path (code/test that validates the claim) - status (claim lifecycle state) Exit codes: - 0: 100% coverage - 1: Incomplete coverage (<100%) Usage: python -m scripts.validate_claims_coverage --format markdown python -m scripts.validate_claims_coverage --format json | unavailable (exit 1) |
| `validate_codebase_readiness_audit.py` | Validate codebase readiness audit JSON structure and scoring invariants. | available |
| `validate_long_running_triggers.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_mutation_baseline.py` | Validate mutation baseline schema contract (fail-closed). | available |
| `validate_pr_gates.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_required_checks.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_required_status_contexts.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `validate_status_claims.py` | Validate public status and anti-overclaim policy for battle usage. | available |
| `validate_workflow_contracts.py` | UNKNOWN/TBD: no module docstring. | unavailable (exit 1) |
| `verify_equivalence.py` | Physical equivalence verification for BN-Syn backends. This script compares reference vs accelerated backends to ensure physics-preserving transformations maintain exact emergent dynamics within specified tolerances. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output equivalence report markdown (default: benchmarks/equivalence_report.md) --tolerance : float Maximum allowed relative deviation (default: 0.01 = 1%) Returns ------- None Writes equivalence report markdown to file Notes ----- This is the CRITICAL validation step. If physics diverges beyond tolerance, the accelerated backend MUST be reverted. References ---------- Problem statement STEP 5 | unavailable (exit 1) |
| `verify_formal_constants.py` | Verify formal specification constants match code reality. This governance gate ensures that formal verification models (TLA+, Coq) use the same constants as the actual code, preventing spec drift. Checks: 1. TLA+ BNsyn.cfg constants vs src/bnsyn/config.py 2. Coq BNsyn_Sigma.v constants vs src/bnsyn/config.py Usage: python -m scripts.verify_formal_constants Exit codes: 0: All constants match 1: Mismatches found | available |
| `verify_reproducible_artifacts.py` | UNKNOWN/TBD: no module docstring. | available |
| `visualize_experiment.py` | Visualize temperature ablation experiment results. This script generates publication-quality figures from experiment results. Usage ----- python -m scripts.visualize_experiment --run-id temp_ablation_v1 python -m scripts.visualize_experiment --run-id temp_ablation_v1 --results results/temp_ablation_v1 --out figures | unavailable (exit 1) |

## Per-script Reference

## `__init__.py`

**Purpose:** SSOT tooling package for CI and quality automation scripts.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts
```

**Help output:** UNKNOWN/TBD

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `_audit_metrics_pr40.py`

**Purpose:** Independent metric audit for PR #40 temperature ablation experiment. This script independently computes metrics from raw trial data to verify the aggregated results reported in the PR.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts._audit_metrics_pr40 --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `audit_spec_implementation.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.audit_spec_implementation --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `bench_ci_smoke.py`

**Purpose:** CI smoke test for benchmark harness. Runs minimal benchmark scenario to validate harness functionality. Not intended for performance measurement.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.bench_ci_smoke --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `benchmark_physics.py`

**Purpose:** Ground-truth physics benchmark for BN-Syn throughput scaling. This script establishes the performance manifold baseline that all optimizations must preserve. It measures biophysical throughput under fixed deterministic conditions. Parameters ---------- --backend : str Execution backend: 'reference' (default) or 'accelerated' --output : str Path to output JSON file (default: benchmarks/physics_baseline.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with ground-truth metrics to file or stdout Notes ----- This benchmark is the SSOT (Single Source of Truth) for physics-preserving optimization. All acceleration must match these results within tolerance. References ---------- docs/SPEC.md#P2-11 Problem statement STEP 1

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.benchmark_physics --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.benchmarks.regime`, `bnsyn.config`, `bnsyn.rng`, `bnsyn.sim.network`


## `benchmark_production.py`

**Purpose:** Local benchmark for BN-Syn production helpers. Not executed in CI. Intended for manual profiling. Run: python -m scripts.benchmark_production

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.benchmark_production --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.production`


## `benchmark_sleep_stack_scale.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.benchmark_sleep_stack_scale --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.tools.benchmark_sleep_stack_scale`


## `build_readiness_artifacts.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.build_readiness_artifacts --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `build_wheelhouse.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.build_wheelhouse --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `calculate_throughput_gain.py`

**Purpose:** Throughput gain calculator for BN-Syn optimization. This script calculates and records throughput improvements from physics-preserving transformations, creating an audit trail of performance gains. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output throughput gain JSON (default: benchmarks/throughput_gain.json) Returns ------- None Writes JSON with throughput metrics to file Notes ----- This creates the performance audit trail required for STEP 6. References ---------- Problem statement STEP 6

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.calculate_throughput_gain --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `check_api_contract.py`

**Purpose:** Semver-aware API contract gate for BN-Syn public modules.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.check_api_contract --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `check_benchmark_regressions.py`

**Purpose:** Regression gate for physics and kernel benchmarks. Compares current benchmark results against committed baselines and fails when performance regresses beyond a configured threshold.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.check_benchmark_regressions --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.benchmarks.regime`


## `check_coverage_gate.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.check_coverage_gate --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `check_mutation_score.py`

**Purpose:** Check mutation score against baseline with tolerance.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.check_mutation_score --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `check_quickstart_consistency.py`

**Purpose:** Validate canonical install/quickstart commands stay consistent across docs.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.check_quickstart_consistency --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `collect_ci_run_urls.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.collect_ci_run_urls --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `compare_benchmarks.py`

**Purpose:** Compare benchmark results against golden baseline. Detects performance regressions by comparing current benchmark results against the golden baseline stored in benchmarks/baselines/golden_baseline.yml. Exit codes: - 0: No significant regressions detected - 1: Regressions detected (>threshold%) Usage: python -m scripts.compare_benchmarks --baseline benchmarks/baselines/golden_baseline.yml \ --current benchmarks/baseline.json \ --format markdown

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.compare_benchmarks --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_benchmark_baseline.py`

**Purpose:** Generate benchmark baselines for the active regime.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_benchmark_baseline --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.benchmarks.regime`


## `generate_coverage_baseline.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_coverage_baseline --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_coverage_trend.py`

**Purpose:** Generate compact coverage trend artifacts for CI observability.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_coverage_trend --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_evidence_coverage.py`

**Purpose:** Generate EVIDENCE_COVERAGE.md from claims.yml and bibliography. This script produces a deterministic evidence coverage table showing traceability for each claim in the registry. Output: docs/EVIDENCE_COVERAGE.md

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_evidence_coverage --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_math_data.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_math_data --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_mutation_baseline.py`

**Purpose:** Generate mutation testing baseline with real data.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_mutation_baseline --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `generate_tests_inventory.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.generate_tests_inventory --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `intelligence_cycle.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.intelligence_cycle --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `lint_ci_truthfulness.py`

**Purpose:** Lint CI workflows for truthfulness and quality. This governance gate scans GitHub Actions workflows for anti-patterns that could lead to false-green CI or policy drift: 1. Test/verification commands followed by `|| true` (masks failures) 2. Hard-coded "success" summaries not derived from actual outputs 3. Workflow inputs declared but never used 4. Missing permissions declarations (should be explicit and minimal) Usage: python -m scripts.lint_ci_truthfulness --out artifacts/ci_truthfulness.json --md artifacts/ci_truthfulness.md Exit codes: 0: All checks passed 1: Critical violations found 2: Warnings found (can be promoted to errors)

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.lint_ci_truthfulness --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `math_validate.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.math_validate --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `contracts`


## `mutation_ci_summary.py`

**Purpose:** Emit canonical mutation CI outputs and GitHub summary.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.mutation_ci_summary --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `mutation_counts.py`

**Purpose:** Canonical mutation metrics model and extraction for CI and gates.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.mutation_counts --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `mutation_survivors_summary.py`

**Purpose:** Append surviving mutants section to GitHub step summary.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.mutation_survivors_summary --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `orchestrate_throughput_scaling.py`

**Purpose:** Master orchestrator for BN-Syn throughput scaling validation. This script executes the complete 7-step physics-preserving optimization workflow: 1. Generate ground-truth baseline 2. Profile kernels 3. Analyze scaling surfaces (already documented in scaling_plan.md) 4. Run accelerated backend 5. Verify physics equivalence 6. Calculate throughput gains 7. Generate comprehensive report Parameters ---------- --steps : int Number of simulation steps (default: 1000) --neurons : int Number of neurons (default: 200) --tolerance : float Physics equivalence tolerance (default: 0.01 = 1%) --output-dir : str Output directory for all reports (default: benchmarks/) Returns ------- None Generates complete validation suite Notes ----- This is the master orchestrator for physics-preserving throughput scaling. References ---------- Problem statement: All 7 steps

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.orchestrate_throughput_scaling --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `profile_kernels.py`

**Purpose:** Kernel profiler for BN-Syn throughput analysis. This script instruments and profiles major computational kernels to identify bottlenecks and scaling surfaces for optimization. Parameters ---------- --output : str Path to output JSON file (default: benchmarks/kernel_profile.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with kernel metrics to file or stdout Notes ----- This creates the "Performance Jacobian" - the gradient of computational cost with respect to each kernel operation. References ---------- Problem statement STEP 2

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.profile_kernels --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.benchmarks.regime`, `bnsyn.config`, `bnsyn.neuron.adex`, `bnsyn.numerics.integrators`, `bnsyn.rng`, `bnsyn.sim.network`


## `rebuild_sources_lock.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.rebuild_sources_lock --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `release_pipeline.py`

**Purpose:** Deterministic release pipeline helper (changelog + version + build + dry-run publish).

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.release_pipeline --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `release_readiness.py`

**Purpose:** Generate a release readiness report for BN-Syn.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.release_readiness --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `render_workflow_policy_docs.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.render_workflow_policy_docs --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `run_benchmarks.py`

**Purpose:** Run deterministic BN-Syn performance benchmarks.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.run_benchmarks --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.benchmarks.regime`


## `run_mutation_pipeline.py`

**Purpose:** Run mutmut with crash/survivor-aware fail-closed semantics.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.run_mutation_pipeline --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `run_scaled_sleep_stack.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.run_scaled_sleep_stack --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** `bnsyn.tools.run_scaled_sleep_stack`


## `scan_governed_docs.py`

**Purpose:** Scan governed docs for untagged normative language. This script reads the authoritative governed docs list from docs/INVENTORY.md and scans for normative keywords and [NORMATIVE] tags. Rules: - Lines containing normative keywords must include [NORMATIVE][CLM-####] - Lines containing [NORMATIVE] must include a CLM-#### identifier Exit codes: - 0: All checks pass - 1: Governed docs could not be parsed or listed files missing - 2: Orphan normative statements found (missing [NORMATIVE][CLM-####])

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.scan_governed_docs --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `scan_normative_tags.py`

**Purpose:** Scan governed docs for normative tags and claim compliance.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.scan_normative_tags --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `scan_placeholders.py`

**Purpose:** Scan code/docs trees for placeholder signals used by governance gates.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.scan_placeholders --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `scan_tierS_misuse.py`

**Purpose:** Scan for misuse of Tier-S bibkeys in normative contexts. This script enforces the governance rule that Tier-S sources (bibkeys starting with 'tierS_') MUST NOT be used in normative contexts: - Lines tagged with [NORMATIVE] - Claims with normative=true in claims.yml Tier-S sources are for non-normative context/inspiration only.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.scan_tierS_misuse --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `ssot_rules.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.ssot_rules --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `sync_required_status_contexts.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.sync_required_status_contexts --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `track_quality.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.track_quality --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_api_maturity.py`

**Purpose:** Validate package maturity status mapping for public BN-Syn modules.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_api_maturity --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_bibliography.py`

**Purpose:** Validate BN-Syn bibliography SSOT: - bnsyn.bib entries include DOI for Tier-A sources - mapping.yml is well-formed and references existing bibkeys - sources.lock lines are syntactically valid and SHA256 matches LOCK_STRING - tiers and claim mappings are consistent across claims/mapping

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_bibliography --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_branch_protection_governance.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_branch_protection_governance --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_claims.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_claims --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_claims_coverage.py`

**Purpose:** Validate Claims→Evidence Coverage (CLM-0011 Enforcement). Ensures all claims in claims.yml have complete bibliographic traceability: - bibkey (reference key) - locator (specific page/section in source) - verification_path (code/test that validates the claim) - status (claim lifecycle state) Exit codes: - 0: 100% coverage - 1: Incomplete coverage (<100%) Usage: python -m scripts.validate_claims_coverage --format markdown python -m scripts.validate_claims_coverage --format json

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_claims_coverage --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_codebase_readiness_audit.py`

**Purpose:** Validate codebase readiness audit JSON structure and scoring invariants.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_codebase_readiness_audit --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_long_running_triggers.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_long_running_triggers --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_mutation_baseline.py`

**Purpose:** Validate mutation baseline schema contract (fail-closed).

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_mutation_baseline --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_pr_gates.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_pr_gates --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_required_checks.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_required_checks --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_required_status_contexts.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_required_status_contexts --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_status_claims.py`

**Purpose:** Validate public status and anti-overclaim policy for battle usage.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_status_claims --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `validate_workflow_contracts.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.validate_workflow_contracts --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `verify_equivalence.py`

**Purpose:** Physical equivalence verification for BN-Syn backends. This script compares reference vs accelerated backends to ensure physics-preserving transformations maintain exact emergent dynamics within specified tolerances. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output equivalence report markdown (default: benchmarks/equivalence_report.md) --tolerance : float Maximum allowed relative deviation (default: 0.01 = 1%) Returns ------- None Writes equivalence report markdown to file Notes ----- This is the CRITICAL validation step. If physics diverges beyond tolerance, the accelerated backend MUST be reverted. References ---------- Problem statement STEP 5

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.verify_equivalence --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `verify_formal_constants.py`

**Purpose:** Verify formal specification constants match code reality. This governance gate ensures that formal verification models (TLA+, Coq) use the same constants as the actual code, preventing spec drift. Checks: 1. TLA+ BNsyn.cfg constants vs src/bnsyn/config.py 2. Coq BNsyn_Sigma.v constants vs src/bnsyn/config.py Usage: python -m scripts.verify_formal_constants Exit codes: 0: All constants match 1: Mismatches found

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.verify_formal_constants --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `verify_reproducible_artifacts.py`

**Purpose:** UNKNOWN/TBD: missing module docstring.

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.verify_reproducible_artifacts --help
```

**Help output:** See generated help output file.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD


## `visualize_experiment.py`

**Purpose:** Visualize temperature ablation experiment results. This script generates publication-quality figures from experiment results. Usage ----- python -m scripts.visualize_experiment --run-id temp_ablation_v1 python -m scripts.visualize_experiment --run-id temp_ablation_v1 --results results/temp_ablation_v1 --out figures

**When to use:** Use when this script's named workflow needs to run from repository root.  
**When not to use:** Do not use for runtime library integration; import `src/` modules directly for programmatic use.

**Invocation:**
```bash
python -m scripts.visualize_experiment --help
```

**Help output:** UNKNOWN/TBD: script does not expose stable --help output.

**Inputs:**
- CLI arguments: See `--help` output when available.
- Environment/config: UNKNOWN/TBD unless documented in script source.

**Outputs:**
- Stdout/stderr logs and process exit code.
- Repository artifacts depend on script logic (see script source for exact files).

**Determinism notes:** Determinism behavior is script-specific; follow each script's seed/config flags where present.

**Failure modes & diagnostics:**
- Non-zero exit typically indicates validation failure, missing inputs, or contract drift.
- Re-run with `--help` and inspect traceback/log output.

**Related modules:** UNKNOWN/TBD

