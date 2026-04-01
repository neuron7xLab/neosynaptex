"""
Tests for layer boundary enforcement.

This test module verifies:
1. core/ modules do NOT import infrastructure (FastAPI, uvicorn, etc.)
2. Integration layer properly separates core from external dependencies
3. No circular imports exist

Reference: docs/MFN_CODE_STRUCTURE.md, docs/ARCHITECTURE.md
"""

import ast
import importlib
import sys
from pathlib import Path

import pytest

# Infrastructure packages that should NOT be imported in core/
INFRASTRUCTURE_PACKAGES = {
    "fastapi",
    "uvicorn",
    "starlette",
    "flask",
    "django",
    "requests",  # HTTP client
    "httpx",  # HTTP client
    "aiohttp",  # Async HTTP
    "kafka",
    "redis",
    "sqlalchemy",
    "pymongo",
    "celery",
}

# Core packages that ARE allowed in core/
ALLOWED_CORE_PACKAGES = {
    "numpy",
    "torch",
    "sympy",
    "scipy",
    "dataclasses",
    "typing",
    "abc",
    "enum",
    "math",
    "collections",
    "functools",
    "itertools",
}


class TestCoreLayerBoundaries:
    """Test that core/ modules do not import infrastructure packages."""

    def _get_imports_from_file(self, filepath: Path) -> set[str]:
        """Extract all import names from a Python file using AST."""
        try:
            with open(filepath) as f:
                tree = ast.parse(f.read())
        except SyntaxError:
            return set()

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

        return imports

    def test_core_does_not_import_fastapi(self) -> None:
        """Verify core/ modules do not import FastAPI."""
        core_path = Path("src/mycelium_fractal_net/core")

        for py_file in core_path.glob("*.py"):
            imports = self._get_imports_from_file(py_file)

            for infra_pkg in ["fastapi", "starlette", "uvicorn"]:
                assert infra_pkg not in imports, (
                    f"{py_file.name} imports {infra_pkg}, violating layer boundary. "
                    f"Core modules must not import web framework packages."
                )

    def test_core_does_not_import_http_clients(self) -> None:
        """Verify core/ modules do not import HTTP clients."""
        core_path = Path("src/mycelium_fractal_net/core")

        for py_file in core_path.glob("*.py"):
            imports = self._get_imports_from_file(py_file)

            for http_pkg in ["requests", "httpx", "aiohttp"]:
                assert http_pkg not in imports, (
                    f"{py_file.name} imports {http_pkg}, violating layer boundary. "
                    f"Core modules must not import HTTP client packages."
                )

    def test_core_does_not_import_message_queues(self) -> None:
        """Verify core/ modules do not import message queue packages."""
        core_path = Path("src/mycelium_fractal_net/core")

        for py_file in core_path.glob("*.py"):
            imports = self._get_imports_from_file(py_file)

            for mq_pkg in ["kafka", "redis", "celery", "pika"]:
                assert mq_pkg not in imports, (
                    f"{py_file.name} imports {mq_pkg}, violating layer boundary. "
                    f"Core modules must not import message queue packages."
                )

    def test_core_module_imports_are_clean(self) -> None:
        """Verify all core/ modules import without errors and have clean imports."""
        core_modules = [
            "mycelium_fractal_net.core",
            "mycelium_fractal_net.core.nernst",
            "mycelium_fractal_net.core.turing",
            "mycelium_fractal_net.core.fractal",
            "mycelium_fractal_net.core.stdp",
            "mycelium_fractal_net.core.federated",
            "mycelium_fractal_net.core.stability",
            "mycelium_fractal_net.core.membrane_engine",
            "mycelium_fractal_net.core.reaction_diffusion_engine",
            "mycelium_fractal_net.core.fractal_growth_engine",
        ]

        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                # ML-dependent modules (stdp, federated) require torch [ml] extra
                if "torch" in str(e) and module_name.split(".")[-1] in (
                    "stdp",
                    "federated",
                ):
                    pytest.skip(f"{module_name} requires torch [ml] extra")
                pytest.fail(f"Failed to import {module_name}: {e}")


