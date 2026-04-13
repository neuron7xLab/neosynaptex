# External Precedents

> **This document is not canon and does not constitute empirical evidence
> for γ; it records external conceptual precedents only.**

## Independent Conceptual Precedents

This document records **external conceptual precedents** that are useful for `Neosynaptex`, but are **not part of canonical evidentiary claims**. They do not strengthen the γ-hypothesis directly. They justify architectural, operational, and safety choices around agent loops, human supervision, and observability.

### 1. OODA as an independent precedent for the agent loop

John Boyd's OODA loop — **Observe → Orient → Decide → Act** — is an independently established decision-cycle model in military and strategic cognition. Air University summaries describe Boyd's concept as a loop in which success depends on observing, orienting, deciding, and acting more effectively than the opponent. In `Neosynaptex`, this is relevant as an **external structural precedent** for a cyclic agent contract, independent of any γ-based claim. It should be cited as **architectural convergence**, not as evidence for metastability.

**Operational use in Neosynaptex**
- Supports explicit loop design in agent substrates and CNS-AI control rails
- Justifies treating Observe/Orient as distinct phases rather than collapsing everything into a generic inference step
- Provides an independent frame for latency, orientation quality, and intervention timing

### 2. Out-of-the-loop performance problem

Endsley and Kiris defined the **out-of-the-loop performance problem** as a major consequence of automation: operators of automated systems become handicapped in taking over manual control after failure, due to reduced situation awareness, vigilance decay, complacency, and a shift from active to passive processing. This is directly relevant to any `CNS-AI Loop` or human-on-the-loop substrate.

**Operational use in Neosynaptex**
- Define explicit human re-entry conditions
- Measure intervention latency and situation-awareness recovery cost
- Treat high automation without re-entry competence as a safety failure, not a UX issue
- Add takeover drills and degraded-mode scenarios to protocol design

### 3. Observability as a hard requirement for agent systems

OpenTelemetry defines observability telemetry around **traces, metrics, and logs**, and emphasizes that distributed tracing follows requests as they propagate through complex distributed systems. This is directly aligned with `Neosynaptex` evidence rails: a distributed agent system without structured logs, latency metrics, and trace correlation cannot localize cognitive bottlenecks or audit causal flow.

**Operational use in Neosynaptex**
- Require structured logs for every agent transition and contract boundary
- Require latency metrics per loop phase and per tool edge
- Require distributed traces across multi-agent and multi-service execution
- Use telemetry correlation to identify bottlenecks, hidden stalls, and failure cascades

## Boundary rule

These precedents are **conceptual and operational supports**, not canonical proof objects. They belong in `EXTERNAL_PRECEDENTS.md`, not in the γ canon. Their role is to strengthen loop design, observability, and supervision discipline without overstating empirical implications.

## Sources

1. Air University Press. *The Blind Strategist: John Boyd and the American Art of War*.
2. Endsley MR, Kiris EO. *The Out-of-the-Loop Performance Problem and Level of Control in Automation*. Human Factors. 1995.
3. OpenTelemetry documentation: Observability primer; Traces; Logs.
