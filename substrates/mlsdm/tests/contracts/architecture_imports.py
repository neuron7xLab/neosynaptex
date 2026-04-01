"""Utilities for parsing MLSDM import dependencies."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mlsdm.config.architecture_manifest import (
    ARCHITECTURE_MANIFEST,
    PACKAGE_ROOT,
    ArchitectureModule,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


@dataclass(frozen=True)
class ImportViolation:
    """Disallowed dependency between architecture modules."""

    source_module: str
    source_file: Path
    target_module: str
    import_statement: str
    reason: str = "disallowed dependency"


@dataclass(frozen=True)
class ImportTarget:
    """Resolved import target for a module reference."""

    module_parts: tuple[str, ...]
    raw: str


def iter_python_files(root: Path) -> Iterator[Path]:
    """Yield python files under the given root."""
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def module_parts_for_path(path: Path) -> tuple[str, ...]:
    """Return module parts for a python file path."""
    relative = path.relative_to(PACKAGE_ROOT)
    parts = list(relative.parts)
    if not parts:
        return ()
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return tuple(part for part in parts if part)


def package_parts_for_path(path: Path) -> tuple[str, ...]:
    """Return package parts for resolving relative imports."""
    module_parts = module_parts_for_path(path)
    if path.name == "__init__.py":
        return module_parts
    return module_parts[:-1]


def normalize_absolute_import(module_name: str | None) -> tuple[str, ...]:
    """Normalize absolute imports under the mlsdm namespace."""
    if not module_name:
        return ()
    if module_name == "mlsdm":
        return ()
    if module_name.startswith("mlsdm."):
        return tuple(module_name.split(".")[1:])
    return ()


def resolve_relative_base(package_parts: tuple[str, ...], level: int) -> tuple[str, ...]:
    """Resolve the base module parts for a relative import."""
    if level <= 0:
        return package_parts
    cutoff = max(len(package_parts) - (level - 1), 0)
    return package_parts[:cutoff]


def iter_import_targets(path: Path) -> Iterator[ImportTarget]:
    """Iterate over import targets within a python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package_parts = package_parts_for_path(path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_parts = normalize_absolute_import(alias.name)
                if module_parts:
                    yield ImportTarget(module_parts=module_parts, raw=f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base_parts = resolve_relative_base(package_parts, node.level)
                if node.module:
                    module_parts = base_parts + tuple(node.module.split("."))
                    yield ImportTarget(
                        module_parts=module_parts,
                        raw=f"from {'.' * node.level}{node.module} import ...",
                    )
                else:
                    for alias in node.names:
                        module_parts = base_parts + tuple(alias.name.split("."))
                        yield ImportTarget(
                            module_parts=module_parts,
                            raw=f"from {'.' * node.level} import {alias.name}",
                        )
            else:
                module_parts = normalize_absolute_import(node.module)
                if module_parts:
                    yield ImportTarget(
                        module_parts=module_parts,
                        raw=f"from {node.module} import ...",
                    )


def build_manifest_index(
    manifest: Iterable[ArchitectureModule] = ARCHITECTURE_MANIFEST,
) -> dict[str, ArchitectureModule]:
    """Index manifest modules by name."""
    return {module.name: module for module in manifest}


def find_architecture_import_violations(
    manifest: Iterable[ArchitectureModule] = ARCHITECTURE_MANIFEST,
    package_root: Path = PACKAGE_ROOT,
) -> list[ImportViolation]:
    """Find import dependencies that violate manifest boundaries."""
    manifest_index = build_manifest_index(manifest)
    violations: list[ImportViolation] = []

    for path in iter_python_files(package_root):
        module_parts = module_parts_for_path(path)
        if not module_parts:
            continue
        source_module = module_parts[0]
        if source_module not in manifest_index:
            continue
        allowed = set(manifest_index[source_module].allowed_dependencies)

        for target in iter_import_targets(path):
            if not target.module_parts:
                continue
            target_module = target.module_parts[0]
            if target_module == source_module:
                continue
            if target_module not in manifest_index:
                violations.append(
                    ImportViolation(
                        source_module=source_module,
                        source_file=path,
                        target_module=target_module,
                        import_statement=target.raw,
                        reason="unknown target module",
                    )
                )
                continue
            if target_module not in allowed:
                violations.append(
                    ImportViolation(
                        source_module=source_module,
                        source_file=path,
                        target_module=target_module,
                        import_statement=target.raw,
                        reason="disallowed dependency",
                    )
                )

    return violations
