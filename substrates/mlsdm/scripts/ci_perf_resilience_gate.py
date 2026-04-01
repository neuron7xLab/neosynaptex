#!/usr/bin/env python3
"""
CI Performance & Resilience Gate for MLSDM Repository

This script implements the SDPL CONTROL BLOCK v2.0 protocol for CI_PERF_RESILIENCE_GATE_V1.
It analyzes PR changes, classifies risk, inspects CI status, and provides merge verdicts.

Usage:
    python scripts/ci_perf_resilience_gate.py --pr-url <github_pr_url>
    python scripts/ci_perf_resilience_gate.py --pr-number <number> --repo neuron7xLab/mlsdm
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


class RiskMode(Enum):
    """Risk classification modes for PR changes."""

    GREEN_LIGHT = "GREEN_LIGHT"
    YELLOW_CRITICAL_PATH = "YELLOW_CRITICAL_PATH"
    RED_HIGH_RISK_OR_RELEASE = "RED_HIGH_RISK_OR_RELEASE"


class ChangeClass(Enum):
    """Classification of change types."""

    DOC_ONLY = "DOC_ONLY"
    NON_CORE_CODE = "NON_CORE_CODE"
    CORE_CRITICAL = "CORE_CRITICAL"


class JobStatus(Enum):
    """CI job status."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    PENDING = "pending"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class JobResult:
    """Result from a CI job."""

    name: str
    status: JobStatus
    key_facts: str


@dataclass
class FileChange:
    """Represents a changed file and its classification."""

    path: str
    change_class: ChangeClass
    reason: str


class PRAnalyzer:
    """Analyzes PR changes and classifies risk."""

    # Core critical path patterns
    CORE_CRITICAL_PATTERNS = [
        # Concurrency/async/queue/scheduler
        r"(async|await|asyncio|threading|multiprocessing|concurrent)",
        r"(queue|scheduler|worker|pool|executor)",
        # Network I/O, clients, storage
        r"(client|request|response|http|api|rest|grpc)",
        r"(storage|cache|redis|database|db|sql)",
        r"(broker|kafka|rabbitmq|message|event)",
        # Router/loop/engine/circuit breaker
        r"(router|loop|engine|circuit.*breaker|retry|backoff)",
        # Timeouts, rate limits, resource limits
        r"(timeout|rate.*limit|resource.*limit|throttle)",
        r"(memory.*limit|cpu.*limit|max.*connections)",
    ]

    # Core critical directories/files
    CORE_CRITICAL_PATHS = [
        "src/mlsdm/neuro_engine",
        "src/mlsdm/memory",
        "src/mlsdm/router",
        "src/mlsdm/circuit_breaker",
        "src/mlsdm/rate_limiter",
        "src/mlsdm/clients",
        "src/mlsdm/cache",
        "src/mlsdm/scheduler",
        "scripts/",  # CLI tools that affect runtime behavior
        "benchmarks/",  # Performance tests that define SLOs
        "config/",
        ".github/workflows/",
    ]

    # Documentation-only patterns
    DOC_PATTERNS = [
        r"\.md$",
        r"\.txt$",
        r"^docs/",
        r"^README",
        r"^CHANGELOG",
        r"^LICENSE",
        r"\.rst$",
    ]

    def __init__(self) -> None:
        """Initialize PR analyzer."""
        self.core_pattern_regex = re.compile("|".join(self.CORE_CRITICAL_PATTERNS), re.IGNORECASE)

    def classify_file(self, file_path: str, patch: str = "") -> FileChange:
        """Classify a single file change."""
        # Check if documentation only
        for pattern in self.DOC_PATTERNS:
            if re.search(pattern, file_path):
                return FileChange(
                    path=file_path,
                    change_class=ChangeClass.DOC_ONLY,
                    reason="Documentation or metadata file",
                )

        # Check if in core critical paths
        for critical_path in self.CORE_CRITICAL_PATHS:
            if file_path.startswith(critical_path):
                return FileChange(
                    path=file_path,
                    change_class=ChangeClass.CORE_CRITICAL,
                    reason=f"File in critical path: {critical_path}",
                )

        # Check patch content for critical patterns
        if self.core_pattern_regex.search(patch):
            matches = self.core_pattern_regex.findall(patch)
            # Flatten tuples from regex groups
            flat_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    flat_matches.extend([m for m in match if m])
                else:
                    flat_matches.append(match)
            return FileChange(
                path=file_path,
                change_class=ChangeClass.CORE_CRITICAL,
                reason=f"Contains critical patterns: {', '.join(list(set(flat_matches))[:3])}",
            )

        # Default to non-core code
        return FileChange(
            path=file_path,
            change_class=ChangeClass.NON_CORE_CODE,
            reason="Utility or non-critical code change",
        )

    def analyze_changes(self, files: list[dict[str, Any]]) -> list[FileChange]:
        """Analyze all changed files in a PR."""
        changes = []
        for file_info in files:
            file_path = file_info.get("filename", "")
            patch = file_info.get("patch", "")
            changes.append(self.classify_file(file_path, patch))
        return changes


