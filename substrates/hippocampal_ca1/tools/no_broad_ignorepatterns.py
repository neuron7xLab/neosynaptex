#!/usr/bin/env python3
"""
No Broad ignorePatterns Policy Checker

Validates that .github/markdown-link-check-config.json does not contain
overly broad ignorePatterns that could hide broken links.

Allowed patterns:
  - ^http://localhost (local development)
  - ^https://img\\.shields\\.io/ (badges, documented exception)

Disallowed patterns (examples):
  - Any pattern matching python.org, semver.org, opensource.org
  - Any pattern matching git-scm.com, conventionalcommits.org
  - Any pattern matching contributor-covenant.org, keepachangelog.com
  - Any pattern matching doi.org (use httpHeaders instead)
  - Any wildcard that broadly ignores domains

This script uses only Python standard library.

Exit codes:
  0 - Policy compliant
  1 - Policy violation found

Usage:
  python tools/no_broad_ignorepatterns.py [config_path]

  If config_path is not provided, uses .github/markdown-link-check-config.json
"""

import json
import os
import sys

# Type hints: Using built-in generics for Python 3.9+ compatibility

# Patterns that are explicitly allowed
ALLOWED_PATTERNS: list[str] = [
    r"^http://localhost",
    r"^https://img\.shields\.io/",
    r"^https://img\\.shields\\.io/",  # Escaped version
]

# Domain keywords that should NOT appear in ignorePatterns
# These sites should use httpHeaders with User-Agent instead
DISALLOWED_DOMAINS: list[str] = [
    "python.org",
    "semver.org",
    "opensource.org",
    "git-scm.com",
    "conventionalcommits.org",
    "contributor-covenant.org",
    "keepachangelog.com",
    "doi.org",
    "github.com",  # Should not broadly ignore GitHub
    "githubusercontent.com",
    "npmjs.com",
    "pypi.org",
    "crates.io",
    "golang.org",
    "rust-lang.org",
]


def is_allowed_pattern(pattern: str) -> bool:
    """Check if a pattern is in the allowed list."""
    pattern_normalized = pattern.strip()
    for allowed in ALLOWED_PATTERNS:
        if pattern_normalized == allowed:
            return True
    return False


def is_broad_pattern(pattern: str) -> bool:
    """Check if a pattern is too broad (matches external domains)."""
    pattern_lower = pattern.lower()

    # Check for disallowed domains
    for domain in DISALLOWED_DOMAINS:
        if domain in pattern_lower:
            return True

    # Check for overly broad wildcards
    # Patterns like ".*", "^https?://.*" are too broad
    broad_wildcards = [
        r"^https?://",  # Matches everything
        r"^http://",  # Too broad without domain
        r"^https://",  # Too broad without domain
        r".*",  # Matches everything
        r".+",  # Matches everything
    ]

    for broad in broad_wildcards:
        # Only flag if pattern is JUST the broad pattern (no domain restriction)
        if pattern_normalized := pattern.strip():
            if pattern_normalized == broad:
                return True

    return False


def check_config(config_path: str) -> tuple[bool, list[str]]:
    """
    Check the markdown-link-check config for policy violations.

    Returns:
        (is_valid, list of error messages)
    """
    errors: list[str] = []

    if not os.path.exists(config_path):
        errors.append(f"Config file not found: {config_path}")
        return False, errors

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return False, errors
    except OSError as e:
        errors.append(f"Cannot read config: {e}")
        return False, errors

    if not isinstance(config, dict):
        errors.append("Config must be a JSON object")
        return False, errors

    # Check ignorePatterns
    ignore_patterns = config.get("ignorePatterns", [])

    if not isinstance(ignore_patterns, list):
        errors.append("'ignorePatterns' must be an array")
        return False, errors

    disallowed_found: list[str] = []

    for item in ignore_patterns:
        if isinstance(item, dict):
            pattern = item.get("pattern", "")
        elif isinstance(item, str):
            pattern = item
        else:
            errors.append(f"Invalid ignorePattern entry: {item}")
            continue

        if not pattern:
            continue

        # Skip if pattern is explicitly allowed
        if is_allowed_pattern(pattern):
            continue

        # Check if pattern matches any disallowed domain
        pattern_lower = pattern.lower()
        for domain in DISALLOWED_DOMAINS:
            if domain in pattern_lower:
                disallowed_found.append(f"Pattern '{pattern}' matches disallowed domain '{domain}'")
                break
        else:
            # Check for broad wildcards
            if is_broad_pattern(pattern):
                disallowed_found.append(f"Pattern '{pattern}' is too broad")

    if disallowed_found:
        errors.append("Policy violation: ignorePatterns contains disallowed patterns")
        errors.append("")
        errors.append("Disallowed patterns found:")
        for finding in disallowed_found:
            errors.append(f"  - {finding}")
        errors.append("")
        errors.append("SOLUTION: Remove these patterns from ignorePatterns.")
        errors.append("Instead, add problematic URLs to 'httpHeaders' with a User-Agent header,")
        errors.append(
            "or add their status codes to 'aliveStatusCodes' if they legitimately block bots."
        )
        errors.append("")
        errors.append("Allowed ignorePatterns:")
        errors.append("  - ^http://localhost (local development)")
        errors.append("  - ^https://img\\.shields\\.io/ (badges only)")
        return False, errors

    return True, []


def main() -> int:
    """Main entry point."""
    # Determine config path
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Try to find repo root
        cwd = os.getcwd()
        config_path = os.path.join(cwd, ".github", "markdown-link-check-config.json")

    config_path = os.path.abspath(config_path)

    print(f"Checking ignorePatterns policy in: {config_path}")
    print()

    is_valid, errors = check_config(config_path)

    if errors:
        for error in errors:
            print(error, file=sys.stderr if not is_valid else sys.stdout)

    if is_valid:
        print("PASSED: ignorePatterns policy is compliant")
        print()
        print("Allowed patterns only:")
        print("  - localhost (for local development)")
        print("  - shields.io (for badges)")
        return 0
    else:
        print()
        print("FAILED: ignorePatterns policy violation detected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
