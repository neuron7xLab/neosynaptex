from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mlsdm.policy.loader import PolicyLoadError, load_policy_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "policy"


def _load_policy(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_policy_dir(tmp_path: Path, security_data: dict, observability_data: dict) -> None:
    (tmp_path / "security-baseline.yaml").write_text(
        yaml.safe_dump(security_data, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "observability-slo.yaml").write_text(
        yaml.safe_dump(observability_data, sort_keys=False),
        encoding="utf-8",
    )


def test_canonical_hash_snapshot() -> None:
    bundle = load_policy_bundle(POLICY_DIR)
    assert bundle.policy_hash == "7c7ae4090ddf49f2a3817b5b0435f2ee9a110884d88f80ae84ce508002b0360c"


def test_policy_missing_required_field_fails(tmp_path: Path) -> None:
    security = _load_policy(POLICY_DIR / "security-baseline.yaml")
    observability = _load_policy(POLICY_DIR / "observability-slo.yaml")
    security.pop("policy_name")

    _write_policy_dir(tmp_path, security, observability)

    with pytest.raises(PolicyLoadError) as exc:
        load_policy_bundle(tmp_path)
    message = str(exc.value)
    assert "security-baseline.yaml" in message
    assert "policy_name" in message
    assert "Remediation" in message


def test_policy_unknown_field_fails(tmp_path: Path) -> None:
    security = _load_policy(POLICY_DIR / "security-baseline.yaml")
    observability = _load_policy(POLICY_DIR / "observability-slo.yaml")
    observability["controls"]["unknown_control"] = True

    _write_policy_dir(tmp_path, security, observability)

    with pytest.raises(PolicyLoadError) as exc:
        load_policy_bundle(tmp_path)
    message = str(exc.value)
    assert "observability-slo.yaml" in message
    assert "unknown_control" in message


def test_policy_wrong_type_fails(tmp_path: Path) -> None:
    security = _load_policy(POLICY_DIR / "security-baseline.yaml")
    observability = _load_policy(POLICY_DIR / "observability-slo.yaml")
    security["thresholds"]["coverage_gate_minimum_percent"] = "high"

    _write_policy_dir(tmp_path, security, observability)

    with pytest.raises(PolicyLoadError) as exc:
        load_policy_bundle(tmp_path)
    assert "coverage_gate_minimum_percent" in str(exc.value)


def test_policy_bad_unit_fails(tmp_path: Path) -> None:
    security = _load_policy(POLICY_DIR / "security-baseline.yaml")
    observability = _load_policy(POLICY_DIR / "observability-slo.yaml")
    observability["thresholds"]["slos"]["api_defaults"]["p95_latency_ms"] = "120 parsecs"

    _write_policy_dir(tmp_path, security, observability)

    with pytest.raises(PolicyLoadError) as exc:
        load_policy_bundle(tmp_path)
    assert "p95_latency_ms" in str(exc.value)
