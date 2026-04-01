from __future__ import annotations

from pathlib import Path

import pytest

from mlsdm.config.policy_drift import PolicyDriftError, check_policy_drift
from mlsdm.policy.loader import load_policy_bundle
from mlsdm.policy.registry import build_policy_registry, write_policy_registry


def _copy_policy_files(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ("security-baseline.yaml", "observability-slo.yaml"):
        (target_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")


def test_policy_drift_check_passes_for_repo_policy() -> None:
    status = check_policy_drift(enforce=False)
    assert status.drift_detected is False
    assert status.registry_signature_valid is True
    assert status.catalog_signature_valid is True
    assert status.catalog_hash is not None


def test_policy_drift_check_raises_on_mismatch(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    _copy_policy_files(Path("policy"), policy_dir)

    bundle = load_policy_bundle(policy_dir, enforce_registry=False)
    registry = build_policy_registry(
        policy_hash="deadbeef" * 8,
        policy_contract_version=bundle.security_baseline.policy_contract_version,
    )
    write_policy_registry(policy_dir / "registry.json", registry)

    status = check_policy_drift(policy_dir=policy_dir, enforce=False)
    assert status.drift_detected is True

    with pytest.raises(PolicyDriftError):
        check_policy_drift(policy_dir=policy_dir, enforce=True)


def test_policy_drift_detects_missing_registry(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    _copy_policy_files(Path("policy"), policy_dir)

    status = check_policy_drift(policy_dir=policy_dir, enforce=False)
    assert status.drift_detected is True
    assert status.registry_signature_valid is False

    with pytest.raises(PolicyDriftError):
        check_policy_drift(policy_dir=policy_dir, enforce=True)


def test_policy_drift_detects_missing_policy_files(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)

    status = check_policy_drift(policy_dir=policy_dir, enforce=False)
    assert status.drift_detected is True

    with pytest.raises(PolicyDriftError):
        check_policy_drift(policy_dir=policy_dir, enforce=True)