class TestIntegrationLayerBoundaries:
    """Test that integration layer properly mediates between core and external."""

    def test_integration_can_import_schemas(self) -> None:
        """Verify integration layer schemas are importable."""
        from mycelium_fractal_net.integration import (
            ValidateRequest,
        )

        # All should be pydantic models or dataclasses
        has_fields = hasattr(ValidateRequest, "__fields__")
        has_dataclass_fields = hasattr(ValidateRequest, "__dataclass_fields__")
        assert has_fields or has_dataclass_fields

    def test_integration_can_import_adapters(self) -> None:
        """Verify integration layer adapters are importable."""
        from mycelium_fractal_net.integration import (
            aggregate_gradients_adapter,
            compute_nernst_adapter,
            run_simulation_adapter,
            run_validation_adapter,
        )

        assert callable(run_validation_adapter)
        assert callable(run_simulation_adapter)
        assert callable(compute_nernst_adapter)
        assert callable(aggregate_gradients_adapter)

    def test_integration_can_import_service_context(self) -> None:
        """Verify integration layer service context is importable."""
        from mycelium_fractal_net.integration import (
            ExecutionMode,
            ServiceContext,
            create_context_from_request,
        )

        assert isinstance(ServiceContext, type)
        assert hasattr(ExecutionMode, "API")
        assert callable(create_context_from_request)


class TestNoCircularImports:
    """Test for absence of circular imports."""

    def test_core_imports_without_errors(self) -> None:
        """Test all core modules can be imported without circular import errors."""
        # Clear any cached imports
        modules_to_clear = [m for m in sys.modules if m.startswith("mycelium_fractal_net")]
        for m in modules_to_clear:
            del sys.modules[m]

        # Re-import main package
        try:
            import mycelium_fractal_net  # noqa: F401

            # Test domain modules
            from mycelium_fractal_net.core import (  # noqa: F401
                federated,
                fractal,
                nernst,
                stability,
                stdp,
                turing,
            )
        except ImportError as e:
            if "torch" in str(e):
                pytest.skip(f"Torch-dependent core modules unavailable: {e}")
            pytest.fail(f"Circular import detected: {e}")

    def test_integration_imports_without_errors(self) -> None:
        """Test integration layer can be imported without errors."""
        try:
            from mycelium_fractal_net import integration  # noqa: F401
            from mycelium_fractal_net.integration import (  # noqa: F401
                adapters,
                schemas,
                service_context,
            )
        except ImportError as e:
            if "torch" in str(e):
                pytest.skip(f"Torch-dependent integration modules unavailable: {e}")
            pytest.fail(f"Import error in integration layer: {e}")


class TestLayerDependencyDirection:
    """Test that dependencies flow in correct direction: core <- integration <- api."""

    def _get_imports_from_file(self, filepath: Path) -> set[str]:
        """Extract all import names from a Python file."""
        try:
            with open(filepath) as f:
                content = f.read()
                tree = ast.parse(content)
        except (SyntaxError, FileNotFoundError):
            return set()

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        return imports

    def test_core_does_not_depend_on_integration(self) -> None:
        """Verify core/ does not import from integration/."""
        core_path = Path("src/mycelium_fractal_net/core")

        for py_file in core_path.glob("*.py"):
            imports = self._get_imports_from_file(py_file)

            integration_imports = [i for i in imports if "integration" in i]
            assert len(integration_imports) == 0, (
                f"{py_file.name} imports from integration: {integration_imports}. "
                f"Core must not depend on integration layer."
            )

    def test_api_uses_integration_not_core_directly(self) -> None:
        """Verify api.py uses integration layer for request/response handling."""
        api_path = Path("src/mycelium_fractal_net/api.py")
        if not api_path.exists():
            pytest.skip("api.py not found at expected canonical location")
        imports = self._get_imports_from_file(api_path)

        # API should import from integration
        integration_imports = [i for i in imports if "integration" in i]
        assert len(integration_imports) > 0, (
            "api.py should import from integration layer for schemas and adapters"
        )


class TestModuleExportsConsistency:
    """Test that module __all__ exports are consistent with actual exports."""

    def test_core_init_exports_all_items(self) -> None:
        """Verify core/__init__.py exports all declared items."""
        from mycelium_fractal_net import core

        # Get declared __all__
        if hasattr(core, "__all__"):
            declared = set(core.__all__)

            # Check each declared export actually exists
            for name in declared:
                try:
                    getattr(core, name)
                except ImportError:
                    # Torch-dependent lazy attributes; skip silently
                    pass

    def test_package_init_exports_all_items(self) -> None:
        """Verify mycelium_fractal_net/__init__.py exports all declared items."""
        import mycelium_fractal_net

        if hasattr(mycelium_fractal_net, "__all__"):
            declared = set(mycelium_fractal_net.__all__)

            for name in declared:
                try:
                    getattr(mycelium_fractal_net, name)
                except ImportError:
                    # Torch-dependent lazy attributes; skip silently
                    pass
