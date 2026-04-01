from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestNode:
    path: str
    category: str
    entropy_signals: list[str]


CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("property", "property"),
    ("chaos", "chaos"),
    ("determin", "determinism"),
    ("mutation", "mutation"),
    ("math", "math_physics"),
    ("physics", "math_physics"),
    ("workflow", "workflow_integrity"),
)


def classify(path: Path) -> str:
    stem = path.stem.lower()
    text = str(path).lower()
    for token, category in CATEGORY_RULES:
        if token in stem or token in text:
            return category
    return "pytest"


def detect_entropy_signals(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    signals: list[str] = []
    if "random" in text and "seed" not in text:
        signals.append("rng_without_explicit_seed")
    if "time." in text or "sleep(" in text:
        signals.append("time_dependency")
    if "tmp_path" in text or "Path(" in text:
        signals.append("filesystem_io")
    if "subprocess" in text:
        signals.append("subprocess_dependency")
    return sorted(set(signals))


def build_inventory(repo_root: Path) -> dict[str, object]:
    test_files = sorted(repo_root.glob("tests/test_*.py"))
    nodes = [
        TestNode(
            path=str(path.relative_to(repo_root)),
            category=classify(path),
            entropy_signals=detect_entropy_signals(path),
        )
        for path in test_files
    ]

    by_category: dict[str, int] = {}
    flaky_indicators = 0
    for node in nodes:
        by_category[node.category] = by_category.get(node.category, 0) + 1
        flaky_indicators += int(bool(node.entropy_signals))

    reusable_workflows = sorted(
        p.name
        for p in (repo_root / ".github" / "workflows").glob("_reusable_*.yml")
    )

    return {
        "generated_by": "python -m scripts.generate_tests_inventory",
        "test_count": len(nodes),
        "coverage_surface": by_category,
        "flaky_indicator_count": flaky_indicators,
        "reusable_workflow_jobs": reusable_workflows,
        "tests": [asdict(node) for node in nodes],
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    inventory = build_inventory(repo_root)
    out_path = repo_root / "tests_inventory.json"
    out_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
