# Architecture Hygiene Register

**Document Version:** 1.0.0  
**Project Version:** 1.2.0  
**Created:** 2026-01-10 12:34 UTC  
**Last Updated:** 2026-01-10 12:34 UTC  
**Time Zone:** UTC  
**Status:** Active

---

## Purpose

This register tracks architectural hygiene gaps, their impact, and ownership. It provides a single place to record issues that affect architectural consistency, dependency boundaries, or policy alignment.

## Governance

- **Who can add records:** Staff/Principal Engineers, Architecture Owners, or delegated Tech Leads for a domain.
- **Required reviewers:** Architecture Owner for the affected domain plus one platform maintainer.
- **Review cadence:** Quarterly review (first week of each quarter) and mandatory review before major releases.
- **How to add:** Submit a PR updating the table below with evidence, impact, and an owner. Mark status as Open/Investigating/Resolved.

## Register Entries

| ID | Gap | Evidence / Location | Impact | Owner | Status | Target Review |
| --- | --- | --- | --- | --- | --- | --- |
| AH-POL-001 | Policy sources split between `policy/` and `policies/` without a canonical index | Policy catalog introduced at `policy/catalog.json` with hash enforcement across both directories | Risk of drift and duplicated policy updates | Architecture Owner | Resolved (2026-01-17) | 2026-Q1 |
| AH-AUD-001 | No import-audit gate in quality checks | Quality gates list `pip-audit` and `deptry` but no import-audit step | Undetected unused or forbidden imports in runtime paths | Platform Maintainer | Open | 2026-Q1 |
| AH-GOV-001 | Architecture hygiene gaps tracked across multiple docs without a dedicated registry | No single register previously existed | Harder to triage architectural hygiene work consistently | Architecture Owner | Resolved (2026-01-10) | 2026-Q1 |
