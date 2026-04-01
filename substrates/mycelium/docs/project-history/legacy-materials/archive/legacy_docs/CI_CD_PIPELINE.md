# CI/CD Pipeline Overview — MyceliumFractalNet v4.1

This document describes the automated delivery pipeline that validates security, correctness, and performance for MyceliumFractalNet. The pipeline is implemented in `.github/workflows/ci.yml` and runs on every pull request and on pushes to `main` and `develop`.

## Pipeline stages

1. **Dependency review (PR only)**
   - Validates new dependencies for known risk levels using GitHub’s dependency review action.
   - Fails the build when high-severity issues are detected.

2. **Linting & type checks**
   - Runs `ruff` and `mypy` to enforce formatting, static analysis, and type safety.

3. **Security checks (SAST + dependency audit)**
   - Runs `bandit` for Python static analysis.
   - Runs `pip-audit` for dependency vulnerability checks.

4. **IaC security checks**
   - Runs `checkov` against Terraform and Kubernetes manifests to detect misconfigurations.

5. **Secrets scanning**
   - Runs `gitleaks` to detect credential leaks and high-entropy secrets in the repo history and working tree.

6. **Test matrix**
   - Executes pytest across Python 3.10, 3.11, and 3.12.
   - Generates coverage reports for Codecov.

7. **Validation & benchmarks**
   - Executes scientific validation, scalability tests, and performance benchmarks to keep regression risk low.

8. **Packaging sanity checks**
   - Builds wheels/sdists and validates that all runtime packages import correctly in a clean virtual environment.

## Local execution

Recommended local checks before submitting a PR:

```bash
pip install -e ".[dev]"
ruff check .
mypy src/mycelium_fractal_net
pytest -v --tb=short
```

For security checks:

```bash
pip install bandit pip-audit
bandit -r src/ -ll -ii --exclude tests
pip-audit -r requirements.txt --strict --desc on
```

For IaC security checks:

```bash
pip install checkov
checkov -d infra/terraform
checkov -f k8s.yaml -f infra/gitops/argocd-application.yaml
```

## Release hygiene

- Keep dependency updates automated via Dependabot (`.github/dependabot.yml`).
- Ensure that production deploys use the Kubernetes manifests in `k8s.yaml` and follow `docs/DEPLOYMENT_GUIDE.md`.
