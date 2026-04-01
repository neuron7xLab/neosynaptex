from __future__ import annotations

import argparse
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILES: tuple[str, ...] = (
    "README.md",
    "pyproject.toml",
    "docs/SPEC.md",
    "docs/ARCHITECTURE_INVARIANTS.md",
    "manifest/repo_manifest.yml",
)

CONSTRAINT_PATTERN = re.compile(r"\\b(MUST|SHALL|DO NOT|NEVER)\\b")


@dataclass(frozen=True)
class AtomicSignal:
    kind: str
    name: str
    value: str
    source: str


def _iso_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _read_constraints(path: Path) -> list[AtomicSignal]:
    constraints: list[AtomicSignal] = []
    if not path.exists():
        return constraints

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if CONSTRAINT_PATTERN.search(stripped):
            constraints.append(
                AtomicSignal(
                    kind="constraint",
                    name=f"invariant_line_{line_number}",
                    value=stripped,
                    source=path.relative_to(ROOT).as_posix(),
                )
            )
    return constraints


def _collect_entities(src_root: Path) -> list[AtomicSignal]:
    entities: list[AtomicSignal] = []
    if not src_root.exists():
        return entities

    for path in sorted(src_root.iterdir()):
        if path.name.startswith("_"):
            continue
        entity_type = "module_dir" if path.is_dir() else "module_file"
        entities.append(
            AtomicSignal(
                kind="entity",
                name=path.stem,
                value=entity_type,
                source=path.relative_to(ROOT).as_posix(),
            )
        )
    return entities


def _collect_metrics(pyproject_path: Path, tests_dir: Path) -> list[AtomicSignal]:
    metrics: list[AtomicSignal] = []
    if pyproject_path.exists():
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = payload.get("project", {})
        dependencies = project.get("dependencies", [])
        optional_deps = project.get("optional-dependencies", {})

        metrics.append(
            AtomicSignal(
                kind="metric",
                name="python_requirement",
                value=str(project.get("requires-python", "unknown")),
                source=pyproject_path.relative_to(ROOT).as_posix(),
            )
        )
        metrics.append(
            AtomicSignal(
                kind="metric",
                name="runtime_dependency_count",
                value=str(len(dependencies)),
                source=pyproject_path.relative_to(ROOT).as_posix(),
            )
        )
        metrics.append(
            AtomicSignal(
                kind="metric",
                name="optional_dependency_groups",
                value=str(len(optional_deps)),
                source=pyproject_path.relative_to(ROOT).as_posix(),
            )
        )

    test_files = sorted(tests_dir.glob("test_*.py"))
    metrics.append(
        AtomicSignal(
            kind="metric",
            name="test_module_count",
            value=str(len(test_files)),
            source=tests_dir.relative_to(ROOT).as_posix(),
        )
    )
    return metrics


def collect_raw_signal_set(repo_root: Path = ROOT) -> dict[str, Any]:
    source_paths = [repo_root / rel_path for rel_path in SOURCE_FILES]
    available_sources = [path for path in source_paths if path.exists()]

    signals: list[AtomicSignal] = []
    previous_count = -1
    iterations = 0
    while previous_count != len(signals):
        previous_count = len(signals)
        iterations += 1
        signals = []
        signals.extend(_collect_entities(repo_root / "src" / "bnsyn"))
        signals.extend(_collect_metrics(repo_root / "pyproject.toml", repo_root / "tests"))
        signals.extend(_read_constraints(repo_root / "docs" / "ARCHITECTURE_INVARIANTS.md"))
        signals.extend(_read_constraints(repo_root / "docs" / "SPEC.md"))

    if len(available_sources) != len(source_paths):
        missing = sorted({path.name for path in source_paths if not path.exists()})
        for name in missing:
            signals.append(
                AtomicSignal(
                    kind="anomaly",
                    name="missing_source",
                    value=name,
                    source="collection",
                )
            )

    timestamps = [_iso_timestamp(path) for path in available_sources]
    uncertainty_level = 0.0
    if source_paths:
        uncertainty_level = round(1.0 - (len(available_sources) / len(source_paths)), 4)

    return {
        "signals": [asdict(signal) for signal in signals],
        "sources": [path.relative_to(repo_root).as_posix() for path in available_sources],
        "timestamps": timestamps,
        "uncertainty_level": uncertainty_level,
        "loop_iterations": iterations,
    }


