#!/usr/bin/env python3
"""Canonical repository-native governance validator."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from governance_contract import (
    ALLOWED_GITHUB_FILES,
    AUTHORITY_MODEL,
    BASELINE_DOC_END,
    BASELINE_DOC_START,
    CLAIM_CLASSES,
    CRITICAL_ARTIFACT_CLASSES,
    DOMAIN_CLASSES,
    EXTERNAL_LINK_EXCLUDE_HOSTS,
    FAILURE_MODE_VOCABULARY,
    FORBIDDEN_RUN_PATTERNS,
    INTERNAL_LINK_EXCLUDE_PREFIXES,
    MANIFEST_DENY_PATTERNS,
    NOT_VERIFIED_DOC_END,
    NOT_VERIFIED_DOC_START,
    POLICY_VERSION,
    PIP_VERSION_POLICY,
    PR_TEMPLATE_SECTIONS,
    PUBLICATION_REQUIRED_META_NAMES,
    REGISTRY_DOC_END,
    REGISTRY_DOC_START,
    REQUIRED_CODEOWNERS_PATHS,
    VERIFICATION_SCOPES,
    expected_job_ids,
    load_registry,
    render_baseline_commands,
    render_not_verified_rows,
    render_registry_rows,
    shared_commands_from_registry,
)

ROOT = Path(os.environ.get("GOVERNANCE_VALIDATOR_ROOT", Path(__file__).resolve().parents[1]))
WORKFLOWS_DIR = ROOT / ".github/workflows"
QUALITY_WORKFLOW = WORKFLOWS_DIR / "quality-gates.yml"
PAGES_WORKFLOW = WORKFLOWS_DIR / "pages.yml"
CODEOWNERS = ROOT / ".github/CODEOWNERS"
PR_TEMPLATE = ROOT / ".github/pull_request_template.md"
PRECOMMIT = ROOT / ".pre-commit-config.yaml"
CHECKLIST = ROOT / "docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
REPO_MAP = ROOT / "repo-map.json"
MANIFEST = ROOT / "MANIFEST.json"
REGISTRY = ROOT / "governance/invariant-registry.json"
REGISTRY_SCHEMA = ROOT / "schemas/governance-invariant-registry.schema.json"
CHANGELOG = ROOT / "docs/GOVERNANCE_CONTRACT_CHANGELOG.md"
REQ = ROOT / "requirements.txt"
REQ_LOCK = ROOT / "governance/requirements-governance.lock.json"
REQUIRED_CHECKS = ROOT / "governance/ci-required-checks.json"
GITHUB_SETTINGS_BASELINE = ROOT / "governance/github-settings-baseline.json"
POLICY_DRIFT_RUNBOOK = ROOT / "docs/GOVERNANCE_POLICY_DRIFT_RUNBOOK.md"
NORMATIVE_SPEC = ROOT / "docs/GOVERNANCE_NORMATIVE_SPEC.md"

TRUSTED_ACTION_OWNERS = {"actions"}


@dataclass
class Violation:
    code: str
    message: str
    severity: str


def severity_for_code(code: str) -> str:
    if code.startswith(("FILE_", "JSON_", "YAML_", "REGISTRY_", "MANIFEST_", "WORKFLOW_", "ACTION_", "RUN_POLICY", "FAIL_CLOSED", "PARITY", "DOC_", "PRECOMMIT", "CODEOWNERS", "REPO_MAP", "GOV_DEP_GRAPH", "GOVERNANCE_CHANGELOG", "ARTIFACT_", "PUBLICATION_", "CRITICAL_ARTIFACT", "PERMISSIONS", "WORKFLOW_TRIGGER", "GITHUB_", "POST_MERGE_OPS_DRIFT", "ONE_PR_DOCTRINE", "DEPENDENCY_POLICY")):
        return "error"
    if code in {"PR_TEMPLATE", "BENCHMARK_HONESTY", "GOVERNANCE_STATUS_ARTIFACT", "ORDERING"}:
        return "error"
    if code.startswith(("SCOPE_CREEP",)):
        return "warning"
    return "warning"


def add(v: list[Violation], code: str, message: str) -> None:
    v.append(Violation(code=code, message=message, severity=severity_for_code(code)))


def read_required_text(path: Path, violations: list[Violation]) -> str:
    if not path.exists():
        add(violations, "FILE_MISSING", f"{path.relative_to(ROOT)}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        add(violations, "FILE_READ_ERROR", f"{path.relative_to(ROOT)} | {type(exc).__name__}")
        return ""


def read_required_json(path: Path, violations: list[Violation]) -> dict[str, Any]:
    text = read_required_text(path, violations)
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        add(violations, "JSON_PARSE_ERROR", f"{path.relative_to(ROOT)} | line={exc.lineno} col={exc.colno}")
        return {}
    if not isinstance(obj, dict):
        add(violations, "JSON_TYPE_ERROR", f"{path.relative_to(ROOT)} | expected object")
        return {}
    return obj


def read_required_yaml(path: Path, violations: list[Violation]) -> dict[str, Any]:
    text = read_required_text(path, violations)
    if not text:
        return {}
    try:
        obj = yaml.safe_load(text)
    except Exception as exc:
        add(violations, "YAML_PARSE_ERROR", f"{path.relative_to(ROOT)} | {type(exc).__name__}")
        return {}
    if not isinstance(obj, dict):
        add(violations, "YAML_TYPE_ERROR", f"{path.relative_to(ROOT)} | expected object")
        return {}
    if path.parent == WORKFLOWS_DIR and True in obj and "on" not in obj:
        normalized = dict(obj)
        normalized["on"] = normalized.pop(True)
        obj = normalized
    return obj


def block_between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        return ""
    s = text.index(start) + len(start)
    e = text.index(end)
    return text[s:e].strip()


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for s in steps:
        if str(s.get("name", "")) == name:
            return s
    return None


def first_run_index_containing(steps: list[dict[str, Any]], token: str) -> int:
    for i, step in enumerate(steps):
        run = step.get("run")
        if isinstance(run, str) and token in run:
            return i
    return -1




def parse_pinned_requirements(text: str, violations: list[Violation]) -> dict[str, str]:
    req: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '==' not in line:
            add(violations, 'DEPENDENCY_POLICY', f'requirement must be exact-pinned: {line}')
            continue
        name, ver = [x.strip() for x in line.split('==', 1)]
        if not name or not ver:
            add(violations, 'DEPENDENCY_POLICY', f'malformed requirement line: {line}')
            continue
        req[name] = ver
    return req


def parse_required_checks_contract(payload: dict[str, Any], violations: list[Violation]) -> list[dict[str, Any]]:
    if payload.get("immutable_reviewer_facing_check_names") is not True:
        add(violations, "GITHUB_REQUIRED_CHECKS", "ci-required-checks must set immutable_reviewer_facing_check_names=true")

    checks = payload.get("required_checks")
    if not isinstance(checks, list) or not checks:
        add(violations, "GITHUB_REQUIRED_CHECKS", "ci-required-checks required_checks must be non-empty list")
        return []

    seen_names: set[str] = set()
    seen_job_ids: set[str] = set()
    for i, item in enumerate(checks):
        if not isinstance(item, dict):
            add(violations, "GITHUB_REQUIRED_CHECKS", f"required_checks[{i}] must be object")
            continue
        name = item.get("check_name")
        job_id = item.get("job_id")
        critical = item.get("critical")
        if not isinstance(name, str) or not name:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"required_checks[{i}] missing check_name")
            continue
        if not isinstance(job_id, str) or not job_id:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"required_checks[{i}] missing job_id")
            continue
        if not isinstance(critical, bool):
            add(violations, "GITHUB_REQUIRED_CHECKS", f"required_checks[{i}] critical must be boolean")
        if name in seen_names:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"duplicate check_name {name}")
        seen_names.add(name)
        if job_id in seen_job_ids:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"duplicate job_id {job_id}")
        seen_job_ids.add(job_id)
    return checks


def git_tracked_files(violations: list[Violation]) -> set[str]:
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        # fallback for temp-fixture roots that are not git repositories
        files = set()
        for p in ROOT.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                files.add(p.relative_to(ROOT).as_posix())
        if not files:
            add(violations, "GOV_DEP_GRAPH", "unable to read tracked files (git and filesystem fallback failed)")
        return files
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def validate_external_github_baseline(
    baseline: dict[str, Any],
    checks_contract: dict[str, Any],
    workflow: dict[str, Any],
    violations: list[Violation],
) -> None:
    note = baseline.get("machine_readable_external_dependency_note")
    if not isinstance(note, str) or "external" not in note.lower() or "github" not in note.lower():
        add(violations, "GITHUB_SETTINGS_BASELINE", "baseline must include machine-readable external GitHub dependency note")

    min_bp = baseline.get("minimum_branch_protection")
    required_bp_keys = {
        "require_pull_request",
        "require_code_owner_reviews",
        "require_linear_history",
        "require_conversation_resolution",
        "allow_force_pushes",
        "allow_deletions",
        "allow_bypass",
    }
    if not isinstance(min_bp, dict):
        add(violations, "GITHUB_SETTINGS_BASELINE", "minimum_branch_protection must be object")
    else:
        missing = sorted(required_bp_keys - set(min_bp.keys()))
        if missing:
            add(violations, "GITHUB_SETTINGS_BASELINE", f"minimum_branch_protection missing keys {missing}")

    status_checks = baseline.get("required_status_checks")
    if not isinstance(status_checks, list) or not status_checks or any(not isinstance(x, str) for x in status_checks):
        add(violations, "GITHUB_SETTINGS_BASELINE", "required_status_checks must be non-empty string list")
        return

    checks = parse_required_checks_contract(checks_contract, violations)
    mapped_names = sorted(str(c.get("check_name")) for c in checks if isinstance(c, dict) and isinstance(c.get("check_name"), str))
    if sorted(status_checks) != mapped_names:
        add(
            violations,
            "POST_MERGE_OPS_DRIFT",
            f"baseline required_status_checks drift from ci-required-checks mapping baseline={sorted(status_checks)} mapping={mapped_names}",
        )

    jobs = workflow.get("jobs") if isinstance(workflow, dict) else None
    if not isinstance(jobs, dict):
        return

    for item in checks:
        if not isinstance(item, dict):
            continue
        check_name = item.get("check_name")
        job_id = item.get("job_id")
        critical = item.get("critical")
        if not isinstance(check_name, str) or not isinstance(job_id, str):
            continue
        if check_name != job_id:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"immutable check_name/job_id mismatch {check_name} vs {job_id}")
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            add(violations, "GITHUB_REQUIRED_CHECKS", f"mapped job_id missing from workflow {job_id}")
            continue
        visible_name = job.get("name")
        if not isinstance(visible_name, str) or visible_name != check_name:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"workflow job name drift for {job_id}: expected {check_name} actual {visible_name}")
        if critical is not True:
            add(violations, "GITHUB_REQUIRED_CHECKS", f"mapped check must mark critical=true for {check_name}")


def check_codeowners_quality(codeowners_text: str, violations: list[Violation]) -> None:
    lines = [ln.strip() for ln in codeowners_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        add(violations, "CODEOWNERS", "CODEOWNERS cannot be empty")
        return
    for i, line in enumerate(lines):
        if line.startswith("*"):
            add(violations, "CODEOWNERS", f"broad wildcard rule forbidden (line {i+1}): {line}")

    required_explicit = [
        "docs/GOVERNANCE_NORMATIVE_SPEC.md",
        "docs/GOVERNANCE_POLICY_DRIFT_RUNBOOK.md",
    ]
    for token in required_explicit:
        if not any(ln.split()[0] == token for ln in lines if " " in ln):
            add(violations, "CODEOWNERS", f"missing explicit CODEOWNERS rule for {token}")


def check_pr_template_quality(pr_template_text: str, violations: list[Violation]) -> None:
    required_prompts = {
        "## Problem": "Describe",
        "## Scope": "List",
        "## Invariants touched": "List",
        "## Evidence": "Provide",
        "## Risks": "State",
        "## Non-goals": "State",
        "## Manifest refresh justification": "If `MANIFEST.json` changed",
        "## Human review required": "List reviewer judgments",
        "## Policy-drift review (mandatory for governance-critical surfaces)": "Reviewer MUST explicitly",
    }
    for section, token in required_prompts.items():
        idx = pr_template_text.find(section)
        if idx == -1:
            add(violations, "PR_TEMPLATE", f"missing section body for {section}")
            continue
        tail = pr_template_text[idx + len(section):].splitlines()
        body = "\n".join([ln.strip() for ln in tail[:40] if ln.strip()])
        if token not in body:
            add(violations, "PR_TEMPLATE", f"section weakened or placeholder-like: {section}")

    if "Policy-drift review" in pr_template_text:
        policy_idx = pr_template_text.find("## Policy-drift review")
        policy_body = pr_template_text[policy_idx : policy_idx + 700]
        required_tokens = [
            ".github/",
            "tools/validate_governance.py",
            "checklist",
            "template",
            "CODEOWNERS",
            "MANIFEST",
            "repo-map",
        ]
        for token in required_tokens:
            if token not in policy_body:
                add(violations, "PR_TEMPLATE", f"policy-drift section missing required governance-critical token: {token}")


def check_repo_map_truthfulness(repo_map: dict[str, Any], manifest: dict[str, Any], violations: list[Violation]) -> None:
    tracked = git_tracked_files(violations)
    if not tracked:
        return

    for rel in sorted((set(manifest.keys()) - tracked) - {"MANIFEST.json"}):
        add(violations, "MANIFEST_POLICY", f"MANIFEST contains non-tracked path {rel}")
    for rel in sorted(tracked - set(manifest.keys())):
        add(violations, "MANIFEST_POLICY", f"tracked file missing from MANIFEST {rel}")

    for key in ("docs", "tools", "github", "governance", "root", "site"):
        vals = repo_map.get(key)
        if not isinstance(vals, list):
            continue
        for item in vals:
            if not isinstance(item, str):
                add(violations, "REPO_MAP", f"{key} contains non-string entry")
                continue
            rel = item
            if key in {"docs", "tools", "governance", "protocols", "schemas", "business", "execution"} and not item.startswith(f"{key}/"):
                rel = f"{key}/{item}"
            if key == "github" and not item.startswith(".github/"):
                rel = item
            if key == "root":
                rel = item
            if key == "site":
                rel = item
            if rel not in tracked:
                add(violations, "REPO_MAP", f"repo-map entry not tracked: {key}:{item}")

    governed_prefixes = [".github/", "governance/", "tools/", "docs/GOVERNANCE", "docs/PR_PREMERGE"]
    mapped_governance: set[str] = set()
    for item in repo_map.get("github", []):
        mapped_governance.add(item)
    for item in repo_map.get("governance", []):
        mapped_governance.add(item)
    for item in repo_map.get("tools", []):
        mapped_governance.add(f"tools/{item}" if not item.startswith("tools/") else item)
    for item in repo_map.get("docs", []):
        rel = f"docs/{item}" if not item.startswith("docs/") else item
        if rel.startswith("docs/GOVERNANCE") or rel.startswith("docs/PR_PREMERGE"):
            mapped_governance.add(rel)

    root_entries = repo_map.get("root") if isinstance(repo_map.get("root"), list) else []
    required_root_governance = {
        "MANIFEST.json",
        "repo-map.json",
        "CONTRIBUTING.md",
        ".pre-commit-config.yaml",
    }
    for rel in sorted(required_root_governance):
        if rel not in root_entries:
            add(violations, "REPO_MAP", f"root governance file missing from repo-map root section {rel}")
        else:
            mapped_governance.add(rel)

    for rel in sorted(tracked):
        if any(rel.startswith(p) for p in governed_prefixes):
            if rel not in mapped_governance and rel not in {"docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md", "docs/GOVERNANCE_CONTRACT_CHANGELOG.md"}:
                add(violations, "REPO_MAP", f"governance surface not mapped in repo-map {rel}")




def check_required_invariant_presence(registry: dict[str, Any], violations: list[Violation]) -> None:
    invariants = registry.get("invariants") if isinstance(registry, dict) else None
    if not isinstance(invariants, list):
        return
    ids = {str(inv.get("invariant_id")) for inv in invariants if isinstance(inv, dict)}
    required_ids = {
        "INV_VALID_EVALUATION_RESULT_ACCEPTED",
        "INV_INVALID_EVALUATION_RESULT_REJECTED",
        "INV_EXECUTION_CHAIN_INDEPENDENTLY_RECOMPUTABLE",
        "INV_GIT_AUTHORITATIVE_EXECUTION_SURFACE",
    }
    for iid in sorted(required_ids - ids):
        add(violations, "REGISTRY_INVARIANTS", f"missing required invariant {iid}")
def scope_creep_signal(violations: list[Violation]) -> None:
    base_ref = os.environ.get("GOVERNANCE_BASE_BRANCH") or os.environ.get("GITHUB_BASE_REF") or "main"
    mb = subprocess.run(["git", "merge-base", "HEAD", f"origin/{base_ref}"], cwd=ROOT, check=False, capture_output=True, text=True)
    if mb.returncode != 0 or not mb.stdout.strip():
        mb = subprocess.run(["git", "merge-base", "HEAD", base_ref], cwd=ROOT, check=False, capture_output=True, text=True)
    if mb.returncode != 0 or not mb.stdout.strip():
        return
    base_sha = mb.stdout.strip()
    proc = subprocess.run(["git", "diff", "--name-only", f"{base_sha}", "HEAD"], cwd=ROOT, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        return
    files = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not files:
        return
    gov_prefixes = (".github/", "governance/", "tools/", "docs/GOVERNANCE", "docs/PR_PREMERGE", "MANIFEST.json", "repo-map.json", "CONTRIBUTING.md")
    gov_changed = [f for f in files if f.startswith(gov_prefixes) or f in {"MANIFEST.json", "repo-map.json", "CONTRIBUTING.md"}]
    non_gov_changed = [f for f in files if f not in gov_changed]
    if gov_changed and len(non_gov_changed) > 8:
        add(violations, "SCOPE_CREEP", f"governance diff appears broad; non-governance files changed={len(non_gov_changed)}")

def validate_registry_contract(registry: dict[str, Any], violations: list[Violation]) -> None:
    if registry.get("policy_version") != POLICY_VERSION:
        add(violations, "REGISTRY_POLICY_VERSION", f"expected={POLICY_VERSION} actual={registry.get('policy_version')}")

    if registry.get("authority_model") != AUTHORITY_MODEL:
        add(violations, "REGISTRY_AUTHORITY_MODEL", "authority model mismatch against canonical mapping")

    vocab = registry.get("failure_mode_vocabulary")
    if not isinstance(vocab, dict):
        add(violations, "REGISTRY_FAILURE_VOCAB", "failure_mode_vocabulary must be object")
        vocab = {}
    for code, desc in FAILURE_MODE_VOCABULARY.items():
        if vocab.get(code) != desc:
            add(violations, "REGISTRY_FAILURE_VOCAB", f"failure_mode_vocabulary missing or drifted canonical entry {code}")

    invariants = registry.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        add(violations, "REGISTRY_INVARIANTS", "invariants must be non-empty list")
        return

    inv_ids: set[str] = set()
    for inv in invariants:
        if not isinstance(inv, dict):
            add(violations, "REGISTRY_INVARIANTS", "invariant item must be object")
            continue
        iid = str(inv.get("invariant_id", ""))
        if not iid.startswith("INV_"):
            add(violations, "REGISTRY_NAMING", f"invalid invariant id {iid}")
        if iid in inv_ids:
            add(violations, "REGISTRY_UNIQUENESS", f"duplicate invariant id {iid}")
        inv_ids.add(iid)
        if inv.get("domain_class") not in DOMAIN_CLASSES:
            add(violations, "REGISTRY_DOMAIN", f"{iid} has invalid domain_class={inv.get('domain_class')}")
        if inv.get("verification_scope") not in VERIFICATION_SCOPES:
            add(violations, "REGISTRY_SCOPE", f"{iid} has invalid verification_scope={inv.get('verification_scope')}")
        if inv.get("authority_class") not in AUTHORITY_MODEL:
            add(violations, "REGISTRY_AUTHORITY", f"{iid} has invalid authority_class={inv.get('authority_class')}")
        if inv.get("claim_class") not in CLAIM_CLASSES:
            add(violations, "REGISTRY_CLAIM_CLASS", f"{iid} has invalid claim_class={inv.get('claim_class')}")
        for fm in inv.get("blocked_failure_mode_codes", []):
            if fm not in vocab:
                add(violations, "REGISTRY_FAILURE_REF", f"{iid} references unknown failure code {fm}")


def workflow_files() -> list[Path]:
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted([p for p in WORKFLOWS_DIR.glob("*.yml") if p.is_file()])


def workflow_trigger_names(workflow: dict[str, Any]) -> set[str]:
    on_cfg = workflow.get("on")
    if on_cfg is None and True in workflow:
        on_cfg = workflow.get(True)

    if isinstance(on_cfg, dict):
        return {str(k) for k in on_cfg.keys()}
    if isinstance(on_cfg, list):
        return {str(x) for x in on_cfg if isinstance(x, str)}
    if isinstance(on_cfg, str):
        return {on_cfg}
    return set()


def validate_workflow_policy(workflow_path: Path, workflow: dict[str, Any], registry: dict[str, Any], violations: list[Violation]) -> None:
    triggers = workflow_trigger_names(workflow)
    allow_workflow_dispatch = workflow_path == PAGES_WORKFLOW
    if "workflow_dispatch" in triggers and not allow_workflow_dispatch:
        add(violations, "WORKFLOW_TRIGGER", f"workflow_dispatch is forbidden in {workflow_path.relative_to(ROOT)}")
    if "pull_request_target" in triggers:
        add(violations, "WORKFLOW_TRIGGER", f"pull_request_target is forbidden in {workflow_path.relative_to(ROOT)}")

    perms = workflow.get("permissions")
    if not isinstance(perms, dict):
        add(violations, "PERMISSIONS", f"workflow permissions must be explicit mapping in {workflow_path.relative_to(ROOT)}")
    else:
        if perms.get("contents") != "read":
            add(violations, "PERMISSIONS", f"workflow contents permission must be read in {workflow_path.relative_to(ROOT)}")
        actions_perm = perms.get("actions")
        if actions_perm not in {None, "none", "read"}:
            add(violations, "PERMISSIONS", f"workflow actions permission must be none/read in {workflow_path.relative_to(ROOT)}")
        for k, v in perms.items():
            if isinstance(v, str) and v not in {"none", "read"}:
                add(violations, "PERMISSIONS", f"forbidden workflow permission {k}={v} in {workflow_path.relative_to(ROOT)}")

    defaults = workflow.get("defaults")
    if not isinstance(defaults, dict):
        add(violations, "WORKFLOW_DISCIPLINE", f"missing workflow-level defaults mapping in {workflow_path.relative_to(ROOT)}")
    else:
        run_defaults = defaults.get("run")
        if not isinstance(run_defaults, dict):
            add(violations, "WORKFLOW_DISCIPLINE", f"missing workflow-level defaults.run mapping in {workflow_path.relative_to(ROOT)}")
        else:
            shell = run_defaults.get("shell")
            expected_shell = "bash --noprofile --norc -euo pipefail {0}"
            if shell != expected_shell:
                add(violations, "WORKFLOW_DISCIPLINE", f"workflow defaults.run.shell must be '{expected_shell}' in {workflow_path.relative_to(ROOT)}")

    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        add(violations, "WORKFLOW_JOBS", f"jobs must be mapping in {workflow_path.relative_to(ROOT)}")
        return

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            add(violations, "WORKFLOW_JOBS", f"job {job_id} must be mapping in {workflow_path.relative_to(ROOT)}")
            continue
        if "uses" in job:
            add(violations, "WORKFLOW_JOBS", f"reusable workflow usage forbidden in job {job_id}")
        if "permissions" in job:
            add(violations, "PERMISSIONS", f"job-level permissions forbidden in {job_id}")
        strategy = job.get("strategy")
        if isinstance(strategy, dict) and "matrix" in strategy:
            add(violations, "WORKFLOW_STRICTNESS", f"matrix strategy forbidden without explicit policy in {job_id}")
        steps = job.get("steps")
        if not isinstance(steps, list):
            add(violations, "WORKFLOW_JOBS", f"job {job_id} steps must be list")
            continue

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                add(violations, "WORKFLOW_JOBS", f"{job_id} step[{i}] must be mapping")
                continue
            if step.get("continue-on-error") is True:
                add(violations, "WORKFLOW_STRICTNESS", f"continue-on-error forbidden in {job_id} step[{i}]")

            uses = step.get("uses")
            if isinstance(uses, str):
                if uses.startswith("actions/cache@"):
                    add(violations, "WORKFLOW_DISCIPLINE", f"actions/cache is forbidden in {job_id}; avoid hidden state side-effects")
                m = re.fullmatch(r"([^/@]+)/([^@]+)@([0-9a-f]{40})(?:\s*#.*)?", uses)
                if not m:
                    add(violations, "ACTION_PINNING", f"{job_id} uses must be full-SHA pinned ({uses})")
                elif m.group(1) not in TRUSTED_ACTION_OWNERS:
                    add(violations, "ACTION_TRUST", f"untrusted action owner {m.group(1)} in {job_id}")
                if uses.startswith("actions/upload-artifact@"):
                    with_cfg = step.get("with")
                    if not isinstance(with_cfg, dict):
                        add(violations, "ARTIFACT_SEMANTICS", f"{job_id} upload-artifact step[{i}] missing with mapping")
                    else:
                        if with_cfg.get("if-no-files-found") != "error":
                            add(violations, "ARTIFACT_SEMANTICS", f"{job_id} upload-artifact step[{i}] must set if-no-files-found=error")
                        retention = with_cfg.get("retention-days")
                        if not isinstance(retention, int) or retention < 14:
                            add(violations, "ARTIFACT_SEMANTICS", f"{job_id} upload-artifact step[{i}] retention-days must be integer >=14")

            run = step.get("run")
            if isinstance(run, str):
                if re.search(r"\b(curl|wget)\b", run, flags=re.IGNORECASE):
                    add(violations, "RUN_POLICY", f"shell download command forbidden in {job_id} step[{i}]")
                for pat in FORBIDDEN_RUN_PATTERNS:
                    if re.search(pat, run, flags=re.IGNORECASE):
                        add(violations, "RUN_POLICY", f"forbidden bootstrap pattern in {job_id} step[{i}]")
                if "|| true" in run:
                    add(violations, "WORKFLOW_STRICTNESS", f"forbidden tolerance pattern '|| true' in {job_id} step[{i}]")
                if "|" in run and "set -o pipefail" not in run and "set -euo pipefail" not in run:
                    add(violations, "WORKFLOW_STRICTNESS", f"pipe usage without pipefail in {job_id} step[{i}]")
                if "python tools/" in run and "set -e" not in run and "set -euo" not in run and "set -o pipefail" not in run and "\n" in run:
                    add(violations, "WORKFLOW_STRICTNESS", f"multi-line repository tool run should enable strict shell flags in {job_id} step[{i}]")

    if workflow_path == PAGES_WORKFLOW:
        job_ids = set(jobs.keys())
        if job_ids != {"no-op"}:
            add(violations, "WORKFLOW_JOBS", "pages workflow must contain only no-op job")
        no_op = jobs.get("no-op")
        if isinstance(no_op, dict):
            steps = no_op.get("steps") if isinstance(no_op.get("steps"), list) else []
            if len(steps) != 1 or not isinstance(steps[0], dict):
                add(violations, "WORKFLOW_DISCIPLINE", "pages no-op job must contain exactly one run step")
            else:
                run = str(steps[0].get("run", ""))
                expected = "echo \"Pages workflow reserved; deployment is intentionally disabled in this repository.\""
                if run.strip() != expected:
                    add(violations, "WORKFLOW_DISCIPLINE", "pages no-op workflow run command drift")
        return

    if workflow_path != QUALITY_WORKFLOW:
        add(violations, "WORKFLOW_JOBS", f"unexpected governed workflow {workflow_path.relative_to(ROOT)}")
        return

    concurrency = workflow.get("concurrency")
    if not isinstance(concurrency, dict):
        add(violations, "WORKFLOW_DISCIPLINE", "missing workflow-level concurrency mapping")
    elif concurrency.get("cancel-in-progress") is not True:
        add(violations, "WORKFLOW_DISCIPLINE", "missing cancel-in-progress: true")

    env = workflow.get("env")
    if not isinstance(env, dict):
        add(violations, "WORKFLOW_DISCIPLINE", "quality-gates missing workflow-level env mapping")
    elif str(env.get("PIP_VERSION")) != PIP_VERSION_POLICY:
        add(violations, "WORKFLOW_DISCIPLINE", f"quality-gates env.PIP_VERSION must equal {PIP_VERSION_POLICY}")

    expected_jobs = expected_job_ids(registry)
    actual_job_ids = set(jobs.keys())
    for j in sorted(expected_jobs - actual_job_ids):
        add(violations, "WORKFLOW_JOBS", f"missing expected job {j}")
    for j in sorted(actual_job_ids - expected_jobs):
        add(violations, "WORKFLOW_JOBS", f"unexpected job {j}")

    chash = jobs.get("inv-canonical-hash-stability")
    if isinstance(chash, dict):
        steps = chash.get("steps", []) if isinstance(chash.get("steps"), list) else []
        if first_run_index_containing(steps, "check_canonical_hash_stability.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "canonical-hash job missing representative-input stability script")
        if first_run_index_containing(steps, "check_canonicalization_negative_cases.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "canonical-hash job missing canonicalization negative-case script")

    worked = jobs.get("inv-worked-example-and-output-validity")
    if isinstance(worked, dict):
        steps = worked.get("steps", []) if isinstance(worked.get("steps"), list) else []
        if first_run_index_containing(steps, "assert_worked_example_semantics.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "worked-example job missing semantic assertion script")
        if first_run_index_containing(steps, "verify_execution_chain.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "worked-example job missing independent execution-chain verifier")
        if first_run_index_containing(steps, "git diff --quiet") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "worked-example job missing strict git-authority precheck")
        if first_run_index_containing(steps, "Build worked-example artifact manifest") == -1 and not find_step(steps, "Build worked-example artifact manifest"):
            add(violations, "ARTIFACT_SEMANTICS", "worked-example job missing artifact manifest build step")
        if first_run_index_containing(steps, "worked-example.run.status.json") == -1:
            add(violations, "ARTIFACT_SEMANTICS", "worked-example job missing run.status artifact generation")
        if find_step(steps, "Upload worked-example evidence") is None:
            add(violations, "ARTIFACT_SEMANTICS", "worked-example job missing evidence upload step")

    bench = jobs.get("inv-benchmark-demo-and-honesty")
    if isinstance(bench, dict):
        steps = bench.get("steps", []) if isinstance(bench.get("steps"), list) else []
        if first_run_index_containing(steps, "python benchmark/benchmark_runner.py") == -1:
            add(violations, "ORDERING", "benchmark job missing benchmark runner")
        if first_run_index_containing(steps, "assert_gate_benchmark_invariants.py") == -1:
            add(violations, "BENCHMARK_HONESTY", "benchmark job missing repository benchmark-honesty assertion script")
        if first_run_index_containing(steps, "benchmark.artifact-manifest.json") == -1:
            add(violations, "ARTIFACT_SEMANTICS", "benchmark job missing artifact-manifest generation")
        if first_run_index_containing(steps, "benchmark.run.status.json") == -1:
            add(violations, "ARTIFACT_SEMANTICS", "benchmark job missing run.status artifact generation")
        if first_run_index_containing(steps, "case-*.evaluation.json") == -1:
            add(violations, "ARTIFACT_SEMANTICS", "benchmark job missing per-case evaluation artifact staging/upload")
        if first_run_index_containing(steps, "git diff --exit-code -- benchmark/metrics.json benchmark/results/case_level_results.csv benchmark/results/case-*.evaluation.json") == -1:
            add(violations, "BENCHMARK_HONESTY", "benchmark job missing regenerated-output parity check")

    failc = jobs.get("inv-fail-closed-missing-evidence")
    if isinstance(failc, dict):
        steps = failc.get("steps", []) if isinstance(failc.get("steps"), list) else []
        if first_run_index_containing(steps, "assert_fail_closed_semantics.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "fail-closed job missing repository fail-closed assertion script")

    pyentry = jobs.get("inv-python-entrypoints-and-compile")
    if isinstance(pyentry, dict):
        steps = pyentry.get("steps", []) if isinstance(pyentry.get("steps"), list) else []
        required_semantic_regressions = [
            "python -m unittest tests/semantic/test_fail_closed_semantics.py",
            "python -m unittest tests/semantic/test_canonicalization_edge_cases.py",
            "python -m unittest tests/semantic/test_reference_runner_injection_detection.py",
            "python -m unittest tests/semantic/test_verify_ci_artifact_manifest.py",
            "python -m unittest tests/semantic/test_verify_execution_chain.py",
        ]
        for cmd in required_semantic_regressions:
            if first_run_index_containing(steps, cmd) == -1:
                add(violations, "WORKFLOW_STRICTNESS", f"inv-python-entrypoints-and-compile missing required semantic regression: {cmd}")

    gateid = jobs.get("inv-gate-id-canonicality")
    if isinstance(gateid, dict):
        steps = gateid.get("steps", []) if isinstance(gateid.get("steps"), list) else []
        if first_run_index_containing(steps, "assert_gate_benchmark_invariants.py") == -1:
            add(violations, "WORKFLOW_STRICTNESS", "gate-id job missing repository gate assertion script")

    art = jobs.get("inv-ci-artifact-semantics-and-provenance")
    if isinstance(art, dict):
        needs = art.get("needs")
        if not isinstance(needs, list) or sorted(needs) != sorted(["inv-worked-example-and-output-validity", "inv-benchmark-demo-and-honesty"]):
            add(violations, "ARTIFACT_SEMANTICS", "artifact-provenance job must need worked-example and benchmark jobs")
        steps = art.get("steps", []) if isinstance(art.get("steps"), list) else []
        verify_idx = first_run_index_containing(steps, "verify_ci_artifact_manifest.py")
        if verify_idx == -1:
            add(violations, "ARTIFACT_SEMANTICS", "artifact-provenance job missing manifest verification")
        else:
            verify_step = steps[verify_idx]
            verify_run = verify_step.get("run") if isinstance(verify_step, dict) else None
            if isinstance(verify_run, str):
                required_tokens = [
                    "--root .ci-artifacts/worked",
                    "--root .ci-artifacts/benchmark",
                    "--strip-path-prefix .ci-artifacts/",
                    "--require-name worked-example-output",
                    "--require-name worked-example-status",
                    "--require-name benchmark-metrics",
                    "--require-name benchmark-case-results",
                    "--require-name benchmark-status",
                ]
                for tok in required_tokens:
                    if tok not in verify_run:
                        add(violations, "ARTIFACT_SEMANTICS", f"artifact-provenance manifest verification missing token: {tok}")
        if find_step(steps, "Upload reviewer inspectability summary") is None:
            add(violations, "ARTIFACT_SEMANTICS", "artifact-provenance job missing inspectability summary upload")

    pub_internal = jobs.get("inv-publication-internal-link-integrity")
    if isinstance(pub_internal, dict):
        steps = pub_internal.get("steps", []) if isinstance(pub_internal.get("steps"), list) else []
        if first_run_index_containing(steps, "check_internal_links.py") == -1:
            add(violations, "PUBLICATION_STRUCTURE", "publication internal-link job missing checker command")

    pub_struct = jobs.get("inv-publication-surface-structure")
    if isinstance(pub_struct, dict):
        steps = pub_struct.get("steps", []) if isinstance(pub_struct.get("steps"), list) else []
        if first_run_index_containing(steps, "validate_publication_surfaces.py") == -1:
            add(violations, "PUBLICATION_STRUCTURE", "publication structure job missing validator command")

    ordered_jobs = [
        'inv-schema-valid-acceptance',
        'inv-schema-invalid-rejection',
        'inv-worked-example-and-output-validity',
        'inv-fail-closed-missing-evidence',
        'inv-benchmark-demo-and-honesty',
        'inv-python-entrypoints-and-compile',
        'inv-dependency-hermeticity',
        'governance-hygiene',
    ]
    for job_id in ordered_jobs:
        job = jobs.get(job_id)
        if not isinstance(job, dict):
            continue
        steps = job.get('steps', []) if isinstance(job.get('steps'), list) else []
        install_i = first_run_index_containing(steps, 'python -m pip install -r requirements.txt')
        if install_i == -1:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} missing dependency install step')
            continue
        pip_pin_i = first_run_index_containing(steps, 'python -m pip install --upgrade pip==${PIP_VERSION}')
        if pip_pin_i == -1:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} missing canonical pip pin step')
        pip_version_i = first_run_index_containing(steps, 'python -m pip --version')
        if pip_version_i == -1:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} missing pip version logging step')
        if pip_pin_i != -1 and pip_version_i != -1 and pip_version_i < pip_pin_i:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} logs pip version before canonical pin')
        if pip_pin_i != -1 and install_i < pip_pin_i:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} installs dependencies before canonical pip pin')
        if pip_version_i != -1 and install_i < pip_version_i:
            add(violations, 'WORKFLOW_ORDERING', f'{job_id} installs dependencies before pip version logging')

        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            run = step.get('run')
            if isinstance(run, str) and 'python tools/' in run and i < install_i:
                add(violations, 'WORKFLOW_ORDERING', f'{job_id} runs repository python tool before dependency install')

    gov = jobs.get("governance-hygiene")
    if isinstance(gov, dict):
        steps = gov.get("steps", []) if isinstance(gov.get("steps"), list) else []
        if first_run_index_containing(steps, "validate_governance.py --json") == -1:
            add(violations, "GOVERNANCE_STATUS_ARTIFACT", "governance-hygiene missing machine-readable status generation")
        if find_step(steps, "Upload governance status artifact") is None:
            add(violations, "GOVERNANCE_STATUS_ARTIFACT", "governance-hygiene missing governance status upload step")
        required_self_hosting_tests = [
            "python -m unittest tests/governance/test_validate_governance.py",
            "python -m unittest tests/governance/test_validate_governance_severity.py",
            "python -m unittest tests/governance/test_run_local_governance_baseline.py",
            "python -m unittest tests/semantic/test_cli_contracts.py",
            "python -m unittest tests/semantic/test_dependency_hermeticity.py",
        ]
        for cmd in required_self_hosting_tests:
            if first_run_index_containing(steps, cmd) == -1:
                add(violations, "WORKFLOW_STRICTNESS", f"governance-hygiene missing required self-hosting test: {cmd}")

def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args()

    violations: list[Violation] = []

    workflows: dict[Path, dict[str, Any]] = {}
    for wf in workflow_files():
        workflows[wf] = read_required_yaml(wf, violations)
    quality_workflow = workflows.get(QUALITY_WORKFLOW, {})
    codeowners_text = read_required_text(CODEOWNERS, violations)
    pr_template_text = read_required_text(PR_TEMPLATE, violations)
    checklist_text = read_required_text(CHECKLIST, violations)
    contributing_text = read_required_text(CONTRIBUTING, violations)
    repo_map = read_required_json(REPO_MAP, violations)
    manifest = read_required_json(MANIFEST, violations)
    precommit_cfg = read_required_yaml(PRECOMMIT, violations)
    registry = read_required_json(REGISTRY, violations)
    _ = read_required_json(REGISTRY_SCHEMA, violations)
    changelog_text = read_required_text(CHANGELOG, violations)
    req_text = read_required_text(REQ, violations)
    req_lock = read_required_json(REQ_LOCK, violations)
    required_checks_contract = read_required_json(REQUIRED_CHECKS, violations)
    github_settings_baseline = read_required_json(GITHUB_SETTINGS_BASELINE, violations)
    policy_drift_runbook_text = read_required_text(POLICY_DRIFT_RUNBOOK, violations)
    normative_spec_text = read_required_text(NORMATIVE_SPEC, violations)

    validate_registry_contract(registry, violations)

    check_required_invariant_presence(registry, violations)

    if f"## {POLICY_VERSION}" not in changelog_text:
        add(violations, "GOVERNANCE_CHANGELOG", f"missing changelog section for policy version {POLICY_VERSION}")

    if "Incident triggers" not in policy_drift_runbook_text or "Response procedure" not in policy_drift_runbook_text:
        add(violations, "DOC_ALIGNMENT", "policy-drift runbook missing canonical incident sections")
    if "Canonical acceptance criteria" not in normative_spec_text:
        add(violations, "DOC_ALIGNMENT", "normative spec missing canonical acceptance criteria")


    req = parse_pinned_requirements(req_text, violations)
    lock_pkgs = req_lock.get('packages') if isinstance(req_lock, dict) else None
    if not isinstance(lock_pkgs, dict):
        add(violations, 'DEPENDENCY_POLICY', 'requirements lock must contain packages object')
    else:
        if set(req.keys()) != set(lock_pkgs.keys()):
            add(violations, 'DEPENDENCY_POLICY', f'requirements/lock package-set mismatch req={sorted(req)} lock={sorted(lock_pkgs)}')
        for k, v in req.items():
            if str(lock_pkgs.get(k)) != v:
                add(violations, 'DEPENDENCY_POLICY', f'lock version drift {k}: requirements={v} lock={lock_pkgs.get(k)}')

    if (ROOT / ".github/dependabot.yml").exists():
        add(violations, "ONE_PR_DOCTRINE", ".github/dependabot.yml must be absent")
    for forbidden in (
        ROOT / ".github/renovate.json",
        ROOT / ".github/renovate.json5",
        ROOT / ".github/workflows/auto-update.yml",
        ROOT / ".github/workflows/create-pr.yml",
    ):
        if forbidden.exists():
            add(violations, "ONE_PR_DOCTRINE", f"forbidden auto-PR surface present {forbidden.relative_to(ROOT)}")

    for wf in workflow_files():
        workflow_src = read_required_text(wf, violations)
        if "create-pull-request" in workflow_src.lower() or "dependabot[bot]" in workflow_src.lower():
            add(violations, "ONE_PR_DOCTRINE", f"workflow references automated PR generation surface {wf.relative_to(ROOT)}")

    expected_workflow_set = {QUALITY_WORKFLOW, PAGES_WORKFLOW}
    actual_workflow_set = set(workflows.keys())
    for missing in sorted(expected_workflow_set - actual_workflow_set):
        add(violations, "FILE_MISSING", f"{missing.relative_to(ROOT)}")
    for unexpected in sorted(actual_workflow_set - expected_workflow_set):
        add(violations, "WORKFLOW_JOBS", f"unexpected workflow file {unexpected.relative_to(ROOT)}")

    for wf, payload in workflows.items():
        if payload and registry:
            validate_workflow_policy(wf, payload, registry, violations)

    if quality_workflow:
        validate_external_github_baseline(github_settings_baseline, required_checks_contract, quality_workflow, violations)
    scope_creep_signal(violations)

    for required in REQUIRED_CODEOWNERS_PATHS:
        if required not in codeowners_text:
            add(violations, "CODEOWNERS", f"missing required path {required}")
    check_codeowners_quality(codeowners_text, violations)

    for section in PR_TEMPLATE_SECTIONS:
        if section not in pr_template_text:
            add(violations, "PR_TEMPLATE", f"missing section {section}")
    check_pr_template_quality(pr_template_text, violations)
    if "Policy-drift review" not in contributing_text:
        add(violations, "DOC_ALIGNMENT", "CONTRIBUTING must require policy-drift review")
    if "GOVERNANCE_POLICY_DRIFT_RUNBOOK.md" not in contributing_text:
        add(violations, "DOC_ALIGNMENT", "CONTRIBUTING must reference policy-drift runbook")
    if "Do not claim repo-native enforcement for controls that are external GitHub settings." not in contributing_text:
        add(violations, "DOC_ALIGNMENT", "CONTRIBUTING must include documentation truthfulness rule for external settings")

    hooks: dict[str, dict[str, Any]] = {}
    repos = precommit_cfg.get("repos") if isinstance(precommit_cfg, dict) else None
    if isinstance(repos, list):
        for repo in repos:
            if isinstance(repo, dict) and repo.get("repo") == "local" and isinstance(repo.get("hooks"), list):
                for h in repo["hooks"]:
                    if isinstance(h, dict) and isinstance(h.get("id"), str):
                        hooks[h["id"]] = h

    required_hooks = {
        **shared_commands_from_registry(registry),
        "governance-registry-schema": "python tools/validate_json.py schemas/governance-invariant-registry.schema.json governance/invariant-registry.json",
        "governance-checklist-render": "python tools/render_governance_checklist.py",
        "governance-self-integrity": "python tools/validate_governance.py",
        "dependency-hermeticity": "python tools/check_dependency_hermeticity.py",
        "governance-cli-contracts": "python tools/check_cli_contracts.py",
        "governance-nondeterminism": "python tools/check_governance_nondeterminism.py",
        "governance-local-baseline": "python tools/run_local_governance_baseline.py",
    }
    for hook_id, token in required_hooks.items():
        h = hooks.get(hook_id)
        if not isinstance(h, dict):
            add(violations, "PRECOMMIT", f"missing hook id {hook_id}")
            continue
        entry = str(h.get("entry", ""))
        if token not in entry:
            add(violations, "PRECOMMIT", f"hook {hook_id} entry drift from canonical command")
        if h.get("pass_filenames") is not False:
            add(violations, "PRECOMMIT", f"hook {hook_id} must set pass_filenames: false")

    workflow_text = "\n".join(read_required_text(wf, violations) for wf in workflow_files())
    for hook_id, token in required_hooks.items():
        if token not in workflow_text:
            add(violations, "PARITY", f"workflow missing shared canonical command for {hook_id}")

    # generated checklist integrity
    expected_registry = "\n".join(render_registry_rows(registry)).strip()
    actual_registry = block_between(checklist_text, REGISTRY_DOC_START, REGISTRY_DOC_END)
    if expected_registry != actual_registry:
        add(violations, "DOC_ALIGNMENT", "checklist generated invariant table is stale")

    expected_baseline = "\n".join(["```bash", *render_baseline_commands(registry), "```"])
    actual_baseline = block_between(checklist_text, BASELINE_DOC_START, BASELINE_DOC_END)
    if expected_baseline.strip() != actual_baseline.strip():
        add(violations, "DOC_ALIGNMENT", "checklist generated baseline commands are stale")

    expected_not_verified = "\n".join(render_not_verified_rows(registry)).strip()
    actual_not_verified = block_between(checklist_text, NOT_VERIFIED_DOC_START, NOT_VERIFIED_DOC_END)
    if expected_not_verified != actual_not_verified:
        add(violations, "DOC_ALIGNMENT", "checklist generated 'what is not verified' block is stale")

    if "policy_version" not in contributing_text or "GOVERNANCE_CONTRACT_CHANGELOG.md" not in contributing_text:
        add(violations, "DOC_ALIGNMENT", "CONTRIBUTING missing governance policy/changelog discipline")


    verify_chain_script = read_required_text(ROOT / "tools/verify_execution_chain.py", violations)
    if verify_chain_script:
        if "allow-non-authoritative-git" not in verify_chain_script:
            add(violations, "GOV_DEP_GRAPH", "verify_execution_chain missing explicit non-authoritative-git opt-out control")

    fail_closed_script = read_required_text(ROOT / "tools/assert_fail_closed_semantics.py", violations)
    if fail_closed_script:
        if "task['evidence_artifact_ids'] = []" not in fail_closed_script and "task[\"evidence_artifact_ids\"] = []" not in fail_closed_script:
            add(violations, "FAIL_CLOSED", "fail-closed script missing schema-valid evidence mutation token")
        if "payload['artifacts'] = []" in fail_closed_script:
            add(violations, "FAIL_CLOSED", "fail-closed script contains invalid payload['artifacts']=[] mutation")

    # policy constants must be referenced in contributing
    for token in ("FM_*", "SHARED", "CI_ONLY", "LOCAL_ONLY"):
        if token not in contributing_text:
            add(violations, "DOC_ALIGNMENT", f"CONTRIBUTING missing policy term {token}")

    # repo-map checks + publication coverage
    for key in ("root", "docs", "tools", "github", "site"):
        if not isinstance(repo_map.get(key), list):
            add(violations, "REPO_MAP", f"{key} must be a list")

    if isinstance(repo_map.get("site"), list):
        mapped = sorted(Path(x).name for x in repo_map["site"] if str(x).endswith(".html"))
        actual = sorted(p.name for p in ROOT.glob("*.html"))
        if mapped != actual:
            add(violations, "PUBLICATION_COVERAGE", f"repo-map site mismatch mapped={mapped} actual={actual}")

    check_repo_map_truthfulness(repo_map, manifest, violations)

    # critical artifact classes present
    for cls, files in CRITICAL_ARTIFACT_CLASSES.items():
        for rel in files:
            if not (ROOT / rel).exists():
                add(violations, "CRITICAL_ARTIFACT", f"{cls} missing file {rel}")
            if manifest and rel not in manifest:
                add(violations, "CRITICAL_ARTIFACT", f"{cls} file not in MANIFEST {rel}")

    # canonical exclusion policy surfaced
    if not INTERNAL_LINK_EXCLUDE_PREFIXES:
        add(violations, "PUBLICATION_POLICY", "internal link exclusions policy must be non-empty")
    if "localhost" not in EXTERNAL_LINK_EXCLUDE_HOSTS:
        add(violations, "PUBLICATION_POLICY", "external reachability exclusion policy missing localhost")
    if "description" not in PUBLICATION_REQUIRED_META_NAMES:
        add(violations, "PUBLICATION_POLICY", "required publication meta policy missing description")

    github_files = {f".github/{p.relative_to(ROOT / '.github').as_posix()}" for p in (ROOT / ".github").rglob("*") if p.is_file()}
    for item in sorted(github_files - ALLOWED_GITHUB_FILES):
        add(violations, "GITHUB_SURFACE", f"unauthorized .github surface {item}")

    for rel in ("tools/check_internal_links.py", "tools/check_external_links.py", "tools/validate_publication_surfaces.py"):
        txt = read_required_text(ROOT / rel, violations)
        if "errors=\"ignore\"" in txt or "errors='ignore'" in txt:
            add(violations, "PUBLICATION_POLICY", f"forbidden decode errors='ignore' in {rel}")

    if manifest:
        for rel in manifest.keys():
            for pat in MANIFEST_DENY_PATTERNS:
                if re.search(pat, rel):
                    add(violations, "MANIFEST_POLICY", f"forbidden entry {rel}")
                    break

    failed = any(v.severity == "error" for v in violations)

    if args.json:
        report = {
            "policy_version": POLICY_VERSION,
            "status": "FAILED" if failed else "OK",
            "violation_count": len(violations),
            "violations": [v.__dict__ for v in violations],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))

    if violations:
        for v in violations:
            print(f"GOVERNANCE_VIOLATION | {v.severity.upper()} | {v.code}: {v.message}")

    if failed:
        print("GOVERNANCE_CHECK_FAILED")
        return 2

    print("GOVERNANCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