class CIInspector:
    """Inspects CI job status from GitHub Actions."""

    PERF_RESILIENCE_JOBS = [
        "Fast Resilience Tests",
        "Performance & SLO Validation",
        "Comprehensive Resilience Tests",
    ]

    REQUIRED_BASE_JOBS = [
        "Lint and Type Check",
        "Security Vulnerability Scan",
        "Unit and Integration Tests",
        "Code Coverage",
    ]

    def __init__(self, github_token: str | None = None) -> None:
        """Initialize CI inspector."""
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.headers = {}
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"

    def get_workflow_runs(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Get workflow runs for a PR."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            pr_data = response.json()
            head_sha = pr_data["head"]["sha"]

            # Get workflow runs for this SHA
            runs_url = (
                f"https://api.github.com/repos/{owner}/{repo}/actions/runs?"
                f"head_sha={head_sha}&per_page=100"
            )
            response = requests.get(runs_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json().get("workflow_runs", [])
        except requests.RequestException as e:
            print(f"Warning: Failed to fetch workflow runs: {e}")
            return []

    def get_jobs_for_run(self, owner: str, repo: str, run_id: int) -> list[dict[str, Any]]:
        """Get jobs for a specific workflow run."""
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json().get("jobs", [])
        except requests.RequestException as e:
            print(f"Warning: Failed to fetch jobs for run {run_id}: {e}")
            return []

    def map_job_status(self, conclusion: str | None, status: str) -> JobStatus:
        """Map GitHub job status to our enum."""
        if conclusion == "success":
            return JobStatus.SUCCESS
        elif conclusion == "failure":
            return JobStatus.FAILURE
        elif conclusion == "cancelled":
            return JobStatus.CANCELLED
        elif conclusion == "skipped" or status == "skipped":
            return JobStatus.SKIPPED
        elif status in ["queued", "in_progress", "waiting"]:
            return JobStatus.PENDING
        return JobStatus.UNKNOWN

    def inspect_ci_jobs(self, owner: str, repo: str, pr_number: int) -> list[JobResult]:
        """Inspect CI jobs for a PR and return results."""
        workflow_runs = self.get_workflow_runs(owner, repo, pr_number)
        if not workflow_runs:
            return []

        job_results = []
        seen_jobs: set[str] = set()

        # Process each workflow run (most recent first)
        for run in sorted(workflow_runs, key=lambda r: r["created_at"], reverse=True):
            workflow_name = run["name"]
            jobs = self.get_jobs_for_run(owner, repo, run["id"])

            for job in jobs:
                job_name = job["name"]
                # Skip if we've already seen this job (use most recent)
                full_job_name = f"{workflow_name} / {job_name}"
                if full_job_name in seen_jobs:
                    continue
                seen_jobs.add(full_job_name)

                status = self.map_job_status(job.get("conclusion"), job.get("status", ""))

                # Extract key facts from job
                key_facts = self._extract_key_facts(job, status)

                job_results.append(
                    JobResult(
                        name=full_job_name,
                        status=status,
                        key_facts=key_facts,
                    )
                )

        return job_results

    def _extract_key_facts(self, job: dict[str, Any], status: JobStatus) -> str:
        """Extract key facts from job data."""
        facts = []

        if status == JobStatus.SUCCESS:
            facts.append("Passed")
        elif status == JobStatus.FAILURE:
            facts.append("Failed")
            # Try to get failure info from steps
            steps = job.get("steps", [])
            failed_steps = [s["name"] for s in steps if s.get("conclusion") == "failure"]
            if failed_steps:
                facts.append(f"Failed steps: {', '.join(failed_steps[:2])}")
        elif status == JobStatus.SKIPPED:
            facts.append("Skipped (conditions not met)")

        duration = (
            job.get("completed_at", "")
            and job.get("started_at", "")
            and self._calculate_duration(job["started_at"], job["completed_at"])
        )
        if duration:
            facts.append(f"Duration: {duration}")

        return " | ".join(facts) if facts else "No details available"

    def _calculate_duration(self, start: str, end: str) -> str:
        """Calculate duration between two ISO timestamps."""
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration = end_dt - start_dt
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            return f"{minutes}m{seconds}s"
        except Exception:
            return ""


class RiskClassifier:
    """Classifies PR risk based on changes and CI status."""

    def classify(
        self, changes: list[FileChange], job_results: list[JobResult], pr_labels: list[str]
    ) -> tuple[RiskMode, list[str]]:
        """Classify risk mode and provide reasoning."""
        reasons = []

        # Count change types
        doc_only = sum(1 for c in changes if c.change_class == ChangeClass.DOC_ONLY)
        core_critical = sum(1 for c in changes if c.change_class == ChangeClass.CORE_CRITICAL)
        non_core = sum(1 for c in changes if c.change_class == ChangeClass.NON_CORE_CODE)

        # Check for release indicators
        is_release = any(label.lower() in ["release", "production", "prod"] for label in pr_labels)

        # Classify based on changes
        if doc_only == len(changes) and len(changes) > 0:
            reasons.append(f"All {doc_only} changes are documentation-only")
            mode = RiskMode.GREEN_LIGHT
        elif core_critical == 0:
            reasons.append(f"No core critical changes detected ({non_core} non-core changes)")
            mode = RiskMode.GREEN_LIGHT
        elif core_critical >= 10 or is_release:
            if is_release:
                reasons.append("PR is marked for release/production")
            reasons.append(
                f"High number of core critical changes ({core_critical} critical, "
                f"{non_core} non-core)"
            )
            mode = RiskMode.RED_HIGH_RISK_OR_RELEASE
        else:
            reasons.append(
                f"Moderate core critical changes detected ({core_critical} critical, "
                f"{non_core} non-core)"
            )
            mode = RiskMode.YELLOW_CRITICAL_PATH

        return mode, reasons


class MergeVerdictor:
    """Determines merge verdict based on mode and CI status."""

    def determine_verdict(
        self, mode: RiskMode, job_results: list[JobResult]
    ) -> tuple[str, list[str], list[str]]:
        """
        Determine merge verdict.

        Returns:
            verdict: SAFE_TO_MERGE_NOW, DO_NOT_MERGE_YET, or
                     MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK
            required_actions: List of actions needed before merge
            reasons: List of reasons for the verdict
        """
        # Find relevant jobs
        perf_resilience_jobs = {
            jr.name: jr
            for jr in job_results
            if any(perf in jr.name for perf in CIInspector.PERF_RESILIENCE_JOBS)
        }
        base_jobs = {
            jr.name: jr
            for jr in job_results
            if any(base in jr.name for base in CIInspector.REQUIRED_BASE_JOBS)
        }

        required_actions = []
        reasons = []

        # Check base jobs first (always required)
        failed_base_jobs = [
            name for name, jr in base_jobs.items() if jr.status == JobStatus.FAILURE
        ]
        if failed_base_jobs:
            reasons.append(f"Base CI jobs failed: {', '.join(failed_base_jobs)}")
            required_actions.append(f"Fix failing base jobs: {', '.join(failed_base_jobs)}")
            return "DO_NOT_MERGE_YET", required_actions, reasons

        if mode == RiskMode.GREEN_LIGHT:
            # For green light, perf/resilience can be skipped
            reasons.append("Changes are low-risk (docs/non-core)")
            reasons.append("Perf/resilience tests not required for this PR")
            return "SAFE_TO_MERGE_NOW", [], reasons

        elif mode == RiskMode.YELLOW_CRITICAL_PATH:
            # Need Fast Resilience + Performance & SLO
            fast_res = next(
                (jr for jr in perf_resilience_jobs.values() if "Fast Resilience" in jr.name),
                None,
            )
            perf_slo = next(
                (jr for jr in perf_resilience_jobs.values() if "Performance & SLO" in jr.name),
                None,
            )

            if fast_res and fast_res.status == JobStatus.FAILURE:
                reasons.append("Fast Resilience Tests failed")
                required_actions.append("Fix Fast Resilience Tests failures")
            if perf_slo and perf_slo.status == JobStatus.FAILURE:
                reasons.append("Performance & SLO Validation failed")
                required_actions.append("Fix Performance & SLO Validation failures")

            if required_actions:
                return "DO_NOT_MERGE_YET", required_actions, reasons

            if (
                not fast_res
                or fast_res.status == JobStatus.SKIPPED
                or not perf_slo
                or perf_slo.status == JobStatus.SKIPPED
            ):
                reasons.append("Critical path changes require perf/resilience validation")
                required_actions.append(
                    "Add 'perf' or 'resilience' label to PR to trigger required tests"
                )
                required_actions.append(
                    "OR manually run 'perf-resilience' workflow via workflow_dispatch"
                )
                return "DO_NOT_MERGE_YET", required_actions, reasons

            # Both fast resilience and perf/slo passed
            reasons.append("Fast Resilience Tests: PASSED")
            reasons.append("Performance & SLO Validation: PASSED")
            return "SAFE_TO_MERGE_NOW", [], reasons

        elif mode == RiskMode.RED_HIGH_RISK_OR_RELEASE:
            # Need ALL three: Fast + Performance + Comprehensive
            fast_res = next(
                (jr for jr in perf_resilience_jobs.values() if "Fast Resilience" in jr.name),
                None,
            )
            perf_slo = next(
                (jr for jr in perf_resilience_jobs.values() if "Performance & SLO" in jr.name),
                None,
            )
            comprehensive = next(
                (jr for jr in perf_resilience_jobs.values() if "Comprehensive" in jr.name),
                None,
            )

            # Check for failures
            if fast_res and fast_res.status == JobStatus.FAILURE:
                reasons.append("Fast Resilience Tests failed")
                required_actions.append("Fix Fast Resilience Tests failures")
            if perf_slo and perf_slo.status == JobStatus.FAILURE:
                reasons.append("Performance & SLO Validation failed")
                required_actions.append("Fix Performance & SLO Validation failures")
            if comprehensive and comprehensive.status == JobStatus.FAILURE:
                reasons.append("Comprehensive Resilience Tests failed")
                required_actions.append("Fix Comprehensive Resilience Tests failures")

            if required_actions:
                return "DO_NOT_MERGE_YET", required_actions, reasons

            # Check for skipped/missing
            missing = []
            if not fast_res or fast_res.status == JobStatus.SKIPPED:
                missing.append("Fast Resilience Tests")
            if not perf_slo or perf_slo.status == JobStatus.SKIPPED:
                missing.append("Performance & SLO Validation")
            if not comprehensive or comprehensive.status == JobStatus.SKIPPED:
                missing.append("Comprehensive Resilience Tests")

            if missing:
                reasons.append(
                    f"High-risk/release PR requires full validation. Missing: {', '.join(missing)}"
                )
                required_actions.append(
                    "Manually run 'perf-resilience' workflow via workflow_dispatch"
                )
                required_actions.append(
                    "Ensure all three resilience/performance jobs complete successfully"
                )
                return "DO_NOT_MERGE_YET", required_actions, reasons

            # All tests passed
            reasons.append("All resilience and performance tests passed")
            reasons.append("Fast Resilience: PASSED")
            reasons.append("Performance & SLO: PASSED")
            reasons.append("Comprehensive Resilience: PASSED")
            return "SAFE_TO_MERGE_NOW", [], reasons

        return "MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK", [], ["Unknown mode"]


class CIPerfResilienceGate:
    """Main CI Performance & Resilience Gate implementation."""

    def __init__(self, github_token: str | None = None) -> None:
        """Initialize the gate."""
        self.pr_analyzer = PRAnalyzer()
        self.ci_inspector = CIInspector(github_token)
        self.risk_classifier = RiskClassifier()
        self.merge_verdictor = MergeVerdictor()

    def analyze_pr(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Analyze a PR and return full gate analysis."""
        print(f"\n🔍 Analyzing PR #{pr_number} in {owner}/{repo}...\n")

        # Fetch PR data
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {}
        if self.ci_inspector.github_token:
            headers["Authorization"] = f"token {self.ci_inspector.github_token}"
        headers["Accept"] = "application/vnd.github.v3+json"

        try:
            response = requests.get(pr_url, headers=headers, timeout=30)
            response.raise_for_status()
            pr_data = response.json()
        except requests.RequestException as e:
            print(f"❌ Error: Failed to fetch PR data: {e}")
            sys.exit(1)

        # Get PR labels
        pr_labels = [label["name"] for label in pr_data.get("labels", [])]

        # Get changed files
        files_url = f"{pr_url}/files"
        try:
            response = requests.get(files_url, headers=headers, timeout=30)
            response.raise_for_status()
            files = response.json()
        except requests.RequestException as e:
            print(f"❌ Error: Failed to fetch changed files: {e}")
            sys.exit(1)

        # Analyze changes
        changes = self.pr_analyzer.analyze_changes(files)

        # Inspect CI
        job_results = self.ci_inspector.inspect_ci_jobs(owner, repo, pr_number)

        # Classify risk
        mode, mode_reasons = self.risk_classifier.classify(changes, job_results, pr_labels)

        # Determine verdict
        verdict, required_actions, verdict_reasons = self.merge_verdictor.determine_verdict(
            mode, job_results
        )

        return {
            "pr_number": pr_number,
            "pr_title": pr_data.get("title", ""),
            "pr_labels": pr_labels,
            "changes": changes,
            "job_results": job_results,
            "mode": mode,
            "mode_reasons": mode_reasons,
            "verdict": verdict,
            "required_actions": required_actions,
            "verdict_reasons": verdict_reasons,
        }

    def generate_slo_improvements(self, analysis: dict[str, Any]) -> list[str]:
        """Generate SLO/CI improvement suggestions."""
        suggestions = []

        job_results = analysis["job_results"]
        mode = analysis["mode"]

        # Check if perf/resilience jobs are being skipped often
        perf_jobs = [
            jr for jr in job_results if any(p in jr.name for p in CIInspector.PERF_RESILIENCE_JOBS)
        ]
        if perf_jobs and all(jr.status == JobStatus.SKIPPED for jr in perf_jobs):
            suggestions.append(
                "Consider making Fast Resilience Tests mandatory for all PRs modifying "
                "src/mlsdm/neuro_engine or src/mlsdm/memory paths"
            )

        # Suggest label automation
        if mode in [RiskMode.YELLOW_CRITICAL_PATH, RiskMode.RED_HIGH_RISK_OR_RELEASE]:
            suggestions.append(
                "Add automatic label assignment based on changed paths (e.g., auto-add "
                "'perf' label when core paths are modified)"
            )

        # Suggest threshold improvements
        perf_slo = next((jr for jr in job_results if "Performance & SLO" in jr.name), None)
        if perf_slo and perf_slo.status == JobStatus.SUCCESS:
            suggestions.append(
                "Review and tighten SLO thresholds incrementally to drive continuous "
                "performance improvement"
            )

        # If no suggestions yet, add a default
        if not suggestions:
            suggestions.append(
                "CI workflows are well-configured. Continue monitoring performance trends."
            )

        return suggestions[:3]  # Limit to 3 suggestions

    def format_output(self, analysis: dict[str, Any]) -> str:
        """Format analysis output as markdown."""
        output = []

        output.append("# CI Performance & Resilience Gate Analysis")
        output.append("")
        output.append(f"**PR**: #{analysis['pr_number']} - {analysis['pr_title']}")
        output.append(f"**Labels**: {', '.join(analysis['pr_labels']) or 'None'}")
        output.append("")

        # Section 1: MODE CLASSIFICATION
        output.append("## Section 1: MODE_CLASSIFICATION")
        output.append("")
        output.append(f"**Mode**: `{analysis['mode'].value}`")
        output.append("")
        output.append("**Reasoning**:")
        for reason in analysis["mode_reasons"]:
            output.append(f"- {reason}")
        output.append("")

        # Section 2: CI STATUS TABLE
        output.append("## Section 2: CI_STATUS_TABLE")
        output.append("")
        output.append("| Job | Status | Key Facts |")
        output.append("|-----|--------|-----------|")

        if not analysis["job_results"]:
            output.append("| *(No CI jobs found)* | - | - |")
        else:
            for jr in analysis["job_results"]:
                status_emoji = {
                    JobStatus.SUCCESS: "✅",
                    JobStatus.FAILURE: "❌",
                    JobStatus.SKIPPED: "⏭️",
                    JobStatus.PENDING: "⏳",
                    JobStatus.CANCELLED: "🚫",
                    JobStatus.UNKNOWN: "❓",
                }.get(jr.status, "❓")
                output.append(f"| {jr.name} | {status_emoji} {jr.status.value} | {jr.key_facts} |")
        output.append("")

        # Section 3: REQUIRED ACTIONS
        output.append("## Section 3: REQUIRED_ACTIONS_BEFORE_MERGE")
        output.append("")
        if analysis["required_actions"]:
            for i, action in enumerate(analysis["required_actions"], 1):
                output.append(f"{i}. {action}")
        else:
            output.append("*(No actions required)*")
        output.append("")

        # Section 4: MERGE VERDICT
        output.append("## Section 4: MERGE_VERDICT")
        output.append("")
        verdict_emoji = {
            "SAFE_TO_MERGE_NOW": "✅",
            "DO_NOT_MERGE_YET": "❌",
            "MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK": "⚠️",
        }.get(analysis["verdict"], "❓")
        output.append(f"### {verdict_emoji} `{analysis['verdict']}`")
        output.append("")
        if analysis["verdict_reasons"]:
            for reason in analysis["verdict_reasons"]:
                output.append(f"- {reason}")
        output.append("")

        # Section 5: SLO/CI IMPROVEMENT IDEAS
        output.append("## Section 5: SLO/CI_IMPROVEMENT_IDEAS")
        output.append("")
        suggestions = self.generate_slo_improvements(analysis)
        for i, suggestion in enumerate(suggestions, 1):
            output.append(f"{i}. {suggestion}")
        output.append("")

        # Appendix: Change Classification
        output.append("## Appendix: Change Classification Details")
        output.append("")
        output.append("| File Path | Classification | Reason |")
        output.append("|-----------|----------------|--------|")
        for change in analysis["changes"]:
            output.append(f"| {change.path} | {change.change_class.value} | {change.reason} |")
        output.append("")

        return "\n".join(output)


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """Parse GitHub PR URL to extract owner, repo, and PR number."""
    # Example: https://github.com/neuron7xLab/mlsdm/pull/231
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise ValueError(f"Invalid PR URL format: {pr_url}")
    return match.group(1), match.group(2), int(match.group(3))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="CI Performance & Resilience Gate for MLSDM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pr-url",
        help="Full GitHub PR URL (e.g., https://github.com/neuron7xLab/mlsdm/pull/231)",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="PR number (use with --repo)",
    )
    parser.add_argument(
        "--repo",
        help="Repository in format owner/repo (e.g., neuron7xLab/mlsdm)",
    )
    parser.add_argument(
        "--github-token",
        help="GitHub API token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--output",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    # Determine owner, repo, and PR number
    if args.pr_url and (args.pr_number or args.repo):
        print("❌ Error: Cannot specify both --pr-url and --pr-number/--repo")
        print("   Use either --pr-url OR --pr-number with --repo, not both")
        sys.exit(1)
    elif args.pr_url:
        try:
            owner, repo, pr_number = parse_pr_url(args.pr_url)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    elif args.pr_number and args.repo:
        if "/" not in args.repo:
            print("❌ Error: --repo must be in format owner/repo")
            sys.exit(1)
        owner, repo = args.repo.split("/", 1)
        pr_number = args.pr_number
    else:
        print("❌ Error: Must provide either --pr-url or both --pr-number and --repo")
        parser.print_help()
        sys.exit(1)

    # Initialize gate
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("⚠️  Warning: No GitHub token provided. API rate limits may apply.")
        print("   Set GITHUB_TOKEN env var or use --github-token for authenticated requests.")
        print()

    gate = CIPerfResilienceGate(github_token)

    # Run analysis
    try:
        analysis = gate.analyze_pr(owner, repo, pr_number)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Output results
    if args.output == "json":
        # Convert enums to strings for JSON serialization
        json_analysis = {
            "pr_number": analysis["pr_number"],
            "pr_title": analysis["pr_title"],
            "pr_labels": analysis["pr_labels"],
            "mode": analysis["mode"].value,
            "mode_reasons": analysis["mode_reasons"],
            "verdict": analysis["verdict"],
            "required_actions": analysis["required_actions"],
            "verdict_reasons": analysis["verdict_reasons"],
            "changes": [
                {
                    "path": c.path,
                    "change_class": c.change_class.value,
                    "reason": c.reason,
                }
                for c in analysis["changes"]
            ],
            "job_results": [
                {
                    "name": jr.name,
                    "status": jr.status.value,
                    "key_facts": jr.key_facts,
                }
                for jr in analysis["job_results"]
            ],
            "slo_improvements": gate.generate_slo_improvements(analysis),
        }
        print(json.dumps(json_analysis, indent=2))
    else:
        print(gate.format_output(analysis))

    # Exit with appropriate code
    if analysis["verdict"] == "SAFE_TO_MERGE_NOW":
        sys.exit(0)
    elif analysis["verdict"] == "DO_NOT_MERGE_YET":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
