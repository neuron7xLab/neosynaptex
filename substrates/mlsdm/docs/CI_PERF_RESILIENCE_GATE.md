# CI Performance & Resilience Gate

## Overview

The CI Performance & Resilience Gate is a comprehensive tool for analyzing Pull Requests in the MLSDM repository to ensure critical performance and resilience tests are run before merge. It implements the **SDPL CONTROL BLOCK v2.0** protocol (`CI_PERF_RESILIENCE_GATE_V1`).

## Purpose

As a solo maintainer, it's easy to miss critical performance and resilience issues before merging. This gate provides:

- **Automated risk classification** (GREEN/YELLOW/RED) based on changed files
- **CI status analysis** to verify that appropriate tests have run
- **Clear merge verdicts** with concrete actions needed
- **SLO/CI improvement suggestions** for continuous improvement

## How It Works

### 1. Parse Scope & Classify Changes

The gate analyzes changed files and classifies them into three categories:

- **DOC_ONLY**: Documentation files (README.md, docs/, etc.)
- **NON_CORE_CODE**: Utility code, helper functions, non-critical refactors
- **CORE_CRITICAL**: Changes that affect:
  - Concurrency, async operations, queues, schedulers, workers
  - Network I/O, clients, storage, caches, brokers
  - Routers, loops, engines, circuit breakers, retries, backoff
  - Timeouts, rate limits, resource limits

### 2. Inspect CI Status

The gate checks GitHub Actions workflow runs for the PR, specifically:

**Performance & Resilience Jobs:**
- Fast Resilience Tests
- Performance & SLO Validation
- Comprehensive Resilience Tests

**Required Base Jobs:**
- Lint and Type Check
- Security Vulnerability Scan
- Unit and Integration Tests
- Code Coverage

### 3. Risk Classification

Based on changes and CI status, the gate assigns one of three modes:

#### GREEN_LIGHT
- **Criteria**: DOC_ONLY changes or NON_CORE_CODE with no critical paths
- **Requirements**: Base jobs must pass; perf/resilience can be skipped
- **Verdict**: Safe to merge if base jobs pass

#### YELLOW_CRITICAL_PATH
- **Criteria**: Moderate (1-9) CORE_CRITICAL changes
- **Requirements**: Fast Resilience + Performance & SLO must pass
- **Verdict**: Requires perf/resilience validation before merge

#### RED_HIGH_RISK_OR_RELEASE
- **Criteria**: Many (≥10) CORE_CRITICAL changes OR release label
- **Requirements**: ALL three resilience/performance jobs must pass
- **Verdict**: Full validation required before merge

### 4. Merge Verdict

The gate provides one of three verdicts:

- ✅ **SAFE_TO_MERGE_NOW**: All required checks passed
- ❌ **DO_NOT_MERGE_YET**: Action required (with specific steps)
- ⚠️ **MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK**: Edge cases

## Usage

### Command Line

```bash
# Using PR URL
python scripts/ci_perf_resilience_gate.py --pr-url https://github.com/neuron7xLab/mlsdm/pull/231

# Using PR number and repo
python scripts/ci_perf_resilience_gate.py --pr-number 231 --repo neuron7xLab/mlsdm

# With GitHub token (for higher API rate limits)
export GITHUB_TOKEN=your_token_here
python scripts/ci_perf_resilience_gate.py --pr-url https://github.com/neuron7xLab/mlsdm/pull/231

# JSON output format
python scripts/ci_perf_resilience_gate.py --pr-url https://github.com/neuron7xLab/mlsdm/pull/231 --output json
```

### GitHub Token

For authenticated API requests (higher rate limits):

```bash
# Set as environment variable
export GITHUB_TOKEN=ghp_your_token_here

# Or pass directly
python scripts/ci_perf_resilience_gate.py --pr-url <url> --github-token ghp_your_token_here
```

Create a token at: https://github.com/settings/tokens
Required scopes: `repo` (read-only)

## Output Format

### Markdown (Default)

The gate produces a structured markdown report with five sections:

#### Section 1: MODE_CLASSIFICATION
Shows the risk mode (GREEN/YELLOW/RED) with reasoning.

#### Section 2: CI_STATUS_TABLE
Table of all CI jobs with status and key facts.

#### Section 3: REQUIRED_ACTIONS_BEFORE_MERGE
Numbered list of specific actions needed (if any).

#### Section 4: MERGE_VERDICT
Clear verdict: SAFE_TO_MERGE_NOW or DO_NOT_MERGE_YET.

#### Section 5: SLO/CI_IMPROVEMENT_IDEAS
Up to 3 concrete suggestions for improving CI workflows.

### JSON

Use `--output json` for machine-readable output suitable for CI integration.

## Examples

### Example 1: Documentation-Only PR

```
Mode: GREEN_LIGHT
- All 3 changes are documentation-only
Verdict: SAFE_TO_MERGE_NOW
- Changes are low-risk (docs/non-core)
```

