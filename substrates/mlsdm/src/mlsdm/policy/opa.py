from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from mlsdm.policy.loader import PolicyBundle, load_policy_bundle


@dataclass(frozen=True)
class OPAExportMapping:
    yaml_path: str
    export_path: str
    rego_path: str
    description: str


OPA_EXPORT_MAPPINGS: tuple[OPAExportMapping, ...] = (
    OPAExportMapping(
        yaml_path="policy/security-baseline.yaml:controls.ci_workflow_policy.prohibited_permissions",
        export_path="policy.security_baseline.controls.ci_workflow_policy.prohibited_permissions",
        rego_path="data.policy.security_baseline.controls.ci_workflow_policy.prohibited_permissions",
        description="Prohibited GitHub Actions permission scopes",
    ),
    OPAExportMapping(
        yaml_path="policy/security-baseline.yaml:controls.ci_workflow_policy.first_party_action_owners",
        export_path="policy.security_baseline.controls.ci_workflow_policy.first_party_action_owners",
        rego_path="data.policy.security_baseline.controls.ci_workflow_policy.first_party_action_owners",
        description="First-party action owners allowlist",
    ),
    OPAExportMapping(
        yaml_path="policy/security-baseline.yaml:controls.ci_workflow_policy.prohibited_mutable_refs",
        export_path="policy.security_baseline.controls.ci_workflow_policy.prohibited_mutable_refs",
        rego_path="data.policy.security_baseline.controls.ci_workflow_policy.prohibited_mutable_refs",
        description="Disallowed mutable action references",
    ),
)


class PolicyExportError(RuntimeError):
    """Raised when policy data export fails validation."""


def build_opa_policy_data(policy_dir: Path) -> tuple[PolicyBundle, dict[str, Any]]:
    bundle = load_policy_bundle(policy_dir)
    data = {
        "policy": bundle.canonical_data,
        "policy_hash": bundle.policy_hash,
    }
    return bundle, data


def _path_exists(data: dict[str, Any], path: str) -> bool:
    current: Any = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return False
    return True


def validate_opa_export_contract(data: dict[str, Any]) -> None:
    missing = [mapping for mapping in OPA_EXPORT_MAPPINGS if not _path_exists(data, mapping.export_path)]
    if not missing:
        return

    lines = [
        "OPA export contract validation failed.",
        "Missing required keys:",
    ]
    for mapping in missing:
        lines.append(
            f"- {mapping.export_path} (rego: {mapping.rego_path}; yaml: {mapping.yaml_path})"
        )
    lines.append("Remediation: update the policy YAML and exporter mapping to restore the contract.")
    raise PolicyExportError("\n".join(lines))


def export_opa_policy_data(policy_dir: Path, output_path: Path) -> dict[str, Any]:
    _, data = build_opa_policy_data(policy_dir)
    validate_opa_export_contract(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def run_conftest(
    fixtures: list[str],
    data_path: Path,
    policy_dir: Path,
    repo_root: Path,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "conftest",
        "test",
        *fixtures,
        "-p",
        str(policy_dir),
        "-d",
        str(data_path),
        "--all-namespaces",
        "--fail-on-warn=false",
    ]
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)


def ensure_conftest_available() -> None:
    result = subprocess.run(
        ["conftest", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PolicyExportError(
            "Conftest binary not available. Remediation: install conftest and retry."
        )


__all__ = [
    "OPAExportMapping",
    "OPA_EXPORT_MAPPINGS",
    "PolicyExportError",
    "build_opa_policy_data",
    "export_opa_policy_data",
    "run_conftest",
    "ensure_conftest_available",
    "validate_opa_export_contract",
]
