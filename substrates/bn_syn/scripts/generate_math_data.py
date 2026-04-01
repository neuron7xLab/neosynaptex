from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.math_validate import (  # noqa: E402
    AUDIT_DIR,
    MANIFEST_PATH,
    REPORT_JSON_PATH,
    REPORT_MD_PATH,
    build_manifest,
    validate_manifest,
    write_report,
)


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    checks = validate_manifest(manifest)
    exit_code = write_report(manifest, checks)
    print(f"wrote:{MANIFEST_PATH.relative_to(ROOT)}")
    print(f"wrote:{REPORT_JSON_PATH.relative_to(ROOT)}")
    print(f"wrote:{REPORT_MD_PATH.relative_to(ROOT)}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
