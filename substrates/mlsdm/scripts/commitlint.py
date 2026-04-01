#!/usr/bin/env python3
"""Validate commit messages follow Conventional Commits format.

This script is used as a commit-msg hook to validate that commit messages
follow the Conventional Commits specification.

Format:
    <type>[optional scope]: <description>

    [optional body]

    [optional footer(s)]

Types:
    - feat: A new feature
    - fix: A bug fix
    - docs: Documentation only changes
    - style: Code style changes (formatting, missing semicolons, etc)
    - refactor: Code change that neither fixes a bug nor adds a feature
    - perf: Performance improvements
    - test: Adding missing tests or correcting existing tests
    - chore: Changes to build process, auxiliary tools, or libraries
    - ci: Changes to CI configuration files and scripts
    - security: Security improvements

Examples:
    feat: add retry decorator for consistent error handling
    fix(api): resolve race condition in health check
    docs: update CONTRIBUTING.md with commit message format
    chore(deps): upgrade pytest to 8.3.0

Exit codes:
    0: Commit message is valid
    1: Commit message is invalid
"""

import re
import sys
from pathlib import Path

# Conventional Commits types
VALID_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "chore",
    "ci",
    "security",
    "sec",  # Alias for security
]

# Pattern for conventional commit format
# Format: <type>[optional scope]: <description>
COMMIT_PATTERN = re.compile(
    r"^(?P<type>" + "|".join(VALID_TYPES) + r")"
    r"(?:\((?P<scope>[a-z0-9-]+)\))?"
    r": "
    r"(?P<description>.+)$",
    re.IGNORECASE,
)

# Special commit patterns that should be allowed
SPECIAL_PATTERNS = [
    re.compile(r"^Merge "),  # Merge commits
    re.compile(r"^Revert "),  # Revert commits
    re.compile(r"^Initial commit"),  # Initial commit
    re.compile(r"^WIP:"),  # Work in progress (should be squashed before merge)
]


def validate_commit_message(message: str) -> tuple[bool, str]:
    """Validate a commit message follows Conventional Commits format.

    Args:
        message: The commit message to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get the first line (subject line)
    lines = message.strip().split("\n")
    subject = lines[0].strip()

    if not subject:
        return False, "Commit message is empty"

    # Allow special commit patterns
    for pattern in SPECIAL_PATTERNS:
        if pattern.match(subject):
            return True, ""

    # Validate against conventional commit pattern
    match = COMMIT_PATTERN.match(subject)
    if not match:
        types_str = ", ".join(VALID_TYPES)
        return (
            False,
            f"""Commit message does not follow Conventional Commits format.

Expected format:
    <type>[optional scope]: <description>

Valid types:
    {types_str}

Examples:
    feat: add retry decorator for consistent error handling
    fix(api): resolve race condition in health check
    docs: update CONTRIBUTING.md with commit message format

Your message:
    {subject}

See: https://www.conventionalcommits.org/
""",
        )

    # Additional validation rules
    description = match.group("description")

    # Description should not be empty
    if not description or description.isspace():
        return False, "Commit description cannot be empty"

    # Description should not end with a period
    if description.endswith("."):
        return False, "Commit description should not end with a period"

    # Description should not be too short
    if len(description) < 3:
        return False, "Commit description is too short (minimum 3 characters)"

    # Description should start with lowercase (except for proper nouns)
    if description[0].isupper() and description.split()[0] not in ["API", "CI", "CD"]:
        return (
            False,
            f"Commit description should start with lowercase: '{description[0].lower()}{description[1:]}'",
        )

    return True, ""


def main() -> int:
    """Main entry point for commit message validation.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) < 2:
        print("Error: Missing commit message file argument", file=sys.stderr)
        print("Usage: commitlint.py <commit-msg-file>", file=sys.stderr)
        return 1

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Error: Commit message file not found: {commit_msg_file}", file=sys.stderr)
        return 1

    # Read commit message
    message = commit_msg_file.read_text(encoding="utf-8")

    # Validate
    is_valid, error = validate_commit_message(message)

    if not is_valid:
        print("❌ Invalid commit message:", file=sys.stderr)
        print("", file=sys.stderr)
        print(error, file=sys.stderr)
        return 1

    # Success - no output needed
    return 0


if __name__ == "__main__":
    sys.exit(main())
