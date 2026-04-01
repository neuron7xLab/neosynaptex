"""Run manifest for provenance tracking.

Parameters
----------
None

Returns
-------
None

Notes
-----
Captures execution metadata for reproducibility: git SHA, Python version,
dependencies, configuration, seed, and output hashes. All operations are
best-effort; failures log warnings but do not raise exceptions.

References
----------
docs/SPEC.md#P2-9
docs/REPRODUCIBILITY.md
"""

from __future__ import annotations

import hashlib
import json
import shutil

# subprocess used for fixed git metadata capture (no shell).
import subprocess  # nosec B404
import sys
import warnings
from importlib import metadata
from typing import Any

def _distribution_iter() -> Any:
    """Return distribution iterable with stdlib/backport fallback."""
    try:
        from importlib.metadata import distributions as stdlib_distributions
    except ImportError:
        import importlib

        backport_module = importlib.import_module("importlib_metadata")
        return backport_module.distributions()
    return stdlib_distributions()



def distributions() -> Any:
    """Compatibility wrapper for fallback import-path tests."""
    return _distribution_iter()



class RunManifest:
    """Library-level manifest for provenance tracking.

    Parameters
    ----------
    seed : int
        Deterministic seed used for the run.
    config : dict[str, Any]
        User-provided configuration dictionary.

    Attributes
    ----------
    seed : int
        Deterministic seed used for the run.
    config : dict[str, Any]
        User-provided configuration dictionary.
    git_sha : str
        Git commit SHA (best-effort, fallback identifier if unavailable).
    python_version : str
        Python version string (e.g., "3.11.5").
    dependencies : dict[str, str]
        Installed package name to version mapping (best-effort).
    output_hashes : dict[str, str]
        Mapping from output names to SHA256 hashes.

    Notes
    -----
    - Git SHA is captured via subprocess.run(['git', 'rev-parse', 'HEAD']).
    - Python version is captured from sys.version_info.
    - Dependencies are captured via importlib.metadata.distributions.
    - All capture operations are best-effort and fail gracefully.
    - Output hashes can be added incrementally via add_output_hash().

    Examples
    --------
    >>> manifest = RunManifest(seed=42, config={"learning_rate": 0.01})
    >>> manifest.add_output_hash("weights", b"binary_weights_data")
    >>> manifest_dict = manifest.to_dict()
    >>> manifest_json = manifest.to_json()
    >>> hash_value = manifest.compute_hash()
    >>> restored = RunManifest.from_dict(manifest_dict)

    References
    ----------
    docs/SPEC.md#P2-9
    docs/REPRODUCIBILITY.md
    """

    def __init__(self, seed: int, config: dict[str, Any]) -> None:
        """Initialize a run manifest.

        Parameters
        ----------
        seed : int
            Deterministic seed used for the run.
        config : dict[str, Any]
            User-provided configuration dictionary.

        Raises
        ------
        TypeError
            If seed is not an integer or config is not a dictionary.
        """
        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        if not isinstance(config, dict):
            raise TypeError("config must be dict")

        self.seed: int = seed
        self.config: dict[str, Any] = config
        self.git_sha: str = self._capture_git_sha()
        self.python_version: str = self._capture_python_version()
        self.dependencies: dict[str, str] = self._capture_dependencies()
        self.output_hashes: dict[str, str] = {}

    def _capture_git_sha(self) -> str:
        """Capture git SHA of current repository HEAD (best-effort).

        Returns
        -------
        str
            Git commit SHA or fallback release identifier if unavailable.

        Notes
        -----
        Uses subprocess.run to invoke 'git rev-parse HEAD'. If git is not
        available or command fails, returns None and logs a warning.
        """
        try:
            git_path = shutil.which("git")
            if not git_path:
                raise FileNotFoundError("git executable not found")
            # Fixed git command without shell; inputs are constant.
            result = subprocess.run(  # nosec B603
                [git_path, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            sha = result.stdout.strip()
            if sha:
                return sha
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            warnings.warn(f"Failed to capture git SHA: {e}", stacklevel=2)
        fallback = self._fallback_git_id()
        warnings.warn(f"Using fallback git identifier: {fallback}", stacklevel=2)
        return fallback

    def _fallback_git_id(self) -> str:
        """Return a release-based fallback git identifier."""
        try:
            version = metadata.version("bnsyn")
        except metadata.PackageNotFoundError:
            version = "0.0.0"
        return f"release-{version}"

    def _capture_python_version(self) -> str:
        """Capture Python version string.

        Returns
        -------
        str
            Python version string (e.g., "3.11.5").

        Notes
        -----
        Uses sys.version_info to construct the version string.
        """
        vi = sys.version_info
        return f"{vi.major}.{vi.minor}.{vi.micro}"

    def _capture_dependencies(self) -> dict[str, str]:
        """Capture installed dependencies (best-effort).

        Returns
        -------
        dict[str, str]
            Mapping from package name to version string.

        Notes
        -----
        Uses importlib.metadata.distributions() to enumerate installed packages.
        If unavailable or errors occur, returns an empty dict and logs a warning.
        """
        try:
            deps: dict[str, str] = {}
            for dist in distributions():
                name = dist.metadata["Name"] if "Name" in dist.metadata else None
                version = dist.metadata["Version"] if "Version" in dist.metadata else None
                if name and version:
                    deps[name] = version
            return deps
        except Exception as e:
            warnings.warn(f"Failed to capture dependencies: {e}", stacklevel=2)
            return {}

    def add_output_hash(self, name: str, data: bytes) -> None:
        """Add SHA256 hash of output data to manifest.

        Parameters
        ----------
        name : str
            Name identifying the output (e.g., "weights", "results.json").
        data : bytes
            Binary data to hash.

        Raises
        ------
        TypeError
            If name is not a string or data is not bytes.

        Notes
        -----
        Computes SHA256 hash of data and stores in output_hashes dictionary.
        If name already exists, overwrites previous hash.

        Examples
        --------
        >>> manifest = RunManifest(seed=42, config={})
        >>> manifest.add_output_hash("weights", b"binary_data")
        """
        if not isinstance(name, str):
            raise TypeError("name must be str")
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")

        hash_obj = hashlib.sha256(data)
        self.output_hashes[name] = hash_obj.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Return manifest as a dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the manifest.

        Notes
        -----
        Dictionary keys are sorted for deterministic serialization.

        Examples
        --------
        >>> manifest = RunManifest(seed=42, config={"lr": 0.01})
        >>> d = manifest.to_dict()
        >>> assert d["seed"] == 42
        """
        return {
            "seed": self.seed,
            "config": self.config,
            "git_sha": self.git_sha,
            "python_version": self.python_version,
            "dependencies": self.dependencies,
            "output_hashes": self.output_hashes,
        }

    def to_json(self) -> str:
        """Return manifest as JSON string with stable ordering.

        Returns
        -------
        str
            JSON string representation of the manifest.

        Notes
        -----
        Uses json.dumps with sort_keys=True and indent=2 for deterministic
        output and human readability.

        Examples
        --------
        >>> manifest = RunManifest(seed=42, config={"lr": 0.01})
        >>> json_str = manifest.to_json()
        >>> assert "seed" in json_str
        """
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)

    def compute_hash(self) -> str:
        """Compute SHA256 hash of the manifest.

        Returns
        -------
        str
            SHA256 hash hex string of the manifest.

        Notes
        -----
        Hashes the JSON representation of the manifest (stable ordering).
        This hash can be used to uniquely identify a run configuration.

        Examples
        --------
        >>> manifest = RunManifest(seed=42, config={"lr": 0.01})
        >>> hash_value = manifest.compute_hash()
        >>> assert len(hash_value) == 64  # SHA256 hex digest length
        """
        json_bytes = self.to_json().encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RunManifest:
        """Recreate a RunManifest from a dictionary.

        Parameters
        ----------
        d : dict[str, Any]
            Dictionary representation of a manifest (from to_dict()).

        Returns
        -------
        RunManifest
            Reconstructed RunManifest instance.

        Raises
        ------
        KeyError
            If required keys are missing from dictionary.
        TypeError
            If types of required fields are incorrect.

        Notes
        -----
        Creates a new RunManifest and manually sets all attributes from the
        dictionary. Does not re-capture system state; uses stored values.

        Examples
        --------
        >>> manifest = RunManifest(seed=42, config={"lr": 0.01})
        >>> d = manifest.to_dict()
        >>> restored = RunManifest.from_dict(d)
        >>> assert restored.seed == 42
        """
        seed = d["seed"]
        config = d["config"]

        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        if not isinstance(config, dict):
            raise TypeError("config must be dict")

        # Create instance without re-capturing system state
        obj = cls.__new__(cls)
        obj.seed = seed
        obj.config = config
        obj.git_sha = d.get("git_sha") or obj._fallback_git_id()
        obj.python_version = d.get("python_version", "unknown")
        obj.dependencies = d.get("dependencies", {})
        obj.output_hashes = d.get("output_hashes", {})

        return obj
