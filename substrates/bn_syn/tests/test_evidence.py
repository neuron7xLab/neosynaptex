import json
import os
import subprocess
import sys
from pathlib import Path


def test_failure_path_emits_evidence_bundle(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    text = Path("examples/basic_task.yaml").read_text(encoding="utf-8")
    text = text.replace("must_include_objective: true", "must_include_objective: false")
    text = text.replace("forbidden_terms:\n    - \"TODO\"", "forbidden_terms:\n    - \"Objective\"")
    cfg.write_text(text, encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.run([sys.executable, "-m", "aoc.cli", "run", "--config", str(cfg)], cwd=tmp_path, check=False, env=env)

    out = tmp_path / "aoc_output"
    verdict = json.loads((out / "termination_verdict.json").read_text())
    assert verdict["status"] in {"FAIL", "MAX_ITER", "INCONCLUSIVE"}
    assert (out / "evidence_bundle" / "termination_verdict.json").exists()
    assert (out / "evidence_bundle" / "final_artifact.md").exists()


def test_zeropoint_immutability(tmp_path: Path) -> None:
    from aoc.contracts import load_task_contract
    from aoc.zeropoint import ZeroPointManager
    import yaml

    payload = yaml.safe_load(Path("examples/basic_task.yaml").read_text(encoding="utf-8"))
    contract = load_task_contract(payload)
    run_dir = tmp_path / "zp"
    run_dir.mkdir()
    manager = ZeroPointManager(run_dir)
    first = manager.materialize(contract)
    second = manager.materialize(contract)
    assert first["hash"] == second["hash"]
