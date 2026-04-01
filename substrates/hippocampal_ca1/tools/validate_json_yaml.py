#!/usr/bin/env python3
"""
JSON/YAML Validation Tool

Validates all JSON and YAML files in the repository for correct syntax.
Additionally validates GitHub Issue Form files for required structure.

This script uses only Python standard library for JSON.
For YAML, it attempts to use PyYAML if available, otherwise skips YAML validation.

Exit codes:
  0 - All files valid
  1 - Validation errors found

Usage:
  python tools/validate_json_yaml.py [path]

  If path is not provided, scans the current directory.
"""

import json
import os
import subprocess
import sys

# Type hints: Using built-in generics for Python 3.9+ compatibility

# Try to import PyYAML
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def get_git_tracked_files(repo_path: str) -> list[str]:
    """Get list of git-tracked files in the repository."""
    try:
        result = subprocess.run(
            ["git", "ls-files"], cwd=repo_path, capture_output=True, text=True, check=True
        )
        stdout = result.stdout.strip()
        if not stdout:
            return []
        return [os.path.join(repo_path, f) for f in stdout.split("\n") if f]
    except subprocess.CalledProcessError:
        # Fallback: walk directory
        files = []
        for root, _, filenames in os.walk(repo_path):
            if ".git" in root:
                continue
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files


def validate_json_file(filepath: str) -> list[str]:
    """Validate a JSON file. Returns list of error messages."""
    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: line {e.lineno}, column {e.colno}: {e.msg}")
    except OSError as e:
        errors.append(f"Cannot read file: {e}")
    return errors


def validate_yaml_file(filepath: str) -> list[str]:
    """Validate a YAML file. Returns list of error messages."""
    if not YAML_AVAILABLE:
        return []  # Skip if PyYAML not available

    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            # Use safe_load to avoid code execution
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
    except OSError as e:
        errors.append(f"Cannot read file: {e}")
    return errors


def validate_issue_form(filepath: str, content: dict) -> list[str]:
    """
    Validate GitHub Issue Form file structure.
    Must contain 'name', 'description', and 'body' list.
    """
    errors = []

    if not isinstance(content, dict):
        errors.append("Issue form must be a YAML mapping (dictionary)")
        return errors

    # Required top-level fields
    if "name" not in content:
        errors.append("Missing required field: 'name'")
    elif not isinstance(content["name"], str) or not content["name"].strip():
        errors.append("Field 'name' must be a non-empty string")

    if "description" not in content:
        errors.append("Missing required field: 'description'")
    elif not isinstance(content["description"], str) or not content["description"].strip():
        errors.append("Field 'description' must be a non-empty string")

    if "body" not in content:
        errors.append("Missing required field: 'body'")
    elif not isinstance(content["body"], list):
        errors.append("Field 'body' must be a list")
    elif len(content["body"]) == 0:
        errors.append("Field 'body' must contain at least one element")

    return errors


def validate_yaml_with_structure(filepath: str, repo_path: str) -> list[str]:
    """Validate YAML file and check Issue Form structure if applicable."""
    if not YAML_AVAILABLE:
        return []

    errors = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
        return errors
    except OSError as e:
        errors.append(f"Cannot read file: {e}")
        return errors

    # Check if this is an Issue Form file
    rel_path = os.path.relpath(filepath, repo_path)
    if rel_path.startswith(".github/ISSUE_TEMPLATE/") and rel_path.endswith(".yml"):
        # Skip config.yml which is not an issue form
        basename = os.path.basename(filepath)
        if basename != "config.yml":
            form_errors = validate_issue_form(filepath, content)
            errors.extend(form_errors)

    return errors


def main() -> int:
    """Main entry point."""
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo_path = os.path.abspath(repo_path)

    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory", file=sys.stderr)
        return 1

    print(f"Validating JSON and YAML files in {repo_path}...")
    if not YAML_AVAILABLE:
        print("Warning: PyYAML not installed. YAML validation will be skipped.")
    print()

    files = get_git_tracked_files(repo_path)

    json_files = [f for f in files if f.endswith(".json")]
    yaml_files = [f for f in files if f.endswith(".yml") or f.endswith(".yaml")]

    total_errors = 0
    files_with_errors = 0

    # Validate JSON files
    for filepath in sorted(json_files):
        errors = validate_json_file(filepath)
        if errors:
            files_with_errors += 1
            rel_path = os.path.relpath(filepath, repo_path)
            for error in errors:
                print(f"{rel_path}: {error}")
                total_errors += 1

    # Validate YAML files
    for filepath in sorted(yaml_files):
        errors = validate_yaml_with_structure(filepath, repo_path)
        if errors:
            files_with_errors += 1
            rel_path = os.path.relpath(filepath, repo_path)
            for error in errors:
                print(f"{rel_path}: {error}")
                total_errors += 1

    print()
    print(f"Validated {len(json_files)} JSON files and {len(yaml_files)} YAML files")

    if total_errors > 0:
        print(f"FAILED: Found {total_errors} error(s) in {files_with_errors} file(s)")
        return 1
    else:
        print("PASSED: All JSON and YAML files are valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
