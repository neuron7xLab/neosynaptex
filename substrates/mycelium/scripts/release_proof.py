"""Release proof."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "evidence"
RELEASE = ROOT / "artifacts" / "release"
RELEASE.mkdir(parents=True, exist_ok=True)
(RELEASE / "benchmark_pack").mkdir(parents=True, exist_ok=True)
(RELEASE / "validation_pack").mkdir(parents=True, exist_ok=True)
(RELEASE / "example_run").mkdir(parents=True, exist_ok=True)
(RELEASE / "example_scenarios").mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], name: str, wave: str) -> Path:
    wave_dir = EVIDENCE / wave
    wave_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = wave_dir / f"{name}.log"
    body = f"$ {' '.join(cmd)}\n\nSTDOUT\n{proc.stdout}\n\nSTDERR\n{proc.stderr}\nRETURN_CODE={proc.returncode}\n"
    log.write_text(body, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"{name} failed: see {log}")
    return log


def _copytree(src: Path, dst: Path) -> None:
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def main() -> int:
    _run([sys.executable, "scripts/dev_doctor.py"], "doctor", "wave_1")
    _run([sys.executable, "scripts/verify_matrix.py"], "verify_matrix", "wave_1")
    _run([sys.executable, "scripts/export_openapi.py"], "export_openapi", "wave_4")
    _run(
        [sys.executable, "scripts/check_openapi_contract.py"],
        "check_openapi_contract",
        "wave_4",
    )
    _run(
        [sys.executable, "validation/run_validation_experiments.py"],
        "validation_cycle",
        "wave_7",
    )
    _run([sys.executable, "benchmarks/benchmark_core.py"], "benchmark_core", "wave_7")
    _run(
        [sys.executable, "benchmarks/benchmark_scalability.py"],
        "benchmark_scalability",
        "wave_7",
    )
    _run(
        [sys.executable, "benchmarks/benchmark_quality.py"],
        "benchmark_quality",
        "wave_7",
    )
    _run([sys.executable, "scripts/release_prep.py"], "release_prep", "wave_6")
    _run([sys.executable, "scripts/showcase_run.py"], "showcase_run", "wave_8")
    _run([sys.executable, "scripts/generate_sbom.py"], "generate_sbom", "wave_8")

    for name in [
        "benchmark_core.json",
        "benchmark_core.csv",
        "benchmark_scalability.json",
        "benchmark_scalability.csv",
        "benchmark_quality.json",
        "benchmark_quality.csv",
    ]:
        src = ROOT / "benchmarks" / "results" / name
        if src.exists():
            shutil.copy2(src, RELEASE / "benchmark_pack" / name)

    val_summary = (
        ROOT / "artifacts" / "evidence" / "wave_7" / "validation" / "validation_summary.json"
    )
    if val_summary.exists():
        shutil.copy2(val_summary, RELEASE / "validation_pack" / "validation_summary.json")

    _copytree(ROOT / "artifacts" / "release" / "scenarios", RELEASE / "example_scenarios")
    example_runs = ROOT / "artifacts" / "runs"
    if example_runs.exists():
        latest = sorted(example_runs.iterdir())[-1]
        _copytree(latest, RELEASE / "example_run")

    checklist = {
        "status": "READY_TO_RELEASE",
        "evidence_root": "artifacts/evidence/",
        "release_root": "artifacts/release/",
        "completed_waves": ["wave_1", "wave_4", "wave_6", "wave_7", "wave_8"],
        "blocked_waves": [],
    }
    (RELEASE / "final_release_checklist.json").write_text(
        json.dumps(checklist, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Final evidence index", ""]
    for path in sorted(EVIDENCE.rglob("*")):
        if path.is_file():
            lines.append(f"- `{path.relative_to(ROOT)}`")
    (RELEASE / "final_evidence_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RELEASE / "final_status.txt").write_text("READY_TO_RELEASE\n", encoding="utf-8")
    print(json.dumps(checklist, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
