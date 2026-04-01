# Problem Spec (PS) — Codex GitHub PR Agent
scpe_release: v1.0
prompt_version: 2026.1.0
target_AL: AL-0

## State Transition
**Before:** A repository has a defined problem with failing or missing evidence (CI, tests, security, docs) and no bounded, proven PR resolution.
**After:** A single bounded pull request (or PR update) exists that closes owned gates with EBS-2026 proof and captured GitHub CI evidence pointers.

## Required Inputs
- PS: problem statement + intended end state
- REPO: owner/name
- BASE_BRANCH
- ALLOWLIST
- BASELINE: CI run URL OR reproduction commands OR failing checks list
- AUTH: gh authenticated; token scopes recorded

## Constraints
- UNKNOWN→FAIL; no inference.
- One PR maximum per run.
- Minimal diff within allowlist; rollbackable.
- Proof = commands + artifacts + sha256; CI pointers required.

## Definition of Done (Owned Gates)
- G.CDX.OBS.001 PASS
- G.CDX.GH.001 PASS
- G.CDX.PR.001 PASS
- G.CDX.CI.001 PASS
- G.CDX.DIFF.001 PASS
- G.CDX.SEC.001 PASS
- G.CDX.PROOF.001 PASS

## Budgets
- max_prs_per_run: 1
- max_files_changed: 25
- max_loc_changed: 800
- max_workflow_runs_per_run: 3
- max_wait_minutes_total: 45

## Non-Goals
- No merges.
- No repository settings modifications.
- No changes outside allowlist.
- No bypassing required checks.
