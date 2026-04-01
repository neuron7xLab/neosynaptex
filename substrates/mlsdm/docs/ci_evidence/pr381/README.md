# CI Workflow Evidence for PR #381

## Overview

This directory contains evidence for the CI workflow modifications made to support manual execution of verification suites that were skipped during PR #381.

## Background

PR #381 ("fix: Secure subprocess usage in run_neuro_service.py example") focused on fixing specific security and type-checking issues. Several verification suites were skipped because they only run:
- On main branch commits
- With specific PR labels
- On scheduled runs

## Modified Workflows

### 1. ci-neuro-cognitive-engine.yml

**Changes Made:**
- Added `workflow_dispatch` inputs:
  - `run_safety_eval` (boolean): Run Cognitive Safety Evaluation
  - `run_benchmarks` (boolean): Run Performance Benchmarks
  
**Jobs Affected:**
1. **Cognitive Safety Evaluation** (neuro-engine-eval)
   - Now runs when: `(github.event_name == 'workflow_dispatch' && inputs.run_safety_eval)`
   - Tests: Sapolsky Validation Suite tests and evaluation
   
2. **Performance Benchmarks** (benchmarks)
   - Now runs when: `(github.event_name == 'workflow_dispatch' && inputs.run_benchmarks)`
   - Tests: SLO-based performance benchmarks

### 2. perf-resilience.yml

**Changes Made:**
- Added `workflow_dispatch` inputs:
  - `run_fast_resilience` (boolean): Run Fast Resilience Tests
  - `run_performance_slo` (boolean): Run Performance & SLO Validation
  - `run_comprehensive_resilience` (boolean): Run Comprehensive Resilience Tests

**Jobs Affected:**
1. **Fast Resilience Tests** (resilience-fast)
   - Now runs when: `(github.event_name == 'workflow_dispatch' && inputs.run_fast_resilience)`
   - Tests: Quick resilience test suite (excluding slow tests)
   
2. **Performance & SLO Validation** (performance-slo)
   - Now runs when: `(github.event_name == 'workflow_dispatch' && inputs.run_performance_slo)`
   - Tests: SLO validation with performance benchmarks
   
3. **Comprehensive Resilience Tests** (resilience-comprehensive)
   - Now runs when: `(github.event_name == 'workflow_dispatch' && inputs.run_comprehensive_resilience)`
   - Tests: Full resilience test suite including slow tests

## How to Trigger Manual Execution

### Using GitHub UI

1. Navigate to the **Actions** tab in the GitHub repository
2. Select the workflow you want to run:
   - `CI - Neuro Cognitive Engine` for safety eval and benchmarks
   - `Performance & Resilience Validation` for resilience/performance tests
3. Click **Run workflow** button
4. Select the branch (e.g., `copilot/fix-mypy-error-and-secure-examples` for PR #381)
5. Check the boxes for the specific jobs you want to run:
   - For `CI - Neuro Cognitive Engine`:
     - ☑️ Run Cognitive Safety Evaluation
     - ☑️ Run Performance Benchmarks
   - For `Performance & Resilience Validation`:
     - ☑️ Run Fast Resilience Tests
     - ☑️ Run Performance & SLO Validation
     - ☑️ Run Comprehensive Resilience Tests
6. Click **Run workflow** to execute

### Using GitHub CLI

```bash
# Cognitive Safety Evaluation
gh workflow run "CI - Neuro Cognitive Engine" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_safety_eval=true \
  -f run_benchmarks=false

# Performance Benchmarks
gh workflow run "CI - Neuro Cognitive Engine" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_safety_eval=false \
  -f run_benchmarks=true

# Fast Resilience Tests
gh workflow run "Performance & Resilience Validation" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_fast_resilience=true \
  -f run_performance_slo=false \
  -f run_comprehensive_resilience=false

# Performance & SLO Validation
gh workflow run "Performance & Resilience Validation" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_fast_resilience=false \
  -f run_performance_slo=true \
  -f run_comprehensive_resilience=false

# Comprehensive Resilience Tests
gh workflow run "Performance & Resilience Validation" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_fast_resilience=false \
  -f run_performance_slo=false \
  -f run_comprehensive_resilience=true

# Run all verification suites at once
gh workflow run "CI - Neuro Cognitive Engine" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_safety_eval=true \
  -f run_benchmarks=true

gh workflow run "Performance & Resilience Validation" \
  --ref copilot/fix-mypy-error-and-secure-examples \
  -f run_fast_resilience=true \
  -f run_performance_slo=true \
  -f run_comprehensive_resilience=true
```

## Implementation Notes

### Design Principles

1. **Minimal Changes**: Only modified workflow trigger conditions, not the job logic
2. **No Product Logic**: Changes are CI-only, no application code affected
3. **Backward Compatible**: Existing trigger mechanisms (labels, scheduled runs) remain unchanged
4. **Explicit Control**: Boolean inputs require explicit selection for each job

### Condition Logic

Jobs now use the pattern:
```yaml
if: [existing conditions] || (github.event_name == 'workflow_dispatch' && inputs.[job_input])
```

This ensures:
- Existing automatic triggers still work (main branch, labels, schedule)
- Manual triggers only run explicitly selected jobs
- Default behavior remains unchanged for normal PR workflows

## Verification Suites Summary

| Suite | Workflow | Input Parameter | Typical Duration | Criticality |
|-------|----------|----------------|------------------|-------------|
| Cognitive Safety Evaluation | ci-neuro-cognitive-engine.yml | `run_safety_eval` | ~15 min | Informational |
| Performance Benchmarks | ci-neuro-cognitive-engine.yml | `run_benchmarks` | ~10 min | SLO Gate |
| Fast Resilience Tests | perf-resilience.yml | `run_fast_resilience` | ~10 min | Required |
| Performance & SLO Validation | perf-resilience.yml | `run_performance_slo` | ~15 min | Required |
| Comprehensive Resilience Tests | perf-resilience.yml | `run_comprehensive_resilience` | ~30 min | Informational |

## Related Files

- `.github/workflows/ci-neuro-cognitive-engine.yml` - Modified workflow with safety eval and benchmarks inputs
- `.github/workflows/perf-resilience.yml` - Modified workflow with resilience/performance inputs
- `docs/ci_evidence/pr381/workflow-diff-ci-neuro-cognitive-engine.md` - Detailed diff for cognitive engine workflow
- `docs/ci_evidence/pr381/workflow-diff-perf-resilience.md` - Detailed diff for perf/resilience workflow

## Testing

To verify the workflow modifications work correctly:

1. Check workflow syntax is valid (YAML validation)
2. Verify conditions are correctly formed
3. Test manual trigger with each input combination
4. Confirm jobs run only when explicitly requested

## References

- PR #381: https://github.com/neuron7xLab/mlsdm/pull/381
- GitHub Actions workflow_dispatch documentation: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch
