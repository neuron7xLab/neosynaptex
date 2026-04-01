from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
OUT_DIR = REPO_ROOT / "artifacts" / "de_tf" / "graphs"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_workflow(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def main() -> int:
    workflows: list[dict[str, Any]] = []
    tools: dict[str, list[str]] = {}
    unpinned: list[str] = []

    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
        parsed = _read_workflow(wf)
        jobs = parsed.get("jobs", {}) if isinstance(parsed.get("jobs"), dict) else {}
        wf_jobs: dict[str, Any] = {}

        for job_name, job_cfg in jobs.items():
            if not isinstance(job_cfg, dict):
                continue
            steps = _as_list(job_cfg.get("steps"))
            uses: list[str] = []
            runs: list[str] = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if "uses" in step:
                    use_val = str(step["uses"])
                    uses.append(use_val)
                    if not use_val.startswith("./") and len(use_val.rsplit("@", 1)[-1]) != 40:
                        unpinned.append(f"{wf.name}:{job_name}:{use_val}")
                if "run" in step:
                    cmd = str(step["run"]).strip()
                    runs.append(cmd)
                    tools.setdefault(job_name, []).append(cmd)
            wf_jobs[job_name] = {
                "concurrency": job_cfg.get("concurrency"),
                "permissions": job_cfg.get("permissions"),
                "run": runs,
                "uses": uses,
            }

        workflows.append(
            {
                "concurrency": parsed.get("concurrency"),
                "jobs": wf_jobs,
                "permissions": parsed.get("permissions"),
                "workflow": wf.name,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "workflows_graph.json").write_text(
        json.dumps({"workflows": workflows}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "tools_graph.json").write_text(
        json.dumps({"tools_by_job": tools}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "gaps.json").write_text(
        json.dumps({"unpinned_actions": sorted(unpinned)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
