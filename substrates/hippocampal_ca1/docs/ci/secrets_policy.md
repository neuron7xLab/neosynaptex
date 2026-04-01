# Secrets Scanning Policy

All pull requests and pushes run **Gitleaks** with a minimal configuration to block accidental credential commits. Findings fail the workflow; reports are uploaded as artifacts for review.

**Local run**
```bash
gitleaks detect --config .gitleaks.toml --report-format sarif --report-path gitleaks.sarif
```

Avoid adding broad allowlists; only essential binary/test fixture paths are ignored in `.gitleaks.toml`.
