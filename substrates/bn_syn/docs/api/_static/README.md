# API Static Assets

This directory holds static assets that Sphinx copies into the API documentation build
(e.g., images, CSS overrides). It is referenced by `html_static_path` in
`docs/api/conf.py` and must remain safe for deterministic builds.

## Contract
- Only place static assets or documentation-only tooling here.
- No runtime code or behavior changes may originate from this directory.
- Keep filenames deterministic and content reproducible.
- Symlinks are not supported to avoid unstable inventories.

## Contents
- `manifest.json`: Deterministic file inventory with SHA-256 hashes.
- `tools/update_manifest.py`: Updates or validates the manifest.

## How to update the manifest
```bash
python docs/api/_static/tools/update_manifest.py
```

## How to validate the manifest
```bash
python docs/api/_static/tools/update_manifest.py --check
```
