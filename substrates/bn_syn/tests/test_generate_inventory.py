from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.generate_inventory import build_inventory, render_inventory


def _tracked_files_under(path_prefix: str) -> list[str]:
    out = subprocess.check_output(["git", "ls-files", f"{path_prefix}/**"], text=True)
    return [line for line in out.splitlines() if line]


def test_inventory_json_matches_repository_state() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = ["src", "tests", "docs", ".github"]

    counts = {path: len(_tracked_files_under(path)) for path in paths}
    workflows = sorted(path.name for path in (root / ".github" / "workflows").glob("*.yml"))
    detected_tools = [
        name
        for name in ["pyproject.toml", "requirements-lock.txt", "docker-compose.yml", "Makefile"]
        if (root / name).exists()
    ]

    expected = {
        "_generated_by": "python tools/generate_inventory.py",
        "paths": paths,
        "counts": counts,
        "workflows": workflows,
        "detected_tools": detected_tools,
    }

    inventory = json.loads((root / "INVENTORY.json").read_text(encoding="utf-8"))
    assert inventory == expected


def test_build_inventory_render_matches_file() -> None:
    root = Path(__file__).resolve().parents[1]
    rendered = render_inventory(build_inventory(root))
    assert (root / "INVENTORY.json").read_text(encoding="utf-8") == rendered
