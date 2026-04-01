"""BN-Syn flagship experiments module.

This module contains reproducible scientific experiments demonstrating
BN-Syn's phase-controlled emergent dynamics capabilities.

Experiments are designed to be:
- Deterministic (seeded RNG)
- Reproducible (versioned manifests)
- Evidence-generating (quantitative metrics + visualizations)

Modules
-------
registry : Experiment configuration registry
temperature_ablation_consolidation : Temperature ablation experiment
runner : CLI entry point for running experiments
verify_hypothesis : Hypothesis verification utilities

References
----------
docs/HYPOTHESIS.md : Experimental hypothesis and design
"""

__version__ = "1.0.0"
