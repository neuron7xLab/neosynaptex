"""Generate sbom."""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "release"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    packages = []
    for dist in sorted(md.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        version = dist.version
        packages.append(
            {
                "name": name,
                "version": version,
                "license": dist.metadata.get("License"),
                "summary": dist.metadata.get("Summary"),
            }
        )
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "name": "Morphology-aware Field Intelligence Engine SBOM",
        "documentNamespace": "https://example.invalid/spdx/mfn-sbom",
        "packages": packages,
    }
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    path = OUT / "sbom.spdx.json"
    path.write_text(text, encoding="utf-8")
    (OUT / "sbom.sha256").write_text(
        hashlib.sha256(text.encode("utf-8")).hexdigest() + "\n", encoding="utf-8"
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
