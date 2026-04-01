#!/usr/bin/env python3
"""
γ-SCALING PROTOCOL v1.1 — 3D Spheroids | Vasylenko 2026
C = ΔH/(β₀+β₁) → log-log fit → γ
Target: Zenodo 8211845 (SpheroScan 3D spheroid test datasets)

Hypothesis: cancer spheroids γ ≈ +1.4 (like brain organoids)
            different conditions → γ separation
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple

import numpy as np
from scipy import ndimage, stats

# ─── Config ──────────────────────────────────────────────────
DATA_DIR = Path("./spheroid_data")
RESULTS_DIR = Path("./gamma_spheroid_results")
IMAGE_SIZE = 256
MIN_POINTS = 4
ZENODO_RECORD_ID = 8211845


class TopoPoint(NamedTuple):
    org_id: str; clone: str; condition: str; day: int
    b0: int; b1: int; topo: int; H: float; dH: float; C: float


class GammaResult(NamedTuple):
    org_id: str; clone: str; condition: str
    gamma: float; r2: float; n: int; p: float


# ─── Core math ───────────────────────────────────────────────

def shannon_entropy(field, bins=64):
    h, _ = np.histogram(field, bins=bins, range=(0, 1), density=False)
    h = h.astype(np.float64) + 1e-12
    p = h / h.sum()
    return float(-np.sum(p * np.log2(p)))


def compute_betti(field):
    """Compute β₀, β₁ — gudhi if available, else Euler-number fallback."""
    try:
        import gudhi
        f = np.asarray(field, dtype=np.float64)
        if f.max() - f.min() < 1e-12:
            return 0, 0
        fs = f.max() - f
        fn = fs / (fs.max() + 1e-12)
        cc = gudhi.CubicalComplex(top_dimensional_cells=fn)
        cc.compute_persistence()
        pairs = cc.persistence()
        return (
            sum(1 for d, (b, de) in pairs if d == 0 and de != float('inf') and de - b > 0.005),
            sum(1 for d, (b, de) in pairs if d == 1 and de != float('inf') and de - b > 0.005),
        )
    except ImportError:
        binary = (field > np.median(field)).astype(int)
        _, b0 = ndimage.label(binary)
        p = binary
        V = p.sum()
        Eh = (p[:, :-1] * p[:, 1:]).sum()
        Ev = (p[:-1, :] * p[1:, :]).sum()
        F = (p[:-1, :-1] * p[:-1, 1:] * p[1:, :-1] * p[1:, 1:]).sum()
        return int(b0), int(max(0, b0 - (V - Eh - Ev + F)))


def compute_gamma(pts):
    valid = [(p.topo, p.C) for p in pts if p.topo > 0 and p.C > 0]
    if len(valid) < MIN_POINTS:
        return None
    x = np.log(np.array([v[0] for v in valid], dtype=float))
    y = np.log(np.array([v[1] for v in valid], dtype=float))
    sl, _, r, p, se = stats.linregress(x, y)
    s = pts[0]
    return GammaResult(s.org_id, s.clone, s.condition, float(-sl), float(r**2), len(valid), float(p))


# ═══════════════════════════════════════════════════════════════
# SYNTHETIC TEST
# ═══════════════════════════════════════════════════════════════

def run_synthetic_test():
    print("[SYNTHETIC TEST] Tumour-stroma spheroid simulation")
    rng = np.random.default_rng(42)
    results = []
    timepoints = list(range(0, 120, 12))  # 0h to 108h, every 12h

    # --- Tumour spheroids: growing, increasing complexity ---
    for org_id in range(5):
        pts = []
        prev_H = None
        for t, hour in enumerate(timepoints):
            field = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.float32)
            # Growing spheroid — radius increases with time
            radius = 30 + t * 8 + rng.integers(-3, 4)
            cx, cy = IMAGE_SIZE // 2, IMAGE_SIZE // 2
            y, x = np.ogrid[:IMAGE_SIZE, :IMAGE_SIZE]
            mask = (x - cx)**2 + (y - cy)**2 < radius**2
            field[mask] = rng.uniform(0.5, 1.0)
            # Internal heterogeneity increases
            n_clusters = max(1, 2 + t + rng.integers(-1, 2))
            for _ in range(n_clusters):
                ccx = cx + rng.integers(-radius//2, radius//2)
                ccy = cy + rng.integers(-radius//2, radius//2)
                cr = rng.integers(5, 15)
                sub_mask = (x - ccx)**2 + (y - ccy)**2 < cr**2
                field[sub_mask] = rng.uniform(0.7, 1.0)
            field += rng.normal(0, 0.03, field.shape).astype(np.float32)
            field = np.clip(field, 0, 1)

            b0, b1 = compute_betti(field)
            H = shannon_entropy(field)
            topo = b0 + b1
            dH = abs(H - prev_H) if prev_H is not None else 0.0
            prev_H = H
            C = dH / topo if topo > 0 and dH > 0 else 0.0
            pts.append(TopoPoint(f"TUM_{org_id}", "tumour", "cancer", hour, b0, b1, topo, H, dH, C))
        g = compute_gamma(pts)
        if g:
            results.append(g)
            print(f"  Tumour {org_id}: γ={g.gamma:+.3f} R²={g.r2:.3f}")

    # --- Drug-treated: fragmented, declining topology ---
    for org_id in range(5):
        pts = []
        prev_H = None
        for t, hour in enumerate(timepoints):
            field = rng.uniform(0, 0.3, (IMAGE_SIZE, IMAGE_SIZE)).astype(np.float32)
            # Fragmented — many small clusters that shrink over time
            n_frags = max(1, 15 - t * 2)
            for _ in range(n_frags):
                ccx, ccy = rng.integers(20, IMAGE_SIZE - 20, size=2)
                cr = rng.integers(3, max(4, 12 - t))
                y, x = np.ogrid[:IMAGE_SIZE, :IMAGE_SIZE]
                field[(x - ccx)**2 + (y - ccy)**2 < cr**2] = rng.uniform(0.4, 0.8)
            field = np.clip(field, 0, 1)

            b0, b1 = compute_betti(field)
            H = shannon_entropy(field)
            topo = b0 + b1
            dH = abs(H - prev_H) if prev_H is not None else 0.0
            prev_H = H
            C = dH / topo if topo > 0 and dH > 0 else 0.0
            pts.append(TopoPoint(f"DRUG_{org_id}", "drug", "treated", hour, b0, b1, topo, H, dH, C))
        g = compute_gamma(pts)
        if g:
            results.append(g)
            print(f"  Drug-treated {org_id}: γ={g.gamma:+.3f} R²={g.r2:.3f}")

    # --- Summary ---
    tum = [r.gamma for r in results if "TUM" in r.org_id]
    drg = [r.gamma for r in results if "DRUG" in r.org_id]
    if tum:
        print(f"\n  Tumour:       γ = {np.mean(tum):+.3f} ± {np.std(tum):.3f}")
    if drg:
        print(f"  Drug-treated: γ = {np.mean(drg):+.3f} ± {np.std(drg):.3f}")
    if tum and drg:
        sep = abs(np.mean(tum) - np.mean(drg))
        print(f"  Separation: {sep:.3f} {'✓ DISTINGUISHABLE' if sep > 0.3 else '✗ NOT separable'}")


# ═══════════════════════════════════════════════════════════════
# FIGSHARE DOWNLOAD
# ═══════════════════════════════════════════════════════════════

def download_dataset():
    import zipfile

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    img_dir = DATA_DIR / "images"
    img_dir.mkdir(exist_ok=True)
    meta_path = DATA_DIR / "zenodo_meta.json"

    if not meta_path.exists():
        print(f"[DOWNLOAD] Fetching Zenodo record {ZENODO_RECORD_ID}...")
        url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            meta = json.loads(resp.read())
        meta_path.write_text(json.dumps(meta, indent=2))
    else:
        meta = json.loads(meta_path.read_text())

    files = meta.get("files", [])
    print(f"[DOWNLOAD] {len(files)} files in record")

    img_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    downloaded = 0

    for f in files:
        key = f["key"]
        if key.lower().endswith(".zip"):
            zip_dest = DATA_DIR / key
            if not zip_dest.exists():
                url = f["links"]["self"]
                size_mb = f.get("size", 0) / (1024 * 1024)
                print(f"  Downloading {key} ({size_mb:.0f} MB)...")
                try:
                    urllib.request.urlretrieve(url, zip_dest)
                except Exception as e:
                    print(f"  [ERROR] download: {e}")
                    continue

            # Extract images from ZIP
            try:
                with zipfile.ZipFile(zip_dest) as z:
                    members = [m for m in z.namelist() if Path(m).suffix.lower() in img_exts]
                    print(f"  {len(members)} images inside {key}")
                    for member in members:
                        dest = img_dir / Path(member).name
                        if not dest.exists():
                            with z.open(member) as src, open(dest, "wb") as tgt:
                                tgt.write(src.read())
                            downloaded += 1
                            if downloaded % 100 == 0:
                                print(f"    {downloaded} extracted...")
            except Exception as e:
                print(f"  [ERROR] extract: {e}")
        elif Path(key).suffix.lower() in img_exts:
            dest = img_dir / key
            if not dest.exists():
                try:
                    urllib.request.urlretrieve(f["links"]["self"], dest)
                    downloaded += 1
                except Exception as e:
                    print(f"  [ERROR] {key}: {e}")

    print(f"[DOWNLOAD] Done: {downloaded} new files")
    return img_dir


# ═══════════════════════════════════════════════════════════════
# REAL DATA PIPELINE
# ═══════════════════════════════════════════════════════════════

def parse_filename(fname):
    """Parse SpheroScan filename into (org_id, condition, index).

    Patterns in this dataset:
    - N.png, N.tif       → "plain" condition
    - N-NSC.png           → "NSC" condition
    - N-UW.png            → "UW" condition
    - imageN.png/jpeg     → "image" condition
    - NNN.png (3-digit)   → "set2" condition
    """
    stem = Path(fname).stem
    ext = Path(fname).suffix.lower()

    # Detect condition from suffix/prefix
    if "-NSC" in stem:
        condition = "NSC"
        num = re.findall(r'\d+', stem.replace("-NSC", ""))
    elif "-UW" in stem:
        condition = "UW"
        num = re.findall(r'\d+', stem.replace("-UW", ""))
    elif stem.startswith("image"):
        condition = "image"
        num = re.findall(r'\d+', stem)
    elif ext == ".tif":
        condition = "tif"
        num = re.findall(r'\d+', stem)
    elif re.match(r'^\d{3,}$', stem):
        condition = "set2"
        num = [stem]
    else:
        condition = "plain"
        num = re.findall(r'\d+', stem)

    idx = int(num[0]) if num else 0
    # Group into pseudo-organoids of 5 consecutive images
    group = idx // 5
    org_id = f"{condition}_g{group}"
    # Use index within group as pseudo-timepoint
    day = idx % 5

    return org_id, condition, day


def run_real_pipeline(img_dir=None):
    if img_dir is None:
        img_dir = DATA_DIR / "images"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
    except ImportError:
        print("[ERROR] Pillow not installed. Run: pip install Pillow")
        return

    # Collect all images
    img_exts = {"*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp"}
    imgs = []
    for ext in img_exts:
        imgs.extend(sorted(img_dir.glob(ext)))
        imgs.extend(sorted(img_dir.glob(ext.upper())))
    imgs = sorted(set(imgs))

    print(f"\n[PIPELINE] {len(imgs)} images in {img_dir}")
    if not imgs:
        print("[PIPELINE] No images found. Check download or path.")
        return

    # Group by organoid
    organoids = {}
    for p in imgs:
        try:
            org_id, condition, day = parse_filename(p.name)
            organoids.setdefault(org_id, []).append((day, condition, p))
        except Exception:
            pass

    print(f"[PIPELINE] {len(organoids)} organoids/spheroids")

    # Show condition distribution
    cond_count = {}
    for org_id, tps in organoids.items():
        cond = tps[0][1]
        cond_count[cond] = cond_count.get(cond, 0) + 1
    for cond, cnt in sorted(cond_count.items()):
        print(f"  {cond}: {cnt} organoids")

    all_pts = []
    gamma_results = []

    for org_id, tps in organoids.items():
        tps.sort()
        condition = tps[0][1]
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
                pt = TopoPoint(org_id, condition, condition, day, b0, b1, topo, H, dH, C)
                pts.append(pt)
                all_pts.append(pt)
            except Exception as e:
                pass
        g = compute_gamma(pts)
        if g:
            gamma_results.append(g)

    # Summary per condition
    print(f"\n{'=' * 60}")
    print("  RESULTS BY CONDITION")
    print(f"{'=' * 60}")

    summary = {}
    conditions = sorted(set(r.condition for r in gamma_results))
    for cond in conditions:
        gs = [r.gamma for r in gamma_results if r.condition == cond and r.r2 > 0.3]
        if not gs:
            continue
        m, s = np.mean(gs), np.std(gs)
        summary[cond] = {"gamma_mean": round(m, 4), "gamma_std": round(s, 4), "n": len(gs)}
        print(f"  {cond:15s}: γ = {m:+.3f} ± {s:.3f}  (n={len(gs)})")

    # Cross-condition comparison
    if len(summary) >= 2:
        print(f"\n  PAIRWISE COMPARISON")
        conds = list(summary.keys())
        for i in range(len(conds)):
            for j in range(i + 1, len(conds)):
                c1, c2 = conds[i], conds[j]
                g1 = [r.gamma for r in gamma_results if r.condition == c1 and r.r2 > 0.3]
                g2 = [r.gamma for r in gamma_results if r.condition == c2 and r.r2 > 0.3]
                if len(g1) >= 2 and len(g2) >= 2:
                    t_stat, p_val = stats.ttest_ind(g1, g2)
                    sep = abs(np.mean(g1) - np.mean(g2))
                    sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                    print(f"  {c1} vs {c2}: Δγ={sep:.3f}, p={p_val:.4f} {sig}")

    # Reference comparison with brain organoids
    print(f"\n  REFERENCE: Brain organoid γ_WT2D = +1.487 ± 0.208")
    for cond, s in summary.items():
        delta = abs(s["gamma_mean"] - 1.487)
        print(f"  {cond:15s} → Δ from organoid = {delta:.3f}")

    # Save
    output = {
        "summary": summary,
        "reference": {"brain_organoid_WT2D": {"gamma_mean": 1.487, "gamma_std": 0.208}},
        "gammas": [
            {"org": r.org_id, "condition": r.condition, "gamma": round(r.gamma, 4), "r2": round(r.r2, 4)}
            for r in gamma_results
        ],
    }
    out_path = RESULTS_DIR / "gamma_spheroid_results.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n  Saved: {out_path}")


# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  γ-SCALING PROTOCOL v1.1 — Spheroids  |  Vasylenko 2026 ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    if "--test" in sys.argv:
        run_synthetic_test()
    elif "--download" in sys.argv:
        download_dataset()
    elif "--run" in sys.argv:
        run_real_pipeline()
    elif "--skip-download" in sys.argv:
        run_real_pipeline(DATA_DIR / "images")
    else:
        print("Usage:")
        print("  python gamma_spheroid_protocol.py --test      # synthetic validation")
        print("  python gamma_spheroid_protocol.py --download   # fetch from Figshare")
        print("  python gamma_spheroid_protocol.py --run        # compute γ on real data")
        print("  python gamma_spheroid_protocol.py --skip-download  # run on already-downloaded data")
