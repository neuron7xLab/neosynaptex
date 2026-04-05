# CI Audit Snapshot (2026-04-05)

## Scope and evidence level
- Джерела: публічні GitHub Actions summary для `main` + локальна перевірка тест-колекції.
- Неаутентифікований доступ: детальні job logs, artifact download та branch-protection API недоступні.

## Observed runs (summary-level)
| Commit | Workflow | Result | Duration | Notes |
|---|---|---:|---:|---|
| `fa36beb` | NFI CI #92 | Success | 10m 33s | 1 artifact |
| `fa36beb` | Security #67 | Success | 54s | `security-reports` 738 B + sha256 |
| `fa36beb` | CodeQL #67 | Success | 4m 40s | deprecation warning (v3) |
| `fa36beb` | Benchmarks #67 | Success | 6m 2s | - |
| `81de48b` | Benchmarks #66 | Failure | 8m 20s | `1 error + 1 warning`, exit code 1 |

## Reproducible local command (test inventory)
```bash
pytest tests --collect-only -q > /tmp/collect_all.txt
pytest tests --collect-only -q -m "not slow" > /tmp/collect_not_slow.txt
tail -n 1 /tmp/collect_all.txt
# ========================= 468 tests collected in ... =========================
tail -n 1 /tmp/collect_not_slow.txt
# =============== 451/468 tests collected (17 deselected) in ... ===============
```

## Implemented hardening (this branch)
1. Verify matrix now always emits JUnit XML:
   - `pytest ... --junitxml=junit-${{ matrix.python-version }}.xml`
2. CI gate is now dynamic over `needs`:
   - parse `${{ toJson(needs) }}` and fail if any upstream result != `success`.
   - removes manual sync risk between `needs` and hard-coded `results` arrays.

## Evidence gaps (explicit)
1. `security-reports` content not verified yet (artifact download requires authenticated access).
2. root-cause of Benchmarks #66 test failure not verified yet (job logs are sign-in gated).
3. `main` branch protection required checks not verified yet (API requires maintainer token/permissions).

## Commands to close remaining gaps (maintainer runbook)
```bash
# 1) Download and inspect security artifact
REPO='neuron7xLab/neosynaptex'
RUN_ID='24005607412'
ART_ID=$(gh api repos/$REPO/actions/runs/$RUN_ID/artifacts --jq '.artifacts[] | select(.name=="security-reports") | .id')
gh api repos/$REPO/actions/artifacts/$ART_ID/zip > /tmp/security-reports.zip
unzip -l /tmp/security-reports.zip
unzip -p /tmp/security-reports.zip bandit-report.json | head -c 4000

# 2) Verify branch protection + required status checks for main
gh api repos/$REPO/branches/main/protection --jq '.required_status_checks'
```

## 7 actionable tasks (revised, realistic DoD)
1. Node deprecation backlog: eliminate Node20 warnings for first-party pinned actions; track third-party blockers in issue list.
2. Migrate `github/codeql-action/*` to `@v4` and verify warnings=0 for CodeQL job.
3. Publish JUnit summaries only on PR events; keep artifact upload on push/main.
4. Define benchmark failure schema (`failure_type`, `failing_test`, `trace_hash`, `commit_sha`) and upload JSON artifact on failure.
5. Runtime regression policy: baseline by trailing time-window (last 30 days) + MAD*k (k=4), min 8 samples.
6. Flaky policy split: `flaky` (mixed pass/fail) vs `consistently-failing` (>=3 consecutive fails) with separate actions.
7. Branch protection governance: enforce required checks list includes `CI Gate` + `Security` + `CodeQL`.

## Sources
- https://github.com/neuron7xLab/neosynaptex/actions/runs/24005607419
- https://github.com/neuron7xLab/neosynaptex/actions/runs/24005607412
- https://github.com/neuron7xLab/neosynaptex/actions/runs/24005607407
- https://github.com/neuron7xLab/neosynaptex/actions/runs/24005607406
- https://github.com/neuron7xLab/neosynaptex/actions/runs/24004173698
- https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
- https://github.blog/changelog/2025-10-28-upcoming-deprecation-of-codeql-action-v3/
