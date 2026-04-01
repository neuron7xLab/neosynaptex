from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SSOT_PATH = ROOT / "manifest/repo_manifest.yml"
SCHEMA_PATH = ROOT / "manifest/repo_manifest.schema.json"
COMPUTED_PATH = ROOT / "manifest/repo_manifest.computed.json"
RENDERED_PATH = ROOT / ".github/REPO_MANIFEST.md"
SCAN_SCOPE_ENTRIES: tuple[str, ...] = (
    ".github/workflows",
    "scripts",
    "docs",
    "Makefile",
    "README.md",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_workflow_yaml(path: Path) -> dict[str, Any]:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _workflow_files(workflows_dir: Path) -> list[Path]:
    return sorted(
        [*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")],
        key=lambda path: path.name,
    )


def _repo_fingerprint() -> str:
    digest = hashlib.sha256()
    tracked = [
        ROOT / "manifest/repo_manifest.yml",
        ROOT / ".github/PR_GATES.yml",
        ROOT / "quality/coverage_gate.json",
        ROOT / "quality/mutation_baseline.json",
    ]
    for path in tracked:
        rel = path.relative_to(ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    for path in _workflow_files(ROOT / ".github/workflows"):
        rel = path.relative_to(ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _count_ci_manifest_references() -> int:
    token = "ci_manifest.json"
    total = 0
    for raw_entry in SCAN_SCOPE_ENTRIES:
        entry = ROOT / raw_entry
        files: list[Path]
        if entry.is_dir():
            files = sorted(path for path in entry.rglob("*") if path.is_file())
        elif entry.is_file():
            files = [entry]
        else:
            files = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            total += sum(1 for line in text.splitlines() if token in line)
    return total


def _workflow_metrics(workflows_dir: Path) -> tuple[int, int, int]:
    files = _workflow_files(workflows_dir)
    reusable_count = 0
    workflow_call_count = 0
    for path in files:
        data = _load_workflow_yaml(path)
        trigger = data.get("on", {}) if isinstance(data, dict) else {}
        trigger_keys: set[str]
        if isinstance(trigger, dict):
            trigger_keys = {str(key) for key in trigger.keys()}
        elif isinstance(trigger, list):
            trigger_keys = {str(item) for item in trigger}
        elif isinstance(trigger, str):
            trigger_keys = {trigger}
        else:
            trigger_keys = set()
        if path.name.startswith("_reusable_"):
            reusable_count += 1
        if "workflow_call" in trigger_keys:
            workflow_call_count += 1
    return len(files), reusable_count, workflow_call_count


def build_computed() -> dict[str, Any]:
    ssot = _load_yaml(SSOT_PATH)
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator(schema).validate(ssot)

    pr_gates_path = ROOT / ssot["required_pr_gates"]["source"]
    pr_gates_bytes = pr_gates_path.read_bytes()
    pr_gates = _load_yaml(pr_gates_path)
    required_pr_gate_total = len(pr_gates.get("required_pr_gates", []))

    workflow_total, reusable_total, workflow_call_total = _workflow_metrics(
        ROOT / ".github/workflows"
    )

    coverage = _load_json(ROOT / "quality/coverage_gate.json")
    mutation = _load_json(ROOT / "quality/mutation_baseline.json")

    ci_manifest_reference_count = _count_ci_manifest_references()

    return {
        "manifest_version": ssot["manifest_version"],
        "generated_at": "deterministic",
        "repo_ref": _repo_fingerprint(),
        "required_pr_gates": {
            "source": ssot["required_pr_gates"]["source"],
            "sha256": hashlib.sha256(pr_gates_bytes).hexdigest(),
            "required_pr_gate_total": required_pr_gate_total,
        },
        "metrics": {
            "workflow_total": workflow_total,
            "workflow_reusable_total": reusable_total,
            "workflow_call_total": workflow_call_total,
            "required_pr_gate_total": required_pr_gate_total,
            "coverage_minimum_percent": coverage["minimum_percent"],
            "coverage_baseline_percent": coverage["baseline_percent"],
            "mutation_baseline_score": mutation["baseline_score"],
            "mutation_total_mutants": mutation["metrics"]["total_mutants"],
            "ci_manifest_exists": (ROOT / "ci_manifest.json").exists(),
            "ci_manifest_reference_count": ci_manifest_reference_count,
            "ci_manifest_reference_scope": list(SCAN_SCOPE_ENTRIES),
        },
        "invariants": ssot["invariants"],
        "policies": ssot["policies"],
        "evidence_rules": ssot["evidence_rules"],
    }


def write_outputs() -> None:
    from tools.manifest.render import render_markdown

    computed = build_computed()
    computed_json = json.dumps(computed, indent=2, sort_keys=True) + "\n"
    markdown = render_markdown(computed)
    COMPUTED_PATH.write_text(computed_json, encoding="utf-8")
    RENDERED_PATH.write_text(markdown, encoding="utf-8")

    computed_sha = hashlib.sha256(computed_json.encode("utf-8")).hexdigest()
    rendered_sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    metrics = computed["metrics"]
    print(
        "manifest.generate "
        f"computed_sha256={computed_sha} "
        f"rendered_sha256={rendered_sha} "
        f"workflow_total={metrics['workflow_total']} "
        f"workflow_call_total={metrics['workflow_call_total']} "
        f"ci_manifest_reference_count={metrics['ci_manifest_reference_count']}"
    )


if __name__ == "__main__":
    write_outputs()
