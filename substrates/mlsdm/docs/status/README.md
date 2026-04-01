# Status Documentation

This directory contains readiness documentation and status tracking.

## Contents

- [READINESS.md](READINESS.md) — Canonical readiness truth and validation commands

## Readiness Gates

Readiness is validated by CI workflows in `.github/workflows/`:

- `ci-smoke.yml` — CI Smoke Tests
- `prod-gate.yml` — Production Gate
- `perf-resilience.yml` — Performance & Resilience Validation
- `property-tests.yml` — Property-Based Tests
- `sast-scan.yml` — SAST Security Scan
- `readiness-evidence.yml` — Readiness Evidence capture

For current project status:
- [docs/index.md](../index.md) — Documentation index
- [CI workflow results](https://github.com/neuron7xLab/mlsdm/actions) — GitHub Actions
