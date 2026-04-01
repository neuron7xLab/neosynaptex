# Proof: Environment

Use these commands to capture deterministic local environment facts:

```bash
python --version
python -m pip --version
python -m pytest --version
```

Expected:
- Python major/minor compatible with `pyproject.toml` (`>=3.11`).
- pip available via `python -m pip`.
- pytest available after `make setup`.
