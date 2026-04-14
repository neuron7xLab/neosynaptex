"""Adversarial orchestration runtime — §IV.B.

Priority order: Verifier > Auditor > Critic > Creator.

This package ships role implementations one at a time. The
Verifier lands first because §IV.B mandates that priority order —
without Verifier, the other roles have no gate to stop at.
"""