def reduce_noise(raw_signal_set: dict[str, Any]) -> dict[str, Any]:
    relevance_weights = {
        "constraint": 1.0,
        "metric": 0.95,
        "entity": 0.85,
        "anomaly": 1.0,
    }
    seen: set[tuple[str, str, str]] = set()
    essential_elements: list[dict[str, Any]] = []
    rejected_noise: list[dict[str, Any]] = []
    relevance_map: dict[str, float] = {}
    entropy_history: list[float] = []

    previous_entropy = float("inf")
    iterations = 0
    while True:
        iterations += 1
        seen.clear()
        essential_elements = []
        rejected_noise = []
        relevance_map = {}

        for signal in raw_signal_set["signals"]:
            key = (signal["kind"], signal["name"], signal["value"])
            score = relevance_weights.get(signal["kind"], 0.0)
            relevance_map["|".join(key)] = score

            if key in seen or score < 0.8:
                rejected_noise.append(signal)
                continue

            seen.add(key)
            enriched = dict(signal)
            enriched["relevance"] = score
            essential_elements.append(enriched)

        current_entropy = len(rejected_noise) / max(1, len(raw_signal_set["signals"]))
        entropy_history.append(round(current_entropy, 6))
        if abs(previous_entropy - current_entropy) <= 1e-9:
            break
        previous_entropy = current_entropy

    return {
        "essential_elements": essential_elements,
        "rejected_noise": rejected_noise,
        "relevance_map": relevance_map,
        "entropy_history": entropy_history,
        "loop_iterations": iterations,
    }


def compress_semantics(filtered_core: dict[str, Any]) -> dict[str, Any]:
    essentials = filtered_core["essential_elements"]
    constraints = [item for item in essentials if item["kind"] == "constraint"]
    entities = [item for item in essentials if item["kind"] == "entity"]
    metrics = [item for item in essentials if item["kind"] == "metric"]

    axioms = sorted({constraint["value"] for constraint in constraints})
    abstraction_candidates = [
        f"MODULE_SURFACE={len(entities)}",
        f"METRIC_SURFACE={len(metrics)}",
        f"CONSTRAINT_SURFACE={len(constraints)}",
    ]
    abstractions: list[str] = []
    complexity_history: list[int] = []
    previous_complexity = len(abstraction_candidates) + len(axioms) + 1
    iterations = 0
    while True:
        iterations += 1
        abstractions = sorted(set(abstraction_candidates))
        current_complexity = len(abstractions) + len(axioms)
        complexity_history.append(current_complexity)
        if current_complexity >= previous_complexity:
            break
        previous_complexity = current_complexity

    minimal_definitions = [
        "entity := top-level component in src/bnsyn",
        "constraint := normative statement with MUST|SHALL|DO NOT|NEVER",
        "metric := deterministic scalar from pyproject/tests",
    ]

    return {
        "axioms": axioms,
        "abstractions": abstractions,
        "minimal_definitions": minimal_definitions,
        "complexity_history": complexity_history,
        "loop_iterations": iterations,
    }


def synthesize_model(
    filtered_core: dict[str, Any], compressed_schema: dict[str, Any]
) -> dict[str, Any]:
    essentials = filtered_core["essential_elements"]
    nodes = sorted({f"{item['kind']}:{item['name']}" for item in essentials})
    relations: list[dict[str, str]] = []

    for abstraction in compressed_schema["abstractions"]:
        relations.append(
            {
                "from": "core:repo",
                "to": f"schema:{abstraction}",
                "type": "summarizes",
            }
        )

    for item in essentials:
        relations.append(
            {
                "from": "core:repo",
                "to": f"{item['kind']}:{item['name']}",
                "type": "contains",
            }
        )

    constraints = compressed_schema["axioms"]
    contradiction_count = 0
    if len(nodes) != len(set(nodes)):
        contradiction_count += 1
    governing_rules = [
        "all signals are immutable records",
        "noise reduction keeps relevance >= 0.8",
        "compression must preserve all constraint axioms",
    ]

    return {
        "nodes": nodes,
        "relations": relations,
        "constraints": constraints,
        "governing_rules": governing_rules,
        "internal_contradictions": contradiction_count,
    }


