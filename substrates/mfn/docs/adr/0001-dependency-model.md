# ADR 0001: Dependency model

- Status: Accepted
- Canonical toolchain: `uv`
- Source of truth: `pyproject.toml` + `uv.lock`
- Local env: repo-root `.venv` only
- CI must execute through `uv run` and `uv sync --locked`.
