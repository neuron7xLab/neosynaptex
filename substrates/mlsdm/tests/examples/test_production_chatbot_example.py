"""
Smoke tests for production_chatbot_example.py

These tests run the example as a subprocess to avoid direct import dependencies.
Uses input redirection to test non-interactive mode.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_production_chatbot_demo_mode():
    """Test that production_chatbot_example.py runs in demo mode."""
    # Find the examples directory
    repo_root = Path(__file__).parent.parent.parent
    example_path = repo_root / "examples" / "production_chatbot_example.py"

    assert example_path.exists(), f"Example not found: {example_path}"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")

    # Run the example in demo mode with a timeout
    # 30 second timeout is sufficient for smoke test
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
    assert "MLSDM PRODUCTION CHATBOT DEMO" in result.stdout
    assert "Demo completed successfully" in result.stdout
    assert "CHATBOT STATISTICS" in result.stdout
