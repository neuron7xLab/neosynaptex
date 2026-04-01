#!/usr/bin/env python3
"""Security audit script for dependency vulnerability scanning.

This script performs security checks including:
1. Dependency vulnerability scanning using pip-audit
2. Security configuration validation
3. Security best practices checks

Primary audit path: requirements.txt-based scan with pip-audit --requirement requirements.txt.

Usage:
    python scripts/security_audit.py [--fix] [--report] [--env]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"
EXPORT_REQUIREMENTS_PATH = PROJECT_ROOT / "scripts" / "ci" / "export_requirements.py"


def check_pip_audit_installed() -> bool:
    """Check if pip-audit is installed."""
    try:
        subprocess.run(["pip-audit", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pip_audit() -> bool:
    """Install pip-audit if not present."""
    print("Installing pip-audit...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pip-audit"], capture_output=True, check=True
        )
        print("✓ pip-audit installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install pip-audit: {e}")
        return False


def load_excluded_packages() -> dict[str, str]:
    """Load excluded package metadata from export_requirements.py if available.

    This keeps audit exclusions consistent with the central requirements generator policy.
    """
    if not EXPORT_REQUIREMENTS_PATH.exists():
        return {}

    spec = importlib.util.spec_from_file_location(
        "export_requirements", EXPORT_REQUIREMENTS_PATH
    )
    if spec is None or spec.loader is None:
        return {}

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"⚠️  Unable to load exclusion metadata: {exc}")
        return {}

    excluded = getattr(module, "EXCLUDED_PACKAGES", {})
    if isinstance(excluded, dict):
        return {str(key): str(value) for key, value in excluded.items()}
    return {}


def _format_excluded_packages(excluded_packages: dict[str, str]) -> list[str]:
    if not excluded_packages:
        return ["None"]
    return [f"{name}: {reason}" for name, reason in sorted(excluded_packages.items())]


def run_pip_audit(
    *,
    fix: bool = False,
    requirements_path: Path | None,
    excluded_packages: dict[str, str],
) -> tuple[bool, dict[str, Any]]:
    """Run pip-audit to check for vulnerabilities.

    Args:
        fix: If True, attempt to fix vulnerabilities by upgrading packages
        requirements_path: Path to requirements.txt (None to scan installed environment)
        excluded_packages: Excluded package metadata for reporting

    Returns:
        Tuple of (success, results_dict)
    """
    print("\n" + "=" * 60)
    if requirements_path is None:
        mode_label = "installed environment"
    else:
        mode_label = f"requirements file ({requirements_path})"
    print(f"Running dependency vulnerability scan with pip-audit ({mode_label})...")
    print("=" * 60)
    if excluded_packages:
        print("Exclusion policy loaded for audit context:")
        for line in _format_excluded_packages(excluded_packages):
            print(f"  - {line}")

    if requirements_path is not None:
        cmd = ["pip-audit", "--requirement", str(requirements_path), "--format", "json"]
    else:
        cmd = ["pip-audit", "--format", "json"]
    if fix:
        cmd.append("--fix")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # Parse JSON output
        if result.stdout:
            try:
                audit_results = json.loads(result.stdout)
            except json.JSONDecodeError:
                audit_results = {"error": "Failed to parse pip-audit output"}
        else:
            audit_results = {}

        if result.returncode == 0:
            print("✓ No vulnerabilities found!")
            return True, audit_results
        else:
            print(f"✗ Found vulnerabilities (exit code: {result.returncode})")
            if audit_results.get("dependencies"):
                for dep in audit_results["dependencies"]:
                    print(f"\n  Package: {dep.get('name', 'unknown')}")
                    print(f"  Version: {dep.get('version', 'unknown')}")
                    for vuln in dep.get("vulns", []):
                        vuln_id = vuln.get("id", "N/A")
                        vuln_desc = vuln.get("description", "No description")
                        print(f"    - {vuln_id}: {vuln_desc}")
                        print(f"      Fix: {vuln.get('fix_versions', 'No fix available')}")
            return False, audit_results

    except FileNotFoundError:
        print("✗ pip-audit not found")
        return False, {"error": "pip-audit not installed"}
    except Exception as e:
        print(f"✗ Error running pip-audit: {e}")
        return False, {"error": str(e)}


def check_security_configs() -> bool:
    """Check security configuration files are present and valid.

    Returns:
        True if all checks pass
    """
    print("\n" + "=" * 60)
    print("Checking security configuration files...")
    print("=" * 60)

    required_files = ["SECURITY_POLICY.md", "THREAT_MODEL.md"]

    all_present = True
    for file in required_files:
        filepath = Path(file)
        if filepath.exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            all_present = False

    return all_present


def check_security_implementations() -> tuple[bool, list[str]]:
    """Check that security features are implemented.

    Returns:
        Tuple of (all_present, list_of_findings)
    """
    print("\n" + "=" * 60)
    print("Checking security feature implementations...")
    print("=" * 60)

    findings = []

    # Check for rate limiter
    rate_limiter_file = Path("src/mlsdm/utils/rate_limiter.py")
    if rate_limiter_file.exists():
        print("✓ Rate limiter implemented")
    else:
        print("✗ Rate limiter not found")
        findings.append("Missing: Rate limiter implementation")

    # Check for input validator
    validator_file = Path("src/mlsdm/utils/input_validator.py")
    if validator_file.exists():
        print("✓ Input validator implemented")
    else:
        print("✗ Input validator not found")
        findings.append("Missing: Input validator implementation")

    # Check for security logger
    logger_file = Path("src/mlsdm/utils/security_logger.py")
    if logger_file.exists():
        print("✓ Security logger implemented")
    else:
        print("✗ Security logger not found")
        findings.append("Missing: Security logger implementation")

    # Check for security tests
    # Security tests are organized across multiple files and directories
    test_locations = [
        "tests/security/test_llm_safety.py",
        "tests/security/test_payload_scrubber.py",
        "tests/unit/test_rate_limiter.py",
        "tests/unit/test_input_validator.py",
        "tests/unit/test_security_logger.py",
    ]

    all_tests_found = True
    for test_file in test_locations:
        test_path = Path(test_file)
        if not test_path.exists():
            all_tests_found = False
            findings.append(f"Missing: {test_file}")

    if all_tests_found:
        print("✓ Security tests present")
    else:
        print("✗ Some security tests not found")
        # Still count as present if at least one test file exists
        if any(Path(tf).exists() for tf in test_locations):
            print("  (Note: Some security test files exist)")
            all_tests_found = True

    return len(findings) == 0, findings


def generate_security_report(
    audit_results: dict,
    config_check: bool,
    impl_check: bool,
    impl_findings: list[str],
    audit_mode: str,
    excluded_packages: dict[str, str],
) -> str:
    """Generate security audit report.

    Args:
        audit_results: Results from pip-audit
        config_check: Whether config files check passed
        impl_check: Whether implementation check passed
        impl_findings: List of implementation findings

    Returns:
        Report as string
    """
    report = []
    report.append("=" * 60)
    report.append("SECURITY AUDIT REPORT")
    report.append("=" * 60)
    report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 60)

    vuln_count = 0
    if audit_results.get("dependencies"):
        for dep in audit_results["dependencies"]:
            vuln_count += len(dep.get("vulns", []))

    report.append(f"Dependencies scanned: {len(audit_results.get('dependencies', []))}")
    report.append(f"Vulnerabilities found: {vuln_count}")
    report.append(f"Audit mode: {audit_mode}")
    report.append(f"Configuration files: {'✓ Present' if config_check else '✗ Missing'}")
    report.append(f"Security implementations: {'✓ Complete' if impl_check else '✗ Incomplete'}")
    report.append(
        "Excluded packages policy: "
        + ("None" if not excluded_packages else f"{len(excluded_packages)} package(s)")
    )
    report.append("")

    # Details
    if vuln_count > 0:
        report.append("VULNERABILITIES")
        report.append("-" * 60)
        for dep in audit_results.get("dependencies", []):
            for vuln in dep.get("vulns", []):
                vuln_id = vuln.get("id", "N/A")
                vuln_desc = vuln.get("description", "No description")
                report.append(f"• {dep['name']} {dep['version']}")
                report.append(f"  {vuln_id}: {vuln_desc}")
                report.append(f"  Fix: {vuln.get('fix_versions', 'No fix available')}")
                report.append("")

    if impl_findings:
        report.append("IMPLEMENTATION FINDINGS")
        report.append("-" * 60)
        for finding in impl_findings:
            report.append(f"• {finding}")
        report.append("")

    if excluded_packages:
        report.append("EXCLUDED PACKAGES (CENTRAL POLICY)")
        report.append("-" * 60)
        for line in _format_excluded_packages(excluded_packages):
            report.append(f"• {line}")
        report.append("")

    # Recommendations
    report.append("RECOMMENDATIONS")
    report.append("-" * 60)
    if vuln_count > 0:
        report.append("• Run 'python scripts/security_audit.py --fix' to attempt automatic fixes")
    if not config_check:
        report.append("• Create missing security configuration files")
    if impl_findings:
        report.append("• Implement missing security features")
    if vuln_count == 0 and config_check and impl_check:
        report.append("• All security checks passed! ✓")

    return "\n".join(report)


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description=(
            "Security audit for MLSDM Cognitive Memory. "
            "Default audit scans requirements.txt via "
            "'pip-audit --requirement requirements.txt --format json'."
        )
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix vulnerabilities by upgrading packages",
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Save report to file",
    )
    audit_group = parser.add_mutually_exclusive_group()
    audit_group.add_argument(
        "--env",
        action="store_true",
        help=(
            "Audit the installed environment instead of requirements.txt "
            "(default uses 'pip-audit --requirement requirements.txt --format json')"
        ),
    )
    audit_group.add_argument(
        "--installed",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    print("MLSDM Governed Cognitive Memory - Security Audit")
    print("=" * 60)

    # Ensure pip-audit is installed
    if not check_pip_audit_installed():
        print("pip-audit not found. Attempting to install...")
        if not install_pip_audit():
            print("\nERROR: Could not install pip-audit")
            print("Please install manually: pip install pip-audit")
            return 1

    excluded_packages = load_excluded_packages()
    if args.env or args.installed:
        requirements_path = None
        audit_mode = "installed environment (pip-audit --format json)"
    else:
        requirements_path = REQUIREMENTS_PATH
        audit_mode = (
            f"requirements file ({requirements_path}, "
            "pip-audit --requirement requirements.txt --format json)"
        )
        if not requirements_path.exists():
            print(f"ERROR: requirements.txt not found at {requirements_path}")
            return 1

    # Run checks
    audit_success, audit_results = run_pip_audit(
        fix=args.fix,
        requirements_path=requirements_path,
        excluded_packages=excluded_packages,
    )
    config_check = check_security_configs()
    impl_check, impl_findings = check_security_implementations()

    # Generate report
    report = generate_security_report(
        audit_results,
        config_check,
        impl_check,
        impl_findings,
        audit_mode,
        excluded_packages,
    )

    print("\n" + report)

    # Save report if requested
    if args.report:
        with open(args.report, "w") as f:
            f.write(report)
        print(f"\n✓ Report saved to {args.report}")

    # Exit with appropriate code
    all_passed = audit_success and config_check and impl_check
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
