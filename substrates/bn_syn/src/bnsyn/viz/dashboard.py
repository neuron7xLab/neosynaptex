"""Interactive dashboard for visualizing emergent dynamics.

Notes
-----
Provides real-time visualization of attractor crystallization, criticality,
sleep stages, consolidation, and avalanche dynamics. Matplotlib imports
are lazy to avoid requiring viz dependencies unless actually used.

References
----------
docs/features/viz_dashboard.md
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from bnsyn.consolidation import DualWeights
    from bnsyn.emergence import AttractorCrystallizer
    from bnsyn.sim.network import Network
    from bnsyn.sleep import SleepCycle

Float64Array = NDArray[np.float64]

# Module-level caches for matplotlib imports
_plt: Any | None = None
_animation: Any | None = None


def _load_matplotlib() -> tuple[Any, Any]:
    """Load matplotlib modules dynamically.

    Returns
    -------
    tuple[Any, Any]
        Tuple of (pyplot, animation) modules.

    Raises
    ------
    RuntimeError
        If matplotlib is not installed.

    Notes
    -----
    Imports matplotlib at runtime to avoid mypy checking missing stubs.
    The 3D projection toolkit is imported for side effects (registration).
    """
    global _plt, _animation

    if _plt is not None and _animation is not None:
        return _plt, _animation

    try:
        _plt = importlib.import_module("matplotlib.pyplot")
        _animation = importlib.import_module("matplotlib.animation")
        # Import for side effects: registers 3d projection
        importlib.import_module("mpl_toolkits.mplot3d")
    except ModuleNotFoundError as e:
        raise RuntimeError(
            'Visualization requires matplotlib. Install with: pip install -e ".[viz]"'
        ) from e

    return _plt, _animation


class EmergenceDashboard:
    """Interactive dashboard for visualizing emergent phase dynamics.

    Parameters
    ----------
    figsize : tuple[int, int], optional
        Figure size in inches (width, height), by default (15, 10).

    Returns
    -------
    None

    Notes
    -----
    Displays 6-panel layout:
    1. Attractor 3D projection (PCA space)
    2. Sigma (branching ratio) trace
    3. Temperature trace
    4. Sleep stage timeline
    5. Consolidation strength
    6. Avalanche size distribution

    Matplotlib is imported lazily only when visualization methods are called.

    Examples
    --------
    >>> dashboard = EmergenceDashboard()
    >>> dashboard.attach(network, crystallizer, sleep_cycle, consolidator)
    >>> for step in range(1000):
    ...     # run simulation
    ...     metrics = collect_metrics()
    ...     dashboard.update(metrics)
    >>> dashboard.show()

    References
    ----------
    docs/features/viz_dashboard.md
    """

    def __init__(self, figsize: tuple[int, int] = (15, 10)) -> None:
        """Initialize dashboard with specified figure size.

        Parameters
        ----------
        figsize : tuple[int, int], optional
            Figure size in inches (width, height), by default (15, 10).

        Returns
        -------
        None

        Notes
        -----
        Does not import matplotlib until visualization methods are called.
        """
        self._figsize = figsize
        self._fig: Any = None
        self._axes: dict[str, Any] = {}
        self._network: Network | None = None
        self._crystallizer: AttractorCrystallizer | None = None
        self._sleep_cycle: SleepCycle | None = None
        self._consolidator: DualWeights | None = None

        # Data buffers
        self._sigma_history: list[float] = []
        self._temp_history: list[float] = []
        self._stage_history: list[tuple[int, str]] = []
        self._consol_history: list[float] = []
        self._avalanche_sizes: list[int] = []
        self._attractor_points: list[Float64Array] = []
        self._step_count = 0

    def attach(
        self,
        network: Network,
        crystallizer: AttractorCrystallizer,
        sleep_cycle: SleepCycle,
        consolidator: DualWeights,
    ) -> None:
        """Attach components for monitoring.

        Parameters
        ----------
        network : Network
            Neural network to monitor.
        crystallizer : AttractorCrystallizer
            Attractor crystallizer to track phase dynamics.
        sleep_cycle : SleepCycle
            Sleep cycle controller for stage tracking.
        consolidator : DualWeights
            Dual-weight consolidator for synaptic dynamics.

        Returns
        -------
        None

        Notes
        -----
        All components must be attached before calling update().
        """
        self._network = network
        self._crystallizer = crystallizer
        self._sleep_cycle = sleep_cycle
        self._consolidator = consolidator

    def update(self, metrics: dict[str, Any]) -> None:
        """Update dashboard with new metrics.

        Parameters
        ----------
        metrics : dict[str, Any]
            Dictionary containing current metrics with keys:
            - 'sigma': float, branching ratio
            - 'temperature': float, system temperature
            - 'sleep_stage': str, current sleep stage name
            - 'consolidation': float, consolidation strength
            - 'avalanche_size': int, optional, size of current avalanche
            - 'attractor_point': Float64Array, optional, current point in attractor space

        Returns
        -------
        None

        Notes
        -----
        Accumulates data for visualization. Call show() or save_animation()
        to render the dashboard.
        """
        self._step_count += 1

        if "sigma" in metrics:
            self._sigma_history.append(float(metrics["sigma"]))

        if "temperature" in metrics:
            self._temp_history.append(float(metrics["temperature"]))

        if "sleep_stage" in metrics:
            self._stage_history.append((self._step_count, str(metrics["sleep_stage"])))

        if "consolidation" in metrics:
            self._consol_history.append(float(metrics["consolidation"]))

        if "avalanche_size" in metrics and metrics["avalanche_size"] > 0:
            self._avalanche_sizes.append(int(metrics["avalanche_size"]))

        if "attractor_point" in metrics:
            point = metrics["attractor_point"]
            if isinstance(point, np.ndarray):
                self._attractor_points.append(point.copy())

    def show(self) -> None:
        """Display the dashboard.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Imports matplotlib and renders all panels with accumulated data.
        Blocks execution until the window is closed.
        """
        plt, _ = _load_matplotlib()
        self._ensure_figure()
        self._render()

        plt.tight_layout()
        plt.show()

    def save_animation(self, filename: str) -> None:
        """Save dashboard as animation or static image.

        Parameters
        ----------
        filename : str
            Output filename. Extension determines format (.png, .pdf, .gif, .mp4).

        Returns
        -------
        None

        Notes
        -----
        For static formats (.png, .pdf), saves current state.
        For animated formats (.gif, .mp4), requires additional dependencies.
        """
        plt, _ = _load_matplotlib()
        # Create a fresh Agg-backed figure for headless file saving,
        # avoiding backend pollution from interactive sessions.
        import importlib
        FigureCanvasAgg = importlib.import_module(
            "matplotlib.backends.backend_agg"
        ).FigureCanvasAgg
        Figure = importlib.import_module("matplotlib.figure").Figure

        fig = Figure(figsize=self._figsize)
        FigureCanvasAgg(fig)

        saved_fig = self._fig
        saved_axes = dict(self._axes)

        self._fig = fig
        self._axes.clear()
        self._axes["attractor"] = fig.add_subplot(2, 3, 1, projection="3d")
        self._axes["sigma"] = fig.add_subplot(2, 3, 2)
        self._axes["temperature"] = fig.add_subplot(2, 3, 3)
        self._axes["sleep"] = fig.add_subplot(2, 3, 4)
        self._axes["consolidation"] = fig.add_subplot(2, 3, 5)
        self._axes["avalanche"] = fig.add_subplot(2, 3, 6)
        self._render()

        fig.tight_layout()
        fig.savefig(filename, dpi=150, bbox_inches="tight")

        self._fig = saved_fig
        self._axes = saved_axes

    def _ensure_figure(self) -> None:
        """Ensure matplotlib figure and axes are initialized.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Lazy initialization of matplotlib objects.
        """
        if self._fig is not None:
            return

        plt, _ = _load_matplotlib()

        self._fig = plt.figure(figsize=self._figsize)

        # Create 6-panel layout (2 rows, 3 columns)
        self._axes["attractor"] = self._fig.add_subplot(2, 3, 1, projection="3d")
        self._axes["sigma"] = self._fig.add_subplot(2, 3, 2)
        self._axes["temperature"] = self._fig.add_subplot(2, 3, 3)
        self._axes["sleep"] = self._fig.add_subplot(2, 3, 4)
        self._axes["consolidation"] = self._fig.add_subplot(2, 3, 5)
        self._axes["avalanche"] = self._fig.add_subplot(2, 3, 6)

    def _render(self) -> None:
        """Render all dashboard panels.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Updates all six panels with current data.
        """
        self._render_attractor()
        self._render_sigma()
        self._render_temperature()
        self._render_sleep()
        self._render_consolidation()
        self._render_avalanche()

    def _render_attractor(self) -> None:
        """Render 3D attractor projection.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows trajectory in PCA-reduced 3D space with attractor centers.
        """
        ax = self._axes["attractor"]
        ax.clear()

        if len(self._attractor_points) > 0:
            # Plot trajectory
            points = np.array(self._attractor_points)
            if points.shape[1] >= 3:
                ax.plot(
                    points[:, 0],
                    points[:, 1],
                    points[:, 2],
                    alpha=0.6,
                    linewidth=0.5,
                    color="steelblue",
                )
                ax.scatter(
                    points[-1, 0],
                    points[-1, 1],
                    points[-1, 2],
                    c="red",
                    s=50,
                    marker="o",
                    label="Current",
                )

        # Plot attractor centers if available
        if self._crystallizer is not None:
            attractors = self._crystallizer.get_attractors()
            if len(attractors) > 0:
                centers = np.array([a.center for a in attractors])
                if centers.shape[1] >= 3:
                    ax.scatter(
                        centers[:, 0],
                        centers[:, 1],
                        centers[:, 2],
                        c="gold",
                        s=100,
                        marker="*",
                        edgecolors="black",
                        linewidths=1,
                        label="Attractors",
                    )

        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_zlabel("PC3")
        ax.set_title("Attractor Space (3D PCA)")
        ax.legend(loc="upper right")

    def _render_sigma(self) -> None:
        """Render sigma (branching ratio) trace.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows branching ratio over time with critical threshold line.
        """
        ax = self._axes["sigma"]
        ax.clear()

        if len(self._sigma_history) > 0:
            steps = np.arange(len(self._sigma_history))
            ax.plot(steps, self._sigma_history, linewidth=1, color="darkblue")
            ax.axhline(y=1.0, color="red", linestyle="--", linewidth=1, alpha=0.7, label="Critical")

        ax.set_xlabel("Step")
        ax.set_ylabel("σ (Branching Ratio)")
        ax.set_title("Criticality Trace")
        ax.grid(True, alpha=0.3)
        ax.legend()

    def _render_temperature(self) -> None:
        """Render temperature trace.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows system temperature evolution over time.
        """
        ax = self._axes["temperature"]
        ax.clear()

        if len(self._temp_history) > 0:
            steps = np.arange(len(self._temp_history))
            ax.plot(steps, self._temp_history, linewidth=1, color="orangered")

        ax.set_xlabel("Step")
        ax.set_ylabel("T (Temperature)")
        ax.set_title("Temperature Trace")
        ax.grid(True, alpha=0.3)

    def _render_sleep(self) -> None:
        """Render sleep stage timeline.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows sleep stage progression as colored timeline.
        """
        ax = self._axes["sleep"]
        ax.clear()

        if len(self._stage_history) > 0:
            # Map stages to numeric values for visualization
            stage_map = {
                "WAKE": 0,
                "NREM1": 1,
                "NREM2": 2,
                "NREM3": 3,
                "REM": 4,
            }

            steps = [s[0] for s in self._stage_history]
            stages = [stage_map.get(s[1], 0) for s in self._stage_history]

            ax.plot(steps, stages, linewidth=2, color="purple", drawstyle="steps-post")
            ax.set_yticks(list(stage_map.values()))
            ax.set_yticklabels(list(stage_map.keys()))

        ax.set_xlabel("Step")
        ax.set_ylabel("Sleep Stage")
        ax.set_title("Sleep Cycle")
        ax.grid(True, alpha=0.3)

    def _render_consolidation(self) -> None:
        """Render consolidation strength trace.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows synaptic consolidation strength over time.
        """
        ax = self._axes["consolidation"]
        ax.clear()

        if len(self._consol_history) > 0:
            steps = np.arange(len(self._consol_history))
            ax.plot(steps, self._consol_history, linewidth=1, color="green")

        ax.set_xlabel("Step")
        ax.set_ylabel("Consolidation Strength")
        ax.set_title("Memory Consolidation")
        ax.grid(True, alpha=0.3)

    def _render_avalanche(self) -> None:
        """Render avalanche size distribution.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        Shows histogram of avalanche sizes on log-log scale.
        """
        ax = self._axes["avalanche"]
        ax.clear()

        if len(self._avalanche_sizes) > 0:
            # Create log-binned histogram
            sizes = np.array(self._avalanche_sizes)
            sizes = sizes[sizes > 0]  # Remove zeros

            if len(sizes) > 0:
                bins = np.logspace(0, np.log10(sizes.max()), 20)
                counts, edges = np.histogram(sizes, bins=bins)
                centers = (edges[:-1] + edges[1:]) / 2

                # Filter out zero counts for log-log plot
                mask = counts > 0
                ax.loglog(
                    centers[mask],
                    counts[mask],
                    marker="o",
                    linestyle="-",
                    linewidth=1,
                    markersize=4,
                    color="darkviolet",
                )

        ax.set_xlabel("Avalanche Size")
        ax.set_ylabel("Count")
        ax.set_title("Avalanche Distribution")
        ax.grid(True, alpha=0.3, which="both")
