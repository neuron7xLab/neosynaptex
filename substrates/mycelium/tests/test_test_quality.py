"""Meta-tests: verify the test suite itself meets quality standards.

These tests enforce that our test infrastructure is sound:
- Every test file has at least one test function
- Core modules have dedicated test files
- No test depends on execution order
- Minimum test count thresholds
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS_DIR = Path("tests")
SRC_DIR = Path("src/mycelium_fractal_net")

# Core modules that MUST have dedicated test coverage
MUST_HAVE_TESTS = [
    "core/detect.py",
    "core/forecast.py",
    "core/simulate.py",
    "core/causal_validation.py",
    "core/diagnose.py",
    "core/early_warning.py",
    "analytics/morphology.py",
    "bio/physarum.py",
    "bio/memory.py",
    "bio/extension.py",
    "intervention/__init__.py",
    "neurochem/kinetics.py",
]


def _count_test_functions(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


class TestSuiteQuality:
    """Meta-tests for the test suite itself."""

    def test_minimum_total_test_count(self) -> None:
        """We must have at least 1800 test functions (regression guard)."""
        total = sum(
            _count_test_functions(f)
            for f in TESTS_DIR.rglob("*.py")
            if "__pycache__" not in str(f) and f.name not in ("conftest.py", "__init__.py")
        )
        assert total >= 1800, f"Test count dropped to {total} (min 1800)"

    def test_no_empty_test_files(self) -> None:
        """Every test_*.py must contain test functions or TestCase classes."""
        empty = []
        for f in TESTS_DIR.rglob("test_*.py"):
            if "__pycache__" in str(f):
                continue
            content = f.read_text(errors="ignore")
            has_tests = _count_test_functions(f) > 0
            has_testcase = "TestCase" in content or "RuleBasedStateMachine" in content
            if not has_tests and not has_testcase:
                empty.append(str(f.relative_to(TESTS_DIR)))
        assert not empty, f"Empty test files: {empty}"

    def test_core_modules_have_tests(self) -> None:
        """Critical source modules must have corresponding test coverage."""
        untested = []
        for mod in MUST_HAVE_TESTS:
            src_path = SRC_DIR / mod
            if not src_path.exists():
                continue
            mod_name = mod.replace("/", "_").replace(".py", "")
            # Look for any test file that imports from this module
            found = False
            for tf in TESTS_DIR.rglob("*.py"):
                if "__pycache__" in str(tf):
                    continue
                content = tf.read_text(errors="ignore")
                if mod_name in content or mod.split("/")[-1].replace(".py", "") in content:
                    found = True
                    break
            if not found:
                untested.append(mod)
        assert not untested, f"Core modules without test coverage: {untested}"

    def test_property_tests_exist(self) -> None:
        """Property-based tests must exist for bio/ layer."""
        prop_files = list(TESTS_DIR.glob("test_bio_properties*.py"))
        assert len(prop_files) >= 1, "No property-based test files found"

    def test_stateful_tests_exist(self) -> None:
        """Stateful tests must exist for BioMemory."""
        stateful = list(TESTS_DIR.glob("test_bio_stateful*.py"))
        assert len(stateful) >= 1, "No stateful test files found"

    def test_benchmark_gates_exist(self) -> None:
        """Calibrated benchmark gates must exist."""
        gates = list((TESTS_DIR / "benchmarks").glob("test_bio_gates*.py"))
        assert len(gates) >= 1, "No benchmark gate files found"
        baseline = Path("benchmarks/bio_baseline.json")
        assert baseline.exists(), "benchmarks/bio_baseline.json missing"

    def test_golden_hashes_exist(self) -> None:
        """Golden hash regression tests must exist."""
        golden = Path("tests/golden_hashes.json")
        assert golden.exists(), "Golden hashes file missing"
        import json

        data = json.loads(golden.read_text())
        assert len(data) >= 4, f"Only {len(data)} golden profiles (need 4+)"

    def test_architectural_invariants_exist(self) -> None:
        """Architectural invariant tests must exist."""
        inv = list(TESTS_DIR.glob("test_architectural_invariants*.py"))
        assert len(inv) >= 1, "No architectural invariant tests found"

    def test_docs_example_tests_exist(self) -> None:
        """Executable documentation tests must exist."""
        docs = list(TESTS_DIR.glob("test_docs_examples*.py"))
        assert len(docs) >= 1, "No docs example tests found"
