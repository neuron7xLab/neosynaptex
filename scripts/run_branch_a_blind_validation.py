"""CLI — Branch A §3.5 blind-validation protocol, end-to-end.

Implements the promotion gate defined in
``manuscript/hrv_bounded_preprint_skeleton.md`` §3.5:

  1. ``split``   — custodian partitions the n=116 cohort; train
                   labels revealed, test labels sealed.
  2. ``lock``    — fit the 2D Fisher-LD marker on train only; emit a
                   cryptographically-hashed lock file.
  3. ``predict`` — apply the locked marker to test features, blind
                   to the sealed truth.
  4. ``reveal``  — open the sealed truth; report out-of-sample
                   accuracy, sensitivity, specificity, AUC, and Cohen
                   d on the projection axis.
  5. ``run``     — all four steps in a single deterministic replay,
                   for reproducibility verification.

Labels
------
  healthy (1)    — cohort ∈ {nsr2db, nsrdb}
  pathology (0)  — cohort ∈ {chf2db, chfdb}

Inputs
------
  results/hrv_mfdfa/{cohort}__{record}_mfdfa.json   (from
  ``scripts.run_mfdfa_full_cohort``)

Claim discipline
----------------
A success on the ``reveal`` step promotes Branch A to
``measured_within_substrate_blinded``. A failure falsifies the marker
at n > pilot. There is no third outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.hrv.branch_a_marker import (  # noqa: E402
    LockedMarker,
    MarkerScore,
    fit_marker,
    score,
    stratified_split,
)

HEALTHY_COHORTS = frozenset({"nsr2db", "nsrdb"})
PATHOLOGY_COHORTS = frozenset({"chf2db", "chfdb"})


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------
def _load_features(mfdfa_dir: Path) -> tuple[list[str], list[tuple[float, float]], list[int]]:
    """Walk MFDFA per-subject JSONs; assemble X, y, ids."""

    ids: list[str] = []
    X: list[tuple[float, float]] = []
    y: list[int] = []
    for path in sorted(mfdfa_dir.glob("*__*_mfdfa.json")):
        doc = json.loads(path.read_text())
        if doc.get("status") != "ok":
            continue
        h = doc.get("h_at_q2")
        d = doc.get("delta_h")
        if h is None or d is None:
            continue
        cohort = doc["cohort"]
        if cohort in HEALTHY_COHORTS:
            label = 1
        elif cohort in PATHOLOGY_COHORTS:
            label = 0
        else:
            continue
        ids.append(f"{cohort}__{doc['record']}")
        X.append((float(h), float(d)))
        y.append(label)
    return ids, X, y


def _hash_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------
def cmd_split(args: argparse.Namespace) -> int:
    ids, _X, y = _load_features(args.mfdfa_dir)
    if len(ids) < 10:
        print(
            f"ERROR: only {len(ids)} usable subjects — need MFDFA full-cohort run first",
            file=sys.stderr,
        )
        return 2
    split = stratified_split(ids, y, seed=args.seed, train_fraction=args.train_fraction)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "split.public.json").write_text(
        json.dumps(split.as_public_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out_dir / "split.ground_truth.json").write_text(
        json.dumps(split.as_ground_truth_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"split: train n={len(split.train_ids)} "
        f"(healthy {sum(1 for l in split.train_labels if l == 1)} / "
        f"pathology {sum(1 for l in split.train_labels if l == 0)}) | "
        f"test n={len(split.test_ids)} "
        f"(healthy {sum(1 for l in split.test_labels if l == 1)} / "
        f"pathology {sum(1 for l in split.test_labels if l == 0)})  "
        f"seed={args.seed}"
    )
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    public = json.loads((args.split_dir / "split.public.json").read_text())
    ids, X_all, y_all = _load_features(args.mfdfa_dir)
    by_id = {i: (x, y) for i, x, y in zip(ids, X_all, y_all, strict=True)}

    X_train: list[tuple[float, float]] = []
    y_train: list[int] = []
    for entry in public["train"]:
        sid = entry["id"]
        if sid not in by_id:
            print(f"ERROR: train id {sid} not in MFDFA features", file=sys.stderr)
            return 2
        X_train.append(by_id[sid][0])
        y_train.append(int(entry["label"]))

    marker = fit_marker(X_train, y_train)
    train_score = score(marker, X_train, y_train)

    lock_doc = {
        "marker": marker.as_json(),
        "train_metrics": train_score.as_json(),
        "split_public_sha256": _hash_path(args.split_dir / "split.public.json"),
        "mfdfa_dir": str(args.mfdfa_dir),
        "n_train": len(y_train),
    }
    (args.out_dir).mkdir(parents=True, exist_ok=True)
    (args.out_dir / "lock.json").write_text(
        json.dumps(lock_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"lock: w={[round(v, 4) for v in marker.w]}  threshold={marker.threshold:.4f}  "
        f"train acc={train_score.accuracy:.3f}  AUC={train_score.auc:.3f}"
    )
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    lock = json.loads((args.lock_dir / "lock.json").read_text())
    public = json.loads((args.split_dir / "split.public.json").read_text())
    ids, X_all, _ = _load_features(args.mfdfa_dir)
    by_id = {i: x for i, x in zip(ids, X_all, strict=True)}

    m = lock["marker"]
    marker = LockedMarker(
        feature_names=tuple(m["feature_names"]),
        w=tuple(m["w"]),
        threshold=m["threshold"],
        healthy_label=m["healthy_label"],
        pathology_label=m["pathology_label"],
        train_n_healthy=m["train_n_healthy"],
        train_n_pathology=m["train_n_pathology"],
        train_projection_mean_healthy=m["train_projection_mean_healthy"],
        train_projection_mean_pathology=m["train_projection_mean_pathology"],
    )

    predictions: list[dict[str, object]] = []
    for sid in public["test_ids"]:
        if sid not in by_id:
            print(f"ERROR: test id {sid} not in MFDFA features", file=sys.stderr)
            return 2
        x = by_id[sid]
        predictions.append(
            {
                "id": sid,
                "features": list(x),
                "score": marker.predict_score(x),
                "predicted_label": marker.predict(x),
            }
        )

    pred_doc = {
        "lock_sha256": _hash_path(args.lock_dir / "lock.json"),
        "predictions": predictions,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "predictions.json").write_text(
        json.dumps(pred_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"predicted {len(predictions)} test subjects")
    return 0


def cmd_reveal(args: argparse.Namespace) -> int:
    truth = json.loads((args.split_dir / "split.ground_truth.json").read_text())
    preds = json.loads((args.predictions_dir / "predictions.json").read_text())
    lock = json.loads((args.lock_dir / "lock.json").read_text())

    truth_map = {r["id"]: int(r["label"]) for r in truth["test"]}
    ids = [p["id"] for p in preds["predictions"]]
    X = [p["features"] for p in preds["predictions"]]
    y_true = [truth_map[i] for i in ids]

    m = lock["marker"]
    marker = LockedMarker(
        feature_names=tuple(m["feature_names"]),
        w=tuple(m["w"]),
        threshold=m["threshold"],
        healthy_label=m["healthy_label"],
        pathology_label=m["pathology_label"],
        train_n_healthy=m["train_n_healthy"],
        train_n_pathology=m["train_n_pathology"],
        train_projection_mean_healthy=m["train_projection_mean_healthy"],
        train_projection_mean_pathology=m["train_projection_mean_pathology"],
    )
    s = score(marker, X, y_true)

    report = {
        "n_test": len(y_true),
        "test_metrics": s.as_json(),
        "lock_sha256": _hash_path(args.lock_dir / "lock.json"),
        "predictions_sha256": _hash_path(args.predictions_dir / "predictions.json"),
        "ground_truth_sha256": _hash_path(args.split_dir / "split.ground_truth.json"),
        "verdict": _verdict(s),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"reveal: acc={s.accuracy:.3f} sens={s.sensitivity:.3f} "
        f"spec={s.specificity:.3f} AUC={s.auc:.3f} "
        f"d(proj)={s.cohen_d_projection:.3f}  →  {report['verdict']}"
    )
    return 0


def _verdict(s: MarkerScore) -> str:
    """Branch A promotion rule — decision is explicit, not a p-value.

    * AUC ≥ 0.80  AND  accuracy ≥ 0.70  →  PROMOTED (measured_blinded).
    * AUC < 0.60  OR   accuracy < 0.55  →  FALSIFIED at n > pilot.
    * Otherwise → INCONCLUSIVE (needs a larger cohort or a richer
      feature than the 2D pilot marker).
    """

    if s.auc >= 0.80 and s.accuracy >= 0.70:
        return "PROMOTED"
    if s.auc < 0.60 or s.accuracy < 0.55:
        return "FALSIFIED"
    return "INCONCLUSIVE"


def cmd_run(args: argparse.Namespace) -> int:
    work = args.work_dir
    work.mkdir(parents=True, exist_ok=True)
    split_ns = argparse.Namespace(
        mfdfa_dir=args.mfdfa_dir,
        out_dir=work,
        seed=args.seed,
        train_fraction=args.train_fraction,
    )
    lock_ns = argparse.Namespace(
        split_dir=work,
        mfdfa_dir=args.mfdfa_dir,
        out_dir=work,
    )
    pred_ns = argparse.Namespace(
        split_dir=work,
        lock_dir=work,
        mfdfa_dir=args.mfdfa_dir,
        out_dir=work,
    )
    rev_ns = argparse.Namespace(
        split_dir=work,
        lock_dir=work,
        predictions_dir=work,
        out_dir=work,
    )
    for step in (cmd_split, cmd_lock, cmd_predict, cmd_reveal):
        rc = step(
            {
                cmd_split: split_ns,
                cmd_lock: lock_ns,
                cmd_predict: pred_ns,
                cmd_reveal: rev_ns,
            }[step]
        )
        if rc != 0:
            return rc
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mfdfa-dir", type=Path, default=Path("results/hrv_mfdfa"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_split = sub.add_parser("split")
    p_split.add_argument("--seed", type=int, required=True)
    p_split.add_argument("--train-fraction", type=float, default=0.5)
    p_split.add_argument("--out-dir", type=Path, required=True)
    p_split.set_defaults(func=cmd_split)

    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--split-dir", type=Path, required=True)
    p_lock.add_argument("--out-dir", type=Path, required=True)
    p_lock.set_defaults(func=cmd_lock)

    p_pred = sub.add_parser("predict")
    p_pred.add_argument("--split-dir", type=Path, required=True)
    p_pred.add_argument("--lock-dir", type=Path, required=True)
    p_pred.add_argument("--out-dir", type=Path, required=True)
    p_pred.set_defaults(func=cmd_predict)

    p_rev = sub.add_parser("reveal")
    p_rev.add_argument("--split-dir", type=Path, required=True)
    p_rev.add_argument("--lock-dir", type=Path, required=True)
    p_rev.add_argument("--predictions-dir", type=Path, required=True)
    p_rev.add_argument("--out-dir", type=Path, required=True)
    p_rev.set_defaults(func=cmd_reveal)

    p_run = sub.add_parser("run", help="split + lock + predict + reveal in one shot")
    p_run.add_argument("--seed", type=int, required=True)
    p_run.add_argument("--train-fraction", type=float, default=0.5)
    p_run.add_argument("--work-dir", type=Path, required=True)
    p_run.set_defaults(func=cmd_run)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
