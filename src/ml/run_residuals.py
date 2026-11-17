"""
run_residuals.py
----------------
Residual Spatial Diagnostics, Spatial Autocorrelation (Moran's I), Correlogram,
Residual Mapping, and Named Region / Extreme Diagnostics.
Parts B and C of Stage 4.

Uses strictly out-of-fold residuals from repeat 0 in tables/oof_predictions.csv.
"""

import sys
from pathlib import Path
import argparse
import warnings

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import lil_matrix, csr_matrix
from sklearn.neighbors import BallTree

from src.ml.config import load_config

warnings.filterwarnings("ignore")


# ----------------------------------------------------------------------
# Standalone Vectorised Moran's I with Permutation Test
# ----------------------------------------------------------------------
def calc_morans_i(residuals: np.ndarray, W: csr_matrix, n_permutations: int = 999, seed: int = 42):
    """
    Compute Moran's I, expected I, analytical and permutation z-scores, and pseudo p-value.
    
    Formula:
      z = residuals - mean(residuals)
      I = (z.T @ W @ z) / (z.T @ z)  [for row-standardised W where sum(W) = N]
    """
    N = len(residuals)
    z = residuals - np.mean(residuals)
    z2_sum = np.sum(z**2)
    
    if z2_sum == 0 or N < 2:
        return {
            "I": 0.0, "expected_I": 0.0, "z_score": 0.0, "pseudo_p": 1.0,
            "sim_mean": 0.0, "sim_std": 0.0
        }
        
    I = float(np.sum(z * W.dot(z)) / z2_sum)
    expected_I = -1.0 / (N - 1)
    
    if n_permutations <= 0:
        return {
            "I": I, "expected_I": expected_I, "z_score": 0.0, "pseudo_p": 1.0,
            "sim_mean": 0.0, "sim_std": 0.0
        }
        
    # Vectorised permutation test
    rng = np.random.default_rng(seed)
    perms = np.empty((n_permutations, N), dtype=float)
    for b in range(n_permutations):
        perms[b] = rng.permutation(z)
        
    # (perms @ W.T) is (n_permutations, N)
    I_sim = np.sum((perms @ W.T) * perms, axis=1) / z2_sum
    
    above = (I_sim >= I).sum()
    larger = above
    if (n_permutations - larger) < larger:
        larger = n_permutations - larger
    pseudo_p = float((larger + 1.0) / (n_permutations + 1.0))
    
    sim_mean = float(np.mean(I_sim))
    sim_std = float(np.std(I_sim))
    z_score = float((I - sim_mean) / sim_std) if sim_std > 0 else 0.0
    
    return {
        "I": I,
        "expected_I": expected_I,
        "z_score": z_score,
        "pseudo_p": pseudo_p,
        "sim_mean": sim_mean,
        "sim_std": sim_std
    }


def build_knn_weights(coords_deg: np.ndarray, k: int = 8) -> csr_matrix:
    """
    Build row-standardised KNN spatial weight matrix using haversine distance.
    coords_deg: (N, 2) with columns [lon, lat] or [lat, lon].
    """
    # BallTree expects radians in [lat, lon]
    lat_rad = np.radians(coords_deg[:, 1])
    lon_rad = np.radians(coords_deg[:, 0])
    coords_rad = np.column_stack([lat_rad, lon_rad])
    
    tree = BallTree(coords_rad, metric="haversine")
    # query k+1 to exclude self
    _, indices = tree.query(coords_rad, k=k+1)
    
    N = len(coords_deg)
    W = lil_matrix((N, N), dtype=float)
    for i in range(N):
        nbrs = indices[i, 1:] # exclude self
        W[i, nbrs] = 1.0 / k
        
    return W.tocsr()


def build_distance_band_weights(coords_deg: np.ndarray, d_min_km: float, d_max_km: float) -> csr_matrix:
    """
    Build row-standardised spatial weight matrix for distance band [d_min_km, d_max_km).
    """
    EARTH_RADIUS_KM = 6371.0088
    lat_rad = np.radians(coords_deg[:, 1])
    lon_rad = np.radians(coords_deg[:, 0])
    coords_rad = np.column_stack([lat_rad, lon_rad])
    
    N = len(coords_deg)
    tree = BallTree(coords_rad, metric="haversine")
    
    # Query all points within d_max_km
    r_max_rad = d_max_km / EARTH_RADIUS_KM
    r_min_rad = d_min_km / EARTH_RADIUS_KM
    
    indices, dists = tree.query_radius(coords_rad, r=r_max_rad, return_distance=True)
    
    W = lil_matrix((N, N), dtype=float)
    for i in range(N):
        nbr_idx = indices[i]
        nbr_dist = dists[i]
        
        # Filter within [r_min_rad, r_max_rad) and not self
        mask = (nbr_dist >= r_min_rad) & (nbr_idx != i)
        valid_nbrs = nbr_idx[mask]
        
        if len(valid_nbrs) > 0:
            W[i, valid_nbrs] = 1.0 / len(valid_nbrs)
            
    return W.tocsr()


