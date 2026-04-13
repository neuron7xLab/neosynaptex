<!--
Required fields are enforced by .github/workflows/claim_status_check.yml
and tools/audit/pr_body_check.py. See docs/SYSTEM_PROTOCOL.md for the full
framework.
-->

## Summary

<!-- What does this PR change? 1–3 sentences. -->

## Test plan

- [ ] <!-- how this was validated -->

## Claim status

<!--
REQUIRED. Replace <label> below with exactly one value from the canonical
taxonomy in docs/SYSTEM_PROTOCOL.md §Barrier rule (item 4):

  - measured            — directly instrumented; survives adversarial controls
  - derived             — follows logically from measured facts or existing canon
  - hypothesized        — engineered conjecture awaiting measurement
  - unverified analogy  — precedent from another domain; does not transfer
  - falsified           — adversarial result that rules the claim out

Pick the status that describes the strongest claim this PR is the evidence
FOR. If the PR is pure tooling / docs hygiene without a new claim, use
"derived".
-->

claim_status: <label>

<!-- 2–4 sentences of rationale — why this status and not a stronger one. -->
