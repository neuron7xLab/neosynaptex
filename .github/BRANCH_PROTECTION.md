# Branch protection contract — main

> **Purpose.** Name the CI status checks that MUST be required for a
> PR to merge into `main`, and provide the exact `gh api` commands
> the repo admin runs to toggle them. This document is the hand-off
> between engine-built audit gates and the human-owned GitHub
> repository settings; branch-protection toggles are a security
> surface and are NOT automated.

## 1. Required status checks on `main`

The following status checks are canonical gates for the measurement
framework. Merging a PR to `main` without all of them green is a
governance regression.

| # | Check name | Workflow | Scope |
|---|---|---|---|
| 1 | `check` | `.github/workflows/claim_status_check.yml` | PR body carries a canonical `claim_status:` label (SYSTEM_PROTOCOL v1.1 kill-signal `taxonomy_disuse`). |
| 2 | `check` | `.github/workflows/adapter_scope_check.yml` | `horizon_knobs.md §4` ↔ `substrates/bridge/levin_runner.py::ADAPTERS` are in sync. |
| 3 | `check` | `.github/workflows/kill_signal_coverage.yml` | Instrumented kill-signals in `SYSTEM_PROTOCOL.md` frontmatter have real tool + test files; count ≥ baseline. |
| 4 | `check` | `.github/workflows/replication_index.yml` | `evidence/replications/registry.yaml` entries are shape-valid; count ≥ baseline. |
| 5 | `check` | `.github/workflows/telemetry_adoption.yml` | Telemetry emit sites match `tools/telemetry/adoption_manifest.yaml`. |
| 6 | `check` | `.github/workflows/canon_reference_check.yml` | Backticked path-references in canonical docs resolve on disk or are allow-listed. |
| 7 | `check` | `.github/workflows/gamma_ledger_integrity.yml` | `evidence/gamma_ledger.json` entries satisfy structural invariants (CI envelope, positive γ, canonical status, T1–T5 tier). |
| 8 | (ci.yml jobs) | `.github/workflows/ci.yml` | Lint (Ruff), types (mypy), tests (matrix), γ formula verify, axiom verification, import-linter. Multiple job names. |
| 9 | (security) | `.github/workflows/security.yml` | Bandit, pip-audit, gitleaks. |
| 10 | `Analyze` | `.github/workflows/codeql.yml` | CodeQL static analysis. |

Workflows 2–7 ship as part of the audit series introduced in the
April 2026 session (PRs #81, #82, #83, #88, #89, #90 and their
stacked dependencies). Before any of them can be set as required,
their defining PR must be merged so the check name exists in
GitHub's list of completed runs.

## 2. Applying the contract — `gh` commands

Run as the repository admin. The commands below assume the GitHub
CLI is authenticated with `admin:repo` scope on `neuron7xLab/neosynaptex`.

### 2.1 View current protection

```bash
gh api \
  -H "Accept: application/vnd.github+json" \
  /repos/neuron7xLab/neosynaptex/branches/main/protection
```

### 2.2 Set the required checks (atomic replace)

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/neuron7xLab/neosynaptex/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "claim_status_check / check",
      "adapter_scope_check / check",
      "kill_signal_coverage / check",
      "replication_index / check",
      "telemetry_adoption / check",
      "canon_reference_check / check",
      "gamma_ledger_integrity / check"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

### 2.3 Post-merge sanity

After running the PUT:

```bash
gh api /repos/neuron7xLab/neosynaptex/branches/main/protection \
  --jq '.required_status_checks.contexts'
```

Expected output is the seven check names above. Any missing entry
means a workflow run has not yet produced a completed status for
that check; merge one PR through the full CI pipeline to populate
GitHub's known-checks list, then re-apply.

## 3. What this document deliberately does NOT cover

- `ci.yml` composite job names and `security.yml` internal job
  names are not pinned here. Those pipelines are broad and change
  shape more often than the audit series; pinning every
  sub-job name would create ongoing maintenance cost without
  measurable governance gain. Treat them as required by referring
  to the workflow file name; the runner-per-job contexts are free
  to evolve.
- Branch-protection on non-`main` branches (feature branches,
  release branches, dependency auto-bump branches). Out of scope
  for the measurement-framework contract.
- Access control, team membership, secret rotation. Those live in
  the GitHub organisation admin surface, not in this repo.

## 4. Updating this contract

A PR that changes the required-checks list MUST:

1. Update the table in §1 with the new/removed check.
2. Update the JSON body in §2.2 to match.
3. Include `claim_status: measured` in the PR body (enforced by
   `claim_status_check`).
4. Land before the corresponding `gh api PUT` is executed by the
   admin — documentation precedes configuration.

Regressions (removing a check from the required list without
replacement) MUST include a written rationale pointing at the
specific `SYSTEM_PROTOCOL.md` or `ADVERSARIAL_CONTROLS.md` clause
that has been retired or replaced.
