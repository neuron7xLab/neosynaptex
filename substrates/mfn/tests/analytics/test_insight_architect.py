import pytest

from mycelium_fractal_net.analytics import (
    FractalInsightArchitect,
    InsufficientDataError,
)


def test_generate_insight_template_and_metrics():
    data = {
        "micro": [{"pattern": "Затримка відповіді", "metric": 0.12, "evidence": "email >5хв"}],
        "meso": [{"pattern": "Накопичення черг", "metric": 0.35}],
        "macro": [{"pattern": "Просідання пропускної здатності", "metric": 0.18}],
        "tensions": ["Локальні затримки накопичуються"],
        "goal": "зменшити латентність",
    }

    architect = FractalInsightArchitect()
    insight = architect.generate(data, principle_name="Latency cascade")
    text = insight.format()

    assert "[LATENCY CASCADE]" in text
    assert "**Фрактальна структура**" in text
    assert "- **Мікро**" in text
    assert "- **Мезо**" in text
    assert "- **Макро**" in text
    assert "Операційні кроки" in text
    assert "0.120" in text  # formatted micro metric
    assert "15%" in text  # improvement target in steps
    assert "20%" in text  # invariant reference


def test_generate_requests_clarifications_when_missing_levels():
    data = {"micro": [{"pattern": "Локальний шум"}]}
    architect = FractalInsightArchitect(max_clarifications=2)

    with pytest.raises(InsufficientDataError) as excinfo:
        architect.generate(data)

    clarifications = excinfo.value.clarifications
    assert len(clarifications) <= 2
    assert any("мезо" in q.lower() for q in clarifications)
    assert any("макро" in q.lower() for q in clarifications)
