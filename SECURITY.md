# Security Policy

## Supported Versions

The `main` branch is actively maintained. Security fixes are applied to `main`
and backported to the latest tagged release on a best-effort basis.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < main  | :x:                |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting:

- https://github.com/neuron7xLab/neosynaptex/security/advisories/new

Please include:

- Affected component / file / commit SHA
- Reproduction steps or proof-of-concept
- Expected vs. observed behavior
- Impact assessment (confidentiality / integrity / availability)
- Any suggested mitigation

### Response targets

- **Acknowledgement:** within 72 hours
- **Initial triage:** within 7 days
- **Fix or mitigation:** scoped per severity (CVSS v3.1)
  - Critical / High: coordinated disclosure within 30 days
  - Medium: within 60 days
  - Low / Informational: next scheduled release

We follow coordinated disclosure. A CVE will be requested via GitHub Security
Advisories for any issue with a CVSS score ≥ 4.0.

## Scope

In scope:

- Source code in this repository (Python core, Rust substrates, web dashboards)
- Build pipelines and release artifacts published from this repository
- Dependencies pinned in `requirements*.txt`, `Cargo.toml`, `package.json`

Out of scope:

- Vulnerabilities in third-party services, hosting, or user environments
- Social engineering, physical access, or denial-of-service via resource exhaustion
- Issues requiring a jailbroken / rooted runtime or compromised developer machine

## Security hardening already in place

- Dependabot security updates: enabled
- Secret scanning + push protection: enabled
- CodeQL default setup (Actions + Python): enabled
- Private vulnerability reporting: enabled
- Signed commits preferred on `main`
- Falsification-shield adversarial test layer (see `tests/`)

## Credit

Reporters who follow this policy will be credited in the published advisory
unless they request anonymity.
