"""
Smoke tests for minimal_example.py

These tests run the example as a subprocess to avoid direct import dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_minimal_example_runs():
    """Test that minimal_example.py can run without errors."""
    # Find the examples directory
    repo_root = Path(__file__).parent.parent.parent
    example_path = repo_root / "examples" / "minimal_example.py"

    assert example_path.exists(), f"Example not found: {example_path}"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")

    # Run the example with a timeout
    result = subprocess.run(
        [sys.executable, str(example_path)],
        capture_output=True,
        cwd=repo_root,
        env=env,
        text=True,
        timeout=30,
    )

    # Check that it ran successfully
    assert result.returncode == 0, f"Example failed with stderr: {result.stderr}"

    # Check for expected output
    assert "MLSDM Minimal Example" in result.stdout
    assert "Minimal example completed successfully" in result.stdout
