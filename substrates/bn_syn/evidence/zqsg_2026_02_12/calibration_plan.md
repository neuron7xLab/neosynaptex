# Calibration Plan

- Budget: PR-blocking no-escape contracts job timeout = 12 minutes.
- Determinism: 3-run SHA256 stability for `tests_inventory.json` and `INVENTORY.json`.
- Flake policy: fail-closed for contract tests.
- Supply-chain: all external `uses:` entries SHA pinned.
- Evidence: command log, pip version, pytest log, reproducibility report, sha256 manifest.
