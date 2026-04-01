# BN-Syn Operational Runbook

## Install
- `python -m pip install -e ".[dev,test]"`

## Quickstart
- `bnsyn demo --steps 100 --seed 42 --N 64`
- `bnsyn smoke --out artifacts/operational_readiness/SMOKE_REPORT.json`

## Reproducibility
- Fix all seeds in CLI/API configs.
- Persist JSON artifacts with sorted keys and explicit schema versions.

## Troubleshooting
- If `bnsyn` is missing, reinstall editable package.
- If smoke status is FAIL, inspect `artifacts/operational_readiness/SMOKE_REPORT.json` checks.

## Artifacts layout
- `artifacts/scientific_product/*`: scientific outputs.
- `artifacts/context_compressor/*`: context/SSOT evidence.
- `artifacts/operational_readiness/*`: smoke + environment + SBOM.
