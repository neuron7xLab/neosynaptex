import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def test_cli_end_to_end(tmp_path: Path) -> None:
    cfg = tmp_path / "basic_task.yaml"
    cfg.write_text(Path("examples/basic_task.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    run = subprocess.run(
        [sys.executable, "-m", "aoc.cli", "run", "--config", str(cfg)],
        cwd=tmp_path,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    verdict = json.loads(run.stdout)
    assert verdict["status"] == "PASS"


def test_cli_non_pass_returns_nonzero(tmp_path: Path) -> None:
    cfg = tmp_path / "basic_task_fail.yaml"
    payload = yaml.safe_load(Path("examples/basic_task.yaml").read_text(encoding="utf-8"))
    payload["constraints"]["forbidden_terms"] = ["Objective", "TODO"]
    cfg.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    run = subprocess.run(
        [sys.executable, "-m", "aoc.cli", "run", "--config", str(cfg)],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    verdict = json.loads(run.stdout)
    assert verdict["status"] in {"FAIL", "MAX_ITER", "INCONCLUSIVE"}
    assert run.returncode != 0
