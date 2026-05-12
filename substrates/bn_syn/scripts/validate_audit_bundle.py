from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_audit_bundle.py <audit_dir>")
        return 2
    audit_dir = Path(sys.argv[1])
    if not audit_dir.exists():
        print("missing_audit_dir")
        return 1

    exits = list(audit_dir.glob("*.exit"))
    for exit_file in exits:
        log_file = exit_file.with_suffix(".log")
        if not log_file.exists():
            print(f"missing_log:{exit_file.name}")
            return 1
        exit_text = exit_file.read_text(encoding="utf-8").strip()
        log_text = log_file.read_text(encoding="utf-8", errors="ignore").strip()
        if exit_text == "0" and not log_text:
            print(f"empty_log_for_success:{exit_file.name}")
            return 1
        if "coverage" in exit_file.name and exit_text == "0" and "TOTAL" not in log_text:
            print(f"invalid_coverage_log:{log_file.name}")
            return 1
        if "release_gate" in exit_file.name and "returncode" not in log_text:
            print(f"invalid_release_gate_log:{log_file.name}")
            return 1

    print("audit_bundle_valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
