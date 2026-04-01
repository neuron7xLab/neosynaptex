from __future__ import annotations

import hashlib
import json
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

if TYPE_CHECKING:
    from collections.abc import Iterable

CATALOG_FILENAME = "catalog.json"
CATALOG_VERSION = "1"
SIGNATURE_ALGORITHM = "sha256"


class PolicyCatalogError(RuntimeError):
    """Raised when policy catalog loading or validation fails."""


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyAsset(StrictBaseModel):
    path: str
    sha256: str


class PolicyCatalog(StrictBaseModel):
    catalog_version: str
    policy_contract_version: str
    policy_bundle_hash: str
    assets: list[PolicyAsset]
    signature_algorithm: str
    signature: str

    @field_validator("catalog_version")
    @classmethod
    def _validate_catalog_version(cls, value: str) -> str:
        if value != CATALOG_VERSION:
            raise ValueError(f"catalog_version must be {CATALOG_VERSION}")
        return value

    @field_validator("signature_algorithm")
    @classmethod
    def _validate_signature_algorithm(cls, value: str) -> str:
        if value != SIGNATURE_ALGORITHM:
            raise ValueError(f"signature_algorithm must be {SIGNATURE_ALGORITHM}")
        return value


def _serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _payload_from_catalog(catalog: PolicyCatalog | dict[str, Any]) -> dict[str, Any]:
    data = catalog if isinstance(catalog, dict) else catalog.model_dump(mode="python")
    return {
        "catalog_version": str(data["catalog_version"]),
        "policy_contract_version": str(data["policy_contract_version"]),
        "policy_bundle_hash": str(data["policy_bundle_hash"]),
        "assets": [
            {"path": asset["path"], "sha256": asset["sha256"]}
            for asset in data["assets"]
        ],
    }


def compute_catalog_signature(payload: dict[str, Any]) -> str:
    canonical = _serialize_payload(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_posix(path: Path, *, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def collect_policy_assets(
    *,
    repo_root: Path,
    policy_dir: Path,
    policies_dir: Path,
) -> list[PolicyAsset]:
    assets: list[PolicyAsset] = []

    def _gather_files(root: Path, exclude: set[Path]) -> Iterable[Path]:
        if not root.exists():
            return []
        return [
            path
            for path in root.rglob("*")
            if path.is_file() and path not in exclude
        ]

    exclude = {policy_dir / CATALOG_FILENAME}
    paths = list(_gather_files(policy_dir, exclude)) + list(
        _gather_files(policies_dir, exclude)
    )

    for path in sorted(paths, key=lambda p: _relative_posix(p, repo_root=repo_root)):
        assets.append(
            PolicyAsset(
                path=_relative_posix(path, repo_root=repo_root),
                sha256=_hash_file(path),
            )
        )

    return assets


def build_policy_catalog(
    *,
    policy_contract_version: str,
    policy_bundle_hash: str,
    assets: list[PolicyAsset],
) -> PolicyCatalog:
    payload = {
        "catalog_version": CATALOG_VERSION,
        "policy_contract_version": policy_contract_version,
        "policy_bundle_hash": policy_bundle_hash,
        "assets": [asset.model_dump(mode="python") for asset in assets],
    }
    signature = compute_catalog_signature(payload)
    return PolicyCatalog(
        catalog_version=CATALOG_VERSION,
        policy_contract_version=policy_contract_version,
        policy_bundle_hash=policy_bundle_hash,
        assets=assets,
        signature_algorithm=SIGNATURE_ALGORITHM,
        signature=signature,
    )


def load_policy_catalog(path: Path) -> PolicyCatalog:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyCatalogError(
            f"Policy catalog not found: {path}. Remediation: run policy catalog export."
        ) from exc
    except json.JSONDecodeError as exc:
        raise PolicyCatalogError(
            f"Policy catalog JSON is invalid: {path}. Remediation: regenerate the catalog."
        ) from exc

    if not isinstance(raw, dict):
        raise PolicyCatalogError(
            f"Policy catalog must be a JSON object: {path}. Remediation: regenerate the catalog."
        )

    try:
        catalog = PolicyCatalog.model_validate(raw)
    except ValidationError as exc:
        raise PolicyCatalogError(
            f"Policy catalog schema invalid: {path}. Remediation: regenerate the catalog."
        ) from exc

    payload = _payload_from_catalog(catalog)
    expected_signature = compute_catalog_signature(payload)
    if catalog.signature != expected_signature:
        raise PolicyCatalogError(
            f"Policy catalog signature mismatch: {path}. Remediation: regenerate the catalog."
        )

    return catalog


def verify_policy_catalog(
    *,
    catalog: PolicyCatalog,
    repo_root: Path,
    policy_dir: Path,
    policies_dir: Path,
) -> tuple[str, ...]:
    errors: list[str] = []
    expected_assets = collect_policy_assets(
        repo_root=repo_root,
        policy_dir=policy_dir,
        policies_dir=policies_dir,
    )
    expected_map = {asset.path: asset.sha256 for asset in expected_assets}
    catalog_map = {asset.path: asset.sha256 for asset in catalog.assets}

    missing = sorted(path for path in expected_map if path not in catalog_map)
    extra = sorted(path for path in catalog_map if path not in expected_map)
    mismatched = sorted(
        path
        for path in expected_map
        if path in catalog_map and expected_map[path] != catalog_map[path]
    )

    if missing:
        errors.append(f"policy catalog missing assets: {', '.join(missing)}")
    if extra:
        errors.append(f"policy catalog has unexpected assets: {', '.join(extra)}")
    if mismatched:
        errors.append(f"policy catalog hash mismatch: {', '.join(mismatched)}")

    return tuple(errors)


def write_policy_catalog(path: Path, catalog: PolicyCatalog) -> None:
    payload = catalog.model_dump(mode="python")
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
