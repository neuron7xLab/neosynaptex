#!/usr/bin/env python3
"""Generate an execution-backed release readiness report for BN-Syn."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_readiness_contract() -> tuple[type[Any], type[Any]]:
    module_path = REPO_ROOT / "src" / "bnsyn" / "qa" / "readiness_contract.py"
    spec = importlib.util.spec_from_file_location("bnsyn_qa_readiness_contract_cli", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load readiness contract from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("bnsyn_qa_readiness_contract_cli", module)
    spec.loader.exec_module(module)
    return module.ReadinessState, module.ReadinessStatus


ReadinessState, ReadinessStatus = _load_readiness_contract()


def build_report(repo_root: Path) -> dict[str, Any]:
    """Build the canonical release readiness report."""
    state = cast(Any, ReadinessState).evaluate(repo_root)
    return cast(dict[str, Any], state.to_report())


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable markdown summary of the readiness report."""
    status = str(report["state"]).upper()
    lines = [
        "# Release Readiness Report",
        "",
        f"- Timestamp: {report['timestamp']}",
        f"- Truth model version: {report['truth_model_version']}",
        f"- Version: {report.get('version') or 'unknown'}",
        f"- Overall state: **{status}**",
        f"- Release ready: **{report['release_ready']}**",
        f"- Execution-backed passes: **{report['execution_backed_pass_count']}**",
        "",
        "## Subsystems",
        "",
    ]
    for subsystem in report["subsystems"]:
        lines.extend(
            [
                f"### {subsystem['label']} ({subsystem['status'].upper()})",
                "",
                "| Check | Kind | Status | Blocking | Details |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for check in subsystem["checks"]:
            lines.append(
                "| {name} | {kind} | {status} | {blocking} | {details} |".format(
                    name=check["name"],
                    kind=check["kind"],
                    status=check["status"],
                    blocking=check["blocking"],
                    details=check["details"],
                )
            )
        lines.append("")

    if report["blocking_failures"]:
        lines.extend(["## Blocking failures", ""])
        lines.extend(f"- {failure}" for failure in report["blocking_failures"])
        lines.append("")

    if report["advisory_findings"]:
        lines.extend(["## Advisory findings", ""])
        lines.extend(f"- {finding}" for finding in report["advisory_findings"])
        lines.append("")

    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release readiness report.")
    parser.add_argument(
        "--json-out",
        default="artifacts/release_readiness.json",
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--md-out",
        default="artifacts/release_readiness.md",
        help="Path to write Markdown report",
    )
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="Exit 0 even if the computed state is blocked",
    )
    args = parser.parse_args()

    repo_root = REPO_ROOT
    report = build_report(repo_root)

    json_path = repo_root / args.json_out
    md_path = repo_root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report) + "\n", encoding="utf-8")

    print(f"Release readiness: {str(report['state']).upper()}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")

    if report["state"] != ReadinessStatus.BLOCKED.value or args.advisory:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
