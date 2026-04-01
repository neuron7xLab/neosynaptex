# Gitleaks Security Scanning Policy

## Overview

This repository uses [Gitleaks](https://github.com/gitleaks/gitleaks) to detect hardcoded secrets in the codebase. Secret scanning is enforced via GitHub Actions CI and runs on every push and pull request.

## What Is Scanned

The CI workflow (`ci-pr.yml`) runs **two** gitleaks scans:

1. **Repository Scan**: Scans all files in all commits in the repository
2. **PR Diff Scan**: Scans only the changes between the PR base and head commits

Both scans pass for the CI job to succeed. If either scan detects secrets, the job fails.

## Configuration

The gitleaks configuration is defined in `.gitleaks.toml` at the repository root.

### Allowlist Policy

The configuration includes a **strict, path-scoped allowlist** for known false positives:

| Pattern | Scope | Reason |
|---------|-------|--------|
| `bibkey:\s+[a-z]+\d{4}[a-z]+` | `bibliography/mapping.yml`, `claims/claims.yml` | Bibliography reference keys (e.g., `bibkey: axelrod1981cooperation`) trigger the `generic-api-key` rule but are not secrets |

### What Is NOT Allowlisted

- **No files outside the bibliography/claims YAML files**
- **No patterns other than `bibkey:` fields**
- **No SHA256 hashes in `bibliography/sources.lock`** (these don't trigger false positives)
- **No broad regex patterns or rule disabling**

## Invariants

1. **Scans remain enabled**: Both repo and PR diff scans run on every CI trigger
2. **Fail-gate is active**: CI fails if any scan finds secrets not covered by the allowlist
3. **Allowlist is minimal**: Only the specific `bibkey:` pattern in specific files is allowlisted
4. **Real secrets fail CI**: Any actual secret (API keys, passwords, tokens) will be detected and fail CI

## If Gitleaks Detects a Secret

If gitleaks detects a real secret:

1. **Do NOT merge the PR**
2. **Remove the secret** from the codebase
3. **Rotate the secret** immediately (assume it's compromised)
4. **Consider history cleanup** if the secret was committed (contact repo maintainers)
5. **Document the incident** in `docs/AUDIT_FINDINGS.md`

## Local Testing

Local secret scanning is reproducible without preinstalled gitleaks.

```bash
# Bootstraps pinned gitleaks v8.24.3 into .tools/gitleaks/ and runs scan
make security

# Invoke bootstrapper directly with custom args if needed
python -m scripts.ensure_gitleaks -- detect --config .gitleaks.toml --log-opts="origin/main..HEAD" --verbose
```

`python -m scripts.ensure_gitleaks` verifies the SHA256 checksum of the downloaded release archive before extracting the binary.

## References

- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [Gitleaks Configuration Reference](https://github.com/gitleaks/gitleaks)
- [Repository Audit Findings](AUDIT_FINDINGS.md)
