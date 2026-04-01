"""Architecture ledger tests — verify structural integrity.

Ensures import boundaries, public API stability, and no uncontrolled drift.
"""

from __future__ import annotations

import json
from pathlib import Path


class TestArchitectureLedger:
    """Verify architecture ledger is consistent with codebase."""

    def _load_ledger(self) -> dict:
        path = Path("artifacts/architecture_ledger.json")
        if not path.exists():
            import subprocess

            subprocess.run(
                [".venv/bin/python", "scripts/generate_architecture_ledger.py"],
                check=True,
                capture_output=True,
            )
        return json.loads(path.read_text())

    def test_ledger_has_schema_version(self) -> None:
        ledger = self._load_ledger()
        assert ledger["schema_version"] == "mfn-architecture-ledger-v1"

    def test_public_api_not_empty(self) -> None:
        ledger = self._load_ledger()
        assert len(ledger["public_api"]) >= 4, "Public API too small"

    def test_no_unexpected_external_deps_in_core(self) -> None:
        """Core modules should not import transport/data deps."""
        ledger = self._load_ledger()
        forbidden_in_core = {"fastapi", "pandas", "pyarrow", "websockets", "httpx"}
        for mod in ledger["modules"]:
            if ".core." in mod["module"] and "compat" not in mod["module"]:
                ext = set(mod["imports_external"])
                violations = ext & forbidden_in_core
                assert not violations, f"{mod['module']} imports forbidden deps: {violations}"

    def test_frozen_modules_identified(self) -> None:
        ledger = self._load_ledger()
        assert ledger["frozen_symbols"] > 0, "No frozen symbols found"

    def test_module_count_reasonable(self) -> None:
        ledger = self._load_ledger()
        assert 50 <= ledger["total_modules"] <= 200
