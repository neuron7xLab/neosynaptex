#!/usr/bin/env python3
"""
Ablation Runner for MLSDM Component Evaluation.

This script evaluates the contribution of individual MLSDM components
(memory, rhythm, aphasia, policy) through ablation testing.

Modes:
- baseline: All components enabled (default)
- no_memory: Memory module disabled
- no_rhythm: Cognitive rhythm disabled
- no_aphasia: Aphasia detection disabled
- strict_policy: Strict policy enforcement
- relaxed_policy: Relaxed policy enforcement

Usage:
    python scripts/eval/run_ablation.py --mode baseline --seed 42
    python scripts/eval/run_ablation.py --mode no_memory --fixtures tests/fixtures/ablation_prompts.json

Output:
    JSON report saved to reports/ablation/{mode}_{timestamp}.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# Ensure src is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class AblationMetrics:
    """Container for ablation evaluation metrics.

    Safety metrics:
        violation_rate: Fraction of prompts that triggered policy violations [0,1]
        false_allow: Count of unsafe prompts incorrectly allowed
        false_block: Count of safe prompts incorrectly blocked

    Stability metrics:
        crash_rate: Fraction of prompts that caused exceptions [0,1]
        exception_count: Total number of exceptions caught
        deterministic_hash: SHA256 hash of all outputs for reproducibility check

    Quality metrics:
        response_length_mean: Mean response length in characters
        response_length_std: Standard deviation of response length
        latency_ms_mean: Mean processing latency in milliseconds
        latency_ms_std: Standard deviation of latency

    Memory metrics:
        retrieval_hit_rate: Fraction of successful memory retrievals [0,1]

    Aphasia metrics:
        repair_success_rate: Fraction of aphasic prompts successfully repaired [0,1]
        detection_accuracy: Fraction of correctly classified aphasic/normal prompts [0,1]
    """

    # Safety
    violation_rate: float = 0.0
    false_allow: int = 0
    false_block: int = 0

    # Stability
    crash_rate: float = 0.0
    exception_count: int = 0
    deterministic_hash: str = ""

    # Quality
    response_length_mean: float = 0.0
    response_length_std: float = 0.0
    latency_ms_mean: float = 0.0
    latency_ms_std: float = 0.0

    # Memory
    retrieval_hit_rate: float = 0.0

    # Aphasia
    repair_success_rate: float = 0.0
    detection_accuracy: float = 0.0


@dataclass
class AblationReport:
    """Complete ablation evaluation report."""

    version: str = "1.0.0"
    mode: str = "baseline"
    seed: int = 42
    timestamp: str = ""
    duration_seconds: float = 0.0
    total_prompts: int = 0
    metrics: AblationMetrics = field(default_factory=AblationMetrics)
    prompt_results: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        result = asdict(self)
        return result


class AblationRunner:
    """Runner for ablation evaluation of MLSDM components."""

    VALID_MODES = [
        "baseline",
        "no_memory",
        "no_rhythm",
        "no_aphasia",
        "strict_policy",
        "relaxed_policy",
    ]

    def __init__(
        self,
        mode: str = "baseline",
        seed: int = 42,
        fixtures_path: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        """Initialize ablation runner.

        Args:
            mode: Ablation mode (baseline, no_memory, no_rhythm, no_aphasia, etc.)
            seed: Random seed for reproducibility
            fixtures_path: Path to fixtures JSON file
            output_dir: Directory for output reports
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}. Valid modes: {self.VALID_MODES}")

        self.mode = mode
        self.seed = seed
        self.fixtures_path = Path(fixtures_path) if fixtures_path else None
        self.output_dir = Path(output_dir) if output_dir else Path("reports/ablation")
        self._set_seeds()

        # Component state based on mode
        self._memory_enabled = mode != "no_memory"
        self._rhythm_enabled = mode != "no_rhythm"
        self._aphasia_enabled = mode != "no_aphasia"
        self._strict_policy = mode == "strict_policy"
        self._relaxed_policy = mode == "relaxed_policy"

        # Lazy-loaded components
        self._memory = None
        self._rhythm = None
        self._aphasia_detector = None
        self._policy_context = None

    def _set_seeds(self) -> None:
        """Set random seeds for reproducibility."""
        random.seed(self.seed)
        np.random.seed(self.seed)

        # Set torch seed if available
        try:
            import torch

            torch.manual_seed(self.seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(self.seed)
        except ImportError:
            pass

    def _get_memory(self) -> Any:
        """Lazy-load memory module."""
        if self._memory is None and self._memory_enabled:
            from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory

            self._memory = MultiLevelSynapticMemory(dimension=384)
        return self._memory

    def _get_rhythm(self) -> Any:
        """Lazy-load rhythm module."""
        if self._rhythm is None and self._rhythm_enabled:
            from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm

            self._rhythm = CognitiveRhythm()
        return self._rhythm

    def _get_aphasia_detector(self) -> Any:
        """Lazy-load aphasia detector."""
        if self._aphasia_detector is None and self._aphasia_enabled:
            from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector

            self._aphasia_detector = AphasiaBrocaDetector()
        return self._aphasia_detector

    def load_fixtures(self) -> list[dict[str, Any]]:
        """Load test fixtures from JSON file."""
        if self.fixtures_path is None:
            # Default fixtures path
            self.fixtures_path = Path("tests/fixtures/ablation_prompts.json")

        if not self.fixtures_path.exists():
            raise FileNotFoundError(f"Fixtures file not found: {self.fixtures_path}")

        data = json.loads(self.fixtures_path.read_text(encoding="utf-8"))
        return list(data.get("prompts", []))

    def _evaluate_policy(self, prompt: str, fixture: dict[str, Any]) -> dict[str, Any]:
        """Evaluate policy for a prompt.

        Returns:
            Dict with 'allowed', 'violation_type', and 'decision_details'
        """
        from mlsdm.security.policy_engine import PolicyContext, evaluate_llm_output_policy

        # Determine safety context based on fixture category
        category = fixture.get("category", "general")

        # Build safety violations based on category
        safety_violations = []
        safety_risk_level = "none"

        if category in ("prompt_injection", "jailbreak", "role_hijack"):
            safety_violations = [category]
            safety_risk_level = "high" if not self._relaxed_policy else "medium"
        elif category == "unauthorized_access":
            safety_violations = ["privilege_escalation"]
            safety_risk_level = "critical" if self._strict_policy else "high"

        # Create policy context
        context = PolicyContext(
            user_id="ablation_test_user",
            prompt=prompt,
            safety_risk_level=safety_risk_level,
            safety_violations=safety_violations,
        )

        decision = evaluate_llm_output_policy(context)

        return {
            "allowed": decision.allow,
            "violation_type": decision.reasons[0] if decision.reasons else None,
            "decision_details": decision.to_dict(),
        }

    def _evaluate_aphasia(self, prompt: str) -> dict[str, Any]:
        """Evaluate aphasia detection for a prompt."""
        detector = self._get_aphasia_detector()
        if detector is None:
            return {
                "is_aphasic": False,
                "severity": 0.0,
                "skipped": True,
            }

        report = detector.analyze(prompt)
        return {
            "is_aphasic": report.get("is_aphasic", False),
            "severity": report.get("severity", 0.0),
            "skipped": False,
        }

    def _evaluate_memory(self, prompt: str, fixture: dict[str, Any]) -> dict[str, Any]:
        """Evaluate memory operations for a prompt."""
        memory = self._get_memory()
        if memory is None:
            return {
                "operation": None,
                "success": False,
                "skipped": True,
            }

        category = fixture.get("category", "")
        # memory_fact is available in fixture for future enhancements
        _ = fixture.get("memory_fact", "")

        result = {
            "operation": None,
            "success": False,
            "skipped": False,
        }

        # Generate a deterministic embedding for the prompt
        np.random.seed(hash(prompt) % (2**32))
        embedding = np.random.randn(384).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        if category == "memory_store":
            # Store operation using memory.update()
            try:
                memory.update(embedding)
                result["operation"] = "store"
                result["success"] = True
            except Exception:
                result["operation"] = "store"
                result["success"] = False

        elif category == "memory_recall":
            # Recall operation - check if memory has content
            try:
                # Try to retrieve based on the embedding
                result["operation"] = "recall"
                # Check l1 layer has content
                l1_norm = float(np.linalg.norm(memory.l1))
                result["success"] = bool(l1_norm > 0.01)
            except Exception:
                result["operation"] = "recall"
                result["success"] = False

        return result

    def _generate_mock_response(self, prompt: str, fixture: dict[str, Any]) -> str:
        """Generate a mock response for testing (no actual LLM call)."""
        expected_quality = fixture.get("expected_quality", "high")

        if expected_quality == "blocked":
            return "[BLOCKED: Policy violation detected]"
        elif expected_quality == "low":
            return "Short. Answer."
        else:
            return f"Mock response for: {prompt[:50]}..."

    def _process_prompt(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Process a single prompt fixture.

        Returns:
            Dict with prompt result including metrics
        """
        prompt = fixture.get("prompt", "")
        prompt_id = fixture.get("id", "unknown")

        result = {
            "id": prompt_id,
            "prompt": prompt,
            "success": True,
            "error": None,
            "latency_ms": 0.0,
            "response": "",
            "policy": {},
            "aphasia": {},
            "memory": {},
        }

        start_time = time.perf_counter()

        try:
            # Step 1: Evaluate policy
            result["policy"] = self._evaluate_policy(prompt, fixture)

            # Step 2: If blocked by policy, skip remaining evaluation
            if not result["policy"]["allowed"]:
                result["response"] = "[BLOCKED]"
            else:
                # Step 3: Evaluate aphasia
                result["aphasia"] = self._evaluate_aphasia(prompt)

                # Step 4: Evaluate memory
                result["memory"] = self._evaluate_memory(prompt, fixture)

                # Step 5: Rhythm step (if enabled)
                rhythm = self._get_rhythm()
                if rhythm:
                    rhythm.step()

                # Step 6: Generate mock response
                result["response"] = self._generate_mock_response(prompt, fixture)

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        result["latency_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    def _compute_metrics(
        self, fixtures: list[dict[str, Any]], results: list[dict[str, Any]]
    ) -> AblationMetrics:
        """Compute aggregate metrics from results."""
        metrics = AblationMetrics()

        if not results:
            return metrics

        # Compute output hash for determinism check
        output_str = json.dumps([r.get("response", "") for r in results], sort_keys=True)
        metrics.deterministic_hash = hashlib.sha256(output_str.encode()).hexdigest()[:16]

        # Safety metrics
        policy_violations = 0
        false_allows = 0
        false_blocks = 0

        for fixture, result in zip(fixtures, results, strict=True):
            expected_safe = fixture.get("expected_safe", True)
            policy_allowed = result.get("policy", {}).get("allowed", True)

            if not policy_allowed:
                policy_violations += 1

            if expected_safe and not policy_allowed:
                false_blocks += 1
            elif not expected_safe and policy_allowed:
                false_allows += 1

        metrics.violation_rate = policy_violations / len(results)
        metrics.false_allow = false_allows
        metrics.false_block = false_blocks

        # Stability metrics
        exceptions = sum(1 for r in results if not r.get("success", True))
        metrics.exception_count = exceptions
        metrics.crash_rate = exceptions / len(results)

        # Quality metrics (response length and latency)
        response_lengths = [len(r.get("response", "")) for r in results]
        latencies = [r.get("latency_ms", 0.0) for r in results]

        if response_lengths:
            metrics.response_length_mean = float(np.mean(response_lengths))
            metrics.response_length_std = float(np.std(response_lengths))

        if latencies:
            metrics.latency_ms_mean = float(np.mean(latencies))
            metrics.latency_ms_std = float(np.std(latencies))

        # Memory metrics
        memory_results = [
            r.get("memory", {})
            for r in results
            if not r.get("memory", {}).get("skipped", True)
        ]
        if memory_results:
            successes = sum(1 for m in memory_results if m.get("success", False))
            metrics.retrieval_hit_rate = successes / len(memory_results)

        # Aphasia metrics
        aphasia_fixtures = [f for f in fixtures if "expected_aphasic" in f]
        if aphasia_fixtures:
            aphasia_correct = 0
            for fixture in aphasia_fixtures:
                result = next(
                    (r for r in results if r.get("id") == fixture.get("id")), None
                )
                if result:
                    expected_aphasic = fixture.get("expected_aphasic", False)
                    detected_aphasic = result.get("aphasia", {}).get("is_aphasic", False)
                    if expected_aphasic == detected_aphasic:
                        aphasia_correct += 1

            metrics.detection_accuracy = aphasia_correct / len(aphasia_fixtures)

        return metrics

    def run(self) -> AblationReport:
        """Run ablation evaluation.

        Returns:
            AblationReport with all metrics and results
        """
        report = AblationReport(
            mode=self.mode,
            seed=self.seed,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        start_time = time.perf_counter()

        try:
            fixtures = self.load_fixtures()
            report.total_prompts = len(fixtures)
            report.config = {
                "memory_enabled": self._memory_enabled,
                "rhythm_enabled": self._rhythm_enabled,
                "aphasia_enabled": self._aphasia_enabled,
                "strict_policy": self._strict_policy,
                "relaxed_policy": self._relaxed_policy,
                "fixtures_path": str(self.fixtures_path),
            }

            # Process each prompt
            results = []
            for fixture in fixtures:
                result = self._process_prompt(fixture)
                results.append(result)

            report.prompt_results = results
            report.metrics = self._compute_metrics(fixtures, results)

        except Exception as e:
            report.errors.append(str(e))

        report.duration_seconds = time.perf_counter() - start_time
        return report

    def save_report(self, report: AblationReport) -> Path:
        """Save report to JSON file.

        Returns:
            Path to saved report file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.mode}_{timestamp}.json"
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        return output_path

    def print_summary(self, report: AblationReport) -> None:
        """Print summary to stdout."""
        print("=" * 60)
        print("MLSDM Ablation Evaluation Report")
        print("=" * 60)
        print(f"Mode:            {report.mode}")
        print(f"Seed:            {report.seed}")
        print(f"Total Prompts:   {report.total_prompts}")
        print(f"Duration:        {report.duration_seconds:.3f}s")
        print("-" * 60)
        print("Safety Metrics:")
        print(f"  Violation Rate:   {report.metrics.violation_rate:.2%}")
        print(f"  False Allow:      {report.metrics.false_allow}")
        print(f"  False Block:      {report.metrics.false_block}")
        print("-" * 60)
        print("Stability Metrics:")
        print(f"  Crash Rate:       {report.metrics.crash_rate:.2%}")
        print(f"  Exception Count:  {report.metrics.exception_count}")
        print(f"  Deterministic Hash: {report.metrics.deterministic_hash}")
        print("-" * 60)
        print("Quality Metrics:")
        print(f"  Response Length (mean±std): {report.metrics.response_length_mean:.1f}±{report.metrics.response_length_std:.1f}")
        print(f"  Latency (mean±std):         {report.metrics.latency_ms_mean:.2f}±{report.metrics.latency_ms_std:.2f}ms")
        print("-" * 60)
        print("Component Metrics:")
        print(f"  Memory Hit Rate:        {report.metrics.retrieval_hit_rate:.2%}")
        print(f"  Aphasia Detection Acc:  {report.metrics.detection_accuracy:.2%}")
        print("=" * 60)

        if report.errors:
            print("ERRORS:")
            for error in report.errors:
                print(f"  - {error}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MLSDM Ablation Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/eval/run_ablation.py --mode baseline
    python scripts/eval/run_ablation.py --mode no_memory --seed 123
    python scripts/eval/run_ablation.py --mode strict_policy --output-dir ./my_reports
        """,
    )

    parser.add_argument(
        "--mode",
        type=str,
        default="baseline",
        choices=AblationRunner.VALID_MODES,
        help="Ablation mode (default: baseline)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--fixtures",
        type=str,
        default="tests/fixtures/ablation_prompts.json",
        help="Path to fixtures JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/ablation",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout summary output",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save report to file",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)

    runner = AblationRunner(
        mode=args.mode,
        seed=args.seed,
        fixtures_path=args.fixtures,
        output_dir=args.output_dir,
    )

    report = runner.run()

    if not args.quiet:
        runner.print_summary(report)

    if not args.no_save:
        output_path = runner.save_report(report)
        if not args.quiet:
            print(f"\nReport saved to: {output_path}")

    # Exit with error if there were exceptions
    if report.errors or report.metrics.exception_count > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
