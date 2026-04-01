"""Dev doctor."""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "evidence" / "wave_1"
OUT.mkdir(parents=True, exist_ok=True)
MODULES = [
    "mycelium_fractal_net",
    "mycelium_fractal_net.core.simulate",
    "mycelium_fractal_net.core.extract",
    "mycelium_fractal_net.core.detect",
    "mycelium_fractal_net.core.forecast",
    "mycelium_fractal_net.core.compare",
    "mycelium_fractal_net.core.report",
    "mycelium_fractal_net.integration.api_server",
]


def _module_status(name: str) -> dict[str, object]:
    try:
        mod = importlib.import_module(name)
        return {"ok": True, "module": name, "file": getattr(mod, "__file__", None)}
    except Exception as exc:
        return {"ok": False, "module": name, "error": f"{type(exc).__name__}: {exc}"}


def _lock_hash() -> str | None:
    lock = ROOT / "uv.lock"
    if not lock.exists():
        return None
    return sha256(lock.read_bytes()).hexdigest()


def _run(cmd: list[str]) -> dict[str, object]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> int:
    uv_path = shutil.which("uv")
    venv = ROOT / ".venv"
    payload = {
        "python": sys.version,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "venv_exists": venv.exists(),
        "venv_python": str(venv / "bin" / "python"),
        "uv": uv_path,
        "uv_lock_exists": (ROOT / "uv.lock").exists(),
        "uv_lock_hash": _lock_hash(),
        "entrypoints": {name: shutil.which(name) for name in ["mfn", "mfn-api", "mfn-validate"]},
        "imports": [_module_status(name) for name in MODULES],
        "commands": {
            "python_import": _run(
                [
                    sys.executable,
                    "-c",
                    "import mycelium_fractal_net; print(mycelium_fractal_net.__version__)",
                ]
            ),
            "mfn_help": (
                _run(["mfn", "--help"])
                if shutil.which("mfn")
                else {"returncode": 127, "stderr": "mfn not found"}
            ),
        },
        "env": {
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
        },
    }
    payload["install_modes"] = {
        "pip_editable": (venv / "pyvenv.cfg").exists() and bool(payload["entrypoints"].get("mfn")),
        "uv_managed": bool(uv_path) and payload["uv_lock_exists"],
    }
    (OUT / "dependency_matrix.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    ok = all(item["ok"] for item in payload["imports"]) and any(payload["install_modes"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
