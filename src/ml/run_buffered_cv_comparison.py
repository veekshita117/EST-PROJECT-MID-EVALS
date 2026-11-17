"""
run_buffered_cv_comparison.py
-----------------------------
Evaluation and comparison script for Buffered Spatial Cross-Validation:
- Compares standard 20° GroupKFold vs. BufferedSpatialCV (5 folds, 1000 km exclusion buffer).
- Reports effective training sample sizes, discarded observations, and discard rates per fold.
- Compares out-of-fold predictive skill (R²) and stability contributions (Delta-R²).
- Evaluates spatial autocorrelation in residuals under both schemes.
- Generates comparison tables and publication-quality diagnostic visualizations.
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
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor

from src.ml.config import get_validated_config
from src.ml.data import load_dataset
from src.ml.cv import spatial_outer_folds, BufferedSpatialCV
from src.ml.run_residuals import calc_morans_i, build_knn_weights
from src.ml.metrics import calc_r2, calc_rmse, pooled_out_of_fold_r2, block_bootstrap_ci


def parse_args():
    parser = argparse.ArgumentParser(description="Compare Block CV vs. Buffered Spatial CV")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--target", type=str, default="gbif_log_richness")
    parser.add_argument("--buffer_km", type=float, default=1000.0, help="Buffer exclusion distance (km)")
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    return parser.parse_args()


def run_buffered_cv_comparison(
    source: str = "paleoclim",
    resolution: str = "base",
    target: str = "gbif_log_richness",
    buffer_km: float = 1000.0,
    fast: bool = False
):
    print("=" * 80)
    print(f"BUFFERED SPATIAL CROSS-VALIDATION COMPARISON")
    print(f"Source: {source.upper()} | Res: {resolution} | Target: {target} | Buffer: {buffer_km:.0f} km")
    print("=" * 80)

    cfg = get_validated_config()
    df, feature_groups, feature_sets = load_dataset(source=source, resolution=resolution, target=target)
    
    tables_dir = REPO_ROOT / "results" / "tables"
    figures_dir = REPO_ROOT / "results" / "figures"
    ml_tables_dir = REPO_ROOT / "results" / "ml" / f"{source}_{resolution}" / "tables"
    ml_figures_dir = REPO_ROOT / "results" / "ml" / f"{source}_{resolution}" / "figures"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    
    coords = df[["lon", "lat"]].values
    W_knn = build_knn_weights(coords, k=8)
    y_true = df["y"].values
    
    # 1. Setup CV Schemes
    # Scheme A: Standard 20° GroupKFold
    block_folds, block_groups = spatial_outer_folds(df, k=5, seed=cfg["seed"], offset=0.0, reuse_phase6=(resolution == "base"))
    
    # Scheme B: BufferedSpatialCV (5 folds, 1000 km buffer)
    buffered_cv = BufferedSpatialCV(n_splits=5, buffer_km=buffer_km, seed=cfg["seed"])
    buffered_folds = list(buffered_cv.split(df, groups=block_groups))
    diag_df = buffered_cv.get_diagnostics_df()
    
    print("\n--- Buffered CV Fold Diagnostics (1000 km exclusion buffer) ---")
    print(diag_df.to_string(index=False))
    
    diag_csv = tables_dir / "buffered_cv_diagnostics.csv"
    diag_df.to_csv(diag_csv, index=False)
    diag_df.to_csv(ml_tables_dir / "buffered_cv_diagnostics.csv", index=False)
    print(f"[OK] Saved fold diagnostics to {diag_csv}")
    
    # Models to test
    models = {
        "ols_reference": lambda: Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression())
        ]),
        "ridge": lambda: Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=10.0, random_state=cfg["seed"]))
        ]),
        "rf": lambda: Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(n_estimators=100 if fast else 300, max_depth=6, random_state=cfg["seed"], n_jobs=-1))
        ]),
        "hgb": lambda: Pipeline([
            ("model", HistGradientBoostingRegressor(max_iter=100 if fast else 200, learning_rate=0.05, max_depth=4, random_state=cfg["seed"], early_stopping=False))
        ])
    }
    
    comparison_rows = []
    
    for cv_name, folds in [("20deg_GroupKFold", block_folds), ("Buffered_1000km", buffered_folds)]:
        for mod_name, mod_fn in models.items():
            for fset_name in ["M1", "M2a"]:
                cols = feature_sets[fset_name]
                oof_preds = np.zeros(len(df))
                
                for tr, te in folds:
                    pipe = mod_fn()
                    pipe.fit(df.iloc[tr][cols], y_true[tr])
                    oof_preds[te] = pipe.predict(df.iloc[te][cols])
                    
                r2 = pooled_out_of_fold_r2(y_true, oof_preds)
                rmse = calc_rmse(y_true, oof_preds)
                resids = y_true - oof_preds
                moran = calc_morans_i(resids, W_knn, n_permutations=499 if fast else 999, seed=cfg["seed"])
                
                comparison_rows.append({
                    "source": source,
                    "resolution": resolution,
                    "cv_scheme": cv_name,
                    "model": mod_name,
                    "feature_tier": fset_name,
                    "r2": round(r2, 4),
                    "rmse": round(rmse, 4),
                    "residual_moran_i": round(moran["I"], 4),
                    "moran_p": round(moran["pseudo_p"], 4),
                })
                
    comp_df = pd.DataFrame(comparison_rows)
    
    # Calculate delta R2 (M2a - M1) for each scheme and model
    pivoted_records = []
    for mod_name in models.keys():
        for cv_name in ["20deg_GroupKFold", "Buffered_1000km"]:
            sub = comp_df[(comp_df.model == mod_name) & (comp_df.cv_scheme == cv_name)]
            r2_m1 = sub[sub.feature_tier == "M1"]["r2"].values[0]
            r2_m2a = sub[sub.feature_tier == "M2a"]["r2"].values[0]
            delta = r2_m2a - r2_m1
            moran_m2a = sub[sub.feature_tier == "M2a"]["residual_moran_i"].values[0]
            
            pivoted_records.append({
                "cv_scheme": cv_name,
                "model": mod_name,
                "r2_m1": r2_m1,
                "r2_m2a": r2_m2a,
                "delta_r2_m2a_m1": round(delta, 4),
                "residual_moran_i": moran_m2a
            })
            
    summary_df = pd.DataFrame(pivoted_records)
    print("\n--- Performance Comparison: 20° GroupKFold vs. Buffered Spatial CV ---")
    print(summary_df.to_string(index=False))
    
    comp_csv = tables_dir / "buffered_cv_comparison.csv"
    summary_df.to_csv(comp_csv, index=False)
    summary_df.to_csv(ml_tables_dir / "buffered_cv_comparison.csv", index=False)
    print(f"\n[OK] Saved CV comparison table to {comp_csv}")
    
    # 2. Publication-Quality Visualization
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    
    # Panel A: Effective Training Size and Discarded Counts per Fold
    ax_a = axes[0]
    fold_nums = diag_df["fold"].values
    w = 0.4
    ax_a.bar(fold_nums - w/2, diag_df["n_effective_train"], w, label="Effective Train Cells", color="#2ca02c")
    ax_a.bar(fold_nums + w/2, diag_df["n_discarded"], w, label="Discarded Buffer Cells (1000 km)", color="#d62728")
    ax_a.set_xlabel("Cross-Validation Fold", fontsize=11, fontweight="bold")
    ax_a.set_ylabel("Number of Grid Cells", fontsize=11, fontweight="bold")
    ax_a.set_title(r"(A) Effective Sample Sizes & Discarded Buffer Cells", fontsize=12, fontweight="bold")
    ax_a.set_xticks(fold_nums)
    ax_a.legend(frameon=True, facecolor="white")
    ax_a.grid(True, linestyle=":", alpha=0.5)
    
    # Annotate discard rate
    for i, r in diag_df.iterrows():
        ax_a.text(r["fold"] + w/2, r["n_discarded"] + 2, f"{r['discard_rate_pct']:.0f}%", ha="center", fontsize=9, fontweight="bold", color="#d62728")
        
    # Panel B: Out-of-fold R2 Comparison (Block vs Buffered)
    ax_b = axes[1]
    mods = list(models.keys())
    x_mod = np.arange(len(mods))
    r2_block = [summary_df[(summary_df.model == m) & (summary_df.cv_scheme == "20deg_GroupKFold")]["r2_m2a"].values[0] for m in mods]
    r2_buff = [summary_df[(summary_df.model == m) & (summary_df.cv_scheme == "Buffered_1000km")]["r2_m2a"].values[0] for m in mods]
    
    ax_b.bar(x_mod - w/2, r2_block, w, label=r"Standard 20° GroupKFold", color="#4C72B0")
    ax_b.bar(x_mod + w/2, r2_buff, w, label=r"Buffered Spatial CV (1000 km)", color="#55A868")
    ax_b.set_xticks(x_mod)
    ax_b.set_xticklabels(mods, fontsize=10, fontweight="bold")
    ax_b.set_ylabel(r"Pooled Out-of-Fold $R^2$ ($M2a$)", fontsize=11, fontweight="bold")
    ax_b.set_title(r"(B) Out-of-Fold Generalization: Block vs. Buffered CV", fontsize=12, fontweight="bold")
    ax_b.legend(frameon=True, facecolor="white")
    ax_b.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    fig_path = figures_dir / "buffered_cv_comparison.png"
    fig.savefig(fig_path, dpi=300)
    fig.savefig(ml_figures_dir / "buffered_cv_comparison.png", dpi=300)
    plt.close(fig)
    print(f"[OK] Saved buffered CV diagnostic figure to {fig_path}")
    
    return summary_df, diag_df


if __name__ == "__main__":
    args = parse_args()
    run_buffered_cv_comparison(
        source=args.source,
        resolution=args.resolution,
        target=args.target,
        buffer_km=args.buffer_km,
        fast=args.fast
    )
