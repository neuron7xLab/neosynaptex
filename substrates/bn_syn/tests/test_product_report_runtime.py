from __future__ import annotations

from pathlib import Path

import pytest

from bnsyn.proof.contracts import manifest_self_hash
import jsonschema

from bnsyn.viz.product_report import (
    _render_index_html,
    _validate_product_summary,
    validate_index_html_contents,
    validate_product_summary_payload,
)


def test_manifest_self_hash_does_not_mutate_input() -> None:
    manifest = {
        "schema_version": "1.0.0",
        "artifacts": {
            "run_manifest.json": "x" * 64,
            "summary_metrics.json": "1" * 64,
        },
    }
    original = {
        "schema_version": manifest["schema_version"],
        "artifacts": dict(manifest["artifacts"]),
    }

    digest = manifest_self_hash(manifest)

    assert isinstance(digest, str)
    assert len(digest) == 64
    assert manifest == original


def test_validate_product_summary_fails_closed_on_bad_type() -> None:
    payload = {
        "status": "PASS",
        "profile": "canonical",
        "seed": "123",
        "artifact_dir": "artifacts/canonical_run",
        "primary_visual": "emergence_plot.png",
        "proof_verdict": "PASS",
        "criticality_verdict": True,
        "avalanche_verdict": True,
        "generated_at": "1970-01-01T00:00:00Z",
        "package_version": "0.2.0",
        "bundle_contract_version": "canonical-export-proof",
        "primary_visual_sha256": "a" * 64,
        "primary_visual_data_artifact": "population_rate_trace.npy",
        "primary_visual_data_sha256": "b" * 64,
    }

    with pytest.raises(ValueError, match="invalid type"):
        _validate_product_summary(payload)  # type: ignore[arg-type]


def test_validate_product_summary_payload_fails_closed_on_schema_violation() -> None:
    payload = {
        "status": "PASS",
        "profile": "canonical",
        "seed": 123,
        "artifact_dir": "artifacts/canonical_run",
        "primary_visual": "emergence_plot.png",
        "proof_verdict": "PASS",
        "criticality_verdict": True,
        "avalanche_verdict": True,
        "generated_at": "1970-01-01T00:00:00Z",
        "package_version": "0.2.0",
        "bundle_contract_version": "canonical-export-proof",
        "primary_visual_sha256": "bad-digest",
        "primary_visual_data_artifact": "population_rate_trace.npy",
        "primary_visual_data_sha256": "b" * 64,
    }

    with pytest.raises(jsonschema.ValidationError):
        validate_product_summary_payload(payload)


def test_validate_index_html_contents_reports_missing_required_markers() -> None:
    missing = validate_index_html_contents("<html><body>product_summary.json</body></html>")
    assert "proof_report.json" in missing
    assert "bnsyn validate-bundle" in missing
    assert "Critical pull request completion tasks" in missing


def test_render_index_html_is_pretty_printed_and_contains_navigation() -> None:
    html = _render_index_html(
        manifest={
            "artifacts": {
                "summary_metrics.json": "0" * 64,
                "criticality_report.json": "1" * 64,
                "avalanche_report.json": "2" * 64,
                "phase_space_report.json": "3" * 64,
                "proof_report.json": "4" * 64,
                "run_manifest.json": "5" * 64,
                "emergence_plot.png": "6" * 64,
            }
        },
        summary={"rate_mean_hz": 1.0},
        product_summary={
            "status": "PASS",
            "profile": "canonical",
            "seed": 123,
            "artifact_dir": Path("artifacts/canonical_run").as_posix(),
            "primary_visual": "emergence_plot.png",
            "proof_verdict": "PASS",
            "criticality_verdict": True,
            "avalanche_verdict": True,
            "generated_at": "1970-01-01T00:00:00Z",
            "package_version": "0.2.0",
            "bundle_contract_version": "canonical-export-proof",
            "primary_visual_sha256": "6" * 64,
            "primary_visual_data_artifact": "population_rate_trace.npy",
            "primary_visual_data_sha256": "7" * 64,
        },
    )

    assert "\n  <head>" in html
    assert "\n  <body>" in html
    assert "Open this report first" in html
    assert "Artifact guide" in html
    assert "Canonical execution cycle" in html
    assert "Merge and local-run readiness" in html
    assert "Demo readiness dashboard" in html
    assert "Operator commands" in html
    assert "Critical pull request completion tasks" in html
    assert "Product validation" in html
    assert "Proof-only validation" in html
    assert "make quickstart-smoke" in html
    assert "bnsyn proof-validate-bundle" in html
    assert "bnsyn validate-bundle" in html
    assert "proof_report.json shows PASS" in html
    assert "Minimal FAQ" in html
    assert "product_summary.json" in html
    assert "proof_report.json" in html
    assert "Cryptographic evidence link" in html
    assert "population_rate_trace.npy" in html
    assert '<a href="index.html">index.html</a> — Primary report:' in html
    assert '<a href="proof_report.json">proof_report.json</a> — Proof verdict:' in html
