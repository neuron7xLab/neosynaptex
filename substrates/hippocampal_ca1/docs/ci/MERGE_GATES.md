# Merge Gates Documentation

This document describes the security and quality gates that run on every PR.

## Gates Overview

| Gate | Workflow | Purpose | How to Run Locally |
|------|----------|---------|-------------------|
| Unicode Lint | `unicode-lint.yml` | Detects Trojan Source attacks (CVE-2021-42574) | `python tools/unicode_lint.py .` |
| Actionlint | `actionlint.yml` | Validates GitHub Actions workflow syntax | `actionlint .github/workflows/*.yml` |
| Config Validation | `validate-configs.yml` | Validates JSON/YAML syntax and Issue Forms | `python tools/validate_json_yaml.py .` |
| Secret Scanning | `gitleaks.yml` | Detects accidentally committed secrets | `gitleaks detect --config .gitleaks.toml` |
| Dependency Audit | `dependency-audit.yml` | Scans Python dependencies for vulnerabilities | `pip-audit -r requirements.txt` |
| Link Check | `docs-link-check.yml` | Validates markdown links are not broken | `markdown-link-check <file> --config .github/markdown-link-check-config.json` |
| ignorePatterns Policy | `docs-link-check.yml` | Prevents hiding broken links with broad ignores | `python tools/no_broad_ignorepatterns.py` |
| Phase Validation | `phase-validation.yml` | Ensures PRs follow the phase workflow | (Runs on PR description) |

## Detailed Gate Descriptions

### Unicode Lint (Trojan Source Detection)

**File**: `.github/workflows/unicode-lint.yml`
**Tool**: `tools/unicode_lint.py`

Scans all source files for dangerous Unicode characters that could be used in Trojan Source attacks:

- **Bidirectional controls**: U+061C, U+200E/F, U+202A–U+202E, U+2066–U+2069
- **Zero-width characters**: U+200B/C/D, U+FEFF
- **Control characters**: U+0000–U+001F (except normal whitespace), U+007F

**Why it matters**: CVE-2021-42574 demonstrated how these characters can hide malicious code in source files that appears benign to reviewers but executes differently.

```bash
# Run locally
python tools/unicode_lint.py .
```

### Actionlint

**File**: `.github/workflows/actionlint.yml`
**Tool**: [actionlint](https://github.com/rhysd/actionlint) v1.7.9

Validates GitHub Actions workflow syntax to catch errors before CI runs.

```bash
# Run locally (download binary first)
curl -sL "https://github.com/rhysd/actionlint/releases/download/v1.7.9/actionlint_1.7.9_linux_amd64.tar.gz" | tar xz -C /tmp
/tmp/actionlint .github/workflows/*.yml
```

### Config Validation

**File**: `.github/workflows/validate-configs.yml`
**Tool**: `tools/validate_json_yaml.py`

Validates:
- All `*.json` files parse correctly
- All `*.yml` and `*.yaml` files parse correctly
- Issue Form files under `.github/ISSUE_TEMPLATE/` contain required fields (`name`, `description`, `body`)

```bash
# Run locally
pip install PyYAML
python tools/validate_json_yaml.py .
```

### Secret Scanning (Gitleaks)

**File**: `.github/workflows/gitleaks.yml`
**Config**: `.gitleaks.toml`
**Tool**: [gitleaks](https://github.com/gitleaks/gitleaks)

Scans for accidentally committed secrets like API keys, passwords, and tokens.

```bash
# Run locally
gitleaks detect --config .gitleaks.toml --source .
```

### Dependency Audit

**File**: `.github/workflows/dependency-audit.yml`
**Tool**: [pip-audit](https://github.com/pypa/pip-audit) v2.7.3

Scans Python dependencies for known vulnerabilities.

```bash
# Run locally
pip install pip-audit==2.7.3
pip-audit -r requirements.txt
pip-audit -r requirements-dev.txt
```

**Note**: This replaces GitHub's `actions/dependency-review-action` which requires Dependency Graph to be enabled in repository settings.

### Markdown Link Check

**File**: `.github/workflows/docs-link-check.yml`
**Config**: `.github/markdown-link-check-config.json`

Validates all links in markdown files are not broken.

```bash
# Run locally
npm install -g markdown-link-check
markdown-link-check README.md --config .github/markdown-link-check-config.json
```

### ignorePatterns Policy

**Tool**: `tools/no_broad_ignorepatterns.py`

Prevents hiding broken links by using overly broad ignore patterns. Only allows:
- `localhost` (for local development)
- `shields.io` (for badges)

Sites that block bots are handled via `httpHeaders` with a User-Agent, not by ignoring them.

```bash
# Run locally
python tools/no_broad_ignorepatterns.py
```

## CODEOWNERS

The following paths require review from designated owners:

```
.github/workflows/*              @neuron7x
tools/*                          @neuron7x
SECURITY.md                      @neuron7x
.gitleaks.toml                   @neuron7x
.github/markdown-link-check-config.json  @neuron7x
```

## Evidence and Audit Trail

Scan evidence is committed to `docs/ci/`:
- `unicode_scan_pr6.txt` - Unicode lint output
- `unicode_sanitization.md` - Unicode check documentation
- `linkcheck_before.txt` / `linkcheck_after.txt` - Link check snapshots

---

*Phase: 7.3 Security & Stability*
