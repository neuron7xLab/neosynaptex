## CI Facts (PR-visible)

- **pr-gate.yml** — runs on `pull_request` (main), `merge_group`, `push` (main), `workflow_dispatch`; jobs: PR Gate / lint, PR Gate / typecheck, PR Gate / tests-fast (pytest `-m "not slow and not integration"` with JUnit + Cobertura artifacts + step summary), PR Gate / security-min (bandit, pip-audit, gitleaks).
- **ci.yml → ci-reusable.yml** — runs on `pull_request` (main, develop), `push` (main, develop), `merge_group`, `workflow_dispatch`; includes workflow lint, dependency review, config lint, lint/format, typecheck, matrix tests with coverage artifacts, security scans, secrets scan, IaC security, docs check, validation, benchmarks, scientific validation, scalability, packaging, and CI summary.
- **codeql.yml** — runs CodeQL analysis on `pull_request` (main), `push` (main), and scheduled weekly.

## Security Scanning

### Gitleaks Secret Detection

- **pr-gate.yml**: Fast PR checks with full git history (`fetch-depth: 0`)
- **ci-reusable.yml**: Comprehensive CI scan with history
- **Configuration**: `.gitleaks.toml` (project-specific rules)
- **Action version**: Pinned to SHA `0c4e38d6dd9b6d32b07f657a0b96aa4aa5e6811f` for reproducibility

### Why fetch-depth: 0?

Gitleaks scans commit diffs to detect secrets introduced in specific commits. Shallow clones (default fetch-depth: 1) only provide the latest commit, causing "unknown revision" errors when scanning ranges like `commit1^..commit2`.

### Handling False Positives

Edit `.gitleaks.toml` to allowlist:
- Scientific constants (Nernst equation values)
- Test fixtures with dummy credentials
- Example code snippets

