"""EEG Resting-State — PhysioNet EEGBCI T1 substrate (Welch + Theil-Sen)."""

from .adapter import EEGRestingAdapter, run_gamma_analysis

__all__ = ["EEGRestingAdapter", "run_gamma_analysis"]
