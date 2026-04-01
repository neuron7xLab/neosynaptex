"""Deterministic response-quality gate for LLM failure-mode control."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FailureModeSignal:
    """Quantified signal for an LLM failure mode."""

    mode: str
    score: float
    threshold: float
    triggered: bool
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "score": self.score,
            "threshold": self.threshold,
            "triggered": self.triggered,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class QualityGateDecision:
    """Decision output from the response quality gate."""

    allow_response: bool
    suppress_memory: bool
    action: str
    triggered_modes: tuple[str, ...]
    signals: dict[str, FailureModeSignal]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow_response": self.allow_response,
            "suppress_memory": self.suppress_memory,
            "action": self.action,
            "triggered_modes": list(self.triggered_modes),
            "signals": {name: signal.as_dict() for name, signal in self.signals.items()},
        }


class ResponseQualityGate:
    """Deterministic quality gate for observable LLM failure modes."""

    _HALLUCINATION_CONFIDENCE_THRESHOLD = 0.4
    _DRIFT_OVERLAP_THRESHOLD = 0.05
    _MIN_DRIFT_TOKENS = 20
    _MIN_PROMPT_TOKENS = 3
    _INCOHERENCE_ALPHA_RATIO_THRESHOLD = 0.6
    _INCOHERENCE_MIN_TOKENS = 12
    _TELEGRAPH_MIN_TOKENS = 12
    _TELEGRAPH_MIN_SENTENCE_LEN = 6.0
    _TELEGRAPH_FUNCTION_WORD_RATIO = 0.2
    _LOOPING_MIN_TOKENS = 18
    _LOOPING_MAX_REPEAT_RATIO = 0.45
    _LOOPING_MAX_CONSECUTIVE_RUN = 4
    _LOOPING_MIN_LINES = 4
    _LOOPING_LINE_REPEAT_RATIO = 0.5

    _FUNCTION_WORDS = {
        "the",
        "and",
        "to",
        "of",
        "in",
        "a",
        "is",
        "it",
        "that",
        "for",
        "on",
        "with",
        "as",
        "are",
        "was",
        "were",
        "be",
        "by",
        "an",
        "or",
        "from",
        "at",
        "this",
        "which",
        "but",
        "not",
        "have",
        "has",
        "had",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "your",
        "you",
        "we",
        "our",
        "they",
        "their",
    }

    def evaluate(self, *, prompt: str, response: str, confidence: float) -> QualityGateDecision:
        prompt_tokens = self._tokenize(prompt)
        response_tokens = self._tokenize(response)
        response_is_empty = len(response.strip()) == 0

        signals: dict[str, FailureModeSignal] = {}

        signals["collapse"] = self._collapse_signal(response, response_tokens)
        signals["looping"] = self._looping_signal(response, response_tokens)
        signals["incoherence"] = self._incoherence_signal(response_tokens)
        signals["telegraphing"] = self._telegraphing_signal(response, response_tokens)
        signals["drift"] = self._drift_signal(prompt_tokens, response_tokens)
        signals["hallucination"] = (
            self._hallucination_signal_for_empty()
            if response_is_empty
            else self._hallucination_signal(confidence)
        )

        triggered_modes = tuple(name for name, sig in signals.items() if sig.triggered)

        reject_modes = {"collapse", "looping", "incoherence"}
        degrade_modes = {"hallucination", "drift", "telegraphing"}

        if any(mode in reject_modes for mode in triggered_modes):
            return QualityGateDecision(
                allow_response=False,
                suppress_memory=True,
                action="reject",
                triggered_modes=triggered_modes,
                signals=signals,
            )

        if any(mode in degrade_modes for mode in triggered_modes):
            return QualityGateDecision(
                allow_response=True,
                suppress_memory=True,
                action="degrade",
                triggered_modes=triggered_modes,
                signals=signals,
            )

        return QualityGateDecision(
            allow_response=True,
            suppress_memory=False,
            action="accept",
            triggered_modes=(),
            signals=signals,
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9']+", text.lower())

    @staticmethod
    def _sentence_split(text: str) -> list[str]:
        segments = re.split(r"[.!?]+", text)
        return [seg.strip() for seg in segments if seg.strip()]

    @staticmethod
    def _max_consecutive_run(tokens: list[str]) -> int:
        if not tokens:
            return 0
        longest = 1
        current = 1
        for idx in range(1, len(tokens)):
            if tokens[idx] == tokens[idx - 1]:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        return longest

    def _collapse_signal(self, response: str, response_tokens: list[str]) -> FailureModeSignal:
        collapsed = len(response.strip()) == 0 or len(response_tokens) == 0
        score = 1.0 if collapsed else 0.0
        return FailureModeSignal(
            mode="collapse",
            score=score,
            threshold=1.0,
            triggered=collapsed,
            evidence={"response_length": len(response.strip()), "token_count": len(response_tokens)},
        )

    def _looping_signal(self, response: str, response_tokens: list[str]) -> FailureModeSignal:
        repetition_ratio = 0.0
        max_run = self._max_consecutive_run(response_tokens)
        if response_tokens:
            repetition_ratio = 1.0 - (len(set(response_tokens)) / len(response_tokens))

        lines = [line.strip() for line in response.splitlines() if line.strip()]
        line_repeat_ratio = 0.0
        if len(lines) >= self._LOOPING_MIN_LINES:
            most_common = max(lines.count(line) for line in set(lines))
            line_repeat_ratio = most_common / len(lines)

        triggered = False
        if len(response_tokens) >= self._LOOPING_MIN_TOKENS:
            triggered = (
                repetition_ratio >= self._LOOPING_MAX_REPEAT_RATIO
                or max_run >= self._LOOPING_MAX_CONSECUTIVE_RUN
                or line_repeat_ratio >= self._LOOPING_LINE_REPEAT_RATIO
            )

        score = max(repetition_ratio, line_repeat_ratio, float(max_run) / max(len(response_tokens), 1))
        return FailureModeSignal(
            mode="looping",
            score=score,
            threshold=self._LOOPING_MAX_REPEAT_RATIO,
            triggered=triggered,
            evidence={
                "repetition_ratio": repetition_ratio,
                "max_consecutive_run": max_run,
                "line_repeat_ratio": line_repeat_ratio,
                "token_count": len(response_tokens),
                "line_count": len(lines),
            },
        )

    def _incoherence_signal(self, response_tokens: list[str]) -> FailureModeSignal:
        if len(response_tokens) < self._INCOHERENCE_MIN_TOKENS:
            return FailureModeSignal(
                mode="incoherence",
                score=0.0,
                threshold=self._INCOHERENCE_ALPHA_RATIO_THRESHOLD,
                triggered=False,
                evidence={"token_count": len(response_tokens)},
            )

        alpha_tokens = [tok for tok in response_tokens if re.search(r"[a-zA-Z]", tok)]
        alpha_ratio = len(alpha_tokens) / max(len(response_tokens), 1)
        triggered = alpha_ratio < self._INCOHERENCE_ALPHA_RATIO_THRESHOLD
        return FailureModeSignal(
            mode="incoherence",
            score=1.0 - alpha_ratio,
            threshold=1.0 - self._INCOHERENCE_ALPHA_RATIO_THRESHOLD,
            triggered=triggered,
            evidence={"alpha_ratio": alpha_ratio, "token_count": len(response_tokens)},
        )

    def _telegraphing_signal(self, response: str, response_tokens: list[str]) -> FailureModeSignal:
        if len(response_tokens) < self._TELEGRAPH_MIN_TOKENS:
            return FailureModeSignal(
                mode="telegraphing",
                score=0.0,
                threshold=1.0,
                triggered=False,
                evidence={"token_count": len(response_tokens)},
            )

        sentences = self._sentence_split(response)
        if not sentences:
            return FailureModeSignal(
                mode="telegraphing",
                score=0.0,
                threshold=1.0,
                triggered=False,
                evidence={"token_count": len(response_tokens)},
            )

        total_tokens = len(response_tokens)
        function_tokens = sum(1 for token in response_tokens if token in self._FUNCTION_WORDS)
        function_ratio = function_tokens / max(total_tokens, 1)
        avg_sentence_len = total_tokens / len(sentences)

        triggered = (
            avg_sentence_len < self._TELEGRAPH_MIN_SENTENCE_LEN
            and function_ratio < self._TELEGRAPH_FUNCTION_WORD_RATIO
        )
        severity = 0.0
        if triggered:
            severity = min(
                1.0,
                (
                    (self._TELEGRAPH_MIN_SENTENCE_LEN - avg_sentence_len) / self._TELEGRAPH_MIN_SENTENCE_LEN
                    + (self._TELEGRAPH_FUNCTION_WORD_RATIO - function_ratio) / self._TELEGRAPH_FUNCTION_WORD_RATIO
                )
                / 2.0,
            )
        return FailureModeSignal(
            mode="telegraphing",
            score=severity,
            threshold=0.0,
            triggered=triggered,
            evidence={
                "avg_sentence_len": avg_sentence_len,
                "function_word_ratio": function_ratio,
                "sentence_count": len(sentences),
                "token_count": len(response_tokens),
            },
        )

    def _drift_signal(
        self, prompt_tokens: list[str], response_tokens: list[str]
    ) -> FailureModeSignal:
        if len(response_tokens) < self._MIN_DRIFT_TOKENS or len(prompt_tokens) < self._MIN_PROMPT_TOKENS:
            return FailureModeSignal(
                mode="drift",
                score=0.0,
                threshold=self._DRIFT_OVERLAP_THRESHOLD,
                triggered=False,
                evidence={
                    "response_token_count": len(response_tokens),
                    "prompt_token_count": len(prompt_tokens),
                },
            )

        prompt_vocab = set(prompt_tokens)
        overlap = sum(1 for token in response_tokens if token in prompt_vocab)
        overlap_ratio = overlap / max(len(response_tokens), 1)
        triggered = overlap_ratio < self._DRIFT_OVERLAP_THRESHOLD
        return FailureModeSignal(
            mode="drift",
            score=1.0 - overlap_ratio,
            threshold=1.0 - self._DRIFT_OVERLAP_THRESHOLD,
            triggered=triggered,
            evidence={
                "overlap_ratio": overlap_ratio,
                "response_token_count": len(response_tokens),
                "prompt_token_count": len(prompt_tokens),
            },
        )

    def _hallucination_signal(self, confidence: float) -> FailureModeSignal:
        triggered = confidence < self._HALLUCINATION_CONFIDENCE_THRESHOLD
        return FailureModeSignal(
            mode="hallucination",
            score=1.0 - confidence,
            threshold=1.0 - self._HALLUCINATION_CONFIDENCE_THRESHOLD,
            triggered=triggered,
            evidence={"confidence": confidence},
        )

    def _hallucination_signal_for_empty(self) -> FailureModeSignal:
        return FailureModeSignal(
            mode="hallucination",
            score=0.0,
            threshold=1.0 - self._HALLUCINATION_CONFIDENCE_THRESHOLD,
            triggered=False,
            evidence={"confidence": None, "skipped": "empty_response"},
        )
