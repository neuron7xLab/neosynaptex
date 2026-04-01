from __future__ import annotations

import json
from pathlib import Path


def test_demo_review_contract_is_complete_and_ordered() -> None:
    payload = json.loads(Path("docs/demo_review_contract.json").read_text(encoding="utf-8"))

    tasks = payload["tasks"]
    assert len(tasks) == 10

    expected_groups = [
        "correctness",
        "correctness",
        "correctness",
        "correctness",
        "stability",
        "stability",
        "integration",
        "integration",
        "merge_readiness",
        "merge_readiness",
    ]
    assert [task["priority_group"] for task in tasks] == expected_groups
    assert [task["rank"] for task in tasks] == list(range(1, 11))
    assert all(task["status"] == "closed" for task in tasks)
    assert payload["system_model"]["canonical_command"] == "bnsyn run --profile canonical --plot --export-proof"


def test_product_summary_schema_is_synced_between_repo_and_runtime_resources() -> None:
    repo_schema = Path("schemas/product-summary.schema.json").read_text(encoding="utf-8")
    runtime_schema = Path("src/bnsyn/resources/schemas/product-summary.schema.json").read_text(
        encoding="utf-8"
    )
    assert repo_schema == runtime_schema
