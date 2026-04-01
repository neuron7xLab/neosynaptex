# API Template Overrides

This directory holds Sphinx template overrides for the API documentation build.
It is referenced by `templates_path` in `docs/api/conf.py` and should only contain
static template assets or documentation-only tooling.

## Contract
- Only add Sphinx template overrides or supporting docs tooling.
- Do not introduce runtime code or behavior changes.
- Keep assets deterministic and reproducible.
- Symlinks are not supported to avoid unstable inventories.

## Contents
- `manifest.json`: Deterministic file inventory with SHA-256 hashes.
- `tools/update_manifest.py`: Updates or validates the manifest.

## How to update the manifest
```bash
python docs/api/_templates/tools/update_manifest.py
```

## How to validate the manifest
```bash
python docs/api/_templates/tools/update_manifest.py --check
```
