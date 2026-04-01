from __future__ import annotations

import re
from pathlib import Path


def test_all_external_workflow_actions_are_sha_pinned() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workflow_paths = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    sha_pin_pattern = re.compile(r"@[0-9a-f]{40}$")

    violations: list[str] = []
    for path in workflow_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            uses_value = stripped.split("uses:", 1)[1].strip().strip("\"'")
            if uses_value.startswith("./"):
                continue
            if not sha_pin_pattern.search(uses_value):
                violations.append(f"{path.name}: {uses_value}")

    assert violations == []
