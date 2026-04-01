# Additional Audit (2026)

## Environment
- Repository: /workspace/bnsyn-phase-controlled-emergent-dynamics
- Python: 3.12.12

## Commands Executed

### Dependency install
```
pip install -e ".[dev,test]"
```

### SSOT validators
```
python -m scripts.validate_bibliography
python -m scripts.validate_claims
python -m scripts.scan_normative_tags
python -m scripts.scan_governed_docs
```

### Smoke tests (non-validation)
```
pytest -m "not validation"
```

## Results

### validate_bibliography.py
```
OK: bibliography SSOT validated.
  Bibkeys: 31
  Mapping entries: 26
  Claim IDs: 26
  Lock entries: 31
```

### validate_claims.py
```
[claims-gate] OK: 26 claims validated; 22 normative.
```

### scan_normative_tags.py
```
OK: normative tag scan passed.
```

### scan_governed_docs.py
```
[governed-docs] Governed docs listed: 32
[governed-docs] Files scanned: 32
[governed-docs] Normative lines: 5
[governed-docs] Orphan normative lines: 0
[governed-docs] Missing governed files: 0
[governed-docs] OK: governed docs have no orphan normative statements.
```

### pytest -m "not validation"
```
377 passed, 4 skipped, 98 deselected, 2 warnings in 84.78s (0:01:24)

Warnings:
- tests/test_cli_interactive.py::test_cli_module_main_executes
  <frozen runpy>:128: RuntimeWarning: 'bnsyn.cli' found in sys.modules after import of package 'bnsyn', but prior to execution of 'bnsyn.cli'; this may result in unpredictable behaviour
- tests/test_coverage_gap_extensions.py::test_viz_interactive_optional_dependency_errors
  <frozen runpy>:128: RuntimeWarning: 'bnsyn.viz.interactive' found in sys.modules after import of package 'bnsyn.viz', but prior to execution of 'bnsyn.viz.interactive'; this may result in unpredictable behaviour
```
