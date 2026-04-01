# MLSDM Policy-as-Code

This directory contains policy rules that enforce governance, security, and configuration
standards across the repository. These policies are checked in CI to ensure consistent
compliance.

## Framework

- **OPA/Rego**: Open Policy Agent policies for declarative policy enforcement
- **Conftest**: CLI tool to run OPA policies against configuration files

## Policy Categories

### CI Workflow Policies (`ci/`)
- Workflow permission restrictions (no `write-all`)
- Action version pinning for third-party actions
- Protection against secret exposure in logs

## Usage

### Running Policy Checks Locally

```bash
# Install conftest (if not installed)
brew install conftest  # macOS
# or
curl -L https://github.com/open-policy-agent/conftest/releases/download/v0.55.0/conftest_0.55.0_Linux_x86_64.tar.gz | tar xzf -

# Check CI workflows
conftest test .github/workflows/*.yml -p policies/ci/

# Check all policies
conftest test -p policies/ .github/workflows/*.yml config/*.yaml
```

### In CI

Policy checks are integrated into the CI workflow and run automatically on PRs.
The CI uses `--fail-on-warn=false` to allow warnings but fail on deny rules.

## Adding New Policies

1. Create a new `.rego` file in the appropriate subdirectory
2. Add tests for the policy in a `*_test.rego` file
3. Update this README with a description of the new policy
4. Run `conftest test` to validate the policies

## Policy Reference

### ci/workflows.rego

**Deny Rules (will fail CI):**

| Policy | Description | STRIDE Category |
|--------|-------------|-----------------|
| Block `write-all` permissions | Prevents workflows/jobs with overly permissive access | Elevation of Privilege |
| Block unpinned third-party actions | Requires `@` version pin on non-github/actions actions | Tampering |
| Block mutable references (@main, @master) | Prevents third-party actions with mutable refs | Tampering |
| Block secret exposure in logs | Flags `echo ${{ secrets.* }}` patterns | Information Disclosure |

**Warn Rules (will warn but not fail CI):**

| Policy | Description | STRIDE Category |
|--------|-------------|-----------------|
| Missing job timeouts | Warns if `timeout-minutes` not set | Denial of Service |
| Mutable action references | Warns about `@main`/`@master` in any action | Tampering |

## Maintenance

Policies should be reviewed and updated:
- When new CI workflows are added
- When security requirements change
- After security incidents or audits
- Quarterly as part of threat model review
