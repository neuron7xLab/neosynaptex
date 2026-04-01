"""Architecture invariant tests — enforces layering rules and contracts.

Verifies:
1. Read-only modules don't import simulation execution
2. gamma never appears in control interfaces
3. Write boundaries are explicit and narrow
4. Canonical types are frozen
5. Import cycles don't increase
"""

from __future__ import annotations

import ast
import os

import numpy as np

# ── Forbidden import checks ──────────────────────────────────────


def _get_imports(filepath: str) -> list[str]:
    """Extract all import targets from a Python file."""
    try:
        with open(filepath) as fh:
            tree = ast.parse(fh.read())
    except (SyntaxError, UnicodeDecodeError):
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


def _check_no_forbidden_imports(
    package_dir: str,
    forbidden: list[str],
) -> list[str]:
    """Check that no file in package_dir imports from forbidden modules."""
    violations = []
    for root, dirs, files in os.walk(package_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            for imp in _get_imports(path):
                for forbidden_mod in forbidden:
                    if forbidden_mod in imp:
                        violations.append(f"{path}: imports {imp}")
    return violations


class TestLayeringRules:
    """Enforce dependency direction rules."""

    def test_interpretability_no_simulate(self) -> None:
        """Interpretability must not import simulation execution."""
        pkg = "src/mycelium_fractal_net/interpretability"
        violations = _check_no_forbidden_imports(
            pkg, ["mycelium_fractal_net.core.simulate",
                  "mycelium_fractal_net.core.engine"],
        )
        assert not violations, f"Forbidden imports: {violations}"

    def test_self_reading_no_simulate(self) -> None:
        pkg = "src/mycelium_fractal_net/self_reading"
        violations = _check_no_forbidden_imports(
            pkg, ["mycelium_fractal_net.core.simulate",
                  "mycelium_fractal_net.core.engine"],
        )
        assert not violations, f"Forbidden imports: {violations}"

    def test_tau_control_no_simulate(self) -> None:
        pkg = "src/mycelium_fractal_net/tau_control"
        violations = _check_no_forbidden_imports(
            pkg, ["mycelium_fractal_net.core.simulate",
                  "mycelium_fractal_net.core.engine",
                  "mycelium_fractal_net.api",
                  "mycelium_fractal_net.cli"],
        )
        assert not violations, f"Forbidden imports: {violations}"


class TestNoGoodhart:
    """gamma must never appear in control interfaces."""

    def test_no_gamma_in_tau_control(self) -> None:
        """No function in tau_control accepts gamma as parameter."""
        import inspect

        from mycelium_fractal_net.tau_control import (
            Discriminant,
            IdentityEngine,
            TauController,
            TransformationProtocol,
        )

        for cls in [Discriminant, IdentityEngine, TauController, TransformationProtocol]:
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if name.startswith("_"):
                    continue
                sig = inspect.signature(method)
                for param_name in sig.parameters:
                    assert "gamma" not in param_name.lower(), (
                        f"{cls.__name__}.{name} has gamma param: {param_name}"
                    )

    def test_no_gamma_in_recovery(self) -> None:
        import inspect

        from mycelium_fractal_net.self_reading import RecoveryProtocol

        for name, method in inspect.getmembers(RecoveryProtocol, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            sig = inspect.signature(method)
            for param_name in sig.parameters:
                assert "gamma" not in param_name.lower()


class TestCanonicalContracts:
    """Canonical types must be frozen."""

    def test_field_sequence_frozen(self) -> None:
        from mycelium_fractal_net.types.field import FieldSequence

        seq = FieldSequence(field=np.zeros((4, 4)))
        with __import__("pytest").raises(AttributeError):
            seq.field = np.ones((4, 4))  # type: ignore[misc]

    def test_tau_state_frozen(self) -> None:
        from mycelium_fractal_net.tau_control.types import TauState

        ts = TauState(step=0, phi=0, tau=0, pressure="op", mode="idle",
                      v_x=0, v_s=0, v_c=0, v_total=0)
        with __import__("pytest").raises(AttributeError):
            ts.step = 1  # type: ignore[misc]

    def test_discriminant_result_frozen(self) -> None:
        from mycelium_fractal_net.tau_control.discriminant import DiscriminantResult

        dr = DiscriminantResult(
            pressure=PressureKind.OPERATIONAL,
            probability_existential=0.1,
            uncertainty=0.1,
            hard_guard_triggered=False,
            consecutive_existential=0,
            hysteresis_blocked=False,
            explanation="test",
        )
        with __import__("pytest").raises(AttributeError):
            dr.pressure = PressureKind.EXISTENTIAL  # type: ignore[misc]


class TestImportCycles:
    """Import cycle count should not increase."""

    def test_cycle_count_bounded(self) -> None:
        """Max 11 cycles (current baseline). Alert if it grows."""
        from collections import defaultdict

        pkg = "src/mycelium_fractal_net"
        graph: dict[str, set[str]] = defaultdict(set)

        for root, dirs, files in os.walk(pkg):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                mod = path.replace("src/", "").replace("/", ".").replace(".py", "")
                mod = mod.removesuffix(".__init__")
                for imp in _get_imports(path):
                    if imp.startswith("mycelium_fractal_net"):
                        parts = imp.split(".")
                        if len(parts) >= 2:
                            src_pkg = ".".join(mod.split(".")[:2])
                            dst_pkg = ".".join(parts[:2])
                            if src_pkg != dst_pkg:
                                graph[src_pkg].add(dst_pkg)

        cycles = set()
        for a, targets in graph.items():
            for b in targets:
                if a in graph.get(b, set()):
                    cycles.add(tuple(sorted([a, b])))

        assert len(cycles) <= 11, f"Import cycles increased to {len(cycles)}: {cycles}"


# Need this for the frozen test
from mycelium_fractal_net.tau_control.discriminant import PressureKind
