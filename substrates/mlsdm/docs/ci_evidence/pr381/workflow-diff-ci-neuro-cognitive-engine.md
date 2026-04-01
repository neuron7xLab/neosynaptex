# Workflow Diff: ci-neuro-cognitive-engine.yml

## Summary

Added `workflow_dispatch` inputs to enable manual execution of:
1. Cognitive Safety Evaluation job
2. Performance Benchmarks job

## Changes

### 1. Workflow Trigger Section

**Before:**
```yaml
on:
  push:
    branches:
      - main
      - 'feature/*'
  pull_request:
    branches:
      - main
      - 'feature/*'
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * *'
```

**After:**
```yaml
on:
  push:
    branches:
      - main
      - 'feature/*'
  pull_request:
    branches:
      - main
      - 'feature/*'
  workflow_dispatch:
    inputs:
      run_safety_eval:
        description: 'Run Cognitive Safety Evaluation'
        required: false
        type: boolean
        default: false
      run_benchmarks:
        description: 'Run Performance Benchmarks'
        required: false
        type: boolean
        default: false
  schedule:
    - cron: '0 3 * * *'
```

**Rationale:**
- Added explicit boolean inputs for each skippable job
- Defaults to `false` to prevent accidental execution
- Clear descriptions for UI usability

### 2. Performance Benchmarks Job Condition

**Before:**
```yaml
  benchmarks:
    name: Performance Benchmarks (SLO Gate)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-benchmarks')
```

**After:**
```yaml
  benchmarks:
    name: Performance Benchmarks (SLO Gate)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-benchmarks') || (github.event_name == 'workflow_dispatch' && inputs.run_benchmarks)
```

**Rationale:**
- Added OR condition for `workflow_dispatch` with `inputs.run_benchmarks`
- Preserves existing behavior (main branch, label-based trigger)
- Only runs when explicitly requested via workflow_dispatch

### 3. Cognitive Safety Evaluation Job Condition

**Before:**
```yaml
  neuro-engine-eval:
    name: Cognitive Safety Evaluation
    runs-on: ubuntu-latest
    timeout-minutes: 15
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-safety-eval')
```

**After:**
```yaml
  neuro-engine-eval:
    name: Cognitive Safety Evaluation
    runs-on: ubuntu-latest
    timeout-minutes: 15
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-safety-eval') || (github.event_name == 'workflow_dispatch' && inputs.run_safety_eval)
```

**Rationale:**
- Added OR condition for `workflow_dispatch` with `inputs.run_safety_eval`
- Maintains backward compatibility with label-based triggering
- Enables on-demand execution for verification

## Impact Analysis

### Jobs NOT Modified
- `lint` - Always runs
- `security` - Always runs
- `test` - Always runs
- `coverage` - Always runs
- `e2e-tests` - Always runs
- `effectiveness-validation` - Always runs
- `all-ci-passed` - Always runs (gate job)

### Jobs Modified
- `benchmarks` - Now supports manual trigger with `run_benchmarks` input
- `neuro-engine-eval` - Now supports manual trigger with `run_safety_eval` input

### Backward Compatibility
✅ All existing trigger mechanisms remain functional:
- Push to main/feature branches
- Pull requests to main/feature
- PR labels (`run-benchmarks`, `run-safety-eval`)
- Scheduled runs (daily at 3 AM UTC)

### New Functionality
✅ Manual execution via workflow_dispatch:
- Can selectively run safety evaluation
- Can selectively run performance benchmarks
- Can run both simultaneously
- Can run neither (existing jobs only)

## Testing Checklist

- [ ] Verify YAML syntax is valid
- [ ] Confirm workflow appears in Actions UI with correct inputs
- [ ] Test manual trigger with `run_safety_eval=true, run_benchmarks=false`
- [ ] Test manual trigger with `run_safety_eval=false, run_benchmarks=true`
- [ ] Test manual trigger with both `true`
- [ ] Test manual trigger with both `false` (should skip both jobs)
- [ ] Verify label-based triggering still works
- [ ] Verify scheduled runs still execute correctly

## Related Documentation

- Main evidence README: `docs/ci_evidence/pr381/README.md`
- GitHub Actions conditions: https://docs.github.com/en/actions/learn-github-actions/expressions
- Workflow dispatch inputs: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch
