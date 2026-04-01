from __future__ import annotations

from pathlib import Path

from mlsdm.policy.catalog import (
    PolicyAsset,
    build_policy_catalog,
    collect_policy_assets,
    verify_policy_catalog,
)
from mlsdm.policy.loader import load_policy_bundle


def test_policy_catalog_matches_repo_sources() -> None:
    repo_root = Path(".").resolve()
    policy_dir = repo_root / "policy"
    policies_dir = repo_root / "policies"
    bundle = load_policy_bundle(policy_dir, enforce_registry=False)

    assets = collect_policy_assets(
        repo_root=repo_root,
        policy_dir=policy_dir,
        policies_dir=policies_dir,
    )
    catalog = build_policy_catalog(
        policy_contract_version=bundle.security_baseline.policy_contract_version,
        policy_bundle_hash=bundle.policy_hash,
        assets=assets,
    )

    errors = verify_policy_catalog(
        catalog=catalog,
        repo_root=repo_root,
        policy_dir=policy_dir,
        policies_dir=policies_dir,
    )

    assert errors == ()


def test_policy_catalog_detects_mismatch() -> None:
    repo_root = Path(".").resolve()
    policy_dir = repo_root / "policy"
    policies_dir = repo_root / "policies"
    bundle = load_policy_bundle(policy_dir, enforce_registry=False)
    assets = collect_policy_assets(
        repo_root=repo_root,
        policy_dir=policy_dir,
        policies_dir=policies_dir,
    )

    tampered_assets = list(assets)
    if tampered_assets:
        tampered = tampered_assets[0]
        tampered_assets[0] = PolicyAsset(path=tampered.path, sha256="deadbeef")

    catalog = build_policy_catalog(
        policy_contract_version=bundle.security_baseline.policy_contract_version,
        policy_bundle_hash=bundle.policy_hash,
        assets=tampered_assets,
    )

    errors = verify_policy_catalog(
        catalog=catalog,
        repo_root=repo_root,
        policy_dir=policy_dir,
        policies_dir=policies_dir,
    )

    assert any("policy catalog hash mismatch" in error for error in errors)
