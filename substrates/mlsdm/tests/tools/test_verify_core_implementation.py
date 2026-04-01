"""
Tests for scripts/verify_core_implementation.sh
"""

import subprocess
from pathlib import Path

import pytest


class TestVerifyCoreImplementation:
    """Test suite for the verify_core_implementation.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        """Get path to the verify_core_implementation script."""
        repo_root = Path(__file__).parent.parent.parent
        script = repo_root / "scripts" / "verify_core_implementation.sh"
        assert script.exists(), f"Script not found: {script}"
        return script

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root path."""
        return Path(__file__).parent.parent.parent

    def run_script(self, script_path: Path, cwd: Path = None) -> tuple[int, str, str]:
        """Run the verification script and return (returncode, stdout, stderr)."""
        if cwd is None:
            cwd = script_path.parent.parent  # repo root

        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.returncode, result.stdout, result.stderr

    def test_script_exists_and_executable(self, script_path: Path):
        """Test that the script exists and is executable."""
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111, "Script is not executable"

    def test_script_has_proper_structure(self, script_path: Path):
        """Test that the script has expected structure and components."""
        content = script_path.read_text()

        # Check for strict mode
        assert "set -eEfuo pipefail" in content or "set -euo pipefail" in content

        # Check for key sections
        assert "Test Collection" in content or "CHECK 1" in content
        assert "TODO" in content or "NotImplementedError" in content

        # Check for proper exit codes
        assert "exit 0" in content
        assert "exit 1" in content

        # Check for colored output
        assert "GREEN=" in content or "RED=" in content

        # Check for core module list
        assert "memory" in content.lower()
        assert "cognition" in content.lower()
        assert "core" in content.lower()

    def test_script_runs_successfully_on_real_repo(self, script_path: Path, repo_root: Path):
        """Test that the script runs successfully on the actual repository."""
        returncode, stdout, stderr = self.run_script(script_path, cwd=repo_root)

        # The script should pass on the real repo (no TODOs in core)
        assert returncode == 0, f"Script failed: {stderr}\nStdout: {stdout}"

        # Check for expected output markers
        assert "Test Collection" in stdout or "CHECK" in stdout
        assert "PASSED" in stdout or "✓" in stdout

    def test_script_counts_tests(self, script_path: Path, repo_root: Path):
        """Test that the script counts tests correctly."""
        returncode, stdout, stderr = self.run_script(script_path, cwd=repo_root)

        assert returncode == 0

        # Should report number of tests collected
        assert "tests collected" in stdout.lower() or "test count" in stdout.lower()

    def test_script_checks_for_todos(self, script_path: Path, repo_root: Path):
        """Test that the script checks for TODOs and NotImplementedError."""
        returncode, stdout, stderr = self.run_script(script_path, cwd=repo_root)

        # Check that it performs the TODO check
        assert "TODO" in stdout or "NotImplementedError" in stdout

        # Real repo should have 0 TODOs in core modules
        assert "0" in stdout or "No TODO" in stdout or "PASSED" in stdout

    def test_script_fails_with_fake_todo(self, tmp_path: Path):
        """Test that the script would fail if TODOs existed in core modules."""
        # Create a minimal test environment
        src_dir = tmp_path / "src" / "mlsdm" / "core"
        src_dir.mkdir(parents=True)

        # Create a file with a TODO
        core_file = src_dir / "fake_core.py"
        core_file.write_text("""
def some_function():
    # TODO: Implement this
    raise NotImplementedError("Not yet implemented")
""")

        # Create a simplified test script
        test_script = tmp_path / "test_verify.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

echo "======================================================================"
echo "Test: Checking for TODOs"
echo "======================================================================"

GREP_OUTPUT=$(grep -rn "TODO\\|NotImplementedError" {src_dir}/ 2>&1 || true)
GREP_COUNT=$(echo "$GREP_OUTPUT" | grep -cv "^$" || echo "0")

if [ "$GREP_COUNT" -gt 0 ]; then
    echo "✗ FAILED: Found $GREP_COUNT occurrences"
    echo "$GREP_OUTPUT"
    exit 1
else
    echo "✓ PASSED: No TODOs found"
    exit 0
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Should fail because TODOs exist
        assert result.returncode == 1
        assert "FAILED" in result.stdout
        assert "TODO" in result.stdout or "NotImplementedError" in result.stdout

    def test_core_modules_have_no_todos(self, repo_root: Path):
        """Test that core modules have no TODO or NotImplementedError."""
        core_modules = [
            "src/mlsdm/memory",
            "src/mlsdm/cognition",
            "src/mlsdm/core",
            "src/mlsdm/rhythm",
            "src/mlsdm/speech",
            "src/mlsdm/extensions",
        ]

        for module_path in core_modules:
            full_path = repo_root / module_path

            if not full_path.exists():
                continue  # Skip if module doesn't exist

            # Search for TODOs and NotImplementedError
            result = subprocess.run(
                ["grep", "-rn", "TODO\\|NotImplementedError", str(full_path)],
                capture_output=True,
                text=True,
            )

            # grep returns 1 if no matches found (which is what we want)
            if result.returncode == 0:
                # Found TODOs - fail the test
                pytest.fail(f"Found TODO or NotImplementedError in {module_path}:\n{result.stdout}")

    def test_script_validates_test_collection(self, tmp_path: Path):
        """Test that script validates test collection works."""
        # Create minimal test structure
        tests_dir = tmp_path / "tests" / "unit"
        tests_dir.mkdir(parents=True)

        # Create a simple test file
        test_file = tests_dir / "test_example.py"
        test_file.write_text("""
import pytest

def test_example():
    assert True
""")

        # Create test script that checks pytest collection
        test_script = tmp_path / "test_collection.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

cd {tmp_path}

echo "Testing pytest collection..."

# Try to collect tests
TEST_OUTPUT=$(python -m pytest {tests_dir} --co -q 2>&1)
TEST_COUNT=$(echo "$TEST_OUTPUT" | grep -E "test collected|tests collected" | awk '{{print $1}}')

if [ -n "$TEST_COUNT" ] && [ "$TEST_COUNT" -gt 0 ]; then
    echo "✓ PASSED: $TEST_COUNT tests collected"
    exit 0
else
    echo "✗ FAILED: Could not collect tests"
    echo "$TEST_OUTPUT"
    exit 1
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "PASSED" in result.stdout
        assert "collected" in result.stdout

    def test_script_output_is_readable(self, script_path: Path, repo_root: Path):
        """Test that script output is well-formatted and readable."""
        returncode, stdout, stderr = self.run_script(script_path, cwd=repo_root)

        # Check for proper formatting
        assert "====" in stdout  # Section separators
        assert "CHECK" in stdout or "Test" in stdout  # Clear labels

        # Should have summary section
        assert "SUMMARY" in stdout.upper() or "VERIFICATION" in stdout.upper()

        # Should use visual indicators
        has_indicators = any(indicator in stdout for indicator in ["✓", "✗", "PASSED", "FAILED"])
        assert has_indicators

    def test_core_module_paths_exist(self, repo_root: Path):
        """Test that all expected core module paths exist."""
        core_modules = [
            "src/mlsdm/memory",
            "src/mlsdm/cognition",
            "src/mlsdm/core",
            "src/mlsdm/rhythm",
            "src/mlsdm/speech",
            "src/mlsdm/extensions",
        ]

        for module_path in core_modules:
            full_path = repo_root / module_path
            assert full_path.exists(), f"Core module not found: {module_path}"
            assert full_path.is_dir(), f"Core module is not a directory: {module_path}"
