from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: str, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Install wheel in isolated venv and run smoke checks")
    parser.add_argument("--log", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--dist-hashes", required=True)
    args = parser.parse_args()

    log_path = Path(args.log)
    report_path = Path(args.report)
    hashes_path = Path(args.dist_hashes)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    hashes_path.parent.mkdir(parents=True, exist_ok=True)

    dist_files = sorted((ROOT / "dist").glob("*"))
    dist_payload = {
        "dist": [
            {
                "path": file.name,
                "sha256": _hash_file(file),
            }
            for file in dist_files
            if file.is_file()
        ]
    }
    hashes_path.write_text(json.dumps(dist_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="bnsyn-install-smoke-") as tmp:
        venv = Path(tmp) / "venv"
        py = venv / "bin" / "python"
        pip = venv / "bin" / "pip"
        bnsyn = venv / "bin" / "bnsyn"
        cmd = " && ".join(
            [
                f"python -m venv {venv}",
                f"{py} -m pip install --upgrade pip",
                f"{pip} install dist/*.whl",
                f"{py} -c \"import bnsyn; print(bnsyn.__version__)\"",
                f"{bnsyn} smoke",
            ]
        )
        rc, output = _run(cmd, ROOT)

    log_path.write_text(output, encoding="utf-8")
    report: dict[str, Any] = {
        "verdict": "PASS" if rc == 0 else "FAIL",
        "dist_hashes": dist_payload,
        "log": log_path.as_posix(),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
