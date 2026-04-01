# Changelog

All notable changes to CA1 Hippocampus Framework.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/)

## [2.0.0] - 2025-12-14

### Added
- **Unified Weight Matrix**: W + STP + Ca²⁺ in single structure
- **Input-specific plasticity**: CA3/EC/LOCAL channels (10x difference)
- **Hierarchical laminar inference**: Random effects + MRF prior
- **Theta-SWR switching**: Full state machine with gating
- **Golden test suite**: 5 tests with seed=42, <1e-10 tolerance
- **Complete documentation**: 12 documents, API reference, examples

### Changed
- Replaced `SynapseManager` with `UnifiedWeightMatrix`
- Upgraded `ZINBLayerModel` to `HierarchicalLaminarModel`
- Ca²⁺ plasticity now exact Graupner-Brunel formula (not STDP)

### Performance
- 2.5x faster laminar EM (vectorized)
- 1.6x faster weight updates

### Scientific
- All 13 DOI sources validated
- 58,065 cell dataset integrated
- SWR curated dataset metrics matched

## [1.1.0] - 2025-12-14

### Added
- Initial release
- Basic CA1 model
- AI integration prototype

## [Unreleased]

### Planned for 2.1.0
- JAX backend for GPU
- Extended validation suite
- Spatial place cell analysis

[2.0.0]: https://github.com/neuron7xLab/Hippocampal-CA1-LAM/releases
[1.1.0]: https://github.com/neuron7xLab/Hippocampal-CA1-LAM/releases