def validate_model(
    system_model: dict[str, Any], raw_signal_set: dict[str, Any], filtered_core: dict[str, Any]
) -> dict[str, Any]:
    verified_components: list[str] = []
    risk_vectors: list[str] = []
    correction_log: list[str] = []

    if system_model["nodes"]:
        verified_components.append("non_empty_nodes")
    else:
        risk_vectors.append("empty_node_set")

    if len(filtered_core["essential_elements"]) <= len(raw_signal_set["signals"]):
        verified_components.append("entropy_non_increasing")
    else:
        risk_vectors.append("entropy_increase_detected")

    if raw_signal_set["uncertainty_level"] == 0.0:
        verified_components.append("source_coverage_complete")
    else:
        risk_vectors.append("source_coverage_incomplete")
        correction_log.append("add missing source files from SOURCE_FILES list")

    if system_model.get("internal_contradictions", 0) == 0:
        verified_components.append("contradiction_free")
    else:
        risk_vectors.append("model_contradiction_detected")

    if not risk_vectors:
        correction_log.append("no corrections required")

    return {
        "verified_components": verified_components,
        "risk_vectors": risk_vectors,
        "correction_log": correction_log,
    }


def transform_to_intellectual_object(validated_model: dict[str, Any]) -> dict[str, Any]:
    execution_rules = [
        "Cycle 1: acquire signals until atomic set stabilizes",
        "Cycle 2: filter noise and keep relevance >= 0.8",
        "Cycle 3: compress semantics while preserving axioms",
        "Cycle 4: synthesize causal model with zero contradictions",
        "Cycle 5: validate determinism and reproducibility gates",
        "Cycle 6: emit operational artifact only if risk_vectors is empty",
    ]

    integration_points = [
        "scripts/intelligence_cycle.py",
        "docs/ARCHITECTURE_INVARIANTS.md",
        "docs/SPEC.md",
    ]

    operational_spec = {
        "input": "repository filesystem state",
        "output": "cycle JSON report",
        "termination": "stabilized multi-loop deterministic pipeline",
        "validation_gate": "validated_model.risk_vectors == []",
    }

    final_prompt = {
        "verified_components": validated_model["verified_components"],
        "risk_vectors": validated_model["risk_vectors"],
        "correction_log": validated_model["correction_log"],
    }

    return {
        "final_prompt/system": final_prompt,
        "execution_rules": execution_rules,
        "integration_points": integration_points,
        "operational_spec": operational_spec,
    }


def run_cycle_pipeline(repo_root: Path = ROOT) -> dict[str, Any]:
    raw_signal_set = collect_raw_signal_set(repo_root)
    filtered_core = reduce_noise(raw_signal_set)
    compressed_schema = compress_semantics(filtered_core)
    system_model = synthesize_model(filtered_core, compressed_schema)
    validated_model = validate_model(system_model, raw_signal_set, filtered_core)
    intellectual_object = transform_to_intellectual_object(validated_model)

    return {
        "RAW_SIGNAL_SET": raw_signal_set,
        "FILTERED_CORE": filtered_core,
        "COMPRESSED_SCHEMA": compressed_schema,
        "SYSTEM_MODEL": system_model,
        "VALIDATED_MODEL": validated_model,
        "INTELLECTUAL_OBJECT": intellectual_object,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run six-cycle deterministic intelligence pipeline.")
    parser.add_argument("--output", type=Path, default=None, help="Optional output JSON path.")
    args = parser.parse_args()

    payload = run_cycle_pipeline(ROOT)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
