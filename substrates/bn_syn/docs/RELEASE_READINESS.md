# Release Readiness Protocol

This document defines the machine-readable readiness contract used by
`python -m scripts.release_readiness`.

## Single-command truth source

Generate the execution-backed readiness report (JSON + Markdown):

```bash
python -m scripts.release_readiness
```

Reports are written to:

- `artifacts/release_readiness.json`
- `artifacts/release_readiness.md`

The JSON report includes a dedicated `truth_model_version` key so downstream
consumers can detect readiness-model changes.

## Readiness states

The readiness model uses exactly three states:

- `blocked`
- `advisory`
- `ready`

Transition criteria:

- `blocked`: any blocking subsystem fails, **or** no execution-backed checks pass.
- `advisory`: every blocking subsystem passes, but at least one non-blocking advisory finding remains.
- `ready`: every subsystem passes and `ready requires at least one execution-backed check`.

Because of that rule, `READY` is impossible if execution-backed checks did not
actually run and pass.

## Subsystems

`ReadinessState` evaluates four subsystems and serializes each subsystem's real
results, including command exit codes and excerpts where applicable.

1. **static quality**
   - `ruff check .`
   - `mypy src --strict --config-file pyproject.toml`
   - `pylint src/bnsyn`
2. **runtime proof path**
   - `bnsyn run --profile canonical --plot --export-proof`
3. **bundle validation**
   - `bnsyn validate-bundle <artifact_dir>` against the readiness proof bundle
4. **governance consistency**
   - `docs/STATUS.md` uses the same `blocked` / `advisory` / `ready` vocabulary
   - `docs/RELEASE_READINESS.md` uses the same criteria
   - `quality/mutation_baseline.json` remains factual and non-trivial
   - `entropy/policy.json` and `entropy/baseline.json` remain consistent with the current repository metrics

## Advisory mode

To generate the report without failing the shell command on `blocked`:

```bash
python -m scripts.release_readiness --advisory
```

The report still records the real computed state; `--advisory` changes only the
process exit code.
