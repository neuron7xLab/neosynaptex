#!/usr/bin/env python3
"""
Wrapper to validate JSON/YAML configs and GitHub Issue Forms.

Delegates to the existing tooling in tools/validate_json_yaml.py to keep behavior
consistent across local and CI runs.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from tools import validate_json_yaml
except ImportError as exc:  # pragma: no cover - import failure should surface in CI
    print(f"Failed to import validator: {exc}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    sys.exit(validate_json_yaml.main())
