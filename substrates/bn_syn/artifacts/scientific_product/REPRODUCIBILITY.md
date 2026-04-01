# Reproducibility Contract

- Environment capture command: `python -V` and platform snapshot are written during atlas generation.
  - `cmd:PYTHONPATH=src python -m scripts.phase_atlas --output artifacts/scientific_product/PHASE_ATLAS.json --seed 20260218 -> log:artifacts/scientific_product/logs/phase_atlas.log`
- Seed protocol: single authoritative seed `20260218` exposed by `--seed` option.
  - `file:scripts/phase_atlas.py:L20-L23`
  - `file:scripts/phase_atlas.py:L131-L147`
- Deterministic output contract:
  - sorted JSON keys and fixed float precision are enforced.
  - output embeds `meta.code_sha`, `meta.payload_sha256`, `schema_version`, and `seed`.
  - `file:scripts/phase_atlas.py:L23-L117`
- Canonical reproduction commands:
  - install: `python -m pip install -e ".[dev,test]"`
  - run atlas (small): `PYTHONPATH=src python -m scripts.phase_atlas --output artifacts/scientific_product/PHASE_ATLAS.json --seed 20260218`
  - dt invariance checks: `python -m pytest tests/test_scientific_product_gate.py -k dt_invariance -q`
  - regression suite: `python -m pytest tests/test_scientific_product_gate.py -q`
- Regression baseline:
  - `file:artifacts/scientific_product/REGRESSION_BASELINES/phase_atlas_small.json:L1-L117`
- CI gate wiring:
  - `file:.github/workflows/scientific_product_gate.yml:L1-L53`
