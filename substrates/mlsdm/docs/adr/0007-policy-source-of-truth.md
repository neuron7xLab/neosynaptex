# ADR-0007: Policy-as-Code Single Source of Truth

- **Status:** Accepted
- **Date:** 2025-12-07

## Problem

The repository currently enforces governance policies via multiple artifacts: human-readable YAML in `policy/`, OPA/Rego rules in `policies/`, runtime configuration defaults in Python, and documentation references. This creates a split-brain risk where thresholds, allowlists, and enforcement rules can drift between sources, causing inconsistent CI gates and runtime behavior.

## Decision

Adopt `policy/` YAML as the single source of truth (SoT) for governance policies. All enforcement mechanisms must be derived from the YAML via a canonical policy loader (`mlsdm.policy.loader`) that validates a strict schema, canonicalizes values, computes a canonical hash, and exports data for:

1. **Runtime configuration:** Python modules load thresholds directly from the YAML via the loader.
2. **OPA/Rego enforcement:** Conftest consumes generated JSON data, and Rego reads from `data.policy.*`.
3. **Documentation and CI validation:** Docs and validation scripts reference the loader output and policy schema.

Contract versioning is enforced via `policy_contract_version`. Unknown fields fail closed, and changes require explicit migration notes.

## Alternatives Considered

1. **Make OPA/Rego the SoT.**
   - Rejected because YAML is the human-authored specification referenced across docs and scripts, and Regos are specialized enforcement artifacts.

2. **Maintain dual SoT (YAML + Rego).**
   - Rejected due to drift risk and audit complexity. Dual SoT violates deterministic governance requirements.

3. **Hardcode runtime thresholds in Python.**
   - Rejected because it bypasses policy validation and creates policy drift not captured by CI or documentation.

## Consequences

- All policy changes must be made in `policy/*.yaml` and validated by the loader schema.
- Rego rules must use `data.policy.*` to reference thresholds and control parameters.
- Runtime SLO defaults now fail fast if policy files are missing or invalid.
- CI adds blocking steps to validate and export policy data.

## Migration

1. Add strict policy schema and loader for YAML contracts.
2. Update YAML policies to include required governance metadata and contract fields.
3. Export OPA data from the loader and wire it into conftest execution.
4. Update runtime SLO defaults to load from the policy contract.
5. Update documentation to reflect SoT architecture and CI gates.

### Contract Version 1.1 Migration Notes (2026-03)

- Enforced strict `policy_contract_version` = `1.1` for all policy YAML.
- Added deterministic canonical hash output for policy bundles.
- Added unit normalization for SLO numeric fields (ms/percent/ratio) with explicit validators.
- Introduced explicit OPA export mapping contract validation before writing data.

### Mutable Ref Policy Fix (2026-01)

- **Issue:** The Rego rule for blocking mutable action references used substring matching
  (`str_contains(uses, ref)`), which caused false positives. For example, an action
  pinned to `@v0.21.1` would be incorrectly blocked because `@v0` is a substring.
- **Fix:** Changed to exact matching by parsing the ref part from the action string
  (everything after `@`) and comparing the full `@ref_part` token against the
  prohibited list. This ensures `@v0.21.1` (immutable semver) is allowed while
  `@v0` (mutable major tag) is still blocked.
- **Policy expansion:** Added major-only version tags (`@v0` through `@v9`) to
  `prohibited_mutable_refs` to enforce supply-chain security by requiring full
  semver or SHA pinning for third-party actions.
- **Test coverage:** Added new fixtures `workflow-good-semver.yml` and
  `workflow-bad-major-version.yml` to validate exact-match behavior.

## Rollback Plan

If a critical release must bypass new gates, temporarily disable the policy validation and conftest data steps in CI with explicit human approval, then re-enable after remediation.
