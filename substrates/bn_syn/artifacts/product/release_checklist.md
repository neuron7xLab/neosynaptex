# Release Checklist

- [ ] `python -m pip install -e ".[test]"`
- [ ] `make quickstart-smoke`
- [ ] `python -m pytest -m "not validation" -q`
- [ ] `python -m build`
- [ ] Verify happy-path JSON artifact generated.
- [ ] Verify risk register has no open P0 items.
- [ ] Attach evidence logs to release notes.
- [ ] Tag release.

## Rollback Procedure
1. `git revert <release-commit>` or rollback tag pointer.
2. Reinstall previous package build.
3. Re-run quickstart smoke to confirm restored behavior.
