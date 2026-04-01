# Product Requirements Document (MVP)

## Product
BN-Syn Thermostated Bio-AI System (research-grade CLI simulation toolkit).

## MVP Objective
Enable a new technical user to run a deterministic simulation and obtain first-value metrics in a single session.

## Users
- Researchers/engineers experimenting with emergent dynamics and reproducibility workflows.

## Jobs To Be Done
1. Run a simulation quickly from CLI.
2. Reproduce outputs deterministically with fixed inputs.
3. Validate quality via standardized checks.

## MVP Scope (In)
- CLI commands: `demo`, `run`, `dtcheck`, `sleep-stack`.
- Deterministic output for fixed seed/config.
- Local testing/build commands documented in README/Makefile.

## Out of Scope (MVP)
- Hosted SaaS service, multi-tenant auth, billing, and external API service.
- SLA-backed production ops.

## Acceptance Criteria
- AC1: Fresh environment can install package and run `bnsyn --help` successfully.
- AC2: `bnsyn demo` returns valid JSON containing `demo` key and numeric metrics.
- AC3: Non-validation test suite passes locally.
- AC4: Release checklist includes deterministic rollback instructions.

## Packaging / Pricing
- Not applicable for current repository scope; OSS/research-distribution model inferred.
