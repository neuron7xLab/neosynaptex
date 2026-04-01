from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / ".github" / "ci_policy.yml"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "de_tf" / "policy"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ci policy must be a mapping")
    return data


def _normalize(policy: dict[str, Any]) -> dict[str, Any]:
    tools = policy.get("tools", {})
    for gate in ("ruff", "mypy", "pytest", "build"):
        cmd = str(tools.get(gate, {}).get("cmd", ""))
        if not cmd.startswith("python -m "):
            raise ValueError(f"tool '{gate}' must use deterministic python -m invocation")

    return {
        "actions": policy["actions"],
        "determinism": policy["determinism"],
        "install": policy["install"],
        "pip": policy["pip"],
        "protocol": policy["protocol"],
        "python": policy["python"],
        "required_checks": policy["required_checks"],
        "security": policy["security"],
        "tiers": policy["tiers"],
        "tools": policy["tools"],
        "normalized": {
            "p0_gates": list(policy["tiers"]["P0"]),
            "required_checks_manifest": policy["required_checks"]["manifest"],
            "tool_commands": {name: cfg["cmd"] for name, cfg in sorted(tools.items()) if "cmd" in cfg},
        },
    }




def _install_repro(policy: dict[str, Any]) -> None:
    install = policy.get("install", {})
    strategy = install.get("strategy")
    if strategy != "extras":
        return
    extras = install.get("extras", [])
    extras_suffix = f"[{','.join(extras)}]" if extras else ""
    cmd = [sys.executable, "-m", "pip", "install", "-e", f".{extras_suffix}"]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)

def main() -> int:
    policy = _normalize(_load_yaml(POLICY_PATH))
    _install_repro(policy)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ci_policy_resolved.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path = REPO_ROOT / policy["required_checks"]["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (OUTPUT_DIR / "required_checks_resolved.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
