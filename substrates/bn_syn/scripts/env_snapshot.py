from __future__ import annotations

import argparse
import json
import locale
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _run_version(command: str) -> str:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.stdout.strip()


def build_snapshot() -> dict[str, Any]:
    tools = {
        "python": "python --version",
        "pip": "python -m pip --version",
        "ruff": "ruff --version",
        "mypy": "mypy --version",
        "pytest": "pytest --version",
        "git": "git --version",
    }
    versions = {name: _run_version(cmd) for name, cmd in sorted(tools.items())}
    return {
        "cwd": str(ROOT),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "locale": locale.getlocale(),
        "tools": versions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic environment snapshot")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot()
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
