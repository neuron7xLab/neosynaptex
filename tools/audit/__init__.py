"""Framework self-audit tooling.

Instruments the kill-criteria heuristics declared in
``docs/SYSTEM_PROTOCOL.md`` frontmatter, transitioning them from
``measurement_status: not_instrumented`` to ``instrumented`` one
signal at a time. Each module in this package implements one signal
with a full measurement-discipline contract: signal, computation,
window, controls, fake-alternative guard, falsifier.
"""
