# Usage Workflows

## Purpose
Golden-path operational workflows with exact commands, expected artifacts, and troubleshooting notes.

## 1) Environment setup

```bash
python -m pip install -e ".[dev]"
```

Expected outcome:
- `bnsyn` console script available.
- Sphinx + pytest tooling installed.

Troubleshooting:
- If dependency resolution fails, retry with upgraded pip: `python -m pip install --upgrade pip`.

## 2) Validate mathematical/contracts behavior

```bash
python -m pytest tests -q
```

Expected outcome:
- Exit code `0` and pytest summary.

Troubleshooting:
- If tests fail on environment-specific optional dependencies, run targeted subsets from `docs/TESTING.md`.

## 3) Run core flows

CLI discovery:
```bash
python -m bnsyn.cli --help
```

Sleep-stack example:
```bash
bnsyn sleep-stack --seed 123 --steps-wake 800 --steps-sleep 600 --out results/demo1
```

Expected artifacts:
- `results/demo1/manifest.json`
- `results/demo1/metrics.json`
- `figures/demo1/summary.png` (if plotting dependencies installed)

## 4) Generate benchmark / analysis artifacts

```bash
python -m scripts.run_benchmarks --help
python -m scripts.compare_benchmarks --help
```

Expected outcome:
- Command-specific benchmark artifacts in `benchmarks/` (see per-script pages in `docs/scripts/`).

Troubleshooting:
- If a script exits non-zero, inspect its page under `docs/scripts/` for failure modes and side effects.

## 5) Build documentation

```bash
make docs
```

Expected outcome:
- HTML output under `docs/_build/`.

Troubleshooting:
- If build fails with missing Sphinx deps, reinstall dev dependencies and retry.
- If autodoc import errors occur, ensure command is run from repository root.

## 6) Documentation verification checklist

```bash
python -m sphinx -b html docs docs/_build/html
python -m sphinx -b linkcheck docs docs/_build/linkcheck
```

Expected outputs:
- `docs/_build/html/index.html`
- `docs/_build/linkcheck/output.txt`


## 7) Repository inventory consistency

```bash
python tools/generate_inventory.py --check
```

If this fails, regenerate and stage inventory:

```bash
python tools/generate_inventory.py
git add INVENTORY.json
```
