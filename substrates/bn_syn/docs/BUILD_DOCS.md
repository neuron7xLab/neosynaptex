# Building Documentation Locally

## Canonical setup

```bash
python -m pip install -e ".[test,docs]"
```

## Build HTML docs

```bash
make docs
```

Expected output:

- `docs/_build/html/index.html`

The docs toolchain is pinned through the `docs` optional dependency group in `pyproject.toml`.
