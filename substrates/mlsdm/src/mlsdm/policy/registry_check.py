from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mlsdm.policy.catalog import (
    CATALOG_FILENAME,
    PolicyCatalogError,
    build_policy_catalog,
    collect_policy_assets,
    load_policy_catalog,
    verify_policy_catalog,
    write_policy_catalog,
)
from mlsdm.policy.loader import PolicyLoadError, load_policy_bundle
from mlsdm.policy.registry import (
    REGISTRY_FILENAME,
    PolicyRegistryError,
    build_policy_registry,
    load_policy_registry,
    verify_policy_registry,
    write_policy_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def run_policy_registry_check(
    *,
    policy_dir: Path,
    registry_path: Path | None,
    catalog_path: Path | None,
    policies_dir: Path | None,
) -> int:
    resolved_policy_dir = _resolve_path(policy_dir)
    resolved_registry_path = _resolve_path(registry_path) if registry_path else None
    registry_file = resolved_registry_path or (resolved_policy_dir / REGISTRY_FILENAME)
    resolved_catalog_path = _resolve_path(catalog_path) if catalog_path else None
    catalog_file = resolved_catalog_path or (resolved_policy_dir / CATALOG_FILENAME)
    resolved_policies_dir = _resolve_path(policies_dir) if policies_dir else None
    policies_root = resolved_policies_dir or (resolved_policy_dir.parent / "policies")

    try:
        bundle = load_policy_bundle(resolved_policy_dir, enforce_registry=False)
        registry = load_policy_registry(registry_file)
        verify_policy_registry(
            policy_hash=bundle.policy_hash,
            policy_contract_version=bundle.security_baseline.policy_contract_version,
            registry=registry,
        )
        catalog = load_policy_catalog(catalog_file)
        catalog_errors = verify_policy_catalog(
            catalog=catalog,
            repo_root=resolved_policy_dir.parent,
            policy_dir=resolved_policy_dir,
            policies_dir=policies_root,
        )
        if catalog.policy_contract_version != bundle.security_baseline.policy_contract_version:
            catalog_errors = catalog_errors + (
                "policy contract version mismatch between policy bundle and catalog",
            )
        if catalog.policy_bundle_hash != bundle.policy_hash:
            catalog_errors = catalog_errors + (
                "policy bundle hash mismatch between policy bundle and catalog",
            )
        if catalog_errors:
            raise PolicyCatalogError("; ".join(catalog_errors))
    except (PolicyLoadError, PolicyRegistryError) as exc:
        print(f"ERROR: {exc}")
        return 1
    except PolicyCatalogError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("✓ Policy registry hash matches canonical policy bundle.")
    print("✓ Policy catalog matches policy sources.")
    return 0


def run_policy_registry_export(
    *,
    policy_dir: Path,
    registry_path: Path | None,
    catalog_path: Path | None,
    policies_dir: Path | None,
) -> int:
    resolved_policy_dir = _resolve_path(policy_dir)
    resolved_registry_path = _resolve_path(registry_path) if registry_path else None
    registry_file = resolved_registry_path or (resolved_policy_dir / REGISTRY_FILENAME)
    resolved_catalog_path = _resolve_path(catalog_path) if catalog_path else None
    catalog_file = resolved_catalog_path or (resolved_policy_dir / CATALOG_FILENAME)
    resolved_policies_dir = _resolve_path(policies_dir) if policies_dir else None
    policies_root = resolved_policies_dir or (resolved_policy_dir.parent / "policies")

    try:
        bundle = load_policy_bundle(resolved_policy_dir, enforce_registry=False)
        registry = build_policy_registry(
            policy_hash=bundle.policy_hash,
            policy_contract_version=bundle.security_baseline.policy_contract_version,
        )
        write_policy_registry(registry_file, registry)
        assets = collect_policy_assets(
            repo_root=resolved_policy_dir.parent,
            policy_dir=resolved_policy_dir,
            policies_dir=policies_root,
        )
        catalog = build_policy_catalog(
            policy_contract_version=bundle.security_baseline.policy_contract_version,
            policy_bundle_hash=bundle.policy_hash,
            assets=assets,
        )
        write_policy_catalog(catalog_file, catalog)
    except (PolicyLoadError, PolicyRegistryError) as exc:
        print(f"ERROR: {exc}")
        return 1
    except PolicyCatalogError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"✓ Wrote policy registry to {registry_file}")
    print(f"✓ Wrote policy catalog to {catalog_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or export the policy registry")
    parser.add_argument(
        "--policy-dir",
        type=Path,
        default=Path("policy"),
        help="Path to policy directory (default: policy/)",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help="Path to policy registry JSON (default: policy/registry.json)",
    )
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=None,
        help="Path to policy catalog JSON (default: policy/catalog.json)",
    )
    parser.add_argument(
        "--policies-dir",
        type=Path,
        default=None,
        help="Path to rego policy directory (default: policies/)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export a registry file instead of verifying",
    )
    args = parser.parse_args()

    if args.export:
        return run_policy_registry_export(
            policy_dir=args.policy_dir,
            registry_path=args.registry_path,
            catalog_path=args.catalog_path,
            policies_dir=args.policies_dir,
        )

    return run_policy_registry_check(
        policy_dir=args.policy_dir,
        registry_path=args.registry_path,
        catalog_path=args.catalog_path,
        policies_dir=args.policies_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
