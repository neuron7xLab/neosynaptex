# Contributing Guide

**Document Version:** 1.0.0
**Project Version:** 1.0.0
**Last Updated:** November 2025
**Minimum Coverage:** 65% (CI gate threshold)

Thank you for your interest in contributing to MLSDM Governed Cognitive Memory! This document provides comprehensive guidelines and instructions for contributors.

> **See also:** [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for a comprehensive guide to the project layout, development workflow, patterns, and debugging.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to professional engineering standards. We expect:

- **Respectful communication** in all interactions
- **Technical excellence** in contributions
- **Constructive feedback** during code reviews
- **Focus on project goals** and user needs

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git for version control
- Understanding of cognitive architectures and LLM systems (recommended)

### First Steps

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mlsdm.git
   cd mlsdm
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/neuron7xLab/mlsdm.git
   ```

## Development Setup

### Install Dependencies

The project uses `uv.lock` for reproducible dependency installation:

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from lock file for reproducibility (recommended)
pip install uv
uv sync

# Or install with requirements.txt (includes all optional dependencies)
pip install -r requirements.txt

# Or install minimal with extras as needed
pip install -e .                # Minimal install
pip install -e ".[embeddings]"  # With semantic embeddings
pip install -e ".[dev]"          # Full dev environment
```

### Verify Installation

```bash
# Install with test dependencies
pip install -e ".[test]"

# Run tests to ensure everything works
make test

# Or directly:
pytest --ignore=tests/load
```

### Development Tools

We use the following tools (all included in dev dependencies):

- **pytest**: Testing framework
- **pytest-cov**: Code coverage
- **hypothesis**: Property-based testing
- **ruff**: Linting and formatting
- **mypy**: Type checking
- **httpx**: HTTP client for testing
- **pip-tools**: Dependency locking and management

### Dependency Management

The project uses **pip-tools** to lock all transitive dependencies with cryptographic hashes for supply chain security and reproducible builds.

#### Adding Dependencies

1. Add the dependency to `pyproject.toml` in the appropriate section:
   - `[project.dependencies]` - Core runtime dependencies
   - `[project.optional-dependencies.dev]` - Development tools
   - `[project.optional-dependencies.test]` - Testing dependencies
   - Other optional groups as needed

2. Regenerate locked dependencies:
   ```bash
   make lock-deps
   ```

   This will:
   - Generate `requirements.txt` with all transitive dependencies pinned with SHA256 hashes
   - Generate `requirements-dev.txt` with dev dependencies pinned with hashes
   - Ensure reproducible builds and detect supply chain attacks

3. Commit both `pyproject.toml` and the regenerated `requirements*.txt` files:
   ```bash
   git add pyproject.toml requirements.txt requirements-dev.txt
   git commit -m "deps: add <package-name>"
   ```

#### Updating Dependencies

To update all dependencies to their latest compatible versions:

```bash
# Update uv.lock (for uv users)
make lock

# Update pip-compile lock files
make lock-deps
```

#### Why We Use Hashed Requirements

- **Supply Chain Security**: SHA256 hashes prevent package substitution attacks
- **Reproducibility**: Exact versions ensure builds are identical across environments
- **Dependency Drift Prevention**: Locks transitive dependencies that would otherwise float
- **Audit Trail**: Hash verification provides cryptographic proof of package integrity

**CI Enforcement**: The `dependency-check` workflow automatically validates that `requirements.txt` matches `pyproject.toml`. PRs will fail if dependencies are out of sync.

### Canonical Development Commands

These commands match what CI runs. **Always run these before pushing:**

```bash
# Run all tests (ignores load tests that require special setup)
make test
# Or: pytest --ignore=tests/load

# Run linter (ruff)
make lint
# Or: ruff check src tests

# Run type checker (mypy)
make type
# Or: mypy src/mlsdm

# Run security checks (CRITICAL - these are blocking gates in CI)
bandit -r src/mlsdm --severity-level high --confidence-level high
pip-audit --requirement requirements.txt --strict

# Run tests with coverage (matches CI gate)
make cov
# Or: pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing \
#     --cov-fail-under=65 --ignore=tests/load -m "not slow and not benchmark" -v

# Or use coverage script
./coverage_gate.sh

# Show all available commands
make help
```

**⚠️ Security Note:** Security checks are **BLOCKING GATES** in CI. Your PR will be blocked if security issues are found. See [docs/CI_SECURITY_GATING.md](docs/CI_SECURITY_GATING.md) for details.

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

### 3. Test Your Changes

```bash
# Run all tests
pytest tests/ src/tests/ -v

# Run with coverage
pytest --cov=src --cov-report=html tests/ src/tests/

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/
```

### 4. Commit Guidelines

We use **Conventional Commits** format for all commit messages. This enables automatic changelog generation and semantic versioning.

#### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Valid Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvements
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to build process, auxiliary tools, or libraries
- `ci`: Changes to CI configuration files and scripts
- `security` or `sec`: Security improvements

#### Commit Message Rules

1. **Description** should be lowercase (except for proper nouns like API, CI)
2. **Description** should not end with a period
3. **Description** should be at least 3 characters
4. **Scope** is optional but recommended for better organization

#### Examples

**Good commit messages:**
```
feat: add retry decorator for consistent error handling
fix(api): resolve race condition in health check endpoint
docs: update CONTRIBUTING.md with commit message format
chore(deps): upgrade pytest to 8.3.0
security: sanitize user input to prevent XSS attacks
```

**Bad commit messages:**
```
Update code                    # Missing type, too vague
feat: Add feature.            # Description ends with period
Fix: bug                      # Type should be lowercase, description too short
added new tests               # Missing type
```

#### Automated Validation

A pre-commit hook validates commit messages. Install it:

```bash
# Install pre-commit hooks
pre-commit install --hook-type commit-msg

# Test a commit message
echo "feat: test commit" | pre-commit run --hook-stage commit-msg
```

#### Generating Changelog

To generate a changelog fragment from your commits:

```bash
# Generate changelog from last tag to HEAD
make changelog

# Generate changelog from specific tag
PREV_TAG=v1.2.0 make changelog
```

The changelog will be automatically generated during releases based on conventional commits.

**Learn more:** https://www.conventionalcommits.org/

## Coding Standards

### Python Style

We follow **PEP 8** with these additions:

- **Maximum line length**: 100 characters
- **Type hints**: Required for all public functions
- **Docstrings**: Required for all public classes and functions (Google style)
- **Import order**: stdlib, third-party, local (use isort)

### Code Quality Standards

1. **Type Hints**
   ```python
   from typing import Optional, List
   import numpy as np

   def process_vector(
       vector: np.ndarray,
       threshold: float = 0.5,
       options: Optional[List[str]] = None
   ) -> dict:
       """Process vector with given threshold.

       Args:
           vector: Input vector of shape (dim,)
           threshold: Processing threshold (0.0-1.0)
           options: Optional processing options

       Returns:
           Dictionary containing processing results

       Raises:
           ValueError: If vector dimension is invalid
       """
       pass
   ```

2. **Error Handling**
   ```python
   def safe_operation(data: np.ndarray) -> np.ndarray:
       """Perform operation with proper error handling."""
       if data.size == 0:
           raise ValueError("Input data cannot be empty")

       try:
           result = complex_operation(data)
       except RuntimeError as e:
           logger.error(f"Operation failed: {e}")
           raise

       return result
   ```

3. **Docstrings** (Google Style)
   ```python
   class MoralFilter:
       """Adaptive moral filtering with homeostatic threshold.

       The filter maintains a dynamic threshold that adapts based on
       acceptance rates to achieve approximately 50% acceptance.

       Attributes:
           threshold: Current moral threshold value (0.30-0.90)
           ema: Exponential moving average of acceptance rate

       Example:
           >>> filter = MoralFilter(initial_threshold=0.5)
           >>> accepted = filter.evaluate(moral_value=0.8)
           >>> filter.adapt(accepted)
       """
       pass
   ```

### Architecture Principles

1. **Immutability**: Prefer immutable data structures where possible
2. **Single Responsibility**: Each class/function should have one clear purpose
3. **Dependency Injection**: Pass dependencies rather than creating them
4. **Interface Segregation**: Keep interfaces focused and minimal
5. **Fail Fast**: Validate inputs early and raise clear errors

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 90% for all new code
- **Critical paths**: 100% coverage required for:
  - Moral filtering logic
  - Memory management
  - Phase transitions
  - Thread-safe operations

### Test Types

1. **Unit Tests** (`src/tests/unit/`)
   - Test individual components in isolation
   - Use mocks for dependencies
   - Fast execution (< 1ms per test)

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Test end-to-end workflows
   - Moderate execution time (< 1s per test)

3. **Property-Based Tests** (`src/tests/unit/`)
   - Use Hypothesis for invariant testing
   - Test mathematical properties
   - Generate edge cases automatically

4. **Validation Tests** (`tests/validation/`)
   - Test effectiveness claims
   - Measure performance characteristics
   - Validate system behavior under load

### Writing Tests

```python
import pytest
import numpy as np
from hypothesis import given, strategies as st

class TestMoralFilter:
    """Test suite for MoralFilter component."""

    def test_basic_evaluation(self):
        """Test basic moral evaluation."""
        filter = MoralFilter(0.5)
        assert filter.evaluate(0.8) is True
        assert filter.evaluate(0.2) is False

    @given(moral_value=st.floats(0.0, 1.0))
    def test_threshold_bounds_property(self, moral_value):
        """Threshold always stays in valid range."""
        filter = MoralFilter(0.5)
        filter.evaluate(moral_value)
        filter.adapt(True)
        assert 0.30 <= filter.threshold <= 0.90

    def test_thread_safety(self):
        """Test concurrent access is safe."""
        filter = MoralFilter(0.5)
        # Thread safety test implementation
        pass
```

### Running Tests

```bash
# All tests
pytest tests/ src/tests/ -v

# Specific test file
pytest tests/integration/test_end_to_end.py -v

# Specific test function
pytest tests/integration/test_end_to_end.py::test_basic_flow -v

# With coverage
pytest --cov=src --cov-report=html tests/ src/tests/

# Property-based tests only
pytest -k property -v

# Integration tests only
pytest tests/integration/ -v
```

## Documentation Requirements

### Code Documentation

1. **Module Docstrings**: Every module needs a docstring describing its purpose
2. **Class Docstrings**: All classes need comprehensive documentation
3. **Function Docstrings**: All public functions need complete docstrings
4. **Inline Comments**: Use for complex logic only, prefer self-documenting code

### Documentation Files

When adding new features, update:

- **README.md**: If feature affects user-facing API
- **USAGE_GUIDE.md**: Add usage examples
- **ARCHITECTURE_SPEC.md**: Document architectural changes
- **IMPLEMENTATION_SUMMARY.md**: Update implementation status

### Example Documentation

See existing files for style guidelines:
- [README.md](README.md) - Feature overview
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Detailed usage
- [examples/](examples/) - Working code examples

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code coverage ≥ 90%
- [ ] Linting passes (ruff)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- Describe testing performed
- List any new tests added

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] Changes are backwards compatible (or documented)
```

### Review Process

1. **Automated Checks**: CI runs tests, linting, type checking
2. **Code Review**: Maintainer reviews code quality and design
3. **Testing**: Maintainer may test changes locally
4. **Merge**: Once approved, changes are merged to main

### Branch Protection (CICD-002)

The `main` branch has branch protection rules that require the following status checks to pass before merging. These checks cover the key workflows: `ci-neuro-cognitive-engine`, `ci-smoke`, `property-tests`, `dependency-review`, `sast-scan`.

**Required Status Checks:**

| Check Name | Workflow | Description |
|------------|----------|-------------|
| `Lint and Type Check` | `ci-neuro-cognitive-engine.yml` | Ruff linting and mypy type checking |
| `Security Vulnerability Scan` | `ci-neuro-cognitive-engine.yml` | pip-audit dependency scanning |
| `test (3.11)` | `ci-neuro-cognitive-engine.yml` | Unit tests on Python 3.11 (default PR matrix) |
| `Code Coverage Gate` | `ci-neuro-cognitive-engine.yml` | Coverage threshold + core module coverage |
| `End-to-End Tests` | `ci-neuro-cognitive-engine.yml` | E2E integration tests |
| `Effectiveness Validation` | `ci-neuro-cognitive-engine.yml` | SLO and effectiveness validation |
| `Smoke Tests` | `ci-smoke.yml` | Fast unit smoke suite |
| `Coverage Gate` | `ci-smoke.yml` | Coverage gate quick check |
| `Ablation Smoke Test` | `ci-smoke.yml` | Ablation baseline smoke checks |
| `Policy Check` | `ci-smoke.yml` | CI policy conftest validation |
| `Property-Based Invariants Tests (3.11)` | `property-tests.yml` | Property-based invariants (default matrix) |
| `Counterexamples Regression Tests` | `property-tests.yml` | Counterexample regression suite |
| `Invariant Coverage Check` | `property-tests.yml` | Invariant documentation coverage |
| `Dependency Review` | `dependency-review.yml` | Dependency diff/vulnerability review |
| `Bandit SAST Scan` | `sast-scan.yml` | Bandit static analysis |
| `Semgrep SAST Scan` | `sast-scan.yml` | Semgrep security analysis |
| `Dependency Vulnerability Scan` | `sast-scan.yml` | pip-audit vulnerability gate |
| `Secrets Scanning` | `sast-scan.yml` | Gitleaks secrets scan |

**Additional Branch Protection Settings:**

- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- ✅ Require at least 1 approval (recommended)
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require approval for workflow runs from forked repositories
- ❌ Do not allow bypassing the above settings

**Configure via GitHub CLI:**

Repository administrators can configure branch protection using the GitHub CLI:

```bash
# Enable branch protection with required status checks
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Lint and Type Check","Security Vulnerability Scan","test (3.11)","Code Coverage Gate","End-to-End Tests","Effectiveness Validation","Smoke Tests","Coverage Gate","Ablation Smoke Test","Policy Check","Property-Based Invariants Tests (3.11)","Counterexamples Regression Tests","Invariant Coverage Check","Dependency Review","Bandit SAST Scan","Semgrep SAST Scan","Dependency Vulnerability Scan","Secrets Scanning"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null