### Example 2: Critical Path PR Without Tests

```
Mode: YELLOW_CRITICAL_PATH
- Moderate core critical changes detected (2 critical, 1 non-core)
Verdict: DO_NOT_MERGE_YET

Required Actions:
1. Add 'perf' or 'resilience' label to PR to trigger required tests
2. OR manually run 'perf-resilience' workflow via workflow_dispatch
```

### Example 3: Release PR With All Tests

```
Mode: RED_HIGH_RISK_OR_RELEASE
- PR is marked for release/production
Verdict: SAFE_TO_MERGE_NOW

- All resilience and performance tests passed
- Fast Resilience: PASSED
- Performance & SLO: PASSED
- Comprehensive Resilience: PASSED
```

## Integration with CI

### GitHub Actions Workflow

You can integrate the gate into your CI:

```yaml
name: CI Gate Check
on: pull_request

jobs:
  gate-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run CI Gate
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python scripts/ci_perf_resilience_gate.py \
            --pr-number ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }}
```

### Pre-Merge Checklist

Before merging any PR, run the gate and ensure:

1. ✅ Mode is appropriate for the changes
2. ✅ All required CI jobs have passed
3. ✅ Verdict is SAFE_TO_MERGE_NOW
4. ✅ Review any SLO improvement suggestions

## Configuration

### Core Critical Paths

The following paths are always considered critical:

- `src/mlsdm/neuro_engine/`
- `src/mlsdm/memory/`
- `src/mlsdm/router/`
- `src/mlsdm/circuit_breaker/`
- `src/mlsdm/rate_limiter/`
- `src/mlsdm/clients/`
- `src/mlsdm/cache/`
- `src/mlsdm/scheduler/`
- `config/`
- `.github/workflows/`

### Core Critical Patterns

Changes containing these patterns are classified as critical:

- Async/await operations
- Threading, multiprocessing, concurrency
- Queues, schedulers, workers, executors
- Network I/O (HTTP, API, REST, gRPC)
- Storage, caching, databases
- Message brokers (Kafka, RabbitMQ)
- Circuit breakers, retries, backoff
- Timeouts, rate limits, resource limits

## Exit Codes

- `0`: SAFE_TO_MERGE_NOW
- `1`: DO_NOT_MERGE_YET
- `2`: MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK

## Best Practices

### For PR Authors

1. **Add labels proactively**: If you're touching critical paths, add `perf` or `resilience` labels
2. **Run the gate locally**: Check status before requesting review
3. **Address failures early**: Don't wait for CI to fail multiple times

### For Maintainers

1. **Run gate before merge**: Always check verdict before clicking merge
2. **Review improvement suggestions**: Consider implementing SLO/CI improvements
3. **Update patterns as needed**: Add new critical paths to the configuration

### For Releases

1. **Always use RED mode**: Release PRs require full validation
2. **Manual workflow dispatch**: Run comprehensive tests explicitly
3. **Double-check verdict**: Ensure all three resilience/performance jobs passed

## Troubleshooting

### "No CI jobs found"

**Cause**: PR hasn't triggered any workflows yet, or workflows haven't completed.

**Solution**:
- Push a new commit to trigger workflows
- Wait for workflows to complete
- Check that workflows are configured to run on PRs

### "API rate limit exceeded"

**Cause**: Too many unauthenticated requests to GitHub API.

**Solution**:
- Set `GITHUB_TOKEN` environment variable
- Use `--github-token` flag
- Wait for rate limit to reset (1 hour)

### "Base CI jobs failed"

**Cause**: Lint, tests, or security checks are failing.

**Solution**:
- Fix the failing jobs first (these are always required)
- Run locally: `pytest`, `ruff check`, `pip-audit`
- Perf/resilience are secondary to base jobs

## Development

### Testing

Run the test suite:

```bash
pytest tests/scripts/test_ci_perf_resilience_gate.py -v
```

### Adding New Critical Patterns

Edit `scripts/ci_perf_resilience_gate.py`:

```python
CORE_CRITICAL_PATTERNS = [
    # Add new patterns here
    r"(your|new|pattern)",
]
```

### Modifying Risk Thresholds

Current thresholds:
- GREEN: 0 critical changes
- YELLOW: 1-9 critical changes
- RED: ≥10 critical changes or release label

To modify, edit the `RiskClassifier.classify()` method.

## References

- **Problem Statement**: SDPL CONTROL BLOCK v2.0 (`CI_PERF_RESILIENCE_GATE_V1`)
- **CI Guide**: [CI_GUIDE.md](../CI_GUIDE.md)
- **Performance Workflow**: [.github/workflows/perf-resilience.yml](../.github/workflows/perf-resilience.yml)
- **SLO Spec**: [SLO_SPEC.md](../SLO_SPEC.md)

---

**Last Updated**: December 2025
**Version**: 1.0.0
**Maintainer**: neuron7x
