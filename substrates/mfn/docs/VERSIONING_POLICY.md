# Versioning Policy

MyceliumFractalNet follows [Semantic Versioning 2.0.0](https://semver.org/).

## Version Format

`{MAJOR}.{MINOR}.{PATCH}`

## What Constitutes a Breaking Change

### SDK (Python API)

| Change | Breaking? |
|--------|-----------|
| Remove symbol from `__all__` | Yes — major version |
| Change function signature (remove parameter) | Yes — major version |
| Change return type | Yes — major version |
| Add new optional parameter | No — minor version |
| Add new function/class | No — minor version |
| Fix bug (changes output for invalid input) | No — patch version |

### CLI

| Change | Breaking? |
|--------|-----------|
| Remove subcommand | Yes — major version |
| Remove flag | Yes — major version |
| Add new subcommand or flag | No — minor version |
| Change default output format | Yes — major version |

### REST API

| Change | Breaking? |
|--------|-----------|
| Remove endpoint | Yes — major version |
| Remove response field | Yes — major version |
| Add new endpoint | No — minor version |
| Add new optional request field | No — minor version |
| Add new response field | No — minor version |

### Artifacts

| Change | Breaking? |
|--------|-----------|
| Change `causal_validation.json` schema | Yes — major version |
| Change report structure | Yes — major version |
| Add new artifact to bundle | No — minor version |
| Change artifact naming convention | Yes — major version |

### Scientific

| Change | Breaking? |
|--------|-----------|
| Change detection thresholds | Minor + `scientific-impacting` label |
| Change causal rule semantics | Minor + `scientific-impacting` label |
| Change biophysical constants | Minor + `scientific-impacting` label |
| Add new causal rule | No — minor version |

## Release Naming

- `v4.1.0` — stable release
- `v4.1.0-rc1` — release candidate
- `v4.1.1` — patch (bug fix only)
- `v4.2.0` — minor (new features, backward-compatible)
- `v5.0.0` — major (breaking changes, deprecated removals)
