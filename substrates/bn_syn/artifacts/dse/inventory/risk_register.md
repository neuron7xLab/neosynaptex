# Risk Register

| Risk | Impact | Likelihood | Detection | Mitigation | Owner |
|---|---:|---:|---|---|---|
| Setup drift omits lint/build dependencies | High | Medium | `make setup` + `pylint`/`python -m build` logs | Keep setup default on `.[dev,test]` | Maintainers |
| Missing optional benchmark deps in ad-hoc envs | Medium | Medium | test collection logs | standardize on `make setup` | Maintainers |
| Toolchain version drift | Medium | Low | pip check + pinned versions in pyproject | keep pinned optional deps | Maintainers |
