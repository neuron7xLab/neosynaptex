#!/usr/bin/env python3
"""Compile deterministic PR intake markdown from repository state and validator evidence."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pr_intake_contract import REQUIRED_HEADINGS


@dataclass(frozen=True)
class PRInfo:
    number: int
    base_ref: str
    head_ref: str
    url: str


@dataclass(frozen=True)
class BaseRef:
    name: str
    revspec: str


@dataclass(frozen=True)
class ValidatorResult:
    command: str
    exit_code: int
    summary: str


@dataclass(frozen=True)
class GovernanceCriticalPolicy:
    prefixes: tuple[str, ...]
    exact_paths: frozenset[str]


def _run(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, check=check, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required executable not found: {args[0]}") from exc


def _first_summary_line(proc: subprocess.CompletedProcess[str]) -> str:
    text = "\n".join([proc.stdout.strip(), proc.stderr.strip()]).strip()
    if not text:
        return "(no output)"
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "(no output)")
    return " ".join(line.split())[:180]


def _branch_exists(branch: str) -> bool:
    return _run(["git", "show-ref", "--verify", f"refs/heads/{branch}"]).returncode == 0


def get_current_pr(*, require_gh: bool) -> PRInfo | None:
    try:
        proc = _run(["gh", "pr", "view", "--json", "number,baseRefName,headRefName,url"])
    except RuntimeError:
        if require_gh:
            raise
        return None
    if proc.returncode != 0:
        return None
    payload = json.loads(proc.stdout)
    return PRInfo(
        number=int(payload["number"]),
        base_ref=str(payload["baseRefName"]),
        head_ref=str(payload["headRefName"]),
        url=str(payload["url"]),
    )


def resolve_base_name(explicit_base: str | None, pr: PRInfo | None) -> str:
    if explicit_base:
        return explicit_base
    if pr is not None and pr.base_ref:
        return pr.base_ref

    head = _run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if head.returncode == 0:
        ref = head.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref.split("refs/remotes/origin/", 1)[1]

    remote_show = _run(["git", "remote", "show", "origin"])
    if remote_show.returncode == 0:
        for line in remote_show.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("HEAD branch:"):
                return stripped.split(":", 1)[1].strip()

    for candidate in ("main", "master", "trunk"):
        if _branch_exists(candidate) or _ref_exists(f"origin/{candidate}") or _ref_exists(f"refs/remotes/origin/{candidate}"):
            return candidate

    raise RuntimeError("Unable to resolve base branch. Pass --base or ensure gh/origin default branch is available.")


def _ref_exists(revspec: str) -> bool:
    return _run(["git", "rev-parse", "--verify", revspec]).returncode == 0


def resolve_base_ref(explicit_base: str | None, pr: PRInfo | None) -> BaseRef:
    base_name = resolve_base_name(explicit_base, pr)
    candidates = [f"origin/{base_name}", base_name, f"refs/remotes/origin/{base_name}"]
    for candidate in candidates:
        if _ref_exists(candidate):
            return BaseRef(name=base_name, revspec=candidate)
    raise RuntimeError(f"Unable to resolve base ref '{base_name}' to an existing local or remote revision")


def current_branch() -> str:
    proc = _run(["git", "branch", "--show-current"], check=True)
    branch = proc.stdout.strip()
    if not branch:
        raise RuntimeError("Unable to determine current branch")
    return branch


def compute_merge_base(base_revspec: str) -> str:
    proc = _run(["git", "merge-base", "HEAD", base_revspec])
    if proc.returncode != 0:
        raise RuntimeError(f"Unable to compute merge-base against base ref '{base_revspec}'")
    return proc.stdout.strip()


def list_changed_files(merge_base: str) -> list[str]:
    proc = _run(["git", "diff", "--name-only", f"{merge_base}..HEAD"], check=True)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def list_commit_subjects(merge_base: str) -> list[str]:
    proc = _run(["git", "log", "--format=%s", f"{merge_base}..HEAD"], check=True)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def run_validators(commands: list[str]) -> list[ValidatorResult]:
    results: list[ValidatorResult] = []
    for command in commands:
        args = shlex.split(command)
        if not args:
            raise RuntimeError("Validator command cannot be empty")
        proc = _run(args)
        results.append(ValidatorResult(command=command, exit_code=proc.returncode, summary=_first_summary_line(proc)))
    return results


def load_governance_critical_policy(repo_map_path: Path = Path("repo-map.json")) -> GovernanceCriticalPolicy:
    prefixes = ["governance/", "tools/validate_"]
    exact_paths = {
        "MANIFEST.json",
        "repo-map.json",
        "CONTRIBUTING.md",
        "docs/PR_PREMERGE_ENGINEERING_CHECKLIST.md",
        "tools/check_cli_contracts.py",
        "tools/validate_governance.py",
        "tools/validate_pr_intake.py",
    }

    if not repo_map_path.exists():
        raise RuntimeError(f"Required policy file missing: {repo_map_path}")

    try:
        payload = json.loads(repo_map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {repo_map_path}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to read {repo_map_path}: {exc}") from exc

    governance_entries = payload.get("governance", [])
    if not isinstance(governance_entries, list):
        raise RuntimeError("Invalid repo-map.json: key 'governance' must be a list")

    for entry in governance_entries:
        if not isinstance(entry, str):
            raise RuntimeError("Invalid repo-map.json: governance entries must be strings")
        if entry.strip():
            exact_paths.add(entry.strip())

    return GovernanceCriticalPolicy(prefixes=tuple(prefixes), exact_paths=frozenset(exact_paths))


def _is_governance_critical(changed_files: list[str], policy: GovernanceCriticalPolicy) -> bool:
    return any(path in policy.exact_paths or any(path.startswith(prefix) for prefix in policy.prefixes) for path in changed_files)


def compile_markdown(
    *,
    branch: str,
    base_branch: str,
    pr: PRInfo,
    merge_base: str,
    changed_files: list[str],
    commit_subjects: list[str],
    validators: list[ValidatorResult],
    governance_policy: GovernanceCriticalPolicy,
) -> str:
    failed = [v for v in validators if v.exit_code != 0]
    governance_critical = _is_governance_critical(changed_files, governance_policy)
    manifest_touched = any(p in {"MANIFEST.json", "repo-map.json"} for p in changed_files)

    evidence_lines = [
        f"- branch: `{branch}`",
        f"- base branch: `{base_branch}`",
        f"- merge-base: `{merge_base}`",
        f"- changed files ({len(changed_files)}): " + ", ".join(f"`{p}`" for p in changed_files),
        f"- commits ({len(commit_subjects)}): " + "; ".join(f"`{c}`" for c in commit_subjects),
    ]
    for val in validators:
        evidence_lines.append(f"- validator `{val.command}` => exit `{val.exit_code}`; summary: {val.summary}")

    risk_line = (
        "At least one required validator failed; PR body application is blocked until all validators return zero."
        if failed
        else "Primary risk is incomplete human review of governance/execution-chain implications despite green validators."
    )

    human_review = [
        f"Review semantic correctness of {len(changed_files)} changed file(s): " + ", ".join(f"`{p}`" for p in changed_files),
        "Confirm validator summaries match local command output and no command masking occurred.",
    ]
    if governance_critical:
        human_review.append("Governance-critical surfaces changed; require maintainer sign-off on policy-impact and fail-closed semantics.")

    policy_drift = (
        "Governance-critical surfaces changed in this diff; reviewers must confirm no contract drift against normative governance docs."
        if governance_critical
        else "No governance-critical surfaces changed by path heuristics; reviewers should still verify intake accuracy for this PR."
    )

    sections = {
        REQUIRED_HEADINGS[0]: f"This PR intake is compiled from live branch state for `{branch}` against `{base_branch}` and eliminates manual/fabricated body content.",
        REQUIRED_HEADINGS[1]: "Includes only files and commits present between merge-base and HEAD; excludes unrelated repository areas.",
        REQUIRED_HEADINGS[2]: "Touches deterministic PR-intake evidence pipeline invariants: base/PR resolution, validator truth capture, and fail-closed apply behavior.",
        REQUIRED_HEADINGS[3]: "\n".join(evidence_lines),
        REQUIRED_HEADINGS[4]: risk_line,
        REQUIRED_HEADINGS[5]: "Does not introduce unrelated governance subsystems or modify non-intake repository workflows.",
        REQUIRED_HEADINGS[6]: (
            "Manifest artifacts were updated in this diff and must be reviewed for truthful parity."
            if manifest_touched
            else "No manifest artifact files changed in this diff; refresh not required for this intake compiler update."
        ),
        REQUIRED_HEADINGS[7]: "\n".join(f"- {line}" for line in human_review),
        REQUIRED_HEADINGS[8]: policy_drift,
    }
    lines: list[str] = []
    for heading in REQUIRED_HEADINGS:
        lines.append(heading)
        lines.append(sections[heading])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def apply_pr_body(pr_number: int, body_file: Path) -> None:
    proc = _run(["gh", "pr", "edit", str(pr_number), "--body-file", str(body_file)])
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to update PR #{pr_number}: {proc.stderr.strip() or proc.stdout.strip()}")


def create_pr(base_branch: str, head_branch: str, body_file: Path, title: str) -> PRInfo:
    proc = _run(
        ["gh", "pr", "create", "--base", base_branch, "--head", head_branch, "--title", title, "--body-file", str(body_file), "--fill-first"]
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to create PR: {proc.stderr.strip() or proc.stdout.strip()}")
    created = get_current_pr(require_gh=True)
    if created is None:
        raise RuntimeError("PR create succeeded but current PR metadata could not be resolved")
    return created


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Explicit base branch")
    parser.add_argument("--validate", action="append", default=[], help="Validator command to execute (repeatable)")
    parser.add_argument("--output", default=".artifacts/compiled-pr-intake.md", help="Output markdown path")
    parser.add_argument("--dry-run", action="store_true", help="Compile and write markdown only; never mutate PR")
    parser.add_argument("--apply", action="store_true", help="Apply compiled markdown body to PR via gh")
    parser.add_argument("--create-if-missing", action="store_true", help="Create PR if one is missing (only with --apply)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.create_if_missing and not args.apply:
        raise RuntimeError("--create-if-missing requires --apply")

    pr = get_current_pr(require_gh=args.apply)
    if args.apply and pr is None and not args.create_if_missing:
        raise RuntimeError("No current PR found for this branch; rerun with --create-if-missing to allow creation")

    base_ref = resolve_base_ref(args.base, pr)
    merge_base = compute_merge_base(base_ref.revspec)
    changed_files = list_changed_files(merge_base)
    commit_subjects = list_commit_subjects(merge_base)
    if not changed_files:
        raise RuntimeError("No changed files found versus base; refusing to compile empty intake")
    if not commit_subjects:
        raise RuntimeError("No commits found versus base; refusing to compile empty intake")

    validator_results = run_validators(args.validate)
    failing = [v for v in validator_results if v.exit_code != 0]
    governance_policy = load_governance_critical_policy()

    branch = current_branch()
    placeholder_pr = pr or PRInfo(number=0, base_ref=base_ref.name, head_ref=branch, url="")
    markdown = compile_markdown(
        branch=branch,
        base_branch=base_ref.name,
        pr=placeholder_pr,
        merge_base=merge_base,
        changed_files=changed_files,
        commit_subjects=commit_subjects,
        validators=validator_results,
        governance_policy=governance_policy,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"COMPILED_PR_INTAKE {output_path}")

    if failing:
        joined = ", ".join(v.command for v in failing)
        raise RuntimeError(f"Validator failures detected; refusing PR update: {joined}")

    if args.dry_run:
        print("DRY_RUN_ONLY")
        return 0

    if args.apply:
        active_pr = pr
        if active_pr is None:
            latest = _run(["git", "log", "-1", "--format=%s"], check=True).stdout.strip()
            title = latest or f"{branch}: compiled PR intake"
            active_pr = create_pr(base_ref.name, branch, output_path, title)
        apply_pr_body(active_pr.number, output_path)
        print(f"PR_BODY_UPDATED #{active_pr.number}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
