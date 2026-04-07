# ADR-002 — AGPL-3.0 license

**Status:** Accepted

---

## Context

The `neosynaptex` engine is a scientific instrument intended for reproducible
research. Any modifications deployed as a service (e.g., a hosted diagnostic
API) must be traceable back to the research record. The project also needs to
be usable by academic researchers without restricting redistribution.

---

## Decision

The project is licensed under **GNU Affero General Public License v3.0
(AGPL-3.0-or-later)**.

The AGPL license text is in [`LICENSE`](../../LICENSE). The license boundary
policy (what is and is not covered) is documented in
[`LICENSE_BOUNDARIES.md`](../../LICENSE_BOUNDARIES.md).

---

## Consequences

**Positive:**

- Any derivative work — including SaaS deployments — must publish their
  modifications under AGPL. This closes the "application service provider"
  loophole present in GPL.
- Protects the scientific record: if someone modifies the gamma computation
  and publishes results, the source must be available for verification.
- Compatible with academic use: universities and researchers can use, modify,
  and redistribute freely as long as they comply with AGPL terms.
- Supported by GitHub (badge, license detection, dependency graph).

**Negative / trade-offs:**

- Commercial users who cannot open-source their modifications must negotiate
  a separate commercial license. This is intentional (virality by design).
- Some downstream packages (permissive-only organizations) may decline to
  depend on AGPL code. Mitigated by the single-file design (easy to audit
  whether their use triggers copyleft).

---

## Alternatives considered

| License | Rejected because |
|---------|-----------------|
| MIT / Apache-2.0 | No network-use copyleft; modifications can be deployed privately without disclosure |
| GPL-2.0 | Does not cover network use (ASP loophole) |
| GPL-3.0 | Same ASP loophole as GPL-2 |
| CC-BY 4.0 | Not recommended for software; no patent grant |
| Proprietary | Contradicts the open reproducibility mission |

---

## References

- `LICENSE` — full AGPL-3.0 text
- `LICENSE_BOUNDARIES.md` — what is in-scope and out-of-scope
- `scripts/check_license_boundaries.py` — CI enforcement
