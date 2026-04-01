# File Excerpts

- Toolchain and dependency pins are declared in `pyproject.toml`.
- Hash-locked dependencies are tracked in `requirements-lock.txt`.
- CI enforces lock refresh via `pip-compile` + `git diff --exit-code`.
- Local `python -m build` and full `python -m pytest -q` both succeeded in this audit run.
- API contract in this repository is a Python module surface, not a marketplace HTTP API.
