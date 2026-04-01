"""
Fractal Insight Architect v2.0

Transforms semi-structured observations into actionable, multi-scale insights
that follow the template described in the problem statement. The implementation
is intentionally lightweight and deterministic so it can run inside automated
tests without external dependencies.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class InsufficientDataError(ValueError):
    """
    Raised when provided observations cannot produce a full micro/meso/macro
    stack. Includes up to ``max_clarifications`` follow-up questions.
    """

    def __init__(self, clarifications: list[str]):
        super().__init__("insufficient data for insight generation")
        self.clarifications = clarifications


@dataclass
class LevelPattern:
    """Normalized representation of a pattern at a given scale."""

    name: str
    metric: float | None = None
    evidence: str | None = None


@dataclass
class Insight:
    """Structured insight payload."""

    name: str
    summary: str
    micro: str
    meso: str
    macro: str
    invariant: str
    steps: list[str]
    validation: str
    boundaries: str

    def format(self) -> str:
        """Render the insight using the mandated template."""
        lines = [
            f"**[{self.name}]**: {self.summary}",
            "",
            "**Фрактальна структура**:",
            f"- **Мікро**: {self.micro}",
            f"- **Мезо**: {self.meso}",
            f"- **Макро**: {self.macro}",
            "",
            f"**Інваріант**: {self.invariant}",
            "",
            "**Операційні кроки**:",
        ]
        lines.extend(self.steps)
        lines.extend(
            [
                "",
                f"**Валідація**: {self.validation}",
                f"**Межі**: {self.boundaries}",
            ]
        )
        return "\n".join(lines)


@dataclass
class _NormalizedData:
    levels: dict[str, list[LevelPattern]]
    tensions: list[str]
    goal: str | None


class FractalInsightArchitect:
    """
    Deterministic insight generator that follows the "ФРАКТАЛЬНИЙ ІНСАЙТ-АРХІТЕКТОР v2.0"
    protocol from the problem statement.
    """

    def __init__(
        self,
        max_clarifications: int = 3,
        coverage_target: float = 0.80,
        variance_reduction_target: float = 0.50,
        macro_improvement_target: float = 0.15,
        invariant_stability_pct: float = 0.20,
        chaos_threshold: float = 0.70,
        review_cadence: str = "щотижня",
        time_horizon: str = "1-2 тижнів",
    ):
        self.max_clarifications = max(1, min(max_clarifications, 3))
        self.coverage_target = coverage_target
        self.variance_reduction_target = variance_reduction_target
        self.macro_improvement_target = macro_improvement_target
        self.invariant_stability_pct = invariant_stability_pct
        self.chaos_threshold = chaos_threshold
        self.review_cadence = review_cadence
        self.time_horizon = time_horizon

    # Public API -----------------------------------------------------------------
    def generate(
        self,
        data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        principle_name: str | None = None,
    ) -> Insight:
        """
        Generate an insight. Expects either a mapping with keys ``micro``,
        ``meso``, ``macro`` or a list of mappings each containing ``level``.
        """
        normalized = self._normalize(data)
        missing_levels = [lvl for lvl in ("micro", "meso", "macro") if not normalized.levels[lvl]]
        if missing_levels:
            raise InsufficientDataError(self._build_clarifications(missing_levels))

        metrics = [
            p.metric for items in normalized.levels.values() for p in items if p.metric is not None
        ]
        invariant_threshold = self._compute_threshold(metrics)

        name = self._build_name(principle_name, normalized)
        summary = self._build_summary(normalized)
        micro_text = self._describe_level("Мікро", normalized.levels["micro"])
        meso_text = self._describe_level("Мезо", normalized.levels["meso"])
        macro_text = self._describe_level("Макро", normalized.levels["macro"])
        invariant = self._build_invariant(invariant_threshold)
        steps = self._build_steps(normalized, invariant_threshold)
        validation = self._build_validation()
        boundaries = self._build_boundaries()

        return Insight(
            name=name,
            summary=summary,
            micro=micro_text,
            meso=meso_text,
            macro=macro_text,
            invariant=invariant,
            steps=steps,
            validation=validation,
            boundaries=boundaries,
        )

    def format_insight(
        self,
        data: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        principle_name: str | None = None,
    ) -> str:
        """Generate and return a formatted string insight."""
        return self.generate(data, principle_name=principle_name).format()

    # Normalization --------------------------------------------------------------
    def _normalize(self, data: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> _NormalizedData:
        levels: dict[str, list[LevelPattern]] = {"micro": [], "meso": [], "macro": []}
        tensions: list[str] = []
        goal = None

        if isinstance(data, Mapping):
            goal = data.get("goal")
            tensions_raw = data.get("tensions")
            if tensions_raw is None:
                tensions_raw = data.get("tension_points", [])
            tensions = list(tensions_raw or [])
            for lvl in levels:
                levels[lvl] = self._normalize_entries(data.get(lvl, []))
        else:
            for item in data:
                if not isinstance(item, Mapping):
                    continue
                lvl = str(item.get("level", "")).lower()
                if lvl in levels:
                    levels[lvl].extend(self._normalize_entries([item]))
                if item.get("tension"):
                    tensions.append(str(item["tension"]))
            goal = None

        return _NormalizedData(levels=levels, tensions=tensions, goal=goal)

    def _normalize_entries(self, entries: Iterable[Any]) -> list[LevelPattern]:
        normalized: list[LevelPattern] = []
        for entry in entries:
            if isinstance(entry, str):
                normalized.append(LevelPattern(name=entry))
                continue
            if isinstance(entry, Mapping):
                name = (
                    entry.get("pattern")
                    or entry.get("name")
                    or entry.get("description")
                    or entry.get("signal")
                )
                if not name:
                    continue
                metric = entry.get("metric")
                if metric is None and isinstance(entry.get("value"), (int, float)):
                    metric = float(entry["value"])
                evidence = entry.get("evidence") or entry.get("example")
                evidence_text = str(evidence) if evidence is not None else None
                normalized.append(
                    LevelPattern(
                        name=str(name),
                        metric=self._safe_float(metric),
                        evidence=evidence_text,
                    )
                )
        return normalized

    # Builders -------------------------------------------------------------------
    def _build_clarifications(self, missing_levels: list[str]) -> list[str]:
        templates = {
            "micro": "Надайте базові мікропатерни (правила/сигнали) та їхні метрики.",
            "meso": "Опишіть взаємодії між елементами на мезорівні та рівень узгодженості.",
            "macro": "Додайте системні наслідки на макрорівні з вимірюваними метриками.",
        }
        clarifications = [templates[lvl] for lvl in missing_levels]
        return clarifications[: self.max_clarifications]

    def _build_name(self, principle_name: str | None, normalized: _NormalizedData) -> str:
        if principle_name:
            return principle_name.strip().upper()
        micro = self._primary_pattern(normalized.levels["micro"]).name
        macro = self._primary_pattern(normalized.levels["macro"]).name
        return f"{micro} → {macro}".upper()

    def _build_summary(self, normalized: _NormalizedData) -> str:
        macro = self._primary_pattern(normalized.levels["macro"]).name
        tension = normalized.tensions[0] if normalized.tensions else "каскадне посилення"
        goal = normalized.goal or "стабілізувати систему"
        return f"{tension} призводить до {macro}; мета — {goal}."

    def _describe_level(self, label: str, patterns: list[LevelPattern]) -> str:
        if not patterns:
            return f"{label.lower()}-правило — даних недостатньо."
        primary = patterns[0]
        metric_text = f" (метрика: {self._format_metric(primary.metric)})"
        example = f" (приклад: {primary.evidence})" if primary.evidence else ""
        extra = f"; повторюваність {len(patterns)}x" if len(patterns) > 1 else ""
        return f"{label.lower()}-правило — {primary.name}{metric_text}{example}{extra}."

    def _build_invariant(self, threshold: float) -> str:
        stability_pct = int(self.invariant_stability_pct * 100)
        return (
            f"Стійкий при змінах >{stability_pct}%; поріг чутливості "
            f"{threshold:.3f} для ключових метрик."
        )

    def _build_steps(self, normalized: _NormalizedData, threshold: float) -> list[str]:
        micro_metric = self._first_metric(normalized.levels["micro"])
        meso_metric = self._first_metric(normalized.levels["meso"])
        goal = normalized.goal or "результат"
        return [
            (
                "1. Зняти базову мікрометріку "
                f"({self._format_metric(micro_metric)}), охоплення "
                f"≥{int(self.coverage_target * 100)}%."
            ),
            (
                "2. Синхронізувати мезорівень через A/B-тест (ціль: -"
                f"{int(self.variance_reduction_target * 100)}% варіації; "
                f"базово {self._format_metric(meso_metric)})."
            ),
            (
                f"3. Моніторити макропоказники {self.review_cadence}; очікуване "
                f"покращення {goal} на {int(self.macro_improvement_target * 100)}% "
                f"упродовж {self.time_horizon}; реагувати при відхиленні >{threshold:.3f}."
            ),
        ]

    def _build_validation(self) -> str:
        return (
            "A/B-тест + контрольна група; контрприклад: якщо зміни випадкові та "
            "не масштабуються, гіпотеза відкидається."
        )

    def _build_boundaries(self) -> str:
        return (
            "Не працює в хаотичних системах із випадковістю "
            f">{int(self.chaos_threshold * 100)}%; сигнал ризику — відсутність "
            "повторюваних патернів."
        )

    # Utilities ------------------------------------------------------------------
    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _compute_threshold(self, metrics: list[float]) -> float:
        clean_metrics: list[float] = []
        for raw in metrics:
            val = self._safe_float(raw)
            if val is not None:
                clean_metrics.append(abs(val))
        if not clean_metrics:
            return 0.1
        max_metric = max(clean_metrics)
        if max_metric == 0:
            return 0.1
        return round(max_metric * self.invariant_stability_pct, 3)

    @staticmethod
    def _first_metric(patterns: list[LevelPattern]) -> float | None:
        for p in patterns:
            if p.metric is not None:
                return p.metric
        return None

    @staticmethod
    def _primary_pattern(patterns: list[LevelPattern]) -> LevelPattern:
        if not patterns:
            raise ValueError("patterns cannot be empty; надайте хоча б один патерн для рівня")
        return patterns[0]

    @staticmethod
    def _format_metric(value: float | None) -> str:
        return f"{value:.3f}" if value is not None else "n/a"
