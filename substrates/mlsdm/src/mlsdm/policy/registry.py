from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

if TYPE_CHECKING:
    from pathlib import Path

REGISTRY_FILENAME = "registry.json"
REGISTRY_VERSION = "1"
SIGNATURE_ALGORITHM = "sha256"


class PolicyRegistryError(RuntimeError):
    """Raised when policy registry loading or validation fails."""


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PolicyRegistry(StrictBaseModel):
    registry_version: str
    policy_contract_version: str
    policy_hash: str
    signature_algorithm: str
    signature: str

    @field_validator("registry_version")
    @classmethod
    def _validate_registry_version(cls, value: str) -> str:
        if value != REGISTRY_VERSION:
            raise ValueError(f"registry_version must be {REGISTRY_VERSION}")
        return value

    @field_validator("signature_algorithm")
    @classmethod
    def _validate_signature_algorithm(cls, value: str) -> str:
        if value != SIGNATURE_ALGORITHM:
            raise ValueError(f"signature_algorithm must be {SIGNATURE_ALGORITHM}")
        return value


def _serialize_payload(payload: dict[str, str]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _payload_from_registry(registry: PolicyRegistry | dict[str, Any]) -> dict[str, str]:
    data = registry if isinstance(registry, dict) else registry.model_dump(mode="python")
    return {
        "registry_version": str(data["registry_version"]),
        "policy_contract_version": str(data["policy_contract_version"]),
        "policy_hash": str(data["policy_hash"]),
    }


def compute_registry_signature(payload: dict[str, str]) -> str:
    canonical = _serialize_payload(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_policy_registry(*, policy_hash: str, policy_contract_version: str) -> PolicyRegistry:
    payload = {
        "registry_version": REGISTRY_VERSION,
        "policy_contract_version": policy_contract_version,
        "policy_hash": policy_hash,
    }
    signature = compute_registry_signature(payload)
    return PolicyRegistry(
        registry_version=REGISTRY_VERSION,
        policy_contract_version=policy_contract_version,
        policy_hash=policy_hash,
        signature_algorithm=SIGNATURE_ALGORITHM,
        signature=signature,
    )


def load_policy_registry(path: Path) -> PolicyRegistry:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PolicyRegistryError(
            f"Policy registry not found: {path}. Remediation: run policy registry export."
        ) from exc
    except json.JSONDecodeError as exc:
        raise PolicyRegistryError(
            f"Policy registry JSON is invalid: {path}. Remediation: regenerate the registry."
        ) from exc

    if not isinstance(raw, dict):
        raise PolicyRegistryError(
            f"Policy registry must be a JSON object: {path}. Remediation: regenerate the registry."
        )

    try:
        registry = PolicyRegistry.model_validate(raw)
    except ValidationError as exc:
        raise PolicyRegistryError(
            f"Policy registry schema invalid: {path}. Remediation: regenerate the registry."
        ) from exc

    payload = _payload_from_registry(registry)
    expected_signature = compute_registry_signature(payload)
    if registry.signature != expected_signature:
        raise PolicyRegistryError(
            f"Policy registry signature mismatch: {path}. Remediation: regenerate the registry."
        )

    return registry


def verify_policy_registry(
    *,
    policy_hash: str,
    policy_contract_version: str,
    registry: PolicyRegistry,
) -> None:
    errors: list[str] = []
    if registry.policy_contract_version != policy_contract_version:
        errors.append(
            "policy_contract_version mismatch between policy bundle and registry "
            f"({policy_contract_version} != {registry.policy_contract_version})"
        )
    if registry.policy_hash != policy_hash:
        errors.append(
            "policy hash mismatch between policy bundle and registry "
            f"({policy_hash} != {registry.policy_hash})"
        )

    if errors:
        detail = "; ".join(errors)
        raise PolicyRegistryError(
            f"Policy registry verification failed: {detail}. "
            "Remediation: update policy YAML and regenerate the registry."
        )


def write_policy_registry(path: Path, registry: PolicyRegistry) -> None:
    payload = registry.model_dump(mode="python")
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
