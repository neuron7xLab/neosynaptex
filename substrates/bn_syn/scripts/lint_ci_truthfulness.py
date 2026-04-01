#!/usr/bin/env python3
"""Lint CI workflows for truthfulness and quality.

This governance gate scans GitHub Actions workflows for anti-patterns that
could lead to false-green CI or policy drift:

1. Test/verification commands followed by `|| true` (masks failures)
2. Hard-coded "success" summaries not derived from actual outputs
3. Workflow inputs declared but never used
4. Missing permissions declarations (should be explicit and minimal)

Usage:
    python -m scripts.lint_ci_truthfulness --out artifacts/ci_truthfulness.json --md artifacts/ci_truthfulness.md

Exit codes:
    0: All checks passed
    1: Critical violations found
    2: Warnings found (can be promoted to errors)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Violation:
    """A single violation found in a workflow."""

    severity: str  # "error" or "warning"
    category: str
    workflow: str
    location: str  # e.g., "job:test-suite, step:3"
    message: str
    suggestion: str = ""


@dataclass
class LintResult:
    """Results from linting workflows."""

    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0

    @property
    def has_errors(self) -> bool:
        return any(v.severity == "error" for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity == "warning" for v in self.violations)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "files_checked": self.files_checked,
            "total_violations": len(self.violations),
            "errors": len([v for v in self.violations if v.severity == "error"]),
            "warnings": len([v for v in self.violations if v.severity == "warning"]),
            "violations": [
                {
                    "severity": v.severity,
                    "category": v.category,
                    "workflow": v.workflow,
                    "location": v.location,
                    "message": v.message,
                    "suggestion": v.suggestion,
                }
                for v in self.violations
            ],
        }

    def to_markdown(self) -> str:
        """Convert to markdown report."""
        lines = ["# CI Truthfulness Lint Report\n"]

        lines.append(f"**Files Checked:** {self.files_checked}\n")
        lines.append(f"**Total Violations:** {len(self.violations)}\n")
        lines.append(f"**Errors:** {len([v for v in self.violations if v.severity == 'error'])}\n")
        lines.append(
            f"**Warnings:** {len([v for v in self.violations if v.severity == 'warning'])}\n"
        )
        lines.append("\n")

        if not self.violations:
            lines.append(
                "✅ **No violations found!** All workflows follow truthfulness guidelines.\n"
            )
            return "\n".join(lines)

        # Group by severity
        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]

        if errors:
            lines.append("## ❌ Errors (Must Fix)\n")
            for v in errors:
                lines.append(f"### {v.category}\n")
                lines.append(f"**Workflow:** `{v.workflow}`\n")
                lines.append(f"**Location:** {v.location}\n")
                lines.append(f"**Issue:** {v.message}\n")
                if v.suggestion:
                    lines.append(f"**Suggestion:** {v.suggestion}\n")
                lines.append("\n")

        if warnings:
            lines.append("## ⚠️ Warnings\n")
            for v in warnings:
                lines.append(f"### {v.category}\n")
                lines.append(f"**Workflow:** `{v.workflow}`\n")
                lines.append(f"**Location:** {v.location}\n")
                lines.append(f"**Issue:** {v.message}\n")
                if v.suggestion:
                    lines.append(f"**Suggestion:** {v.suggestion}\n")
                lines.append("\n")

        return "\n".join(lines)


class WorkflowLinter:
    """Lint GitHub Actions workflows for truthfulness."""

    def __init__(self) -> None:
        self.result = LintResult()

    def lint_file(self, workflow_path: Path) -> None:
        """Lint a single workflow file."""
        try:
            with workflow_path.open() as f:
                workflow = yaml.safe_load(f)
        except Exception as e:
            self.result.violations.append(
                Violation(
                    severity="error",
                    category="Parse Error",
                    workflow=workflow_path.name,
                    location="file",
                    message=f"Failed to parse workflow: {e}",
                )
            )
            return

        self.result.files_checked += 1

        # Check for missing permissions
        self._check_permissions(workflow, workflow_path.name)

        # Check jobs
        jobs = workflow.get("jobs", {})
        for job_name, job_def in jobs.items():
            self._check_job(job_name, job_def, workflow_path.name)

        # Check for unused inputs
        self._check_unused_inputs(workflow, workflow_path.name)

    def _check_permissions(self, workflow: dict, workflow_name: str) -> None:
        """Check that permissions are explicit and minimal."""
        # Check workflow-level permissions
        if "permissions" not in workflow:
            # Check if any job has permissions
            jobs = workflow.get("jobs", {})
            has_job_permissions = any("permissions" in job for job in jobs.values())

            if not has_job_permissions:
                self.result.violations.append(
                    Violation(
                        severity="warning",
                        category="Missing Permissions",
                        workflow=workflow_name,
                        location="workflow-level",
                        message="No explicit permissions defined at workflow or job level",
                        suggestion="Add 'permissions: contents: read' at minimum",
                    )
                )

    def _check_job(self, job_name: str, job_def: dict, workflow_name: str) -> None:
        """Check a single job for violations."""
        steps = job_def.get("steps", [])

        for i, step in enumerate(steps):
            step_name = step.get("name", f"step-{i}")
            location = f"job:{job_name}, step:{i + 1} ({step_name})"

            # Check for `run` steps with commands
            if "run" in step:
                self._check_run_step(step["run"], location, workflow_name)

    def _check_run_step(self, run_command: str, location: str, workflow_name: str) -> None:
        """Check a run command for anti-patterns."""
        # Check for `|| true` after test/verification commands
        # Exception: mutmut show --status may have no survivors (documented as acceptable)
        test_patterns = [
            r"pytest.*\|\|\s*true",
            r"mutmut\s+run.*\|\|\s*true",  # Only flag mutmut run, not mutmut show
            r"make\s+test.*\|\|\s*true",
            r"make\s+check.*\|\|\s*true",
            r"coqc.*\|\|\s*true",
            r"java.*tlc.*\|\|\s*true",
        ]

        for pattern in test_patterns:
            if re.search(pattern, run_command, re.IGNORECASE):
                self.result.violations.append(
                    Violation(
                        severity="error",
                        category="Masked Test Failure",
                        workflow=workflow_name,
                        location=location,
                        message="Test command followed by '|| true' - this masks failures!",
                        suggestion="Remove '|| true'. Use 'if: always()' on artifact upload steps instead.",
                    )
                )

        # Check for hard-coded success messages in summaries
        hardcoded_success_patterns = [
            r'echo\s+".*[Pp]assed.*"\s*>>.*GITHUB_STEP_SUMMARY',
            r'echo\s+".*[Ss]uccess.*"\s*>>.*GITHUB_STEP_SUMMARY',
            r'echo\s+".*\d+\s+tests.*"\s*>>.*GITHUB_STEP_SUMMARY',  # Hard-coded test counts
        ]

        for pattern in hardcoded_success_patterns:
            if re.search(pattern, run_command):
                # Only flag if not preceded by actual parsing
                if "grep" not in run_command and "tail" not in run_command:
                    self.result.violations.append(
                        Violation(
                            severity="warning",
                            category="Hard-Coded Summary",
                            workflow=workflow_name,
                            location=location,
                            message="Hard-coded success message in GITHUB_STEP_SUMMARY",
                            suggestion="Derive summaries from actual test output using grep/tail/parsing",
                        )
                    )

    def _check_unused_inputs(self, workflow: dict, workflow_name: str) -> None:
        """Check for workflow inputs that are never used."""
        on_config = workflow.get("on", {})

        if isinstance(on_config, dict) and "workflow_dispatch" in on_config:
            dispatch_config = on_config["workflow_dispatch"]
            if isinstance(dispatch_config, dict) and "inputs" in dispatch_config:
                inputs = dispatch_config["inputs"]

                # Convert workflow to string to search for input usage
                workflow_str = yaml.dump(workflow)

                for input_name in inputs.keys():
                    # Check if input is referenced in the workflow
                    # Inputs are referenced as ${{ inputs.input_name }} or ${{ github.event.inputs.input_name }}
                    input_patterns = [
                        rf"\$\{{\s*inputs\.{input_name}\s*\}}",
                        rf"\$\{{\s*github\.event\.inputs\.{input_name}\s*\}}",
                    ]

                    used = any(re.search(pattern, workflow_str) for pattern in input_patterns)

                    if not used:
                        self.result.violations.append(
                            Violation(
                                severity="warning",
                                category="Unused Input",
                                workflow=workflow_name,
                                location=f"workflow_dispatch.inputs.{input_name}",
                                message=f"Input '{input_name}' is declared but never used",
                                suggestion="Either use the input or remove it from the workflow_dispatch configuration",
                            )
                        )

    def lint_all(self, workflows_dir: Path) -> LintResult:
        """Lint all workflow files in directory."""
        workflow_files = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))

        for workflow_file in workflow_files:
            if workflow_file.name.startswith("_"):
                # Skip reusable workflows
                continue
            self.lint_file(workflow_file)

        return self.result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lint CI workflows for truthfulness")
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="Directory containing workflow files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Output JSON report path",
    )
    parser.add_argument(
        "--md",
        type=Path,
        help="Output Markdown report path",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    args = parser.parse_args()

    # Lint workflows
    linter = WorkflowLinter()
    result = linter.lint_all(args.workflows_dir)

    # Write JSON output
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"JSON report written to: {args.out}")

    # Write Markdown output
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        with args.md.open("w") as f:
            f.write(result.to_markdown())
        print(f"Markdown report written to: {args.md}")

    # Print summary
    print("\n📊 CI Truthfulness Lint Summary")
    print(f"Files checked: {result.files_checked}")
    print(f"Violations: {len(result.violations)}")
    print(f"  Errors: {len([v for v in result.violations if v.severity == 'error'])}")
    print(f"  Warnings: {len([v for v in result.violations if v.severity == 'warning'])}")

    # Determine exit code
    if result.has_errors:
        print("\n❌ FAILED: Critical violations found")
        return 1
    elif args.strict and result.has_warnings:
        print("\n❌ FAILED: Warnings found (strict mode)")
        return 1
    elif result.has_warnings:
        print("\n⚠️  PASSED with warnings")
        return 0
    else:
        print("\n✅ PASSED: No violations found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
