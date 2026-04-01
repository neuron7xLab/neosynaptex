# Repository Architecture Map

## Top-level structure

- `src/`: Core runtime, model orchestration, and system logic for the neuro-inspired AI engine.
- `docs/`: Specifications, protocols, runbooks, and system documentation.
- `tests/`: Unit, integration, and system tests aligned with validation strategies.
- `scripts/`: Developer and CI utilities for automation, analysis, and maintenance.
- `config/`: Configuration schemas, defaults, and environment-specific settings.
- `deploy/`: Deployment manifests, infrastructure scaffolding, and release assets.
- `policies/`: Governance, safety, and compliance policy artifacts.
- `reports/`: Generated evaluation, audit, and CI evidence reports.

## Module → Purpose → Owner docs

| Module | Purpose | Owner docs |
| --- | --- | --- |
| `src/` | Production codebase for models, orchestration, and runtime services. | [ARCHITECTURE_SPEC](ARCHITECTURE_SPEC.md), [NEURO_COG_ENGINE_SPEC](NEURO_COG_ENGINE_SPEC.md), [LLM_PIPELINE](LLM_PIPELINE.md) |
| `docs/` | System-of-record specifications, operational guides, and governance. | [DOCUMENTATION_FORMALIZATION_PROTOCOL](DOCUMENTATION_FORMALIZATION_PROTOCOL.md), [DEVELOPER_GUIDE](DEVELOPER_GUIDE.md) |
| `tests/` | Verification coverage for functional, integration, and system requirements. | [TESTING_GUIDE](TESTING_GUIDE.md), [TESTING_STRATEGY](TESTING_STRATEGY.md) |
| `scripts/` | Automation and tooling for developer workflows and CI. | [TOOLS_AND_SCRIPTS](TOOLS_AND_SCRIPTS.md), [CI_GUIDE](CI_GUIDE.md) |
| `config/` | Configuration contracts and environment setup. | [CONFIGURATION_GUIDE](CONFIGURATION_GUIDE.md), [ARCHITECTURE_CONFIG](ARCHITECTURE_CONFIG.md) |
| `deploy/` | Deployment procedures, infrastructure, and runtime rollout. | [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md), [RUNBOOK](RUNBOOK.md) |
| `policies/` | Safety, security, and governance controls. | [SECURITY_POLICY](SECURITY_POLICY.md), [SECURITY_GUARDRAILS](SECURITY_GUARDRAILS.md) |
| `reports/` | Audit, evaluation, and CI evidence outputs. | [CI_GATE_AUDIT_REPORT](CI_GATE_AUDIT_REPORT.md), [AUDIT_REGISTER](AUDIT_REGISTER.md) |
