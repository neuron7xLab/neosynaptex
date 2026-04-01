# Release Checklist

- [x] Build release artifacts with `python -m build`.
- [x] Record SHA-256 for release artifacts.
- [x] Verify recorded hashes with `sha256sum -c`.
- [x] Provide rollback note: reinstall previous known-good wheel from artifact store.
