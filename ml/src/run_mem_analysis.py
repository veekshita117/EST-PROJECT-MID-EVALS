"""
run_mem_analysis.py
-------------------
Execution script for Spatial Eigenvector Mapping (MEM).
Evaluates Random Forest (RF) and HistGradientBoosting (HGB) with and without MEM.
Calculates residual Moran's I and delta-R² before and after MEM using fold-safe projection.
Saves comparison tables and publication-quality diagnostic figures.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

from ml.src.config import get_validated_config
from ml.src.data import load_dataset
from ml.src.cv import spatial_outer_folds
from ml.src.run_residuals import calc_morans_i, build_knn_weights
from ml.src.metrics import calc_r2, calc_rmse, calc_mae, calc_spearman, pooled_out_of_fold_r2, block_bootstrap_ci
from ml.src.mem import SpatialEigenvectorMapper, compute_mem_eigenvectors


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Spatial Eigenvector Mapping (MEM)")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--target", type=str, default="gbif_log_richness")
    parser.add_argument("--k", type=int, default=8, help="Number of spatial neighbors for MEM (default 8)")
    parser.add_argument("--moran_threshold", type=float, default=0.1, help="Moran's I threshold for MEM (default 0.1)")
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    return parser.parse_args()


def run_mem_evaluation(
    source: str = "paleoclim",
    resolution: str = "base",
    target: str = "gbif_log_richness",
    k: int = 8,
    moran_threshold: float = 0.1,
    fast: bool = False
):
    print("=" * 80)
    print(f"RUNNING SPATIAL EIGENVECTOR MAPPING (MEM) EVALUATION")
    print(f"Source: {source.upper()} | Res: {resolution} | Target: {target} | k={k} | Threshold={moran_threshold}")
    print("=" * 80)

    cfg = get_validated_config()
    df, feature_groups, feature_sets = load_dataset(source=source, resolution=resolution, target=target)
    
    tables_dir = REPO_ROOT / "tables"
    figures_dir = REPO_ROOT / "figures"
    ml_tables_dir = REPO_ROOT / "ml" / "outputs" / f"{source}_{resolution}" / "tables"
    ml_figures_dir = REPO_ROOT / "ml" / "outputs" / f"{source}_{resolution}" / "figures"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    
    coords = df[["lon", "lat"]].values
    y_true = df["y"].values
    
    # 1. Global diagnostic of MEM eigenvectors
    global_evecs, global_mi, global_idx, W_global = compute_mem_eigenvectors(
        coords, k=k, moran_threshold=moran_threshold
    )
    print(f"[Global MEM] Extracted {global_evecs.shape[1]} positive Moran eigenvectors with Moran's I > {moran_threshold}")
    print(f"[Global MEM] Moran's I range: {global_mi.min():.4f} to {global_mi.max():.4f} (Mean: {global_mi.mean():.4f})")
    
    # 2. Setup Spatial Cross-Validation folds (5-fold 20-degree GroupKFold)
    folds, groups = spatial_outer_folds(df, k=5, seed=cfg["seed"], offset=0.0, reuse_phase6=(resolution == "base"))
    
    # Models to test: RF and HistGradientBoosting
    models = {
        "rf": lambda: RandomForestRegressor(
            n_estimators=100 if fast else 300,
            max_depth=6,
            min_samples_leaf=2,
            random_state=cfg["seed"],
            n_jobs=-1
        ),
        "hgb": lambda: HistGradientBoostingRegressor(
            max_iter=100 if fast else 200,
            learning_rate=0.05,
            max_depth=4,
            random_state=cfg["seed"],
            early_stopping=False
        )
    }
    
    # Feature configurations to compare:
    # 1. M1 vs M1 + MEM
    # 2. M2a vs M2a + MEM
    tiers = ["M1", "M2a"]
    
    results_records = []
    oof_predictions = {}
    
    for mod_name, mod_fn in models.items():
        for tier in tiers:
            feat_cols = feature_sets[tier]
            
            oof_base = np.zeros(len(df))
            oof_mem = np.zeros(len(df))
            n_mem_per_fold = []
            
            for f_idx, (tr, te) in enumerate(folds):
                X_tr_base = df.iloc[tr][feat_cols].values
                X_te_base = df.iloc[te][feat_cols].values
                y_tr = y_true[tr]
                
                coords_tr = coords[tr]
                coords_te = coords[te]
                
                # Fold-safe MEM construction: fit strictly on training fold
                mapper = SpatialEigenvectorMapper(k=k, moran_threshold=moran_threshold)
                mem_tr = mapper.fit_transform(coords_tr)
                mem_te = mapper.transform(coords_te)
                n_mem_per_fold.append(mapper.n_features_out_)
                
                # Base model (without MEM)
                pipe_base = Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("model", mod_fn())
                ])
                pipe_base.fit(X_tr_base, y_tr)
                oof_base[te] = pipe_base.predict(X_te_base)
                
                # Model with MEM features
                X_tr_mem = np.hstack([X_tr_base, mem_tr])
                X_te_mem = np.hstack([X_te_base, mem_te])
                
                pipe_mem = Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("model", mod_fn())
                ])
                pipe_mem.fit(X_tr_mem, y_tr)
                oof_mem[te] = pipe_mem.predict(X_te_mem)
                
            oof_predictions[f"{mod_name}_{tier}_base"] = oof_base
            oof_predictions[f"{mod_name}_{tier}_mem"] = oof_mem
            
            # Compute R2, RMSE and MAE
            r2_base = pooled_out_of_fold_r2(y_true, oof_base)
            r2_mem = pooled_out_of_fold_r2(y_true, oof_mem)
            delta_r2 = r2_mem - r2_base
            
            rmse_base = calc_rmse(y_true, oof_base)
            rmse_mem = calc_rmse(y_true, oof_mem)
            mae_base = calc_mae(y_true, oof_base)
            mae_mem = calc_mae(y_true, oof_mem)
            
            # Block-bootstrap CI for delta R2
            pt_est, ci_low, ci_high = block_bootstrap_ci(
                y_true, oof_base, oof_mem, groups, metric="r2", n=1000, seed=cfg["seed"]
            )
            
            # Residual spatial autocorrelation before and after MEM
            resids_base = y_true - oof_base
            resids_mem = y_true - oof_mem
            
            moran_base = calc_morans_i(resids_base, W_global, n_permutations=999, seed=cfg["seed"])
            moran_mem = calc_morans_i(resids_mem, W_global, n_permutations=999, seed=cfg["seed"])
            
            moran_reduction_pct = ((moran_base["I"] - moran_mem["I"]) / moran_base["I"]) * 100.0 if moran_base["I"] > 0 else 0.0
            
            record = {
                "source": source,
                "resolution": resolution,
                "model": mod_name,
                "feature_tier": tier,
                "mean_mem_features": float(np.mean(n_mem_per_fold)),
                "r2_without_mem": round(r2_base, 4),
                "r2_with_mem": round(r2_mem, 4),
                "delta_r2": round(delta_r2, 4),
                "delta_r2_ci95_low": round(ci_low, 4),
                "delta_r2_ci95_high": round(ci_high, 4),
                "rmse_without_mem": round(rmse_base, 4),
                "rmse_with_mem": round(rmse_mem, 4),
                "mae_without_mem": round(mae_base, 4),
                "mae_with_mem": round(mae_mem, 4),
                "residual_moran_i_without_mem": round(moran_base["I"], 4),
                "residual_moran_i_with_mem": round(moran_mem["I"], 4),
                "moran_i_reduction_pct": round(moran_reduction_pct, 1),
                "moran_p_without_mem": round(moran_base["pseudo_p"], 4),
                "moran_p_with_mem": round(moran_mem["pseudo_p"], 4),
            }
            results_records.append(record)
            
            print(f"[{mod_name.upper():4s} | {tier:3s}] "
                  f"R2: {r2_base:.4f} -> {r2_mem:.4f} (ΔR2 = {delta_r2:+.4f}, 95% CI [{ci_low:+.4f}, {ci_high:+.4f}]) | "
                  f"Residual Moran's I: {moran_base['I']:.4f} (p={moran_base['pseudo_p']:.3f}) -> {moran_mem['I']:.4f} (p={moran_mem['pseudo_p']:.3f}) "
                  f"[{moran_reduction_pct:.1f}% reduction]")
                  
    results_df = pd.DataFrame(results_records)
    
    # Save tables
    mem_table_path = tables_dir / "mem_comparison.csv"
    ml_mem_table_path = ml_tables_dir / "mem_comparison.csv"
    results_df.to_csv(mem_table_path, index=False)
    results_df.to_csv(ml_mem_table_path, index=False)
    print(f"\n[OK] Saved MEM comparison table to {mem_table_path} and {ml_mem_table_path}")
    
    # 3. Create Publication-Quality Diagnostic Figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=300)
    
    # Panel A: R2 Before and After MEM
    ax_a = axes[0, 0]
    labels = [f"{r['model'].upper()} ({r['feature_tier']})" for r in results_records]
    x = np.arange(len(labels))
    width = 0.35
    ax_a.bar(x - width/2, [r["r2_without_mem"] for r in results_records], width, label="Without MEM", color="#4C72B0")
    ax_a.bar(x + width/2, [r["r2_with_mem"] for r in results_records], width, label="With MEM", color="#55A868")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(labels, rotation=15, ha="right", fontsize=9, fontweight="bold")
    ax_a.set_ylabel(r"Pooled Out-of-Fold $R^2$", fontsize=10, fontweight="bold")
    ax_a.set_title(r"(A) Model Predictive Skill ($R^2$): Base vs. With MEM", fontsize=11, fontweight="bold")
    ax_a.legend(frameon=True, facecolor="white")
    ax_a.grid(True, linestyle=":", alpha=0.5)
    
    # Panel B: Residual Moran's I Before and After MEM
    ax_b = axes[0, 1]
    ax_b.bar(x - width/2, [r["residual_moran_i_without_mem"] for r in results_records], width, label="Without MEM", color="#C44E52")
    ax_b.bar(x + width/2, [r["residual_moran_i_with_mem"] for r in results_records], width, label="With MEM", color="#8172B3")
    ax_b.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(labels, rotation=15, ha="right", fontsize=9, fontweight="bold")
    ax_b.set_ylabel("Residual Moran's I", fontsize=10, fontweight="bold")
    ax_b.set_title(r"(B) Spatial Autocorrelation Reduction in Residuals", fontsize=11, fontweight="bold")
    ax_b.legend(frameon=True, facecolor="white")
    ax_b.grid(True, linestyle=":", alpha=0.5)
    
    # Panel C: Delta R2 with 95% Block-Bootstrap CI
    ax_c = axes[1, 0]
    for i, r in enumerate(results_records):
        ax_c.errorbar(
            r["delta_r2"], i,
            xerr=[[r["delta_r2"] - r["delta_r2_ci95_low"]], [r["delta_r2_ci95_high"] - r["delta_r2"]]],
            fmt="o", color="#2ca02c", ecolor="#2ca02c", elinewidth=2, capsize=4, markersize=7
        )
    ax_c.axvline(0, color="gray", linestyle="--", linewidth=1.0)
    ax_c.set_yticks(np.arange(len(labels)))
    ax_c.set_yticklabels(labels, fontsize=9, fontweight="bold")
    ax_c.set_xlabel(r"$\Delta R^2$ (With MEM - Without MEM)", fontsize=10, fontweight="bold")
    ax_c.set_title(r"(C) Incremental Value of MEM ($\Delta R^2 \pm 95\%$ Block CI)", fontsize=11, fontweight="bold")
    ax_c.grid(True, linestyle=":", alpha=0.5)
    
    # Panel D: Spectrum of Extracted Spatial Eigenvectors
    ax_d = axes[1, 1]
    ax_d.plot(np.arange(1, len(global_mi) + 1), global_mi, "o-", color="#1f77b4", markersize=4, linewidth=1.5)
    ax_d.axhline(moran_threshold, color="crimson", linestyle="--", label=f"Threshold (I > {moran_threshold})")
    ax_d.set_xlabel("Eigenvector Rank", fontsize=10, fontweight="bold")
    ax_d.set_ylabel("Moran's I of Eigenvector", fontsize=10, fontweight="bold")
    ax_d.set_title(r"(D) Global Spatial Eigenvector Spectrum (k=8 Haversine)", fontsize=11, fontweight="bold")
    ax_d.legend(frameon=True, facecolor="white")
    ax_d.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    fig_path = figures_dir / "mem_comparison.png"
    ml_fig_path = ml_figures_dir / "mem_comparison.png"
    fig.savefig(fig_path, dpi=300)
    fig.savefig(ml_fig_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved MEM diagnostic figure to {fig_path} and {ml_fig_path}")
    
    return results_df


if __name__ == "__main__":
    args = parse_args()
    run_mem_evaluation(
        source=args.source,
        resolution=args.resolution,
        target=args.target,
        k=args.k,
        moran_threshold=args.moran_threshold,
        fast=args.fast
    )
