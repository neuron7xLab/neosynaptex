# Environment Matrix

| Dimension | Value |
|---|---|
| OS | Linux (containerized runner) |
| Python | 3.12 runtime with project requirement >=3.11 |
| Virtual env | `.venv_lpro` |
| Package install mode | Editable (`pip install -e '.[dev]'`) |
| Determinism controls | pinned dependencies in `pyproject.toml`; Hypothesis `derandomize = true` |
