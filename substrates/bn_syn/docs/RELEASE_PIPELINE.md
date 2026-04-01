# Release Pipeline

Deterministic release pipeline stages:

1. changelog contract check
2. version bump automation
3. artifact build
4. publish dry-run

## Local dry-run

```bash
python -m scripts.release_pipeline --verify-only
python -m scripts.release_pipeline
```

## Version bump flow

```bash
python -m scripts.release_pipeline --bump patch --apply-version-bump --verify-only
```

After bump, ensure `CHANGELOG.md` has a matching section header `## [X.Y.Z]`.

## CI workflow

Workflow file: `.github/workflows/release-pipeline.yml`

Manual dispatch inputs:

- `bump`: `patch|minor|major`
- `apply-version-bump`: whether to modify `pyproject.toml` in workflow workspace

The pipeline always performs build + dry-run publish validation.
