"""Branch A 2D marker: Fisher linear discriminant on ``(h(q=2), Δh)``.

A minimal, auditable classifier for the preprint's §3.5 blind-validation
protocol. Intentionally *not* a black-box sklearn pipeline: every
parameter of the locked classifier is a plain float on disk, so an
external custodian can re-implement ``predict`` in ten lines of any
language.

Why Fisher LD, not logistic regression or SVM?
----------------------------------------------
- Two features, a few dozen samples per class. No tuning budget needed.
- Closed form; deterministic from training data alone (no seed).
- Assumes class-conditional Gaussians with common covariance — a known
  bias, but one the reader can judge from the same two feature columns.
- The projection ``w · x`` has a direct geometric meaning: the most
  separating axis in the 2D plane. Paper figure = lock file.

Public API
----------
- :func:`stratified_split` — deterministic custodian split.
- :class:`LockedMarker`    — frozen, JSON-serialisable classifier.
- :func:`fit_marker`       — fit a ``LockedMarker`` from training data.
- :func:`score`            — standard binary-classification metrics.
"""

from __future__ import annotations

import dataclasses
import math
import random
from collections.abc import Sequence

__all__ = [
    "LockedMarker",
    "MarkerScore",
    "fit_marker",
    "score",
    "stratified_split",
]


# ---------------------------------------------------------------------------
# Stratified split — the custodian step
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class CohortSplit:
    train_ids: tuple[str, ...]
    train_labels: tuple[int, ...]  # 1 = healthy, 0 = pathology
    test_ids: tuple[str, ...]
    test_labels: tuple[int, ...]  # custodian-held truth
    seed: int
    train_fraction: float

    def as_public_json(self) -> dict[str, object]:
        """Train labels are revealed; test labels are hidden."""

        return {
            "seed": self.seed,
            "train_fraction": self.train_fraction,
            "train": [
                {"id": i, "label": l}
                for i, l in zip(self.train_ids, self.train_labels, strict=True)
            ],
            "test_ids": list(self.test_ids),  # labels HIDDEN
        }

    def as_ground_truth_json(self) -> dict[str, object]:
        """Sealed envelope — opened only by the reveal step."""

        return {
            "seed": self.seed,
            "test": [
                {"id": i, "label": l} for i, l in zip(self.test_ids, self.test_labels, strict=True)
            ],
        }


def stratified_split(
    subject_ids: Sequence[str],
    labels: Sequence[int],
    *,
    seed: int,
    train_fraction: float = 0.5,
) -> CohortSplit:
    """Deterministic class-balanced split. Same seed → same partition."""

    if len(subject_ids) != len(labels):
        raise ValueError("subject_ids and labels must be parallel")
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be in (0, 1)")

    by_class: dict[int, list[str]] = {}
    for sid, y in zip(subject_ids, labels, strict=True):
        by_class.setdefault(y, []).append(sid)

    rng = random.Random(seed)
    train_ids: list[str] = []
    train_y: list[int] = []
    test_ids: list[str] = []
    test_y: list[int] = []
    for y, ids in sorted(by_class.items()):
        shuffled = sorted(ids)
        rng.shuffle(shuffled)
        n_train = max(1, int(round(train_fraction * len(shuffled))))
        train_ids.extend(shuffled[:n_train])
        train_y.extend([y] * n_train)
        test_ids.extend(shuffled[n_train:])
        test_y.extend([y] * (len(shuffled) - n_train))

    return CohortSplit(
        train_ids=tuple(train_ids),
        train_labels=tuple(train_y),
        test_ids=tuple(test_ids),
        test_labels=tuple(test_y),
        seed=seed,
        train_fraction=train_fraction,
    )