# Verify branch protection is configured
gh api repos/{owner}/{repo}/branches/main/protection
```

**Trusted PR Auto-Approval (Forks)**

To prevent trusted fork PRs from staying in `action_required`, configure the auto-approval workflow:

1. Ensure `.github/workflows/trusted-pr-auto-approve.yml` is enabled.
2. Set the repository variable `TRUSTED_PR_ACTORS` with a comma-separated list of GitHub logins to auto-approve.
3. Contributors with association `OWNER`, `MEMBER`, or `COLLABORATOR` auto-approve without manual intervention; other forks still require manual approval.

### Aphasia / NeuroLang CI Gate

Each PR that modifies NeuroLang/Aphasia-Broca components triggers a dedicated CI job (`aphasia-neurolang`) that:

- **Runs all Aphasia/NeuroLang tests**, including:
  - `tests/validation/test_aphasia_detection.py` - Core aphasia detection tests
  - `tests/eval/test_aphasia_eval_suite.py` - Evaluation suite tests
  - `tests/observability/test_aphasia_logging.py` - Logging tests
  - `tests/security/test_aphasia_*` - Security-related tests
  - `tests/packaging/test_neurolang_optional_dependency.py` - Dependency tests
  - `tests/scripts/test_*neurolang*` - NeuroLang script tests

- **Runs AphasiaEvalSuite quality gate** (`scripts/run_aphasia_eval.py --fail-on-low-metrics`) which verifies:
  - True Positive Rate (TPR) ≥ 0.8
  - True Negative Rate (TNR) ≥ 0.8
  - Mean severity for telegraphic samples ≥ 0.3

- **Blocks merge** if:
  - Any aphasia/neurolang test fails
  - Metrics fall below required thresholds

**Local Reproduction:**

To run the same checks locally before pushing:

```bash
# Install with neurolang extras
pip install '.[neurolang]'

