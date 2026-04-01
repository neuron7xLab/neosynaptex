from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]

from bnsyn.proof.contracts import EXPORT_PROOF_ARTIFACTS, manifest_self_hash
from bnsyn.proof.evaluate import sha256_file
from bnsyn.paths import runtime_file
from bnsyn.viz.product_report import validate_index_html_contents, validate_product_summary_payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def validate_canonical_bundle(
    artifact_dir: str | Path, *, require_product_surface: bool = False
) -> dict[str, Any]:
    root = Path(artifact_dir)
    errors: list[str] = []
    manifest = _load_json(root / "run_manifest.json")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest artifacts must be object")

    for artifact in EXPORT_PROOF_ARTIFACTS:
        path = root / artifact
        if not path.is_file():
            errors.append(f"missing artifact: {artifact}")
            continue
        if artifact not in artifacts:
            errors.append(f"manifest missing hash entry: {artifact}")
            continue
        expected = artifacts[artifact]
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"manifest hash mismatch: {artifact}")
            continue

        if artifact == "run_manifest.json":
            if expected != manifest_self_hash(manifest):
                errors.append("manifest hash mismatch: run_manifest.json")
            continue

        if sha256_file(path) != expected:
            errors.append(f"manifest hash mismatch: {artifact}")

    schema_map = {
        "run_manifest.json": "run-manifest.schema.json",
        "proof_report.json": "proof-report.schema.json",
        "avalanche_report.json": "avalanche-report.schema.json",
        "avalanche_fit_report.json": "avalanche-fit-report.schema.json",
        "robustness_report.json": "robustness-report.schema.json",
        "envelope_report.json": "envelope-report.schema.json",
        "phase_space_report.json": "phase-space-report.schema.json",
    }
    for artifact, schema_name in schema_map.items():
        path = root / artifact
        if not path.exists():
            continue
        schema = _load_json(runtime_file(f"schemas/{schema_name}"))
        try:
            jsonschema.validate(instance=_load_json(path), schema=schema)
        except jsonschema.ValidationError as exc:
            errors.append(f"{artifact} schema violation at {exc.json_path}: {exc.message}")

    if require_product_surface:
        product_summary_path = root / "product_summary.json"
        index_path = root / "index.html"
        summary_metrics_path = root / "summary_metrics.json"
        proof_report_path = root / "proof_report.json"

        if not product_summary_path.is_file():
            errors.append("missing artifact: product_summary.json")
        if not index_path.is_file():
            errors.append("missing artifact: index.html")
        if not summary_metrics_path.is_file():
            errors.append("missing artifact: summary_metrics.json")
        if not proof_report_path.is_file():
            errors.append("missing artifact: proof_report.json")

        if product_summary_path.is_file():
            product_summary = _load_json(product_summary_path)
            summary_metrics: dict[str, Any] | None = None
            proof_report: dict[str, Any] | None = None

            try:
                validate_product_summary_payload(product_summary)
            except (ValueError, jsonschema.ValidationError) as exc:
                errors.append(f"product_summary invalid: {exc}")

            if summary_metrics_path.is_file():
                summary_metrics = _load_json(summary_metrics_path)
            if proof_report_path.is_file():
                proof_report = _load_json(proof_report_path)

            if product_summary.get("profile") != "canonical":
                errors.append("product_summary profile must be canonical")
            if product_summary.get("proof_verdict") != "PASS":
                errors.append("product_summary proof_verdict must be PASS")
            if product_summary.get("status") != product_summary.get("proof_verdict"):
                errors.append("product_summary status must match proof_verdict")
            if proof_report is not None and product_summary.get("proof_verdict") != proof_report.get("verdict"):
                errors.append("product_summary proof_verdict mismatch vs proof_report verdict")
            if product_summary.get("primary_visual") != "emergence_plot.png":
                errors.append("product_summary primary_visual must be emergence_plot.png")
            if product_summary.get("primary_visual_data_artifact") != "population_rate_trace.npy":
                errors.append("product_summary primary_visual_data_artifact must be population_rate_trace.npy")
            if product_summary.get("artifact_dir") != root.as_posix():
                errors.append("product_summary artifact_dir mismatch")
            if product_summary.get("bundle_contract_version") != manifest.get("bundle_contract"):
                errors.append("product_summary bundle_contract_version mismatch vs run_manifest")
            if product_summary.get("primary_visual_sha256") != artifacts.get("emergence_plot.png"):
                errors.append("product_summary primary_visual_sha256 mismatch vs run_manifest")
            if product_summary.get("primary_visual_data_sha256") != artifacts.get("population_rate_trace.npy"):
                errors.append("product_summary primary_visual_data_sha256 mismatch vs run_manifest")

            seed = product_summary.get("seed")
            if seed != manifest.get("seed"):
                errors.append("product_summary seed mismatch vs run_manifest")
            if summary_metrics is not None and seed != summary_metrics.get("seed"):
                errors.append("product_summary seed mismatch vs summary_metrics")

        if index_path.is_file():
            if index_path.stat().st_size == 0:
                errors.append("index.html is empty")
            else:
                index_html = index_path.read_text(encoding="utf-8")
                for snippet in validate_index_html_contents(index_html):
                    errors.append(f"index.html missing required content: {snippet}")

    return {"status": "PASS" if not errors else "FAIL", "errors": errors}
