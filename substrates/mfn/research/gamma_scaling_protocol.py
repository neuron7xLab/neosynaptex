#!/usr/bin/env python3
# NOTE: This script uses OLS (linregress) for historical comparison with published results.
# Canonical γ computation: core.gamma.compute_gamma() (Theil-Sen + bootstrap CI).
"""
γ-SCALING PROTOCOL v1.0 | Vasylenko 2026
C = ΔH/(β₀+β₁) → log-log fit → γ
Target: Brain Organoid Dataset (Zenodo 10301912)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple

import numpy as np
from scipy import ndimage, stats

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DATA_DIR = Path("./organoid_data")
RESULTS_DIR = Path("./gamma_results")
CLONES = {"WT2D": "healthy", "A1A": "TUBA1A", "B2A": "TUBB2A", "TH2": "TUBB2B"}
TIMEPOINTS = [2, 5, 8, 10, 12, 16, 19, 22, 25, 30]
IMAGE_SIZE = 256
MIN_POINTS = 4


class TopoPoint(NamedTuple):
    org_id: str; clone: str; condition: str; day: int
    b0: int; b1: int; topo: int; H: float; dH: float; C: float


class GammaResult(NamedTuple):
    org_id: str; clone: str; condition: str
    gamma: float; r2: float; n: int; p: float


def shannon_entropy(field, bins=64):
    h, _ = np.histogram(field, bins=bins, range=(0, 1), density=False)
    h = h.astype(np.float64) + 1e-12
    p = h / h.sum()
    return float(-np.sum(p * np.log2(p)))


def compute_betti(field):
    try:
        import gudhi
        f = np.asarray(field, dtype=np.float64)
        if f.max() - f.min() < 1e-12: return 0, 0
        fs = f.max() - f; fn = fs / (fs.max() + 1e-12)
        cc = gudhi.CubicalComplex(top_dimensional_cells=fn)
        cc.compute_persistence()
        pairs = cc.persistence()
        return (sum(1 for d, (b, de) in pairs if d == 0 and de != float('inf') and de - b > 0.005),
                sum(1 for d, (b, de) in pairs if d == 1 and de != float('inf') and de - b > 0.005))
    except ImportError:
        binary = (field > np.median(field)).astype(int)
        _, b0 = ndimage.label(binary)
        p = binary
        V = p.sum(); Eh = (p[:, :-1] * p[:, 1:]).sum(); Ev = (p[:-1, :] * p[1:, :]).sum()
        F = (p[:-1, :-1] * p[:-1, 1:] * p[1:, :-1] * p[1:, 1:]).sum()
        return int(b0), int(max(0, b0 - (V - Eh - Ev + F)))


def compute_gamma(pts):
    valid = [(p.topo, p.C) for p in pts if p.topo > 0 and p.C > 0]
    if len(valid) < MIN_POINTS: return None
    x = np.log(np.array([v[0] for v in valid], dtype=float))
    y = np.log(np.array([v[1] for v in valid], dtype=float))
    sl, _, r, p, se = stats.linregress(x, y)
    s = pts[0]
    return GammaResult(s.org_id, s.clone, s.condition, float(-sl), float(r**2), len(valid), float(p))


# ═══════════════════════════════════════════════════════════════
# SYNTHETIC TEST
# ═══════════════════════════════════════════════════════════════

def run_synthetic_test():
    print("[SYNTHETIC TEST]")
    rng = np.random.default_rng(42)
    results = []

    for org_id in range(5):
        pts = []
        prev_H = None
        for t, day in enumerate(TIMEPOINTS):
            field = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.float32)
            n_blobs = max(1, 5 + t * 2 + rng.integers(-1, 2))
            for _ in range(n_blobs):
                cx, cy = rng.integers(20, IMAGE_SIZE - 20, size=2)
                r = rng.integers(8, 20)
                y, x = np.ogrid[:IMAGE_SIZE, :IMAGE_SIZE]
                field[(x - cx)**2 + (y - cy)**2 < r**2] = rng.uniform(0.6, 1.0)
            field += rng.normal(0, 0.05, field.shape).astype(np.float32)
            field = np.clip(field, 0, 1)
            b0, b1 = compute_betti(field)
            H = shannon_entropy(field)
            topo = b0 + b1
            dH = abs(H - prev_H) if prev_H is not None else 0.0
            prev_H = H
            C = dH / topo if topo > 0 and dH > 0 else 0.0
            pts.append(TopoPoint(f"GS_{org_id}", "WT2D", "healthy", day, b0, b1, topo, H, dH, C))
        g = compute_gamma(pts)
        if g:
            results.append(g)
            print(f"  Healthy {org_id}: γ={g.gamma:+.3f} R²={g.r2:.3f}")

    for org_id in range(5):
        pts = []
        prev_H = None
        for t, day in enumerate(TIMEPOINTS):
            field = rng.uniform(0, 1, (IMAGE_SIZE, IMAGE_SIZE)).astype(np.float32)
            n = max(1, 20 - t * 2)
            for _ in range(n):
                cx, cy = rng.integers(10, IMAGE_SIZE - 10, size=2)
                r = rng.integers(3, 8)
                y, x = np.ogrid[:IMAGE_SIZE, :IMAGE_SIZE]
                field[(x - cx)**2 + (y - cy)**2 < r**2] = 0.1
            b0, b1 = compute_betti(field)
            H = shannon_entropy(field)
            topo = b0 + b1
            dH = abs(H - prev_H) if prev_H is not None else 0.0
            prev_H = H
            C = dH / topo if topo > 0 and dH > 0 else 0.0
            pts.append(TopoPoint(f"Patho_{org_id}", "A1A", "pathological", day, b0, b1, topo, H, dH, C))
        g = compute_gamma(pts)
        if g:
            results.append(g)
            print(f"  Pathological {org_id}: γ={g.gamma:+.3f} R²={g.r2:.3f}")

    gs = [r.gamma for r in results if "GS" in r.org_id]
    pa = [r.gamma for r in results if "Patho" in r.org_id]
    print(f"\n  Healthy:     γ = {np.mean(gs):+.3f} ± {np.std(gs):.3f}")
    print(f"  Pathological: γ = {np.mean(pa):+.3f} ± {np.std(pa):.3f}")
    sep = abs(np.mean(gs) - np.mean(pa))
    print(f"  Separation: {sep:.3f} {'✓ DISTINGUISHABLE' if sep > 0.3 else '✗ NOT separable'}")


# ═══════════════════════════════════════════════════════════════
# ZENODO DOWNLOAD
# ═══════════════════════════════════════════════════════════════

def download_dataset():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    img_dir = DATA_DIR / "images"
    img_dir.mkdir(exist_ok=True)
    meta_path = DATA_DIR / "zenodo_meta.json"

    if not meta_path.exists():
        print(f"[DOWNLOAD] Fetching Zenodo record 10301912...")
        url = "https://zenodo.org/api/records/10301912"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            meta = json.loads(resp.read())
        meta_path.write_text(json.dumps(meta, indent=2))
    else:
        meta = json.loads(meta_path.read_text())

    files = meta.get("files", [])
    pngs = [f for f in files if f["key"].endswith(".png") and "mask" not in f["key"].lower()]
    print(f"[DOWNLOAD] {len(pngs)} PNG files")

    downloaded = 0
    for i, f in enumerate(pngs[:100]):  # limit to 100 for speed
        dest = img_dir / Path(f["key"]).name
        if dest.exists(): continue
        url = f["links"]["self"]
        try:
            urllib.request.urlretrieve(url, dest)
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"  {downloaded} downloaded...")
            time.sleep(0.05)
        except Exception as e:
            print(f"  [ERROR] {e}")
    print(f"[DOWNLOAD] Done: {downloaded} new files")
    return img_dir


# ═══════════════════════════════════════════════════════════════
# REAL DATA PIPELINE
# ═══════════════════════════════════════════════════════════════

def parse_filename(fname):
    import re
    stem = Path(fname).stem.upper()
    clone = None
    for c in CLONES:
        if c.upper() in stem: clone = c; break
    if not clone: return None
    nums = re.findall(r'\d+', stem.replace(clone.upper(), ""))
    day = None
    for n in nums:
        d = int(n)
        if d in TIMEPOINTS: day = d; break
    if day is None and nums:
        day = min(TIMEPOINTS, key=lambda t: abs(t - int(nums[-1])))
    if day is None: return None
    return f"{clone}_{stem[:20]}", clone, day


def run_real_pipeline(img_dir):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    imgs = sorted(img_dir.glob("*.png"))
    print(f"\n[PIPELINE] {len(imgs)} images")
    if not imgs: return

    organoids = {}
    for p in imgs:
        parsed = parse_filename(p.name)
        if not parsed: continue
        org_id, clone, day = parsed
        organoids.setdefault(org_id, []).append((day, clone, p))

    print(f"[PIPELINE] {len(organoids)} organoids")
    all_pts = []
    gamma_results = []

    for org_id, tps in organoids.items():
        tps.sort()
        clone = tps[0][1]
        condition = "healthy" if clone == "WT2D" else "pathological"
        prev_H = None
        pts = []
        for day, _, path in tps:
            try:
                img = Image.open(path).convert("L").resize((IMAGE_SIZE, IMAGE_SIZE))
                field = np.asarray(img, dtype=np.float32) / 255.0
                b0, b1 = compute_betti(field)
                H = shannon_entropy(field)
                topo = b0 + b1
                dH = abs(H - prev_H) if prev_H is not None else 0.0
                prev_H = H
                C = dH / topo if topo > 0 and dH > 0 else 0.0
                pt = TopoPoint(org_id, clone, condition, day, b0, b1, topo, H, dH, C)
                pts.append(pt)
                all_pts.append(pt)
            except Exception as e:
                pass
        g = compute_gamma(pts)
        if g:
            gamma_results.append(g)

    # Summary per clone
    print(f"\n{'='*60}")
    print("  RESULTS BY CLONE")
    print(f"{'='*60}")
    summary = {}
    for clone, label in CLONES.items():
        gs = [r.gamma for r in gamma_results if r.clone == clone and r.r2 > 0.3]
        if not gs: continue
        m, s = np.mean(gs), np.std(gs)
        summary[clone] = {"gamma_mean": round(m, 4), "gamma_std": round(s, 4), "n": len(gs)}
        flag = "HEALTHY" if clone == "WT2D" else "PATHO"
        print(f"  {flag:7s} {clone:5s}: γ={m:+.3f}±{s:.3f} (n={len(gs)})")

    # Save
    output = {"summary": summary,
              "gammas": [{"org": r.org_id, "clone": r.clone, "gamma": round(r.gamma, 4),
                          "r2": round(r.r2, 4)} for r in gamma_results]}
    (RESULTS_DIR / "gamma_results.json").write_text(json.dumps(output, indent=2))
    print(f"\n  Saved: gamma_results/gamma_results.json")


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║  γ-SCALING PROTOCOL v1.0  |  Vasylenko 2026 ║")
    print("╚══════════════════════════════════════════════╝\n")

    if "--test" in sys.argv:
        run_synthetic_test()
    elif "--skip-download" in sys.argv:
        run_real_pipeline(DATA_DIR / "images")
    else:
        img_dir = download_dataset()
        run_real_pipeline(img_dir)
