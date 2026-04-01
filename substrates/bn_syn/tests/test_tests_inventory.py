from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_tests_inventory_matches_repository_state() -> None:
    inventory = json.loads((REPO_ROOT / "tests_inventory.json").read_text(encoding="utf-8"))

    assert inventory["test_count"] == len(inventory["tests"])
    pytest_entries = [entry for entry in inventory["tests"] if entry.get("category") == "pytest"]
    assert inventory["coverage_surface"]["pytest"] == len(pytest_entries)
    paths = [entry["path"] for entry in inventory["tests"]]
    assert len(paths) == len(set(paths))
    assert "tests/test_avalanche_analysis.py" in paths
    assert "tests/test_phase_space_analysis.py" in paths


def test_acceptance_map_contains_no_escape_contract() -> None:
    payload = yaml.safe_load((REPO_ROOT / "acceptance_map.yaml").read_text(encoding="utf-8"))
    no_escape = payload["no_escape_acceptance"]

    assert no_escape["merge_safety_budget_minutes"] == 12
    assert no_escape["determinism_runs"] == 3
    assert no_escape["decision_mode"] == "fail_closed"

    required_checks = no_escape["required_checks"]
    assert required_checks == ["ci-pr-atomic", "workflow-integrity", "determinism", "contracts"]

    forbidden = set(no_escape["forbidden"])
    assert "unpinned_actions" in forbidden
    assert "flaky_tests" in forbidden
    assert "unknown_evidence" in forbidden
