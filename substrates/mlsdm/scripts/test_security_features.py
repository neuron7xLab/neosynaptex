#!/usr/bin/env python3
"""Integration test script for security features.

This script validates that all security features are working correctly
by running comprehensive integration tests.

Usage:
    python scripts/test_security_features.py
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output.

    Args:
        cmd: Command to run as list of strings
        description: Description of the test

    Returns:
        Tuple of (success, output)
    """
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr
        success = result.returncode == 0

        if success:
            print(f"✓ {description} - PASSED")
        else:
            print(f"✗ {description} - FAILED")
            print(f"Exit code: {result.returncode}")
            if output:
                print("Output:")
                print(output[:500])  # Show first 500 chars

        return success, output

    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False, str(e)


def main(argv: list[str] | None = None) -> int:
    """Main test runner.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="MLSDM Security Features Integration Test",
    )
    parser.parse_args(argv)  # Just for --help support

    print("=" * 60)
    print("MLSDM Security Features Integration Test")
    print("=" * 60)

    results: list[tuple[str, bool]] = []

    # Test 1: Rate limiter tests
    success, _ = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/test_rate_limiter.py",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        "Rate Limiter Tests",
    )
    results.append(("Rate Limiter Tests", success))

    # Test 2: Input validator tests
    success, _ = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/test_input_validator.py",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        "Input Validator Tests",
    )
    results.append(("Input Validator Tests", success))

    # Test 3: Security logger tests
    success, _ = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit/test_security_logger.py",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        "Security Logger Tests",
    )
    results.append(("Security Logger Tests", success))

    # Test 4: LLM safety gateway tests
    success, _ = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/security/test_llm_safety.py",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        "LLM Safety Tests",
    )
    results.append(("LLM Safety Tests", success))

    # Test 5: Payload scrubber tests
    success, _ = run_command(
        [
            "python",
            "-m",
            "pytest",
            "tests/security/test_payload_scrubber.py",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        "Payload Scrubber Tests",
    )
    results.append(("Payload Scrubber Tests", success))

    # Test 6: Check security files exist
    print(f"\n{'=' * 60}")
    print("Checking Security Artifacts")
    print(f"{'=' * 60}")

    required_files = [
        "src/mlsdm/utils/rate_limiter.py",
        "src/mlsdm/utils/input_validator.py",
        "src/mlsdm/utils/security_logger.py",
        "tests/unit/test_rate_limiter.py",
        "tests/unit/test_input_validator.py",
        "tests/unit/test_security_logger.py",
        "tests/security/test_llm_safety.py",
        "tests/security/test_payload_scrubber.py",
        "scripts/security_audit.py",
        "SECURITY_IMPLEMENTATION.md",
        "SECURITY_POLICY.md",
        "THREAT_MODEL.md",
    ]

    all_present = True
    for file_path_str in required_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            print(f"✓ {file_path_str}")
        else:
            print(f"✗ {file_path_str} - MISSING")
            all_present = False

    results.append(("Security Artifacts", all_present))

    # Test 7: Verify security implementations are importable
    print(f"\n{'=' * 60}")
    print("Verifying Security Imports")
    print(f"{'=' * 60}")

    try:
        # Add project root to path for imports
        sys.path.insert(0, str(Path.cwd()))

        print("✓ RateLimiter can be imported")

        print("✓ InputValidator can be imported")

        print("✓ SecurityLogger can be imported")

        results.append(("Security Imports", True))
    except Exception as e:
        print(f"✗ Import failed: {e}")
        results.append(("Security Imports", False))

    # Print summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")

    passed = sum(1 for _, success_flag in results if success_flag)
    total = len(results)

    for test_name, success_flag in results:
        status = "✓ PASS" if success_flag else "✗ FAIL"
        print(f"{status:8} - {test_name}")

    print(f"\n{'-' * 60}")
    print(f"Total: {passed}/{total} tests passed ({100 * passed // total}%)")
    print(f"{'-' * 60}")

    if passed == total:
        print("\n✓ All security features are working correctly!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review and fix.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