# ---------------------------------------------------------------------------
# Fisher LD marker
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class LockedMarker:
    """Frozen classifier. Every field is a plain float — no opaque state."""

    feature_names: tuple[str, ...]  # e.g. ("h_at_q2", "delta_h")
    w: tuple[float, ...]  # Fisher direction
    threshold: float  # scalar cut in projection space
    healthy_label: int  # label predicted when projection > threshold
    pathology_label: int
    train_n_healthy: int
    train_n_pathology: int
    train_projection_mean_healthy: float
    train_projection_mean_pathology: float

    def predict_score(self, x: Sequence[float]) -> float:
        if len(x) != len(self.w):
            raise ValueError(f"expected {len(self.w)} features, got {len(x)}")
        return sum(wi * xi for wi, xi in zip(self.w, x, strict=True))

    def predict(self, x: Sequence[float]) -> int:
        s = self.predict_score(x)
        return self.healthy_label if s > self.threshold else self.pathology_label

    def as_json(self) -> dict[str, object]:
        return {
            "feature_names": list(self.feature_names),
            "w": [round(v, 6) for v in self.w],
            "threshold": round(self.threshold, 6),
            "healthy_label": self.healthy_label,
            "pathology_label": self.pathology_label,
            "train_n_healthy": self.train_n_healthy,
            "train_n_pathology": self.train_n_pathology,
            "train_projection_mean_healthy": round(self.train_projection_mean_healthy, 6),
            "train_projection_mean_pathology": round(self.train_projection_mean_pathology, 6),
        }


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _cov2(a: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    """Sample 2×2 covariance (ddof=1). Returns (s00, s01, s11)."""

    n = len(a)
    if n < 2:
        raise ValueError("need ≥2 rows for a covariance")
    m0 = sum(r[0] for r in a) / n
    m1 = sum(r[1] for r in a) / n
    s00 = sum((r[0] - m0) ** 2 for r in a) / (n - 1)
    s01 = sum((r[0] - m0) * (r[1] - m1) for r in a) / (n - 1)
    s11 = sum((r[1] - m1) ** 2 for r in a) / (n - 1)
    return s00, s01, s11


def _inv2(s00: float, s01: float, s11: float) -> tuple[float, float, float]:
    det = s00 * s11 - s01 * s01
    if abs(det) < 1e-18:
        raise ValueError("singular within-class scatter — classes coincide")
    return s11 / det, -s01 / det, s00 / det


def fit_marker(
    X: Sequence[Sequence[float]],
    y: Sequence[int],
    *,
    feature_names: tuple[str, str] = ("h_at_q2", "delta_h"),
    healthy_label: int = 1,
    pathology_label: int = 0,
) -> LockedMarker:
    """Fit Fisher LD; threshold at midpoint of projected class means."""

    if len(X) != len(y):
        raise ValueError("X and y must be parallel")
    if any(len(r) != 2 for r in X):
        raise ValueError("this marker is strictly 2D")

    h = [X[i] for i, yi in enumerate(y) if yi == healthy_label]
    p = [X[i] for i, yi in enumerate(y) if yi == pathology_label]
    if len(h) < 2 or len(p) < 2:
        raise ValueError(f"need ≥2 per class; got healthy={len(h)}, pathology={len(p)}")

    m_h = (_mean([r[0] for r in h]), _mean([r[1] for r in h]))
    m_p = (_mean([r[0] for r in p]), _mean([r[1] for r in p]))

    s_h = _cov2(h)
    s_p = _cov2(p)
    nh, np_ = len(h), len(p)
    pooled = (
        ((nh - 1) * s_h[0] + (np_ - 1) * s_p[0]) / (nh + np_ - 2),
        ((nh - 1) * s_h[1] + (np_ - 1) * s_p[1]) / (nh + np_ - 2),
        ((nh - 1) * s_h[2] + (np_ - 1) * s_p[2]) / (nh + np_ - 2),
    )
    inv = _inv2(*pooled)

    diff = (m_h[0] - m_p[0], m_h[1] - m_p[1])
    w = (
        inv[0] * diff[0] + inv[1] * diff[1],
        inv[1] * diff[0] + inv[2] * diff[1],
    )

    proj_h_mean = w[0] * m_h[0] + w[1] * m_h[1]
    proj_p_mean = w[0] * m_p[0] + w[1] * m_p[1]
    threshold = 0.5 * (proj_h_mean + proj_p_mean)
    if proj_h_mean < proj_p_mean:
        w = (-w[0], -w[1])
        proj_h_mean, proj_p_mean = -proj_h_mean, -proj_p_mean
        threshold = -threshold

    return LockedMarker(
        feature_names=feature_names,
        w=w,
        threshold=threshold,
        healthy_label=healthy_label,
        pathology_label=pathology_label,
        train_n_healthy=nh,
        train_n_pathology=np_,
        train_projection_mean_healthy=proj_h_mean,
        train_projection_mean_pathology=proj_p_mean,
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class MarkerScore:
    n: int
    n_healthy: int
    n_pathology: int
    accuracy: float
    sensitivity: float  # healthy recall
    specificity: float  # pathology recall
    auc: float  # ranked by projection score
    cohen_d_projection: float

    def as_json(self) -> dict[str, float | int]:
        return {
            "n": self.n,
            "n_healthy": self.n_healthy,
            "n_pathology": self.n_pathology,
            "accuracy": round(self.accuracy, 4),
            "sensitivity": round(self.sensitivity, 4),
            "specificity": round(self.specificity, 4),
            "auc": round(self.auc, 4),
            "cohen_d_projection": round(self.cohen_d_projection, 4),
        }


def _auc(scores_healthy: Sequence[float], scores_path: Sequence[float]) -> float:
    """Mann–Whitney U / (n_h · n_p) — probability of correct rank."""

    if not scores_healthy or not scores_path:
        return float("nan")
    wins = 0.0
    for sh in scores_healthy:
        for sp in scores_path:
            if sh > sp:
                wins += 1.0
            elif sh == sp:
                wins += 0.5
    return wins / (len(scores_healthy) * len(scores_path))


def score(
    marker: LockedMarker,
    X: Sequence[Sequence[float]],
    y_true: Sequence[int],
) -> MarkerScore:
    if len(X) != len(y_true):
        raise ValueError("X and y_true must be parallel")

    scores = [marker.predict_score(x) for x in X]
    preds = [
        marker.healthy_label if s > marker.threshold else marker.pathology_label for s in scores
    ]

    tp = sum(
        1
        for p, t in zip(preds, y_true, strict=True)
        if p == marker.healthy_label and t == marker.healthy_label
    )
    tn = sum(
        1
        for p, t in zip(preds, y_true, strict=True)
        if p == marker.pathology_label and t == marker.pathology_label
    )
    fp = sum(
        1
        for p, t in zip(preds, y_true, strict=True)
        if p == marker.healthy_label and t == marker.pathology_label
    )
    fn = sum(
        1
        for p, t in zip(preds, y_true, strict=True)
        if p == marker.pathology_label and t == marker.healthy_label
    )

    n = len(y_true)
    n_h = tp + fn
    n_p = tn + fp
    accuracy = (tp + tn) / n if n else float("nan")
    sensitivity = tp / n_h if n_h else float("nan")
    specificity = tn / n_p if n_p else float("nan")

    scores_h = [s for s, t in zip(scores, y_true, strict=True) if t == marker.healthy_label]
    scores_p = [s for s, t in zip(scores, y_true, strict=True) if t == marker.pathology_label]
    auc = _auc(scores_h, scores_p)

    if len(scores_h) >= 2 and len(scores_p) >= 2:
        mh, mp = _mean(scores_h), _mean(scores_p)
        var_h = sum((s - mh) ** 2 for s in scores_h) / (len(scores_h) - 1)
        var_p = sum((s - mp) ** 2 for s in scores_p) / (len(scores_p) - 1)
        sp2 = ((len(scores_h) - 1) * var_h + (len(scores_p) - 1) * var_p) / (n - 2)
        cohen = (mh - mp) / math.sqrt(sp2) if sp2 > 0.0 else float("nan")
    else:
        cohen = float("nan")

    return MarkerScore(
        n=n,
        n_healthy=n_h,
        n_pathology=n_p,
        accuracy=accuracy,
        sensitivity=sensitivity,
        specificity=specificity,
        auc=auc,
        cohen_d_projection=cohen,
    )