# Run aphasia/neurolang tests
pytest tests/validation/test_aphasia_detection.py
pytest tests/eval/test_aphasia_eval_suite.py
pytest tests/observability/test_aphasia_logging.py
pytest tests/security/test_aphasia_*
pytest tests/packaging/test_neurolang_optional_dependency.py
pytest tests/scripts/test_*neurolang*

# Run quality gate
python scripts/run_aphasia_eval.py \
  --corpus tests/eval/aphasia_corpus.json \
  --fail-on-low-metrics
```

**Trigger Conditions:**

The Aphasia/NeuroLang CI job is triggered when PRs modify:
- `src/mlsdm/extensions/**` - NeuroLang extension code
- `src/mlsdm/observability/**` - Observability components
- `tests/eval/**` - Evaluation tests and data
- `tests/validation/test_aphasia_*` - Aphasia validation tests
- `tests/observability/test_aphasia_*` - Aphasia observability tests
- `tests/security/test_aphasia_*` - Aphasia security tests
- `tests/packaging/test_neurolang_optional_dependency.py` - Dependency tests
- `scripts/*neurolang*` - NeuroLang-related scripts
- `scripts/run_aphasia_eval.py` - Evaluation script

### Review Criteria

Reviewers will check:

- **Correctness**: Does code work as intended?
- **Design**: Is architecture sound?
- **Testing**: Are tests comprehensive?
- **Documentation**: Is documentation clear and complete?
- **Performance**: Are there performance implications?
- **Security**: Are there security considerations?

## Release Process

### Version Numbering

We follow **Semantic Versioning** (semver.org):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Checklist

1. Update version in all relevant files
2. Update CHANGELOG.md
3. Update documentation
4. Run full test suite
5. Create git tag
6. Build and test package
7. Publish release notes

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: See README.md and USAGE_GUIDE.md
- **Email**: Contact maintainer for sensitive issues

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Acknowledgments

Thank you for contributing to advancing neurobiologically-grounded AI systems with built-in safety and governance!

---

**Note**: This is a professional, production-ready project. We maintain high standards for code quality, testing, and documentation. Please take time to understand these guidelines before contributing.
