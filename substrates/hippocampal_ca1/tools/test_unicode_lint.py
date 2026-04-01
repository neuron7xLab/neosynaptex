#!/usr/bin/env python3
"""
Test for unicode_lint.py

Verifies that the unicode lint tool correctly detects bidirectional
and control characters in test fixtures.
"""

import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNICODE_LINT = os.path.join(REPO_ROOT, "tools", "unicode_lint.py")


def test_detects_bidi_character():
    """Test that unicode_lint detects bidi control characters."""
    # Create a temp file with a bidi character
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize as git repo so unicode_lint can find files
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)

        bidi_file = os.path.join(tmpdir, "bidi_test.txt")
        # U+202E is Right-to-Left Override (e2 80 ae in UTF-8)
        with open(bidi_file, "w", encoding="utf-8") as f:
            f.write("Normal text \u202e hidden bidi\n")

        # Add to git
        subprocess.run(["git", "add", "bidi_test.txt"], cwd=tmpdir, capture_output=True)

        result = subprocess.run(
            [sys.executable, UNICODE_LINT, tmpdir], capture_output=True, text=True
        )

        # Should fail (exit code 1) because file contains bidi char
        assert (
            result.returncode == 1
        ), f"Expected exit code 1, got {result.returncode}\nOutput: {result.stdout}"

        # Should report the U+202E character
        assert "U+202E" in result.stdout, f"Expected U+202E in output, got: {result.stdout}"
        assert "Right-to-Left Override" in result.stdout, "Expected char name in output"

    print("PASSED: unicode_lint correctly detects bidi characters")
    return True


def test_clean_directory_passes():
    """Test that unicode_lint passes on clean directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize as git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)

        clean_file = os.path.join(tmpdir, "clean.txt")
        with open(clean_file, "w") as f:
            f.write("This is clean text without any bidi characters.\n")

        # Add to git
        subprocess.run(["git", "add", "clean.txt"], cwd=tmpdir, capture_output=True)

        result = subprocess.run(
            [sys.executable, UNICODE_LINT, tmpdir], capture_output=True, text=True
        )

        # Should pass (exit code 0)
        assert (
            result.returncode == 0
        ), f"Expected exit code 0, got {result.returncode}\nOutput: {result.stdout}"
        assert "PASSED" in result.stdout, f"Expected PASSED in output, got: {result.stdout}"

    print("PASSED: unicode_lint correctly passes on clean files")
    return True


if __name__ == "__main__":
    try:
        test_detects_bidi_character()
        test_clean_directory_passes()
        print("\nAll tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
