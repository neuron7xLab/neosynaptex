"""Tests for experiments.experiment_cards — Task 7 TRL kit."""

from __future__ import annotations

from experiments.experiment_cards import ExperimentCard, generate_all_cards


class TestExperimentCards:
    def test_generates_all_five_cards(self) -> None:
        cards = generate_all_cards()
        assert len(cards) == 5

    def test_all_cards_have_required_fields(self) -> None:
        for card in generate_all_cards():
            assert isinstance(card, ExperimentCard)
            assert card.name
            assert card.description
            assert card.category in ("coherence", "fdt", "hallucination", "ablation", "resonance")
            assert isinstance(card.parameters, dict)
            assert isinstance(card.metrics, dict)
            assert isinstance(card.passed, bool)
            assert isinstance(card.seed, int)
            assert card.reproduce_command

    def test_coherence_stability_passes(self) -> None:
        cards = generate_all_cards()
        card = next(c for c in cards if c.name == "coherence_stability_default")
        assert card.passed is True
        assert card.metrics["spectral_radius"] < 1.0

    def test_fdt_gamma_recovery_passes(self) -> None:
        cards = generate_all_cards()
        card = next(c for c in cards if c.name == "fdt_gamma_recovery_ou")
        assert card.passed is True
        assert card.metrics["relative_error"] < 0.05

    def test_hallucination_benchmark_passes(self) -> None:
        cards = generate_all_cards()
        card = next(c for c in cards if c.name == "hallucination_benchmark_accuracy")
        assert card.passed is True
        assert card.metrics["recall"] > 0.5

    def test_ablation_card_has_metrics(self) -> None:
        cards = generate_all_cards()
        card = next(c for c in cards if c.name == "ablation_energy_vs_roles")
        assert "energy_quality" in card.metrics
        assert "roles_quality" in card.metrics

    def test_resonance_diagnosis_passes(self) -> None:
        cards = generate_all_cards()
        card = next(c for c in cards if c.name == "resonance_diagnosis_speed")
        assert card.passed is True
        assert card.metrics["time_to_diagnosis"] <= 10.0

    def test_all_categories_covered(self) -> None:
        cards = generate_all_cards()
        categories = {c.category for c in cards}
        assert categories == {"coherence", "fdt", "hallucination", "ablation", "resonance"}

    def test_all_reproduce_commands_are_python(self) -> None:
        for card in generate_all_cards():
            assert card.reproduce_command.startswith("python")
