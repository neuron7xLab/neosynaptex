from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ci_pr_atomic_declares_pull_request_and_codeql_pr_job_guard() -> None:
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci-pr-atomic.yml").read_text(encoding="utf-8")
    )

    on_section = workflow.get("on", workflow.get(True, {}))
    assert isinstance(on_section, dict)
    assert "pull_request" in on_section

    jobs = workflow.get("jobs", {})
    assert isinstance(jobs, dict)
    assert "codeql-pr" in jobs

    codeql_pr_job = jobs["codeql-pr"]
    assert isinstance(codeql_pr_job, dict)
    condition = str(codeql_pr_job.get("if", ""))
    assert "github.event_name == 'pull_request'" in condition
    assert "run-codeql" in condition
    assert "heavy-ci" in condition
