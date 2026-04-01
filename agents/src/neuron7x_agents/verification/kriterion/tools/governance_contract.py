#!/usr/bin/env python3
"""Canonical governance contract constants and rendering helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POLICY_VERSION = "2026.24.0"
PIP_VERSION_POLICY = "25.3"

AUTHORITY_MODEL = {
    "MACHINE_VERIFIED": "Deterministic hard gate; non-zero exit blocks merge.",
    "MACHINE_ASSISTED": "Machine-checked hygiene model that improves review quality but is not correctness proof alone.",
    "HUMAN_REVIEW_ONLY": "Human constitutional judgment; cannot be fully automated.",
}

DOMAIN_CLASSES = [
    "integrity",
    "validity",
    "semantic_sufficiency",
    "publication",
    "hygiene",
]

VERIFICATION_SCOPES = ["SHARED", "CI_ONLY", "LOCAL_ONLY"]

CLAIM_CLASSES = [
    "artifact_integrity_claim",
    "schema_validity_claim",
    "semantic_behavior_claim",
    "publication_surface_claim",
    "governance_hygiene_claim",
]

FAILURE_MODE_VOCABULARY = {
    "FM_MANIFEST_DRIFT": "Repository tree drifts from MANIFEST hashes.",
    "FM_SCHEMA_REGRESSION": "Schema acceptance/rejection semantics regress.",
    "FM_NONDETERMINISTIC_HASH": "Canonical hashing output becomes unstable.",
    "FM_RUNNER_EXECUTION_DRIFT": "Worked example execution path regresses.",
    "FM_FAIL_CLOSED_REGRESSION": "Missing evidence fails to fail-closed.",
    "FM_GATE_ID_DRIFT": "Gate IDs drift from canonical contract.",
    "FM_BENCHMARK_OVERCLAIM": "Benchmark claims exceed demo-only reality.",
    "FM_ENTRYPOINT_BREAKAGE": "Core tool entrypoints no longer invoke.",
    "FM_SYNTAX_BREAKAGE": "Syntax/import breakage in tools/benchmark scripts.",
    "FM_INTERNAL_LINK_BREAKAGE": "Internal links/anchors resolve incorrectly.",
    "FM_EXTERNAL_LINK_BREAKAGE": "External reachability indicates broken public references.",
    "FM_PAGES_SURFACE_BREAKAGE": "Published HTML surface is structurally broken.",
    "FM_ARTIFACT_PROVENANCE_DRIFT": "CI evidence artifacts lack canonical names/checksums/provenance.",
    "FM_DOCTRINE_DRIFT": "Governance doctrine drifts from policy constraints.",
    "FM_POLICY_DOC_DRIFT": "Checklist/docs diverge from canonical governance contract.",
    "FM_GOVERNANCE_REGRESSION": "Validator behavior drifts without regression guardrails.",
    "FM_DEPENDENCY_HERMETICITY": "Dependency policy is non-deterministic or lockfile drifts.",
    "FM_UNDECLARED_DEPENDENCY": "Governance tools import undeclared hidden dependencies.",
    "FM_CLI_CONTRACT_DRIFT": "Governance-critical CLI entrypoints drift from expected contract.",
    "FM_REQUIRED_CHECK_MAPPING_DRIFT": "Required-check to workflow-job mapping drifts from canonical immutable contract.",
    "FM_GITHUB_SETTINGS_BASELINE_DRIFT": "Declared external GitHub settings baseline drifts from enforced governance contract.",
    "FM_POST_MERGE_OPS_DRIFT": "Post-merge GitHub operations drift from repository governance assumptions.",
    "FM_POLICY_DRIFT_REVIEW_MISSING": "Policy-drift review section is missing for governance-critical changes.",
    "FM_WORKFLOW_PRIVILEGE_ESCALATION": "Workflow permissions/triggers/escalation surfaces violate trust model.",
    "FM_MANIFEST_INVENTORY_UNTRUTHFUL": "MANIFEST inventory is incomplete, manipulated, or includes forbidden artifacts.",
    "FM_REPO_MAP_UNTRUTHFUL": "repo-map inventory is incomplete, stale, or unauthorized.",
    "FM_CODEOWNERS_DILUTION": "CODEOWNERS rules are diluted by broad later patterns.",
    "FM_PR_TEMPLATE_WEAKENING": "PR template structure/content quality is weakened or placeholder-only.",
    "FM_LOCAL_BASELINE_DRIFT": "Canonical local baseline parity drifts from CI/checklist surfaces.",
    "FM_GOVERNANCE_ARTIFACT_NONDETERMINISM": "Tracked governance artifacts are generated nondeterministically.",
    "FM_ONE_PR_DOCTRINE_WEAKENING": "Auto-generated PR mechanisms or maintenance bots can bypass one-PR doctrine.",
    "FM_JOB_WEAKENING": "Critical CI jobs are silently weakened (strictness, retention, tolerating failures).",
    "FM_DOCUMENTATION_UNTRUTHFUL": "Governance docs claim enforcement beyond repo-native capability.",
    "FM_PR_INTAKE_QUALITY": "Pull request intake quality is empty/formal for mandatory governance sections.",
}

PR_TEMPLATE_SECTIONS = [
    "## Problem",
    "## Scope",
    "## Invariants touched",
    "## Evidence",
    "## Risks",
    "## Non-goals",
    "## Manifest refresh justification",
    "## Human review required",
    "## Policy-drift review (mandatory for governance-critical surfaces)",
]

REQUIRED_CODEOWNERS_PATHS = [
    ".github/workflows/*",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".pre-commit-config.yaml",
    "MANIFEST.json",
    "repo-map.json",
    "tools/*",
    "docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md",
    "CONTRIBUTING.md",
    "governance/*",
    "requirements.txt",
]

ALLOWED_GITHUB_FILES = {
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
    ".github/workflows/quality-gates.yml",
    ".github/workflows/pages.yml",
}

MANIFEST_DENY_PATTERNS = [
    r"(^|/)__pycache__(/|$)",
    r"\.pyc$",
    r"\.pyo$",
    r"\.swp$",
    r"~$",
    r"\.tmp$",
    r"\.cache(/|$)",
]

FORBIDDEN_RUN_PATTERNS = [
    r"curl\s+[^\n|]*\|\s*(?:bash|sh)",
    r"wget\s+[^\n|]*\|\s*(?:bash|sh)",
    r"pip\s+install\s+git\+",
    r"python\s+-m\s+pip\s+install\s+git\+",
]

INTERNAL_LINK_EXCLUDE_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
    "javascript:",
    ".github/",
)

EXTERNAL_LINK_EXCLUDE_HOSTS = {
    "localhost",
    "127.0.0.1",
    "example.invalid",
}

PUBLICATION_REQUIRED_META_NAMES = ["description", "viewport"]

CRITICAL_ARTIFACT_CLASSES = {
    "governance": [
        ".github/workflows/quality-gates.yml",
        ".pre-commit-config.yaml",
        ".gitignore",
        "governance/invariant-registry.json",
        "schemas/governance-invariant-registry.schema.json",
        "tools/validate_governance.py",
        "tools/governance_contract.py",
        "tools/render_governance_checklist.py",
        "tools/check_canonical_hash_stability.py",
        "tools/check_canonicalization_negative_cases.py",
        "tools/assert_worked_example_semantics.py",
        "tools/assert_fail_closed_semantics.py",
        "tools/assert_gate_benchmark_invariants.py",
        "tools/check_cli_contracts.py",
        "tools/check_dependency_hermeticity.py",
        "governance/requirements-governance.lock.json",
        "governance/ci-required-checks.json",
        "governance/github-settings-baseline.json",
        "docs/GOVERNANCE_POLICY_DRIFT_RUNBOOK.md",
        "docs/GOVERNANCE_NORMATIVE_SPEC.md",
        "tools/check_governance_nondeterminism.py",
        "tools/run_local_governance_baseline.py",
        "tools/validate_pr_intake.py",
    ],
    "publication": [
        "index.html",
        "system-map.html",
        "protocol-explorer.html",
        "benchmark-dashboard.html",
        "doctrine.html",
        "execution-layer.html",
    ],
    "benchmark": [
        "benchmark/benchmark_runner.py",
        "benchmark/metrics.json",
        "benchmark/results/case_level_results.csv",
    ],
    "execution": [
        "tools/reference_runner.py",
        "schemas/evaluation-result.schema.json",
        "examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json",
    ],
}

REGISTRY_DOC_START = "<!-- GOVERNANCE_REGISTRY_TABLE:START -->"
REGISTRY_DOC_END = "<!-- GOVERNANCE_REGISTRY_TABLE:END -->"
BASELINE_DOC_START = "<!-- GOVERNANCE_BASELINE_COMMANDS:START -->"
BASELINE_DOC_END = "<!-- GOVERNANCE_BASELINE_COMMANDS:END -->"
NOT_VERIFIED_DOC_START = "<!-- GOVERNANCE_NOT_VERIFIED:START -->"
NOT_VERIFIED_DOC_END = "<!-- GOVERNANCE_NOT_VERIFIED:END -->"


def load_registry(root: Path) -> dict[str, Any]:
    path = root / "governance" / "invariant-registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def shared_commands_from_registry(registry: dict[str, Any]) -> dict[str, str]:
    shared: dict[str, str] = {}
    for inv in registry.get("invariants", []):
        if inv.get("verification_scope") == "SHARED" and inv.get("local_command"):
            shared[str(inv["local_command_id"])] = str(inv["local_command"])
    return shared


def expected_job_ids(registry: dict[str, Any]) -> set[str]:
    jobs = {str(i["ci_job_id"]) for i in registry.get("invariants", []) if i.get("ci_job_id")}
    jobs.add("governance-hygiene")
    return jobs


def render_registry_rows(registry: dict[str, Any]) -> list[str]:
    rows = []
    for inv in registry.get("invariants", []):
        rows.append(
            "- `"
            + f"{inv['invariant_id']} | {inv['domain_class']} | {inv['verification_scope']} | {inv['authority_class']} | "
            + f"{inv['enforcer']} | {', '.join(inv['blocked_failure_mode_codes'])}`"
        )
    return rows


def render_not_verified_rows(registry: dict[str, Any]) -> list[str]:
    notes = sorted({str(n) for inv in registry.get("invariants", []) for n in inv.get("what_is_not_verified", [])})
    return [f"- {n}" for n in notes]


def render_baseline_commands(registry: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    for inv in registry.get("invariants", []):
        scope = inv.get("verification_scope")
        cmd = inv.get("local_command")
        if scope in {"LOCAL_ONLY", "SHARED"} and cmd:
            commands.append(str(cmd))
    deduped = []
    seen = set()
    for c in commands:
        if c not in seen:
            deduped.append(c)
            seen.add(c)
    return deduped
