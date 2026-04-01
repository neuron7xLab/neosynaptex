from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mlsdm.config import perf_slo
from mlsdm.policy.loader import PolicyLoadError, canonicalize_policy_data, load_policy_bundle


def test_policy_hash_is_stable() -> None:
    bundle_a = load_policy_bundle()
    bundle_b = load_policy_bundle()

    assert bundle_a.policy_hash == bundle_b.policy_hash


def test_policy_canonicalization_orders_named_lists() -> None:
    data = {
        "items": [
            {"name": "zeta", "value": 1},
            {"name": "alpha", "value": 2},
        ]
    }

    canonical = canonicalize_policy_data(data)
    assert [item["name"] for item in canonical["items"]] == ["alpha", "zeta"]


def test_policy_canonicalization_normalizes_units() -> None:
    data = {"latency_ms": "120ms", "error_percent": "1%"}

    canonical = canonicalize_policy_data(data)
    assert canonical["latency_ms"] == 120.0
    assert canonical["error_percent"] == 1.0


def test_policy_schema_validation_rejects_missing_fields(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir()

    (policy_dir / "security-baseline.yaml").write_text("version: '1.0'\n", encoding="utf-8")
    (policy_dir / "observability-slo.yaml").write_text("version: '1.0'\n", encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        load_policy_bundle(policy_dir)


def test_policy_schema_rejects_unknown_fields(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir()

    security_policy = yaml.safe_load(Path("policy/security-baseline.yaml").read_text(encoding="utf-8"))
    observability_policy = yaml.safe_load(Path("policy/observability-slo.yaml").read_text(encoding="utf-8"))

    security_policy["unexpected_field"] = "nope"
    observability_policy["unexpected_field"] = "nope"

    (policy_dir / "security-baseline.yaml").write_text(
        yaml.safe_dump(security_policy), encoding="utf-8"
    )
    (policy_dir / "observability-slo.yaml").write_text(
        yaml.safe_dump(observability_policy), encoding="utf-8"
    )

    with pytest.raises(PolicyLoadError):
        load_policy_bundle(policy_dir)


def test_runtime_slo_parity_with_policy() -> None:
    bundle = load_policy_bundle()
    runtime_defaults = bundle.observability_slo.thresholds.runtime_defaults

    assert perf_slo.DEFAULT_LATENCY_SLO.api_p95_ms == runtime_defaults.latency.api_p95_ms
    assert perf_slo.DEFAULT_ERROR_RATE_SLO.max_error_rate_percent == runtime_defaults.error_rate.max_error_rate_percent
    assert perf_slo.DEFAULT_THROUGHPUT_SLO.min_rps == runtime_defaults.throughput.min_rps
    assert runtime_defaults.load_multipliers.moderate_load_slo == perf_slo.MODERATE_LOAD_SLO_MULTIPLIER


def test_rego_rules_reference_policy_data() -> None:
    rego_path = Path("policies/ci/workflows.rego")
    content = rego_path.read_text(encoding="utf-8")

    assert "data.policy.security_baseline.controls.ci_workflow_policy" in content
    assert "write-all" not in content
    assert "@main" not in content
    assert "@master" not in content
