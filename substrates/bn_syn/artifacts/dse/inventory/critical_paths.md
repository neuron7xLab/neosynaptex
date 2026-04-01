# Critical Paths

1. Environment setup: `make setup`.
2. Runtime proof path: `make demo` / `bnsyn demo ...`.
3. PR correctness path: `python -m pytest -m "not validation" -q`.
4. Quality path: `ruff check .`, `pylint src/bnsyn`, `mypy src --strict --config-file pyproject.toml`.
5. Packaging path: `python -m build`.