def run_residuals_diagnostics(source: str = "paleoclim", resolution: str = "base", fast: bool = False):
    print(f"\n=======================================================")
    print(f"  RUNNING RESIDUAL DIAGNOSTICS: source={source}, res={resolution}, fast={fast}")
    print(f"=======================================================\n")
    
    cfg = load_config()
    k_nn = 8
    
    tables_dir = REPO_ROOT / "results" / "tables"
    ml_out_dir = REPO_ROOT / "results" / "ml" / f"{source}_{resolution}"
    ml_tables_dir = ml_out_dir / "tables"
    ml_figures_dir = ml_out_dir / "figures"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Load out-of-fold predictions
    oof_path = tables_dir / "oof_predictions.csv"
    if not oof_path.exists():
        oof_path = ml_tables_dir / "oof_predictions.csv"
    assert oof_path.exists(), f"Could not find oof_predictions.csv at {oof_path}!"
    
    oof_df = pd.read_csv(oof_path)
    
    # Filter repeat 0
    rep0 = oof_df[oof_df["repeat"] == 0].copy()
    
    # Models and feature sets to test
    models_to_test = ["ols_reference", "rf", "hgb"]
    fsets_to_test = ["M1", "M2a", "M2b"]
    
    # -------------------------------------------------------------
    # PART B: Residual Moran's I
    # -------------------------------------------------------------
    print("--- PART B: Spatial Autocorrelation of Residuals (Moran's I) ---")
    
    # Get unique spatial locations for repeat 0
    # Any single model/feature_set slice has the full set of cells
    sample_slice = rep0[(rep0["model"] == "rf") & (rep0["feature_set"] == "M2a")].sort_values("cell_idx").reset_index(drop=True)
    coords_deg = sample_slice[["lon", "lat"]].values
    N_cells = len(sample_slice)
    print(f"Total cells evaluated: {N_cells}. Constructing k={k_nn} NN spatial weights...")
    
    W_knn = build_knn_weights(coords_deg, k=k_nn)
    
    # Optional PySal cross-check
    pysal_available = False
    try:
        import esda
        import libpysal
        pysal_available = True
    except ImportError:
        pass
        
    moran_rows = []
    
    for mod in models_to_test:
        for fset in fsets_to_test:
            sub = rep0[(rep0["model"] == mod) & (rep0["feature_set"] == fset)].sort_values("cell_idx").reset_index(drop=True)
            if len(sub) == 0:
                continue
                
            resids = (sub["y_true"] - sub["y_pred"]).values
            
            # Custom vectorised calculation
            res_m = calc_morans_i(resids, W_knn, n_permutations=999, seed=cfg["seed"])
            
            moran_rows.append({
                "source": source,
                "resolution": resolution,
                "model": mod,
                "feature_set": fset,
                "I": res_m["I"],
                "expected_I": res_m["expected_I"],
                "z_score": res_m["z_score"],
                "pseudo_p": res_m["pseudo_p"]
            })
            
            print(f"  {mod:14s} {fset:5s} | Moran's I: {res_m['I']:+.4f} | E[I]: {res_m['expected_I']:+.4f} | z: {res_m['z_score']:+.2f} | pseudo-p: {res_m['pseudo_p']:.4f}")
            
    # PySal cross-check on one result (e.g. rf M2a)
    if pysal_available:
        rf_m2a_sub = rep0[(rep0["model"] == "rf") & (rep0["feature_set"] == "M2a")].sort_values("cell_idx").reset_index(drop=True)
        rf_resids = (rf_m2a_sub["y_true"] - rf_m2a_sub["y_pred"]).values
        
        # Build libpysal weights
        lat_rad = np.radians(coords_deg[:, 1])
        lon_rad = np.radians(coords_deg[:, 0])
        tree = BallTree(np.column_stack([lat_rad, lon_rad]), metric="haversine")
        _, idxs = tree.query(np.column_stack([lat_rad, lon_rad]), k=k_nn+1)
        knn_dict = {i: list(idxs[i, 1:]) for i in range(N_cells)}
        w_pysal = libpysal.weights.W(knn_dict)
        w_pysal.transform = "R"
        
        mi_pysal = esda.moran.Moran(rf_resids, w_pysal, permutations=999)
        
        custom_val = [r["I"] for r in moran_rows if r["model"] == "rf" and r["feature_set"] == "M2a"][0]
        print(f"\n[PySal Cross-Check (rf M2a)]:")
        print(f"  Custom Moran's I : {custom_val:.6f}")
        print(f"  esda Moran's I   : {mi_pysal.I:.6f}")
        print(f"  Difference       : {abs(custom_val - mi_pysal.I):.1e}")
        assert abs(custom_val - mi_pysal.I) < 1e-5, "Moran's I mismatch with PySal!"
        
    moran_df = pd.DataFrame(moran_rows)
    moran_csv = tables_dir / "morans_i.csv"
    ml_moran_csv = ml_tables_dir / "morans_i.csv"
    moran_df.to_csv(moran_csv, index=False)
    moran_df.to_csv(ml_moran_csv, index=False)
    print(f"[OK] Saved Moran's I table to {moran_csv} and {ml_moran_csv}")
    
    # Plain language check on spatial autocorrelation
    sig_autocorr = (moran_df["pseudo_p"] < 0.05).any()
    if sig_autocorr:
        print("\n[DIAGNOSTIC NOTICE]: Out-of-fold residuals exhibit statistically significant spatial autocorrelation (p < 0.05).")
        print("Plainly stated: The ML models have NOT captured the full spatial structure; residual spatial patterning persists.")
        
    # Correlogram across distance bands
    print("\nComputing distance-band correlogram...")
    dist_bands = [
        (0.0, 250.0),
        (250.0, 500.0),
        (500.0, 1000.0),
        (1000.0, 2000.0),
        (2000.0, 4000.0),
        (4000.0, 8000.0)
    ]
    band_midpoints = [(b[0] + b[1]) / 2.0 for b in dist_bands]
    
    correlogram_results = {m: [] for m in ["ols_reference", "rf", "hgb"]}
    
    for b_min, b_max in dist_bands:
        W_band = build_distance_band_weights(coords_deg, b_min, b_max)
        for m in ["ols_reference", "rf", "hgb"]:
            sub = rep0[(rep0["model"] == m) & (rep0["feature_set"] == "M2a")].sort_values("cell_idx").reset_index(drop=True)
            resids = (sub["y_true"] - sub["y_pred"]).values
            mi_res = calc_morans_i(resids, W_band, n_permutations=49 if fast else 199, seed=cfg["seed"])
            correlogram_results[m].append(mi_res["I"])
            
    # Plot correlogram
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for m, c in zip(["ols_reference", "rf", "hgb"], ["#4C72B0", "#C44E52", "#8172B3"]):
        ax.plot(band_midpoints, correlogram_results[m], marker="o", linewidth=2.0, label=f"{m} (M2a)", color=c)
        
    ax.axhline(-1.0 / (N_cells - 1), color="gray", linestyle="--", linewidth=1.2, label=r"Expected $E[I]$")
    ax.axhline(0, color="black", linestyle=":", linewidth=0.8)
    ax.set_xlabel("Spatial Distance Lag (km)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Moran's I", fontsize=11, fontweight="bold")
    ax.set_title("Spatial Correlogram of Out-of-Fold Residuals ($M2a$)", fontsize=12, fontweight="bold")
    ax.legend(frameon=True, facecolor="white")
    ax.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    correlogram_path = ml_figures_dir / "moran_correlogram.png"
    plt.savefig(correlogram_path, dpi=300)
    plt.close()
    print(f"[OK] Saved spatial correlogram to {correlogram_path}")
    
    # -------------------------------------------------------------
    # PART C: Residual Maps and Named Regions
    # -------------------------------------------------------------
    print("\n--- PART C: Residual Maps and Named Regions ---")
    
    # Select best M2 model (rf M2a)
    best_sub = rep0[(rep0["model"] == "rf") & (rep0["feature_set"] == "M2a")].copy()
    best_sub["residual"] = best_sub["y_true"] - best_sub["y_pred"]
    
    # Residual map
    p2 = np.percentile(best_sub["residual"], 2)
    p98 = np.percentile(best_sub["residual"], 98)
    vlim = max(abs(p2), abs(p98))
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    # Check cartopy
    has_cartopy = False
    try:
        import cartopy.crs as ccrs
        has_cartopy = True
    except ImportError:
        pass
        
    sc = ax.scatter(
        best_sub["lon"], best_sub["lat"],
        c=best_sub["residual"],
        cmap="coolwarm",
        vmin=-vlim,
        vmax=vlim,
        s=45,
        edgecolors="black",
        linewidths=0.5,
        alpha=0.9
    )
    cbar = fig.colorbar(sc, ax=ax, orientation="horizontal", pad=0.08, shrink=0.7)
    cbar.set_label(r"Out-of-Fold Residual ($y_{\mathrm{true}} - y_{\mathrm{pred}}$)", fontsize=11, fontweight="bold")
    
    ax.set_xlim(-180, 180)
    ax.set_ylim(-65, 85)
    ax.set_xlabel("Longitude (°)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°)", fontsize=11, fontweight="bold")
    ax.set_title(r"Global Spatial Distribution of Out-of-Fold Residuals (Random Forest $M2a$)", fontsize=13, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    resmap_path = ml_figures_dir / "residual_map_best_m2.png"
    plt.savefig(resmap_path, dpi=300)
    plt.close()
    print(f"[OK] Saved residual map to {resmap_path}")
    
    # Named Regions Analysis
    named_regions = cfg.get("named_regions", {})
    region_rows = []
    
    for r_name, bbox in named_regions.items():
        min_lon, min_lat, max_lon, max_lat = bbox
        sub_reg = best_sub[
            (best_sub["lon"] >= min_lon) & (best_sub["lon"] <= max_lon) &
            (best_sub["lat"] >= min_lat) & (best_sub["lat"] <= max_lat)
        ]
        n_reg = len(sub_reg)
        
        if n_reg < 3:
            mean_res = "too few cells"
            median_res = "too few cells"
            bias_dir = "too few cells"
        else:
            m_val = float(sub_reg["residual"].mean())
            med_val = float(sub_reg["residual"].median())
            mean_res = f"{m_val:+.3f}"
            median_res = f"{med_val:+.3f}"
            bias_dir = "under-predicts" if m_val > 0 else "over-predicts"
            
        region_rows.append({
            "region": r_name,
            "bbox": f"[{min_lon}, {min_lat}, {max_lon}, {max_lat}]",
            "n_cells": n_reg,
            "mean_residual": mean_res,
            "median_residual": median_res,
            "bias_direction": bias_dir
        })
        
    region_df = pd.DataFrame(region_rows)
    reg_csv = tables_dir / "residual_regions.csv"
    ml_reg_csv = ml_tables_dir / "residual_regions.csv"
    region_df.to_csv(reg_csv, index=False)
    region_df.to_csv(ml_reg_csv, index=False)
    print(f"[OK] Saved named regions table to {reg_csv} and {ml_reg_csv}")
    
    # Residual Extremes: Top 15 under-predicted & Top 15 over-predicted
    # Under-predicted: true > pred (residual > 0, highest positive)
    # Over-predicted: true < pred (residual < 0, most negative)
    sorted_res = best_sub.sort_values("residual", ascending=False).reset_index(drop=True)
    
    top_under = sorted_res.head(15).copy()
    top_under["type"] = "under-predicted"
    top_under["rank"] = range(1, 16)
    
    top_over = sorted_res.tail(15).iloc[::-1].copy().reset_index(drop=True)
    top_over["type"] = "over-predicted"
    top_over["rank"] = range(1, 16)
    
    extremes_df = pd.concat([top_under, top_over], ignore_index=True)
    cols_to_keep = ["rank", "type", "lon", "lat", "continent", "y_true", "y_pred", "residual"]
    extremes_df = extremes_df[cols_to_keep]
    
    ext_csv = tables_dir / "residual_extremes.csv"
    ml_ext_csv = ml_tables_dir / "residual_extremes.csv"
    extremes_df.to_csv(ext_csv, index=False)
    extremes_df.to_csv(ml_ext_csv, index=False)
    print(f"[OK] Saved residual extremes to {ext_csv} and {ml_ext_csv}")
    
    return moran_df, region_df, extremes_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 4 Parts B & C: Residual Diagnostics")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    args = parser.parse_args()
    
    run_residuals_diagnostics(source=args.source, resolution=args.resolution, fast=args.fast)
