from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from mlsdm.policy.catalog import (
    CATALOG_FILENAME,
    PolicyCatalogError,
    load_policy_catalog,
    verify_policy_catalog,
)
from mlsdm.policy.exceptions import PolicyDriftError
from mlsdm.policy.loader import DEFAULT_POLICY_DIR, PolicyLoadError, load_policy_bundle
from mlsdm.policy.registry import (
    REGISTRY_FILENAME,
    PolicyRegistryError,
    load_policy_registry,
    verify_policy_registry,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyDriftStatus:
    policy_name: str
    policy_hash: str
    policy_contract_version: str
    registry_hash: str | None
    registry_signature_valid: bool
    catalog_hash: str | None
    catalog_signature_valid: bool
    drift_detected: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PolicySnapshot:
    policy_name: str
    policy_hash: str
    policy_contract_version: str
    loaded_at: datetime


def _resolve_policy_dir(policy_dir: Path | None) -> Path:
    env_dir = os.getenv("MLSDM_POLICY_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (policy_dir or DEFAULT_POLICY_DIR).resolve()


def _resolve_registry_path(policy_dir: Path, registry_path: Path | None) -> Path:
    env_path = os.getenv("MLSDM_POLICY_REGISTRY_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (registry_path or (policy_dir / REGISTRY_FILENAME)).resolve()


def _resolve_catalog_path(policy_dir: Path, catalog_path: Path | None) -> Path:
    env_path = os.getenv("MLSDM_POLICY_CATALOG_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (catalog_path or (policy_dir / CATALOG_FILENAME)).resolve()


def _resolve_policies_dir(policy_dir: Path, policies_dir: Path | None) -> Path:
    env_path = os.getenv("MLSDM_POLICIES_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (policies_dir or (policy_dir.parent / "policies")).resolve()


def check_policy_drift(
    *,
    policy_dir: Path | None = None,
    registry_path: Path | None = None,
    catalog_path: Path | None = None,
    policies_dir: Path | None = None,
    enforce: bool = True,
) -> PolicyDriftStatus:
    resolved_policy_dir = _resolve_policy_dir(policy_dir)
    resolved_registry_path = _resolve_registry_path(resolved_policy_dir, registry_path)
    resolved_catalog_path = _resolve_catalog_path(resolved_policy_dir, catalog_path)
    resolved_policies_dir = _resolve_policies_dir(resolved_policy_dir, policies_dir)
    errors: list[str] = []
    registry_hash: str | None = None
    registry_signature_valid = False
    catalog_hash: str | None = None
    catalog_signature_valid = False

    try:
        bundle = load_policy_bundle(resolved_policy_dir, enforce_registry=False)
    except PolicyLoadError as exc:
        errors.append(str(exc))
        status = PolicyDriftStatus(
            policy_name="unknown",
            policy_hash="unavailable",
            policy_contract_version="unknown",
            registry_hash=None,
            registry_signature_valid=False,
            catalog_hash=None,
            catalog_signature_valid=False,
            drift_detected=True,
            errors=tuple(errors),
        )
        if enforce:
            raise PolicyDriftError(str(exc)) from exc
        return status

    policy_name = bundle.security_baseline.policy_name
    policy_hash = bundle.policy_hash
    policy_contract_version = bundle.security_baseline.policy_contract_version

    try:
        registry = load_policy_registry(resolved_registry_path)
        registry_hash = registry.policy_hash
        registry_signature_valid = True
        try:
            verify_policy_registry(
                policy_hash=policy_hash,
                policy_contract_version=policy_contract_version,
                registry=registry,
            )
        except PolicyRegistryError as exc:
            errors.append(str(exc))
    except PolicyRegistryError as exc:
        errors.append(str(exc))

    try:
        catalog = load_policy_catalog(resolved_catalog_path)
        catalog_hash = catalog.signature
        catalog_signature_valid = True
        if catalog.policy_contract_version != policy_contract_version:
            errors.append(
                "policy contract version mismatch between policy bundle and catalog "
                f"({policy_contract_version} != {catalog.policy_contract_version})"
            )
        if catalog.policy_bundle_hash != policy_hash:
            errors.append(
                "policy bundle hash mismatch between policy bundle and catalog "
                f"({policy_hash} != {catalog.policy_bundle_hash})"
            )
        catalog_errors = verify_policy_catalog(
            catalog=catalog,
            repo_root=resolved_policy_dir.parent,
            policy_dir=resolved_policy_dir,
            policies_dir=resolved_policies_dir,
        )
        errors.extend(catalog_errors)
    except PolicyCatalogError as exc:
        errors.append(str(exc))

    drift_detected = bool(errors)
    if drift_detected:
        logger.error("Policy drift detected: %s", "; ".join(errors))
        if enforce:
            raise PolicyDriftError("; ".join(errors))

    return PolicyDriftStatus(
        policy_name=policy_name,
        policy_hash=policy_hash,
        policy_contract_version=policy_contract_version,
        registry_hash=registry_hash,
        registry_signature_valid=registry_signature_valid,
        catalog_hash=catalog_hash,
        catalog_signature_valid=catalog_signature_valid,
        drift_detected=drift_detected,
        errors=tuple(errors),
    )


@lru_cache(maxsize=1)
def get_policy_snapshot(
    *,
    policy_dir: Path | None = None,
    registry_path: Path | None = None,
) -> PolicySnapshot:
    status = check_policy_drift(
        policy_dir=policy_dir,
        registry_path=registry_path,
        enforce=True,
    )
    return PolicySnapshot(
        policy_name=status.policy_name,
        policy_hash=status.policy_hash,
        policy_contract_version=status.policy_contract_version,
        loaded_at=datetime.now(timezone.utc),
    )
