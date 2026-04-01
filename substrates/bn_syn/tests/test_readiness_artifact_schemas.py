from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_readiness_report_matches_schema() -> None:
    schema = _load_schema(ROOT / "schemas" / "readiness_report.schema.json")
    payload = _load_json(ROOT / "readiness_report.json")

    jsonschema.validate(instance=payload, schema=schema)


def test_attack_paths_graph_matches_schema() -> None:
    schema = _load_schema(ROOT / "schemas" / "attack_paths_graph.schema.json")
    payload = _load_json(ROOT / "attack_paths_graph.json")

    jsonschema.validate(instance=payload, schema=schema)


def test_audit_reproducibility_matches_schema() -> None:
    schema = _load_schema(ROOT / "schemas" / "audit_reproducibility.schema.json")
    payload = _load_json(ROOT / "audit_reproducibility.json")

    jsonschema.validate(instance=payload, schema=schema)


def test_readiness_summary_word_budget_120() -> None:
    words = (ROOT / "readiness_summary.md").read_text(encoding="utf-8").split()
    assert len(words) <= 120
