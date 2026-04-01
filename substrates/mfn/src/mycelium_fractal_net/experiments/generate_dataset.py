"""
Dataset Generation Pipeline for MyceliumFractalNet.

Generates experimental datasets by running simulations with parameter sweeps
and extracting features as defined in MFN_FEATURE_SCHEMA.md.

Usage:
    python -m mycelium_fractal_net.experiments.generate_dataset \
        --num-samples 200 --output data/mfn_dataset.parquet

Features:
- ConfigSampler for generating valid simulation configurations
- Reproducible via seed control
- Error handling for StabilityError/ValueOutOfRangeError
- Output in Parquet format (NPZ fallback)

Reference: docs/MFN_DATASET_SPEC.md
"""

from __future__ import annotations

import argparse
import datetime
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from mycelium_fractal_net.analytics.legacy_features import (
    FeatureConfig,
    FeatureVector,
    compute_features,
)
from mycelium_fractal_net.core import (
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    ReactionDiffusionMetrics,
    StabilityError,
    ValueOutOfRangeError,
)
from mycelium_fractal_net.core.exceptions import NumericalInstabilityError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _get_mfn_version() -> str:
    """Get MyceliumFractalNet version dynamically."""
    try:
        from importlib.metadata import version

        return version("mycelium-fractal-net")
    except Exception:
        # Fallback if package metadata not available
        return "0.1.0"


MFN_VERSION = _get_mfn_version()

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# === Constants ===
DEFAULT_OUTPUT_PATH = Path("data/mfn_dataset.parquet")
DEFAULT_NUM_SAMPLES = 200
MAX_RETRIES = 3


