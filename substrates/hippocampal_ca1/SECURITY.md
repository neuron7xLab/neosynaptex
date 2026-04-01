# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | ✅ Yes    |
| 1.x.x   | ❌ No     |

## Reporting a Vulnerability

**DO NOT** open public issues for security vulnerabilities.

Instead, use one of the following methods:

1. **Preferred**: If this repository has GitHub Security Advisories enabled, use the
   "Report a vulnerability" button on the Security tab to submit a private report.
2. **Fallback**: Open a GitHub issue WITHOUT any vulnerability details, stating only
   that you have a security concern and requesting a private communication channel.

**Note**: A dedicated security email/contact is TBD. Until then, use the methods above.

When reporting, include (privately):
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

Expected response time: **48 hours**

## Secrets Policy

**⚠️ IMPORTANT: Never share credentials in public channels**

1. **Do NOT paste credentials, API keys, or tokens in issues or pull requests.**
2. **Do NOT commit secrets to the repository** - use environment variables instead.
3. If you accidentally expose a secret:
   - Immediately revoke/rotate the compromised credential
   - Report it privately using the methods above
   - Do NOT try to "hide" it with a force push (it's already in git history)

All commits are scanned with [gitleaks](https://github.com/gitleaks/gitleaks) to detect
accidentally committed secrets before they reach the main branch.

## Security Measures

### Code Security

- **No hardcoded secrets**: All sensitive data in environment variables
- **Input validation**: All user inputs are validated
- **Dependency scanning**: Automated checks with Dependabot
- **Type safety**: Full type hints enforce correctness

### Data Security

- **No external data**: All processing is local
- **Reproducible**: Seeded RNG ensures deterministic output
- **No telemetry**: No data sent to external servers

### CI/CD Security

- **Automated scanning**: SAST tools in GitHub Actions
- **Dependency updates**: Weekly automated PRs
- **Signed commits**: GPG verification enabled

## Known Issues

None currently.

Last updated: December 14, 2025
