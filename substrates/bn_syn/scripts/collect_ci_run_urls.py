from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

REQUIRED_WORKFLOWS = [
    {
        "key": "ci-pr-atomic",
        "name": "ci-pr-atomic",
        "workflow_path": ".github/workflows/ci-pr-atomic.yml",
    },
    {
        "key": "workflow-integrity",
        "name": "Workflow Integrity",
        "workflow_path": ".github/workflows/workflow-integrity.yml",
    },
    {
        "key": "math-quality-gate",
        "name": "Math Quality Gate",
        "workflow_path": ".github/workflows/math-quality-gate.yml",
    },
    {
        "key": "dependency-review",
        "name": "dependency-review",
        "workflow_path": ".github/workflows/dependency-review.yml",
    },
]


def infer_repo() -> str:
    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo

    try:
        url = (
            subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                text=True,
            )
            .strip()
            .replace(".git", "")
        )
    except subprocess.CalledProcessError:
        return "neuron7x/bnsyn-phase-controlled-emergent-dynamics"

    if url.startswith("git@github.com:"):
        return url.split(":", 1)[1]
    if "github.com/" in url:
        return url.split("github.com/", 1)[1]
    return "neuron7x/bnsyn-phase-controlled-emergent-dynamics"


def infer_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def github_get_json(url: str, token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ci-proof-collector",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code}: {body}") from exc


def run_sort_key(run: dict[str, Any]) -> tuple[str, int]:
    return (run.get("updated_at") or "", int(run.get("id") or 0))


def select_required_runs(all_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for wf in REQUIRED_WORKFLOWS:
        candidates = [
            run
            for run in all_runs
            if run.get("workflow_path") == wf["workflow_path"]
            or run.get("name") == wf["name"]
        ]

        successful = [
            run
            for run in candidates
            if run.get("status") == "completed" and run.get("conclusion") == "success"
        ]

        if successful:
            run = sorted(successful, key=run_sort_key)[-1]
            selected.append(
                {
                    "key": wf["key"],
                    "status": "SUCCESS",
                    "run_id": run.get("id"),
                    "html_url": run.get("html_url"),
                    "name": run.get("name"),
                    "workflow_path": run.get("workflow_path"),
                    "event": run.get("event"),
                    "created_at": run.get("created_at"),
                    "updated_at": run.get("updated_at"),
                    "run_status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                }
            )
            continue

        if wf["key"] == "dependency-review":
            selected.append(
                {
                    "key": wf["key"],
                    "status": "NOT_TRIGGERED",
                    "reason": "path-filter",
                    "name": wf["name"],
                    "workflow_path": wf["workflow_path"],
                }
            )
        else:
            selected.append(
                {
                    "key": wf["key"],
                    "status": "MISSING",
                    "reason": "no runs for head_sha",
                    "name": wf["name"],
                    "workflow_path": wf["workflow_path"],
                }
            )
    return selected


def summarize(selected: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"success": 0, "not_triggered": 0, "missing": 0}
    for item in selected:
        status = item.get("status")
        if status == "SUCCESS":
            counts["success"] += 1
        elif status == "NOT_TRIGGERED":
            counts["not_triggered"] += 1
        else:
            counts["missing"] += 1

    ready = counts["missing"] == 0
    return {
        **counts,
        "required_total": len(REQUIRED_WORKFLOWS),
        "pass": ready,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect GitHub Actions run URLs for a head SHA")
    parser.add_argument("--repo", default=infer_repo())
    parser.add_argument("--sha", default=infer_sha())
    parser.add_argument("--out", default="artifacts/audit/runs_for_head.json")
    parser.add_argument("--required", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    query = urllib.parse.urlencode({"head_sha": args.sha, "per_page": 100})
    url = f"https://api.github.com/repos/{args.repo}/actions/runs?{query}"
    payload = github_get_json(url, token)
    all_runs = payload.get("workflow_runs", [])

    selected = select_required_runs(all_runs)
    summary = summarize(selected)
    output = {
        "repo": args.repo,
        "head_sha": args.sha,
        "collected_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "required_workflows": REQUIRED_WORKFLOWS,
        "query": {"url": url, "total_count": payload.get("total_count", 0)},
        "runs": selected,
        "summary": summary,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
        fh.write("\n")

    if args.required and not summary["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
