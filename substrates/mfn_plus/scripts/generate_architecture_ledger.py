#!/usr/bin/env python3
"""Generate Architecture Ledger — snapshot of dependencies, exports, contracts.

Produces: artifacts/architecture_ledger.json

This snapshot enables PR-level architectural drift detection.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "mycelium_fractal_net"


def _collect_imports(file_path: Path) -> list[str]:
    """Extract all import targets from a Python file."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return sorted(set(imports))


def _collect_exports(file_path: Path) -> list[str]:
    """Extract __all__ from a Python file, or public names."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    # Fallback: collect public class/function names
    names = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
    return sorted(names)


def _module_name(file_path: Path) -> str:
    rel = file_path.relative_to(SRC_ROOT.parent)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _classify_symbol(name: str, module: str) -> str:
    """Classify as stable/frozen/deprecated based on known surfaces."""
    frozen = {"crypto", "federated", "stdp", "turing", "ws_"}
    deprecated = {"crypto"}
    mod_lower = module.lower()
    for f in frozen:
        if f in mod_lower:
            return "frozen"
    for d in deprecated:
        if d in mod_lower:
            return "deprecated"
    return "stable"


def main() -> None:
    modules = []

    for py_file in sorted(SRC_ROOT.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        mod_name = _module_name(py_file)
        imports = _collect_imports(py_file)
        exports = _collect_exports(py_file)

        # Separate internal vs external imports
        internal = [i for i in imports if i.startswith("mycelium_fractal_net")]
        external = [i for i in imports if not i.startswith("mycelium_fractal_net") and "." not in i]

        modules.append(
            {
                "module": mod_name,
                "file": str(py_file.relative_to(SRC_ROOT.parents[1])),
                "imports_internal": internal,
                "imports_external": sorted(set(external)),
                "exports": exports,
                "symbols": [{"name": e, "status": _classify_symbol(e, mod_name)} for e in exports],
            }
        )

    # Build dependency graph (directed edges)
    dep_graph = {}
    for mod in modules:
        deps = [i.replace("mycelium_fractal_net.", "") for i in mod["imports_internal"]]
        dep_graph[mod["module"].replace("mycelium_fractal_net.", "")] = deps

    # Public API manifest from __init__.py
    init_file = SRC_ROOT / "__init__.py"
    public_api = _collect_exports(init_file) if init_file.exists() else []

    # Stable / frozen / deprecated counts
    all_symbols = [s for m in modules for s in m["symbols"]]
    stable = sum(1 for s in all_symbols if s["status"] == "stable")
    frozen = sum(1 for s in all_symbols if s["status"] == "frozen")
    deprecated = sum(1 for s in all_symbols if s["status"] == "deprecated")

    ledger = {
        "schema_version": "mfn-architecture-ledger-v1",
        "engine_version": "0.1.0",
        "total_modules": len(modules),
        "total_symbols": len(all_symbols),
        "stable_symbols": stable,
        "frozen_symbols": frozen,
        "deprecated_symbols": deprecated,
        "public_api": public_api,
        "dependency_graph": dep_graph,
        "modules": modules,
    }

    out_path = Path("artifacts/architecture_ledger.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(ledger, f, indent=2)

    print(f"Architecture Ledger: {out_path}")
    print(f"  Modules: {len(modules)}")
    print(f"  Symbols: stable={stable} frozen={frozen} deprecated={deprecated}")
    print(f"  Public API: {len(public_api)} exports")


if __name__ == "__main__":
    main()
