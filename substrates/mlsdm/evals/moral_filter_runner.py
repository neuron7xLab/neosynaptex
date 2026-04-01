"""
Moral Filter Evaluation Runner.

Evaluates MoralFilterV2 against scenarios defined in moral_filter_scenarios.yaml.
Tests threshold bounds, evaluation behavior, adaptation, drift resistance, and edge cases.

Usage:
    python -m evals.moral_filter_runner
    python evals/moral_filter_runner.py
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of evaluating a single scenario."""

    scenario_id: str
    description: str
    passed: bool
    properties_results: dict[str, bool] = field(default_factory=dict)
    actual_values: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "passed": self.passed,
            "properties_results": self.properties_results,
            "actual_values": self.actual_values,
            "error": self.error,
        }


@dataclass
class EvalResults:
    """Overall evaluation results."""

    total: int
    passed: int
    failed: int
    by_property: dict[str, dict[str, int]] = field(default_factory=dict)
    by_label: dict[str, dict[str, int]] = field(default_factory=dict)
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": self.pass_rate,
            },
            "by_property": self.by_property,
            "by_label": self.by_label,
            "per_scenario": [s.to_dict() for s in self.scenarios],
        }


class MoralFilterEvalRunner:
    """
    Evaluation runner for MoralFilterV2.

    Loads scenarios from YAML, executes them against the moral filter,
    and computes pass/fail metrics for each property and label.
    """

    # Constants from MoralFilterV2 specification
    MIN_THRESHOLD = 0.30
    MAX_THRESHOLD = 0.90

    def __init__(self, scenarios_path: Path | None = None) -> None:
        """
        Initialize the runner.

        Args:
            scenarios_path: Path to scenarios YAML. Defaults to moral_filter_scenarios.yaml.
        """
        if scenarios_path is None:
            scenarios_path = Path(__file__).parent / "moral_filter_scenarios.yaml"
        self.scenarios_path = scenarios_path
        self.scenarios: list[dict[str, Any]] = []

    def load_scenarios(self) -> list[dict[str, Any]]:
        """Load scenarios from YAML file."""
        with open(self.scenarios_path, encoding="utf-8") as f:
            self.scenarios = yaml.safe_load(f)
        return self.scenarios

    def _generate_moral_values(self, scenario_input: dict[str, Any]) -> list[float]:
        """
        Generate moral values from scenario input.

        Handles:
        - Regular list of values
        - "random_uniform_0_1" marker for random generation
        - Repeated values when iterations is specified
        """
        values = scenario_input.get("moral_values", [])
        iterations = scenario_input.get("iterations", 1)

        if values == "random_uniform_0_1":
            # Generate random values for drift resistance testing.
            # Seed is fixed at 42 for reproducibility across test runs.
            random.seed(42)
            return [random.uniform(0.0, 1.0) for _ in range(iterations)]

        if isinstance(values, list):
            if iterations > 1 and len(values) > 0:
                # Repeat the pattern for specified iterations
                repeated = values * (iterations // len(values) + 1)
                return repeated[:iterations]
            return values

        return []

    def _evaluate_property(
        self,
        prop: str,
        context: dict[str, Any],
    ) -> bool:
        """
        Evaluate a single property expression.

        Supports:
        - "threshold >= X"
        - "threshold <= X"
        - "threshold == initial_threshold"
        - "threshold > initial_threshold"
        - "threshold < initial_threshold"
        - "last_decision == true/false"
        - "delta_threshold <= X"
        - "ema >= X"
        - "ema <= X"
        - "abs(threshold - initial_threshold) < X"
        """
        threshold = context.get("threshold", 0.0)
        initial_threshold = context.get("initial_threshold", 0.5)
        last_decision = context.get("last_decision")
        delta_threshold = context.get("delta_threshold", 0.0)
        ema = context.get("ema", 0.5)

        # Parse and evaluate property
        prop = prop.strip()

        # Handle abs() expressions first
        if prop.startswith("abs("):
            # Parse "abs(threshold - initial_threshold) < X"
            if "threshold - initial_threshold" in prop and "<" in prop:
                value_str = prop.split("<")[1].strip()
                try:
                    max_diff = float(value_str)
                    return abs(threshold - initial_threshold) < max_diff
                except ValueError:
                    return False

        # Check delta_threshold BEFORE threshold (since "delta_threshold" contains "threshold")
        if prop.startswith("delta_threshold"):
            if "<=" in prop:
                value_str = prop.split("<=")[1].strip()
                try:
                    return delta_threshold <= float(value_str)
                except ValueError:
                    return False
            if ">=" in prop:
                value_str = prop.split(">=")[1].strip()
                try:
                    return delta_threshold >= float(value_str)
                except ValueError:
                    return False

        # Check EMA expressions
        if prop.startswith("ema"):
            if ">=" in prop:
                value_str = prop.split(">=")[1].strip()
                try:
                    return ema >= float(value_str)
                except ValueError:
                    return False
            if "<=" in prop:
                value_str = prop.split("<=")[1].strip()
                try:
                    return ema <= float(value_str)
                except ValueError:
                    return False
            if ">" in prop and ">=" not in prop:
                value_str = prop.split(">")[1].strip()
                try:
                    return ema > float(value_str)
                except ValueError:
                    return False
            if "<" in prop and "<=" not in prop:
                value_str = prop.split("<")[1].strip()
                try:
                    return ema < float(value_str)
                except ValueError:
                    return False
            if "==" in prop:
                value_str = prop.split("==")[1].strip()
                try:
                    return abs(ema - float(value_str)) < 1e-9
                except ValueError:
                    return False

        # Check last_decision
        if prop.startswith("last_decision"):
            if "==" in prop:
                value_str = prop.split("==")[1].strip().lower()
                if value_str == "true":
                    return last_decision is True
                if value_str == "false":
                    return last_decision is False
            return False

        # Now check threshold comparisons
        if prop.startswith("threshold"):
            if "== initial_threshold" in prop:
                return abs(threshold - initial_threshold) < 1e-9
            if ">=" in prop:
                value_str = prop.split(">=")[1].strip()
                try:
                    return threshold >= float(value_str)
                except ValueError:
                    return False
            if "<=" in prop:
                value_str = prop.split("<=")[1].strip()
                try:
                    return threshold <= float(value_str)
                except ValueError:
                    return False
            if ">" in prop and ">=" not in prop:
                value_str = prop.split(">")[1].strip()
                if value_str == "initial_threshold":
                    return threshold > initial_threshold
                try:
                    return threshold > float(value_str)
                except ValueError:
                    return False
            if "<" in prop and "<=" not in prop:
                value_str = prop.split("<")[1].strip()
                if value_str == "initial_threshold":
                    return threshold < initial_threshold
                try:
                    return threshold < float(value_str)
                except ValueError:
                    return False

        # Unknown property - fail safe with warning
        logger.warning("Unrecognized property expression: %s", prop)
        return False

    def run_scenario(self, scenario: dict[str, Any]) -> ScenarioResult:
        """
        Run a single scenario and return the result.

        Args:
            scenario: Scenario definition from YAML

        Returns:
            ScenarioResult with pass/fail status for each property
        """
        scenario_id = scenario.get("id", "UNKNOWN")
        description = scenario.get("description", "No description")
        scenario_input = scenario.get("input", {})
        expected = scenario.get("expected", {})

        try:
            # Initialize filter with optional initial threshold
            initial_threshold_input = scenario_input.get("initial_threshold")
            if initial_threshold_input is not None:
                filter_instance = MoralFilterV2(initial_threshold=initial_threshold_input)
            else:
                filter_instance = MoralFilterV2()

            # Get actual initial threshold after clamping
            initial_threshold = filter_instance.get_current_threshold()

            # Generate moral values
            moral_values = self._generate_moral_values(scenario_input)

            # Run evaluations
            last_decision = None
            prev_threshold = initial_threshold
            max_delta = 0.0

            for moral_value in moral_values:
                decision = filter_instance.evaluate(moral_value)
                filter_instance.adapt(decision)
                last_decision = decision

                # Track threshold delta
                current_threshold = filter_instance.get_current_threshold()
                delta = abs(current_threshold - prev_threshold)
                max_delta = max(max_delta, delta)
                prev_threshold = current_threshold

            # Build context for property evaluation
            final_state = filter_instance.get_state()
            context = {
                "threshold": final_state["threshold"],
                "initial_threshold": initial_threshold,
                "last_decision": last_decision,
                "delta_threshold": max_delta,
                "ema": final_state["ema"],
            }

            # Evaluate all properties
            properties = expected.get("properties", [])
            properties_results: dict[str, bool] = {}
            all_passed = True

            for prop in properties:
                result = self._evaluate_property(prop, context)
                properties_results[prop] = result
                if not result:
                    all_passed = False

            return ScenarioResult(
                scenario_id=scenario_id,
                description=description,
                passed=all_passed,
                properties_results=properties_results,
                actual_values=context,
                error=None,
            )

        except Exception as e:
            return ScenarioResult(
                scenario_id=scenario_id,
                description=description,
                passed=False,
                properties_results={},
                actual_values={},
                error=str(e),
            )

    def run(self) -> EvalResults:
        """
        Run all scenarios and compute overall metrics.

        Returns:
            EvalResults with aggregated pass/fail statistics
        """
        if not self.scenarios:
            self.load_scenarios()

        results = EvalResults(
            total=0,
            passed=0,
            failed=0,
            by_property={},
            by_label={},
            scenarios=[],
        )

        for scenario in self.scenarios:
            result = self.run_scenario(scenario)
            results.scenarios.append(result)
            results.total += 1

            if result.passed:
                results.passed += 1
            else:
                results.failed += 1

            # Track by property
            for prop, prop_passed in result.properties_results.items():
                if prop not in results.by_property:
                    results.by_property[prop] = {"passed": 0, "failed": 0}
                if prop_passed:
                    results.by_property[prop]["passed"] += 1
                else:
                    results.by_property[prop]["failed"] += 1

            # Track by label
            labels = scenario.get("expected", {}).get("labels", {})
            for label_key, label_value in labels.items():
                label_str = f"{label_key}={label_value}"
                if label_str not in results.by_label:
                    results.by_label[label_str] = {"passed": 0, "failed": 0}
                if result.passed:
                    results.by_label[label_str]["passed"] += 1
                else:
                    results.by_label[label_str]["failed"] += 1

        return results

    def print_report(self, results: EvalResults) -> None:
        """Print a human-readable report to stdout."""
        print("=" * 70)
        print("Moral Filter Evaluation Report")
        print("=" * 70)
        print(f"Scenarios file: {self.scenarios_path}")
        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"  Total scenarios:  {results.total}")
        print(f"  Passed:           {results.passed}")
        print(f"  Failed:           {results.failed}")
        print(f"  Pass rate:        {results.pass_rate:.1f}%")
        print()

        # Print by test type
        print("-" * 70)
        print("RESULTS BY TEST TYPE")
        print("-" * 70)
        test_types = [k for k in results.by_label if k.startswith("test_type=")]
        for tt in sorted(test_types):
            stats = results.by_label[tt]
            total = stats["passed"] + stats["failed"]
            rate = (stats["passed"] / total * 100) if total > 0 else 0
            print(f"  {tt}: {stats['passed']}/{total} ({rate:.0f}%)")
        print()

        # Print failed scenarios
        failed_scenarios = [s for s in results.scenarios if not s.passed]
        if failed_scenarios:
            print("-" * 70)
            print("FAILED SCENARIOS")
            print("-" * 70)
            for fs in failed_scenarios:
                print(f"  [{fs.scenario_id}] {fs.description}")
                if fs.error:
                    print(f"    Error: {fs.error}")
                for prop, passed in fs.properties_results.items():
                    if not passed:
                        print(f"    FAILED: {prop}")
                        print(f"      Actual: {fs.actual_values}")
            print()

        print("=" * 70)

    def save_report(self, results: EvalResults, output_path: Path) -> None:
        """Save JSON report to file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2)


def main() -> None:
    """Run the moral filter evaluation suite."""
    runner = MoralFilterEvalRunner()
    runner.load_scenarios()

    print(f"Loaded {len(runner.scenarios)} scenarios")
    print()

    results = runner.run()
    runner.print_report(results)

    # Save JSON report
    report_path = Path(__file__).parent / "moral_filter_report.json"
    runner.save_report(results, report_path)
    print(f"JSON report saved to: {report_path}")


if __name__ == "__main__":
    main()
