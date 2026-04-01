# Workflow Diff: perf-resilience.yml

## Summary

Added `workflow_dispatch` inputs to enable manual execution of:
1. Fast Resilience Tests
2. Performance & SLO Validation
3. Comprehensive Resilience Tests

## Changes

### 1. Workflow Trigger Section

**Before:**
```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
    types: [opened, synchronize, reopened, labeled]
  schedule:
    # Run nightly at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual triggering
```

**After:**
```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
    types: [opened, synchronize, reopened, labeled]
  schedule:
    # Run nightly at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual triggering
    inputs:
      run_fast_resilience:
        description: 'Run Fast Resilience Tests'
        required: false
        type: boolean
        default: false
      run_performance_slo:
        description: 'Run Performance & SLO Validation'
        required: false
        type: boolean
        default: false
      run_comprehensive_resilience:
        description: 'Run Comprehensive Resilience Tests'
        required: false
        type: boolean
        default: false
```

**Rationale:**
- Added explicit boolean inputs for each job that can be skipped
- Defaults to `false` to prevent accidental execution of expensive tests
- Clear descriptions for UI usability
- Allows selective execution of individual test suites

### 2. Fast Resilience Tests Job Condition

**Before:**
```yaml
    if: |
      github.ref == 'refs/heads/main' ||
      contains(github.event.pull_request.labels.*.name, 'resilience') ||
      contains(github.event.pull_request.labels.*.name, 'perf') ||
      github.event_name == 'schedule' ||
      github.event_name == 'workflow_dispatch'
```

**After:**
```yaml
    if: |
      github.ref == 'refs/heads/main' ||
      contains(github.event.pull_request.labels.*.name, 'resilience') ||
      contains(github.event.pull_request.labels.*.name, 'perf') ||
      github.event_name == 'schedule' ||
      (github.event_name == 'workflow_dispatch' && inputs.run_fast_resilience)
```

**Rationale:**
- Changed from generic `workflow_dispatch` to explicit input check
- Prevents job from running unless explicitly requested
- Previous behavior: any workflow_dispatch would run this job
- New behavior: only runs when `run_fast_resilience` input is true

### 3. Performance & SLO Validation Job Condition

**Before:**
```yaml
    if: |
      github.ref == 'refs/heads/main' ||
      contains(github.event.pull_request.labels.*.name, 'perf') ||
      contains(github.event.pull_request.labels.*.name, 'resilience') ||
      github.event_name == 'schedule' ||
      github.event_name == 'workflow_dispatch'
```

**After:**
```yaml
    if: |
      github.ref == 'refs/heads/main' ||
      contains(github.event.pull_request.labels.*.name, 'perf') ||
      contains(github.event.pull_request.labels.*.name, 'resilience') ||
      github.event_name == 'schedule' ||
      (github.event_name == 'workflow_dispatch' && inputs.run_performance_slo)
```

**Rationale:**
- Changed from generic `workflow_dispatch` to explicit input check
- Allows selective execution of performance/SLO tests
- More granular control over expensive test execution

### 4. Comprehensive Resilience Tests Job Condition

**Before:**
```yaml
    if: |
      github.event_name == 'schedule' ||
      github.event_name == 'workflow_dispatch'
```

**After:**
```yaml
    if: |
      github.event_name == 'schedule' ||
      (github.event_name == 'workflow_dispatch' && inputs.run_comprehensive_resilience)
```

**Rationale:**
- Changed from generic `workflow_dispatch` to explicit input check
- This is the slowest test suite (~30 min timeout)
- Explicit opt-in prevents accidental execution of expensive tests
- Scheduled runs (nightly) still execute automatically

## Impact Analysis

### Jobs Modified
- `resilience-fast` (Fast Resilience Tests)
  - Runs on: main, labeled PRs, schedule, **or explicit manual trigger**
  - Duration: ~10 minutes
  - Status: Required for gate

- `performance-slo` (Performance & SLO Validation)
  - Runs on: main, labeled PRs, schedule, **or explicit manual trigger**
  - Duration: ~15 minutes
  - Status: Required for gate

- `resilience-comprehensive` (Comprehensive Resilience Tests)
  - Runs on: schedule **or explicit manual trigger only**
  - Duration: ~30 minutes
  - Status: Informational (continue-on-error: true)

- `perf-resilience-gate` (Gate Job)
  - No changes to logic
  - Still validates fast and performance-slo results
  - Handles skipped vs failed appropriately

### Behavior Changes

**Before:**
- Any `workflow_dispatch` execution would run ALL jobs that check for it
- No way to selectively run individual test suites
- Could waste CI resources running unnecessary tests

**After:**
- Manual execution requires explicit selection per job
- Can run individual test suites independently
- Better resource utilization
- More targeted verification for specific changes

### Backward Compatibility
✅ All existing trigger mechanisms remain functional:
- Push to main branch
- PR labels (`resilience`, `perf`)
- Scheduled runs (nightly at 2 AM UTC)
- Automatic execution logic unchanged

### New Functionality
✅ Selective manual execution:
- Run only fast resilience tests
- Run only performance/SLO validation
- Run only comprehensive tests
- Run any combination of the three
- Run none (to manually trigger workflow without these jobs)

## Use Cases

### 1. Quick Resilience Check
```bash
gh workflow run "Performance & Resilience Validation" \
  --ref feature-branch \
  -f run_fast_resilience=true
```
Use when: Testing resilience-related code changes, want fast feedback

### 2. Performance Regression Check
```bash
gh workflow run "Performance & Resilience Validation" \
  --ref feature-branch \
  -f run_performance_slo=true
```
Use when: Testing performance-sensitive changes, need SLO validation

### 3. Full Verification Before Merge
```bash
gh workflow run "Performance & Resilience Validation" \
  --ref feature-branch \
  -f run_fast_resilience=true \
  -f run_performance_slo=true \
  -f run_comprehensive_resilience=true
```
Use when: Critical changes requiring complete verification suite

### 4. Comprehensive Long-Running Tests
```bash
gh workflow run "Performance & Resilience Validation" \
  --ref feature-branch \
  -f run_comprehensive_resilience=true
```
Use when: Specifically testing edge cases, have 30+ minutes for execution

## Testing Checklist

- [ ] Verify YAML syntax is valid
- [ ] Confirm workflow appears in Actions UI with 3 input checkboxes
- [ ] Test manual trigger with only `run_fast_resilience=true`
- [ ] Test manual trigger with only `run_performance_slo=true`
- [ ] Test manual trigger with only `run_comprehensive_resilience=true`
- [ ] Test manual trigger with all three `true`
- [ ] Test manual trigger with all three `false` (should skip all 3 jobs)
- [ ] Verify gate job handles skipped jobs correctly
- [ ] Verify label-based triggering still works (`resilience`, `perf` labels)
- [ ] Verify scheduled runs still execute all relevant jobs

## Related Documentation

- Main evidence README: `docs/ci_evidence/pr381/README.md`
- GitHub Actions conditions: https://docs.github.com/en/actions/learn-github-actions/expressions
- Workflow dispatch inputs: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch
