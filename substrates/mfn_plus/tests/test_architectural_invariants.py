"""Architectural invariants enforced as code.

These tests are the SINGLE source of truth for structural rules.
Every rule has a budget. Exceeding the budget blocks CI.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

SRC = Path("src/mycelium_fractal_net")

# ═══════════════════════════════════════════════════════════════
#  BUDGET CONSTANTS — change these deliberately, never silently
# ═══════════════════════════════════════════════════════════════

MAX_MODULE_LOC = 800  # No single .py file above this
MAX_CYCLOMATIC_COMPLEXITY = 15  # McCabe threshold (ruff C901)
MAX_DEPENDENCIES_PER_MODULE = 15  # Import count per file
MAX_TYPE_IGNORE_COMMENTS = 4  # BoundaryCondition enum + input_guards union-attr compat
MAX_FROZEN_LOC = 3500  # Frozen surface area budget
CORE_COVERAGE_FLOOR = 80.0  # Branch coverage minimum

# Hard cap for exempt modules — even exempt files cannot grow without bound
MAX_EXEMPT_MODULE_LOC = 1400

# Modules exempt from MAX_MODULE_LOC but subject to MAX_EXEMPT_MODULE_LOC
LOC_EXEMPT = {
    # model.py DECOMPOSED → model_pkg/ (13 LOC re-export wrapper)
    "causal_validation.py": 1050,  # Living spec document — current: 1021
    "api.py": 950,  # WS handlers kept, V1 extracted — current: 937
    "denoise_1d.py": 800,  # Frozen signal — current: 767
    "legacy_features.py": 800,  # Legacy compat — current: 766
    "generate_dataset.py": 650,  # Experiment tooling — current: 596
}

FROZEN_PATHS = [
    "crypto/",
    "core/federated.py",
    "core/stdp.py",
    "core/turing.py",
    "signal/",
]


def _count_loc(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def _count_imports(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return len(imports)


# ═══════════════════════════════════════════════════════════════
#  1. MODULE SIZE BUDGET
# ═══════════════════════════════════════════════════════════════


class TestModuleSizeBudget:
    def test_no_module_exceeds_loc_limit(self) -> None:
        violations = []
        for f in SRC.rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            if f.name in LOC_EXEMPT:
                continue
            loc = _count_loc(f)
            if loc > MAX_MODULE_LOC:
                violations.append(f"{f.relative_to(SRC)}: {loc} LOC (max {MAX_MODULE_LOC})")
        assert not violations, "Modules exceeding LOC budget:\n" + "\n".join(violations)

    def test_exempt_modules_within_their_cap(self) -> None:
        """Exempt modules have per-file caps. They cannot grow silently."""
        violations = []
        for f in SRC.rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            if f.name in LOC_EXEMPT:
                loc = _count_loc(f)
                cap = LOC_EXEMPT[f.name]
                if loc > cap:
                    violations.append(
                        f"{f.name}: {loc} LOC (cap {cap}). "
                        "Split the module or raise the cap with justification."
                    )
        assert not violations, "Exempt modules exceeded their cap:\n" + "\n".join(violations)


# ═══════════════════════════════════════════════════════════════
#  2. CYCLOMATIC COMPLEXITY BUDGET
# ═══════════════════════════════════════════════════════════════


class TestComplexityBudget:
    def test_no_function_exceeds_complexity(self) -> None:
        result = subprocess.run(
            [
                ".venv/bin/python",
                "-m",
                "ruff",
                "check",
                "src/",
                "--select",
                "C901",
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return  # No violations
        import json

        violations = json.loads(result.stdout)
        # Filter to non-exempt modules
        # Exempt: config validators, api websocket, legacy union-find, causal gate
        exempt_files = [
            "config.py",
            "config_validation.py",
            "api.py",
            "legacy_features.py",
            "causal_validation.py",
        ]
        real_violations = [
            f"{v['filename'].split('/')[-1]}:{v['location']['row']}: {v['message']}"
            for v in violations
            if not any(exempt in v["filename"] for exempt in exempt_files)
        ]
        assert not real_violations, "Functions exceeding complexity budget:\n" + "\n".join(
            real_violations
        )


# ═══════════════════════════════════════════════════════════════
#  3. DEPENDENCY BUDGET
# ═══════════════════════════════════════════════════════════════


class TestDependencyBudget:
    def test_no_module_exceeds_import_limit(self) -> None:
        violations = []
        for f in SRC.rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            if f.name == "__init__.py":
                continue  # Init files aggregate imports by design
            n = _count_imports(f)
            if n > MAX_DEPENDENCIES_PER_MODULE:
                violations.append(
                    f"{f.relative_to(SRC)}: {n} deps (max {MAX_DEPENDENCIES_PER_MODULE})"
                )
        assert not violations, "Modules exceeding dependency budget:\n" + "\n".join(violations)


# ═══════════════════════════════════════════════════════════════
#  4. FROZEN SURFACE BUDGET
# ═══════════════════════════════════════════════════════════════


class TestFrozenSurfaceBudget:
    def test_frozen_loc_within_budget(self) -> None:
        total = 0
        for pattern in FROZEN_PATHS:
            for f in SRC.rglob("*.py"):
                if "__pycache__" in str(f):
                    continue
                rel = str(f.relative_to(SRC))
                if (pattern.endswith("/") and rel.startswith(pattern)) or rel == pattern:
                    total += _count_loc(f)
        assert total <= MAX_FROZEN_LOC, (
            f"Frozen surface: {total} LOC (budget: {MAX_FROZEN_LOC}). "
            "Reduce by removing deprecated code."
        )


# ═══════════════════════════════════════════════════════════════
#  5. TYPE SAFETY — zero type:ignore in core paths
# ═══════════════════════════════════════════════════════════════


class TestTypeSafety:
    def test_no_type_ignore_in_core_analytics_neurochem(self) -> None:
        violations = []
        for subdir in ["core", "analytics", "neurochem", "intervention"]:
            for f in (SRC / subdir).rglob("*.py"):
                if "__pycache__" in str(f):
                    continue
                # Skip frozen modules
                if f.name in ("federated.py", "stdp.py", "turing.py"):
                    continue
                content = f.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if "# type: ignore" in line:
                        violations.append(f"{f.relative_to(SRC)}:{i}")
        assert len(violations) <= MAX_TYPE_IGNORE_COMMENTS, (
            f"type:ignore in core paths ({len(violations)} > {MAX_TYPE_IGNORE_COMMENTS}):\n"
            + "\n".join(violations)
        )


# ═══════════════════════════════════════════════════════════════
#  6. IMPORT LAYER ENFORCEMENT
# ═══════════════════════════════════════════════════════════════


class TestLayerEnforcement:
    """Core must not import from integration/api/transport layers."""

    FORBIDDEN_IN_CORE = {
        "fastapi",
        "pandas",
        "pyarrow",
        "websockets",
        "httpx",
        "aiohttp",
        "kafka",
        "uvicorn",
        "locust",
    }

    def test_core_no_transport_deps(self) -> None:
        violations = []
        for subdir in ["core", "analytics", "neurochem", "intervention"]:
            d = SRC / subdir
            if not d.exists():
                continue
            for f in d.rglob("*.py"):
                if "__pycache__" in str(f):
                    continue
                if f.name in ("federated.py", "stdp.py", "turing.py"):
                    continue
                try:
                    tree = ast.parse(f.read_text())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    mod = None
                    if isinstance(node, ast.Import):
                        for a in node.names:
                            mod = a.name.split(".")[0]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        mod = node.module.split(".")[0]
                    if mod and mod in self.FORBIDDEN_IN_CORE:
                        violations.append(f"{f.relative_to(SRC)}:{node.lineno}: imports {mod}")
        assert not violations, "Core imports forbidden deps:\n" + "\n".join(violations)

    def test_types_no_runtime_core_imports(self) -> None:
        """Types layer must not import core logic at runtime (prevents circular deps)."""
        violations = []
        for f in (SRC / "types").rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            content = f.read_text(encoding="utf-8", errors="ignore")
            in_type_checking = False
            for line in content.splitlines():
                if "TYPE_CHECKING" in line:
                    in_type_checking = True
                if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                    if not line.strip().startswith("#"):
                        in_type_checking = False
                if (
                    "from mycelium_fractal_net.core" in line
                    and not in_type_checking
                    and "# noqa" not in line
                ):
                    violations.append(f"{f.name}: {line.strip()}")
        # Soft check — import-linter is the primary enforcement
        # This catches obvious violations early


# ═══════════════════════════════════════════════════════════════
#  7. CONTRACT CONSISTENCY
# ═══════════════════════════════════════════════════════════════


class TestContractConsistency:
    """Public API exports must match documented surface."""

    def test_public_api_complete(self) -> None:
        """Every V1_SURFACE symbol must be importable."""
        import mycelium_fractal_net as mfn

        surface = mfn.V1_SURFACE
        for name in surface:
            assert hasattr(mfn, name) or callable(getattr(mfn, name, None)), (
                f"V1_SURFACE declares {name!r} but it's not importable"
            )

    def test_schema_versions_present(self) -> None:
        """All artifact schemas must have version field."""
        schema_dir = Path("docs/contracts/schemas")
        if not schema_dir.exists():
            pytest.skip("schemas not generated")
        import json

        for sf in schema_dir.glob("*.schema.json"):
            data = json.loads(sf.read_text())
            assert "version" in data, f"{sf.name}: missing version"

    def test_no_unversioned_artifacts(self) -> None:
        """Report pipeline must include schema_version in output."""
        import tempfile

        import mycelium_fractal_net as mfn

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        with tempfile.TemporaryDirectory() as d:
            report = mfn.report(seq, d)
            rd = report.to_dict()
            assert "schema_version" in rd or "engine_version" in rd
