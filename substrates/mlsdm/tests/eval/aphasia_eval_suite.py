"""
Aphasia-Broca Evaluation Suite.

Uses AphasiaBrocaDetector to evaluate:
- true_positive_rate (TPR) for telegraphic speech detection
- true_negative_rate (TNR) for normal speech classification
- false_positive_rate (FPR) for incorrectly flagged normal speech
- false_negative_rate (FNR) for missed telegraphic speech
- overall_accuracy for combined performance
- mean severity for telegraphic cases

Corpus: tests/eval/aphasia_corpus.json
Run locally: python tests/eval/aphasia_eval_suite.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector

# Minimum corpus sizes for reliable metrics
MIN_TELEGRAPHIC_SAMPLES = 50
MIN_NORMAL_SAMPLES = 50


@dataclass
class AphasiaEvalResult:
    """Evaluation results for Aphasia-Broca detection.

    Metrics:
        true_positive_rate (TPR): TP / (TP + FN) - sensitivity for telegraphic
        true_negative_rate (TNR): TN / (TN + FP) - specificity for normal
        false_positive_rate (FPR): FP / (FP + TN) = 1 - TNR
        false_negative_rate (FNR): FN / (FN + TP) = 1 - TPR
        overall_accuracy: (TP + TN) / (TP + TN + FP + FN)
        balanced_accuracy: (TPR + TNR) / 2
        mean_severity_telegraphic: Average severity score for aphasic samples
    """

    true_positive_rate: float  # TPR = TP / (TP + FN)
    true_negative_rate: float  # TNR = TN / (TN + FP)
    false_positive_rate: float  # FPR = FP / (FP + TN)
    false_negative_rate: float  # FNR = FN / (FN + TP)
    overall_accuracy: float  # (TP + TN) / Total
    balanced_accuracy: float  # (TPR + TNR) / 2
    mean_severity_telegraphic: float
    # Counts for transparency
    true_positives: int  # Correctly detected telegraphic
    true_negatives: int  # Correctly classified normal
    false_positives: int  # Normal incorrectly flagged as aphasic
    false_negatives: int  # Telegraphic missed (classified as normal)
    telegraphic_samples: int
    normal_samples: int


class AphasiaEvalSuite:
    """Evaluation suite for Aphasia-Broca detector.

    Loads a corpus of telegraphic (aphasic) and normal samples,
    runs the AphasiaBrocaDetector on each, and computes standard
    classification metrics.
    """

    def __init__(
        self,
        corpus_path: str | Path,
        severity_threshold: float | None = None,
    ) -> None:
        """Initialize the evaluation suite.

        Args:
            corpus_path: Path to the JSON corpus file.
            severity_threshold: Optional threshold for severity.
                If not specified, uses the detector's is_aphasic flag.
        """
        self.corpus_path = Path(corpus_path)
        self.detector = AphasiaBrocaDetector()
        self.severity_threshold = severity_threshold

    def load_corpus(self) -> dict[str, list[str]]:
        """Load corpus from JSON file.

        Returns:
            Dict with 'telegraphic' and 'normal' lists of text samples.
        """
        data = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        return {
            "telegraphic": list(data.get("telegraphic", [])),
            "normal": list(data.get("normal", [])),
        }

    def _is_detected_aphasic(self, report: dict[str, Any]) -> bool:
        """Determine if a sample is detected as aphasic.

        Uses severity_threshold if set, otherwise uses is_aphasic flag.
        """
        if self.severity_threshold is not None:
            return report["severity"] >= self.severity_threshold
        return report["is_aphasic"]

    def run(self) -> AphasiaEvalResult:
        """Run evaluation and compute metrics.

        Returns:
            AphasiaEvalResult with all classification metrics.

        Raises:
            ValueError: If corpus is missing required samples.
        """
        corpus = self.load_corpus()
        tele = corpus["telegraphic"]
        norm = corpus["normal"]

        if not tele:
            raise ValueError("Corpus must contain at least one telegraphic sample")
        if not norm:
            raise ValueError("Corpus must contain at least one normal sample")

        # Confusion matrix components
        tp = 0  # True Positives: telegraphic correctly detected
        fn = 0  # False Negatives: telegraphic missed
        tn = 0  # True Negatives: normal correctly classified
        fp = 0  # False Positives: normal incorrectly flagged

        sev_sum = 0.0

        # Evaluate telegraphic samples (expected: is_aphasic=True)
        for text in tele:
            report = self.detector.analyze(text)
            if self._is_detected_aphasic(report):
                tp += 1
            else:
                fn += 1
            sev_sum += float(report["severity"])

        # Evaluate normal samples (expected: is_aphasic=False)
        for text in norm:
            report = self.detector.analyze(text)
            if not self._is_detected_aphasic(report):
                tn += 1
            else:
                fp += 1

        # Calculate metrics
        total = len(tele) + len(norm)
        tpr = tp / len(tele) if tele else 0.0
        tnr = tn / len(norm) if norm else 0.0
        fpr = fp / len(norm) if norm else 0.0
        fnr = fn / len(tele) if tele else 0.0
        overall_accuracy = (tp + tn) / total if total > 0 else 0.0
        balanced_accuracy = (tpr + tnr) / 2.0
        mean_severity = sev_sum / len(tele) if tele else 0.0

        return AphasiaEvalResult(
            true_positive_rate=tpr,
            true_negative_rate=tnr,
            false_positive_rate=fpr,
            false_negative_rate=fnr,
            overall_accuracy=overall_accuracy,
            balanced_accuracy=balanced_accuracy,
            mean_severity_telegraphic=mean_severity,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            telegraphic_samples=len(tele),
            normal_samples=len(norm),
        )


def main() -> None:
    """Run the evaluation suite and print results."""
    corpus_path = Path(__file__).parent / "aphasia_corpus.json"
    if not corpus_path.exists():
        print(f"Corpus not found: {corpus_path}")
        return

    suite = AphasiaEvalSuite(corpus_path=corpus_path)
    result = suite.run()

    print("=" * 60)
    print("Aphasia-Broca Evaluation Results")
    print("=" * 60)
    print(f"Corpus: {corpus_path}")
    print(f"Telegraphic samples: {result.telegraphic_samples}")
    print(f"Normal samples: {result.normal_samples}")
    print("-" * 60)
    print("Confusion Matrix:")
    print(f"  True Positives (TP):  {result.true_positives}")
    print(f"  True Negatives (TN):  {result.true_negatives}")
    print(f"  False Positives (FP): {result.false_positives}")
    print(f"  False Negatives (FN): {result.false_negatives}")
    print("-" * 60)
    print("Metrics:")
    print(f"  True Positive Rate (TPR/Sensitivity): {result.true_positive_rate:.2%}")
    print(f"  True Negative Rate (TNR/Specificity): {result.true_negative_rate:.2%}")
    print(f"  False Positive Rate (FPR):            {result.false_positive_rate:.2%}")
    print(f"  False Negative Rate (FNR):            {result.false_negative_rate:.2%}")
    print(f"  Overall Accuracy:                     {result.overall_accuracy:.2%}")
    print(f"  Balanced Accuracy:                    {result.balanced_accuracy:.2%}")
    print(f"  Mean Severity (telegraphic):          {result.mean_severity_telegraphic:.3f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
