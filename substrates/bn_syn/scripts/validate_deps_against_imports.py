"""Validate declared dependencies cover third-party imports."""

from __future__ import annotations

import ast
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from pathlib import Path

STDLIB = set(__import__("sys").stdlib_module_names)
PACKAGE_NAME_MAP = {
    "yaml": "pyyaml",
    "PIL": "pillow",
}
IGNORED_THIRD_PARTY = {"importlib_metadata", "defusedxml"}


class ValidationError(RuntimeError):
    pass


def _parse_deps() -> tuple[set[str], set[str], set[str]]:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    def normalize(req: str) -> str:
        return req.split("==")[0].split("[")[0].lower().replace("-", "_")

    core = {normalize(dep) for dep in project.get("dependencies", [])}
    optional = project.get("optional-dependencies", {})
    test_deps = {normalize(dep) for group in ("test", "dev") for dep in optional.get(group, [])}
    optional_all = {normalize(dep) for deps in optional.values() for dep in deps}
    return core, test_deps, optional_all


def _local_modules() -> set[str]:
    local = {"bnsyn", "aoc", "scripts", "tools", "benchmarks", "tests", "contracts", "entropy", "claims"}
    for base in (Path("src/bnsyn"), Path("src/aoc"), Path("scripts"), Path("benchmarks"), Path("tools")):
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            name = p.stem
            if name != "__init__":
                local.add(name)
        for d in base.rglob("*"):
            if d.is_dir() and (d / "__init__.py").exists():
                local.add(d.name)
    return local


def _imports(root: Path) -> set[str]:
    mods: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
    return mods


def _normalize_module(mod: str) -> str:
    return PACKAGE_NAME_MAP.get(mod, mod).lower().replace("-", "_")


def _third_party(modules: set[str], local: set[str]) -> set[str]:
    return {_normalize_module(m) for m in modules if m not in STDLIB and m not in local and m not in IGNORED_THIRD_PARTY}


def main() -> int:
    core, test_deps, optional_all = _parse_deps()
    local = _local_modules()
    src_imports = _third_party(_imports(Path("src")), local)
    test_imports = _third_party(_imports(Path("tests")), local)

    missing_core = sorted(src_imports - core - optional_all)
    if missing_core:
        raise ValidationError(f"missing dependency declarations for src imports: {missing_core}")

    available_for_tests = core | test_deps | optional_all
    missing_test = sorted(test_imports - available_for_tests)
    if missing_test:
        raise ValidationError(f"missing test deps for tests imports: {missing_test}")

    print("validate_deps_against_imports: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validate_deps_against_imports: FAIL: {exc}")
        raise SystemExit(1)