@dataclass
class ConfigSampler:
    """
    Generates valid SimulationConfig instances within specified parameter ranges.

    All parameters are constrained to valid ranges from MFN_MATH_MODEL.md:
    - alpha (diffusion): Must be < 0.25 for CFL stability
    - turing_threshold: Must be in [0, 1]
    - grid_size: Minimum 4 for meaningful simulation

    Attributes
    ----------
    grid_sizes : list[int]
        Grid sizes to sample from. Default [32, 64].
    steps_range : tuple[int, int]
        (min, max) steps to sample. Default (50, 200).
    alpha_range : tuple[float, float]
        (min, max) diffusion coefficient. Default (0.10, 0.20).
    turing_values : list[bool]
        Turing enabled values to sample. Default [True, False].
    spike_prob_range : tuple[float, float]
        (min, max) spike probability. Default (0.15, 0.35).
    turing_threshold_range : tuple[float, float]
        (min, max) Turing threshold. Default (0.65, 0.85).
    base_seed : int
        Base seed for reproducibility. Default 42.
    """

    grid_sizes: list[int] = field(default_factory=lambda: [32, 64])
    steps_range: tuple[int, int] = (50, 200)
    alpha_range: tuple[float, float] = (0.10, 0.20)
    turing_values: list[bool] = field(default_factory=lambda: [True, False])
    spike_prob_range: tuple[float, float] = (0.15, 0.35)
    turing_threshold_range: tuple[float, float] = (0.65, 0.85)
    base_seed: int = 42

    def __post_init__(self) -> None:
        """Validate parameter ranges."""
        if self.alpha_range[1] >= 0.25:
            raise ValueError(
                f"alpha_range max ({self.alpha_range[1]}) must be < 0.25 for CFL stability"
            )
        if any(g < 4 for g in self.grid_sizes):
            raise ValueError("All grid_sizes must be >= 4")
        if self.steps_range[0] < 1:
            raise ValueError("steps_range min must be >= 1")

    def sample(
        self,
        num_samples: int,
        rng: np.random.Generator | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Generate num_samples configuration dictionaries.

        Parameters
        ----------
        num_samples : int
            Number of configurations to generate.
        rng : np.random.Generator | None
            Random generator. If None, uses base_seed.

        Yields
        ------
        dict
            Configuration dictionary for each sample.
        """
        if rng is None:
            rng = np.random.default_rng(self.base_seed)

        for sim_id in range(num_samples):
            # Sample parameters
            grid_size = int(rng.choice(self.grid_sizes))
            steps = int(rng.integers(self.steps_range[0], self.steps_range[1] + 1))
            alpha = float(rng.uniform(self.alpha_range[0], self.alpha_range[1]))
            turing_enabled = bool(rng.choice(self.turing_values))
            spike_prob = float(rng.uniform(self.spike_prob_range[0], self.spike_prob_range[1]))
            turing_threshold = float(
                rng.uniform(self.turing_threshold_range[0], self.turing_threshold_range[1])
            )

            # Generate reproducible seed for this simulation
            random_seed = self.base_seed + sim_id

            yield {
                "sim_id": sim_id,
                "grid_size": grid_size,
                "steps": steps,
                "alpha": alpha,
                "turing_enabled": turing_enabled,
                "spike_probability": spike_prob,
                "turing_threshold": turing_threshold,
                "random_seed": random_seed,
            }


@dataclass
class SweepConfig:
    """Backward-compatible sweep configuration used by legacy tests and scripts."""

    grid_sizes: list[int] | None = None
    steps_list: list[int] | None = None
    alpha_values: list[float] | None = None
    turing_values: list[bool] | None = None
    seeds_per_config: int = 3
    base_seed: int = 42
    spike_probability: float = 0.25
    turing_threshold: float = 0.75

    def __post_init__(self) -> None:
        if self.grid_sizes is None:
            self.grid_sizes = [32, 64]
        if self.steps_list is None:
            self.steps_list = [50, 100]
        if self.alpha_values is None:
            self.alpha_values = [0.10, 0.15, 0.20]
        if self.turing_values is None:
            self.turing_values = [True, False]
        if any(g < 4 for g in self.grid_sizes):
            raise ValueError("All grid_sizes must be >= 4")
        if any(a >= 0.25 for a in self.alpha_values):
            raise ValueError("alpha_values must all be < 0.25 for CFL stability")


def _generate_sweep_configs(sweep: SweepConfig) -> list[dict[str, Any]]:
    """Expand legacy SweepConfig into explicit parameter dictionaries."""
    configs: list[dict[str, Any]] = []
    sim_id = 0
    for grid_size in sweep.grid_sizes or []:
        for steps in sweep.steps_list or []:
            for alpha in sweep.alpha_values or []:
                for turing_enabled in sweep.turing_values or []:
                    for _ in range(sweep.seeds_per_config):
                        configs.append(
                            {
                                "sim_id": sim_id,
                                "grid_size": int(grid_size),
                                "steps": int(steps),
                                "alpha": float(alpha),
                                "turing_enabled": bool(turing_enabled),
                                "spike_probability": float(sweep.spike_probability),
                                "turing_threshold": float(sweep.turing_threshold),
                                "random_seed": int(sweep.base_seed + sim_id),
                            }
                        )
                        sim_id += 1
    return configs


def to_record(
    config: dict[str, Any],
    features: FeatureVector,
    *,
    metrics: ReactionDiffusionMetrics,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Convert simulation config and features to a flat dataset record.

    Parameters
    ----------
    config : dict
        Simulation configuration dictionary.
    features : FeatureVector
        Extracted features from simulation.
    metrics : ReactionDiffusionMetrics
        Simulation metrics.
    timestamp : str | None
        ISO timestamp. If None, uses current time.

    Returns
    -------
    dict
        Flat dictionary with all record fields.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record: dict[str, Any] = {
        # Configuration fields
        "sim_id": config["sim_id"],
        "random_seed": config["random_seed"],
        "grid_size": config["grid_size"],
        "steps": config["steps"],
        "alpha": config["alpha"],
        "turing_enabled": config["turing_enabled"],
        "spike_probability": config.get("spike_probability", 0.25),
        "turing_threshold": config.get("turing_threshold", 0.75),
        # Feature fields (from FeatureVector)
        **features.to_dict(),
        # Metadata fields
        "mfn_version": MFN_VERSION,
        "timestamp": timestamp,
        "growth_events": metrics.growth_events,
        "turing_activations": metrics.turing_activations,
        "clamping_events": metrics.clamping_events,
    }

    return record


def run_simulation(
    params: dict[str, Any],
) -> tuple[NDArray[np.floating[Any]], ReactionDiffusionMetrics] | None:
    """
    Run a single simulation with given parameters.

    Handles StabilityError and ValueOutOfRangeError gracefully.

    Parameters
    ----------
    params : dict
        Simulation parameters from ConfigSampler.

    Returns
    -------
    tuple | None
        (field_history, metrics) or None if simulation failed.
    """
    try:
        config = ReactionDiffusionConfig(
            grid_size=params["grid_size"],
            alpha=params["alpha"],
            spike_probability=params.get("spike_probability", 0.25),
            turing_threshold=params.get("turing_threshold", 0.75),
            random_seed=params["random_seed"],
        )
        engine = ReactionDiffusionEngine(config)

        # Run simulation with history for temporal features
        history, metrics = engine.simulate(
            steps=params["steps"],
            turing_enabled=params["turing_enabled"],
            return_history=True,
        )

        return history, metrics

    except StabilityError as e:
        logger.warning(f"StabilityError for sim_id={params['sim_id']}: {e}")
        return None
    except ValueOutOfRangeError as e:
        logger.warning(f"ValueOutOfRangeError for sim_id={params['sim_id']}: {e}")
        return None
    except NumericalInstabilityError as e:
        logger.warning(f"NumericalInstabilityError for sim_id={params['sim_id']}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error for sim_id={params['sim_id']}: {e}")
        return None


def generate_dataset(
    sweep: SweepConfig | None = None,
    output_path: str | Path | None = None,
    feature_config: FeatureConfig | None = None,
    *,
    num_samples: int | None = None,
    config_sampler: ConfigSampler | None = None,
) -> dict[str, Any]:
    """
    Generate dataset with num_samples simulations.

    For each configuration:
    - Runs run_mycelium_simulation(...)
    - Computes FeatureVector via compute_features(...)
    - Writes record to output dataset

    Parameters
    ----------
    num_samples : int
        Number of simulations to generate.
    config_sampler : ConfigSampler | None
        Configuration sampler. If None, uses default sampler.
    output_path : str | Path | None
        Output path for parquet file. If None, doesn't save to file.
    feature_config : FeatureConfig | None
        Feature extraction configuration.

    Returns
    -------
    dict
        Dataset generation statistics including:
        - total_samples: Requested number of samples
        - successful: Number of successful simulations
        - failed: Number of failed simulations
        - success_rate: Ratio of successful to total
        - output_path: Path where dataset was saved (if any)
        - rows: List of all records (for testing)
    """
    if feature_config is None:
        feature_config = FeatureConfig()

    if sweep is not None:
        if config_sampler is not None or num_samples is not None:
            raise ValueError(
                "Use either legacy sweep mode or num_samples/config_sampler mode, not both"
            )
        configs = _generate_sweep_configs(sweep)
        requested_samples = len(configs)
    else:
        if num_samples is None:
            raise TypeError("num_samples is required when sweep is not provided")
        if config_sampler is None:
            config_sampler = ConfigSampler()
        rng = np.random.default_rng(config_sampler.base_seed)
        configs = list(config_sampler.sample(num_samples, rng))
        requested_samples = num_samples

    logger.info(f"Starting dataset generation with {requested_samples} samples")

    all_rows: list[dict[str, Any]] = []
    n_success = 0
    n_failed = 0
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for i, params in enumerate(configs):
        if (i + 1) % max(1, requested_samples // 10) == 0 or i == 0:
            logger.info(f"Processing {i + 1}/{requested_samples}...")

        result = run_simulation(params)
        if result is None:
            n_failed += 1
            continue

        history, metrics = result

        # Extract features
        try:
            features = compute_features(history, feature_config)
        except Exception as e:
            logger.warning(f"Feature extraction failed for sim_id={params['sim_id']}: {e}")
            n_failed += 1
            continue

        # Build record
        record = to_record(params, features, metrics=metrics, timestamp=timestamp)
        all_rows.append(record)
        n_success += 1

    # Save dataset
    saved_path: str | None = None
    if all_rows and output_path is not None:
        output_path = Path(output_path)
        saved_path = _save_dataset(all_rows, output_path)

    # Compute statistics
    stats: dict[str, Any] = {
        "total_samples": requested_samples,
        "successful": n_success,
        "failed": n_failed,
        "success_rate": n_success / requested_samples if requested_samples > 0 else 0.0,
        "output_path": saved_path,
        "rows": all_rows,
    }

    # Feature statistics
    if all_rows:
        feature_names = FeatureVector.feature_names()
        for fname in feature_names:
            values = [r.get(fname, np.nan) for r in all_rows]
            values = [v for v in values if not np.isnan(v)]
            if values:
                stats[f"{fname}_min"] = float(np.min(values))
                stats[f"{fname}_max"] = float(np.max(values))
                stats[f"{fname}_mean"] = float(np.mean(values))

    logger.info(f"Dataset generation complete: {n_success}/{requested_samples} successful")

    return stats


def _save_dataset(rows: list[dict[str, Any]], output_path: Path) -> str:
    """
    Save dataset to file in Parquet format (with NPZ fallback).

    Parameters
    ----------
    rows : list[dict]
        List of record dictionaries.
    output_path : Path
        Output file path.

    Returns
    -------
    str
        Actual path where dataset was saved.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        df.to_parquet(output_path, index=False)
        logger.info(f"Dataset saved to {output_path}")
        return str(output_path)

    except ImportError:
        logger.warning("pandas not installed, saving as npz instead")
        npz_path = output_path.with_suffix(".npz")
        np.savez(
            npz_path,
            data=np.array([list(r.values()) for r in rows], dtype=object),
            columns=np.array(list(rows[0].keys())),
        )
        logger.info(f"Dataset saved to {npz_path}")
        return str(npz_path)


def main() -> None:
    """
    CLI entry point for dataset generation.

    Parses command-line arguments and generates the dataset.
    """
    parser = argparse.ArgumentParser(
        description="Generate MyceliumFractalNet experimental dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--num-samples",
        "-n",
        type=int,
        default=DEFAULT_NUM_SAMPLES,
        help="Number of simulations to generate",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output path for dataset",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base random seed for reproducibility",
    )
    parser.add_argument(
        "--sweep",
        type=str,
        choices=["minimal", "default", "extended"],
        default="default",
        help="Sweep configuration preset",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Configure sampler based on preset
    if args.sweep == "minimal":
        sampler = ConfigSampler(
            grid_sizes=[32],
            steps_range=(50, 50),
            alpha_range=(0.15, 0.15),
            turing_values=[True],
            base_seed=args.seed,
        )
    elif args.sweep == "extended":
        sampler = ConfigSampler(
            grid_sizes=[32, 64, 128],
            steps_range=(50, 300),
            alpha_range=(0.08, 0.22),
            turing_values=[True, False],
            base_seed=args.seed,
        )
    else:  # default
        sampler = ConfigSampler(
            grid_sizes=[32, 64],
            steps_range=(50, 200),
            alpha_range=(0.10, 0.20),
            turing_values=[True, False],
            base_seed=args.seed,
        )

    # Generate dataset
    stats = generate_dataset(
        num_samples=args.num_samples,
        config_sampler=sampler,
        output_path=args.output,
    )

    # Log summary
    logger.info("=== Dataset Generation Summary ===")
    logger.info("Total samples requested: %d", stats["total_samples"])
    logger.info("Successful: %d", stats["successful"])
    logger.info("Failed: %d", stats["failed"])
    logger.info("Success rate: %.1f%%", stats["success_rate"] * 100)
    if stats["output_path"]:
        logger.info("Output: %s", stats["output_path"])

    if stats["successful"] > 0:
        logger.info("=== Feature Ranges ===")
        for key in ["D_box", "V_mean", "f_active"]:
            if f"{key}_mean" in stats:
                logger.info(
                    "%s: [%.3f, %.3f] (mean: %.3f)",
                    key,
                    stats[f"{key}_min"],
                    stats[f"{key}_max"],
                    stats[f"{key}_mean"],
                )


if __name__ == "__main__":
    main()
