from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _tracked_files_under(path_prefix: str) -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", f"{path_prefix}/**"], text=True)
    return [Path(line) for line in out.splitlines() if line]


def build_inventory(root: Path) -> dict[str, object]:
    paths = ["src", "tests", "docs", ".github"]
    counts = {path: len(_tracked_files_under(path)) for path in paths}
    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    workflow_names = [path.name for path in workflows]
    detected_tools = [
        name
        for name in ["pyproject.toml", "requirements-lock.txt", "docker-compose.yml", "Makefile"]
        if (root / name).exists()
    ]
    return {
        "_generated_by": "python tools/generate_inventory.py",
        "paths": paths,
        "counts": counts,
        "workflows": workflow_names,
        "detected_tools": detected_tools,
    }


def render_inventory(inventory: dict[str, object]) -> str:
    return json.dumps(inventory, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or check INVENTORY.json")
    parser.add_argument("--check", action="store_true", help="Fail if INVENTORY.json is out of date")
    args = parser.parse_args()

    root = Path(".")
    inventory_path = root / "INVENTORY.json"
    rendered = render_inventory(build_inventory(root))

    current = inventory_path.read_text(encoding="utf-8") if inventory_path.exists() else ""
    if args.check:
        if current != rendered:
            print("INVENTORY.json is out of date. Run: python tools/generate_inventory.py && git add INVENTORY.json")
            return 2
        print("OK: INVENTORY.json is up to date")
        return 0

    inventory_path.write_text(rendered, encoding="utf-8")
    print("UPDATED: INVENTORY.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
