"""
run_orthogonalized_stability.py
-------------------------------
Stage: Orthogonalized Climate Stability Evaluation.

Implements:
1. Orthogonalization of Quaternary climate stability features against absolute latitude,
   elevation, and topographic relief using Ridge(alpha=1e-3).
2. Fold-safe evaluation: fit transformations strictly on training folds and apply to test folds.
3. Recalculation of Variance Inflation Factors (VIF) and Pearson correlations.
4. Evaluation of the unique incremental predictive contribution of stability (Delta-R2)
   across linear (OLS reference, Ridge) and non-linear (RF, HGB) models.
5. Generation of comparison tables and diagnostic figures.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.config import get_validated_config
from ml.src.data import load_dataset, StabilityOrthogonalizer, orthogonalize_stability_features
from ml.src.cv import spatial_outer_folds
from ml.src.metrics import calc_r2, calc_rmse, pooled_out_of_fold_r2, block_bootstrap_ci


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Orthogonalized Climate Stability")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--target", type=str, default="gbif_log_richness")
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    return parser.parse_args()


def compute_vif_table(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """Compute Variance Inflation Factor table for a list of features."""
    clean_df = df[feature_cols].dropna()
    X = sm.add_constant(clean_df)
    vif_rows = []
    for i, col in enumerate(X.columns):
        if col == "const":
            continue
        try:
            val = float(variance_inflation_factor(X.values, i))
        except Exception:
            val = np.nan
        vif_rows.append({"feature": col, "VIF": round(val, 2)})
    return pd.DataFrame(vif_rows)


def run_orthogonalized_stability_evaluation(
    source: str = "paleoclim",
    resolution: str = "base",
    target: str = "gbif_log_richness",
    fast: bool = False
):
    print("=" * 80)
    print(f"RUNNING ORTHOGONALIZED CLIMATE STABILITY EVALUATION")
    print(f"Source: {source.upper()} | Res: {resolution} | Target: {target}")
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
    
    comp_col = f"{'pc' if source == 'paleoclim' else 'wc'}_composite_instability"
    stability_cols = cfg["stability_columns"][source]
    control_cols = ["abs_lat", "elevation", "relief"]
    if "elevation_mean" in df.columns and "elevation" not in df.columns:
        control_cols = ["abs_lat", "elevation_mean", "topographic_heterogeneity"]
        
    y_true = df["y"].values
    
    # -------------------------------------------------------------------------
    # 1. Global VIF and Correlations: Before vs. After Orthogonalization
    # -------------------------------------------------------------------------
    print("\n--- 1. Computing VIF & Correlations: Raw vs. Orthogonalized ---")
    
    vif_features_base = control_cols + [comp_col]
    vif_df_raw = compute_vif_table(df, vif_features_base)
    vif_df_raw.rename(columns={"VIF": "VIF_raw"}, inplace=True)
    
    # Orthogonalize on full dataset for global correlation / VIF reporting
    df_orth_global, _ = orthogonalize_stability_features(
        df, stability_cols=stability_cols, control_cols=control_cols, alpha=1e-3
    )
    vif_df_orth = compute_vif_table(df_orth_global, vif_features_base)
    vif_df_orth.rename(columns={"VIF": "VIF_orthogonalized"}, inplace=True)
    
    vif_comparison = vif_df_raw.merge(vif_df_orth, on="feature")
    print("VIF Comparison (Controls + Composite Stability):")
    print(vif_comparison.to_string(index=False))
    
    # Pearson correlations with controls before and after
    corr_records = []
    for sc in [comp_col] + [c for c in stability_cols if "composite" not in c][:3]:
        for ctrl in control_cols:
            r_raw = float(df[[sc, ctrl]].corr().iloc[0, 1])
            r_orth = float(df_orth_global[[sc, ctrl]].corr().iloc[0, 1])
            corr_records.append({
                "stability_metric": sc,
                "control": ctrl,
                "raw_correlation": round(r_raw, 4),
                "orthogonalized_correlation": round(r_orth, 4)
            })
    corr_df = pd.DataFrame(corr_records)
    print("\nCorrelations with Controls (Raw vs. Orthogonalized):")
    print(corr_df.to_string(index=False))
    
    # Save VIF & correlation tables
    vif_out_csv = tables_dir / "orthogonalized_stability_vif.csv"
    vif_comparison.to_csv(vif_out_csv, index=False)
    vif_comparison.to_csv(ml_tables_dir / "orthogonalized_stability_vif.csv", index=False)
    
    corr_out_csv = tables_dir / "orthogonalized_stability_correlations.csv"
    corr_df.to_csv(corr_out_csv, index=False)
    corr_df.to_csv(ml_tables_dir / "orthogonalized_stability_correlations.csv", index=False)
    
    # -------------------------------------------------------------------------
    # 2. Fold-Safe Spatial CV Evaluation
    # -------------------------------------------------------------------------
    print("\n--- 2. Fold-Safe Spatial Cross-Validation: Raw vs. Orthogonalized ---")
    folds, groups = spatial_outer_folds(df, k=5, seed=cfg["seed"], offset=0.0, reuse_phase6=(resolution == "base"))
    
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
    
    eval_records = []
    
    # Benchmark M1 (controls only)
    m1_cols = feature_sets["M1"]
    m2a_cols = feature_sets["M2a"]
    
    for mod_name, mod_fn in models.items():
        oof_m1 = np.zeros(len(df))
        oof_m2a_raw = np.zeros(len(df))
        oof_m2a_orth = np.zeros(len(df))
        
        for tr, te in folds:
            df_tr = df.iloc[tr].copy()
            df_te = df.iloc[te].copy()
            y_tr = y_true[tr]
            
            # Fit orthogonalizer strictly on training fold
            orth = StabilityOrthogonalizer(stability_cols=stability_cols, control_cols=control_cols, alpha=1e-3)
            orth.fit(df_tr)
            
            df_tr_orth = orth.transform(df_tr)
            df_te_orth = orth.transform(df_te)
            
            # Model 1: M1 controls alone
            pipe_m1 = mod_fn()
            pipe_m1.fit(df_tr[m1_cols], y_tr)
            oof_m1[te] = pipe_m1.predict(df_te[m1_cols])
            
            # Model 2a Raw: M1 + Raw Composite Stability
            pipe_raw = mod_fn()
            pipe_raw.fit(df_tr[m2a_cols], y_tr)
            oof_m2a_raw[te] = pipe_raw.predict(df_te[m2a_cols])
            
            # Model 2a Orth: M1 + Orthogonalized Composite Stability
            pipe_orth = mod_fn()
            pipe_orth.fit(df_tr_orth[m2a_cols], y_tr)
            oof_m2a_orth[te] = pipe_orth.predict(df_te_orth[m2a_cols])
            
        r2_m1 = pooled_out_of_fold_r2(y_true, oof_m1)
        r2_raw = pooled_out_of_fold_r2(y_true, oof_m2a_raw)
        r2_orth = pooled_out_of_fold_r2(y_true, oof_m2a_orth)
        
        delta_raw = r2_raw - r2_m1
        delta_orth = r2_orth - r2_m1
        
        # Block-bootstrap CIs
        _, ci_raw_l, ci_raw_h = block_bootstrap_ci(y_true, oof_m1, oof_m2a_raw, groups, metric="r2", n=1000, seed=cfg["seed"])
        _, ci_orth_l, ci_orth_h = block_bootstrap_ci(y_true, oof_m1, oof_m2a_orth, groups, metric="r2", n=1000, seed=cfg["seed"])
        
        eval_records.append({
            "source": source,
            "resolution": resolution,
            "model": mod_name,
            "r2_m1_controls": round(r2_m1, 4),
            "r2_m2a_raw": round(r2_raw, 4),
            "r2_m2a_orthogonalized": round(r2_orth, 4),
            "delta_r2_raw": round(delta_raw, 4),
            "delta_r2_raw_ci95_low": round(ci_raw_l, 4),
            "delta_r2_raw_ci95_high": round(ci_raw_h, 4),
            "delta_r2_orthogonalized": round(delta_orth, 4),
            "delta_r2_orth_ci95_low": round(ci_orth_l, 4),
            "delta_r2_orth_ci95_high": round(ci_orth_h, 4),
        })
        
        print(f"[{mod_name:13s}] M1 R2: {r2_m1:.4f} | Raw M2a ΔR2: {delta_raw:+.4f} (95% CI [{ci_raw_l:+.4f}, {ci_raw_h:+.4f}]) | "
              f"Orth M2a ΔR2: {delta_orth:+.4f} (95% CI [{ci_orth_l:+.4f}, {ci_orth_h:+.4f}])")
              
    eval_df = pd.DataFrame(eval_records)
    eval_out_csv = tables_dir / "orthogonalized_stability_evaluation.csv"
    eval_df.to_csv(eval_out_csv, index=False)
    eval_df.to_csv(ml_tables_dir / "orthogonalized_stability_evaluation.csv", index=False)
    print(f"\n[OK] Saved orthogonalized evaluation table to {eval_out_csv}")
    
    # -------------------------------------------------------------------------
    # 3. Publication Figure: Orthogonalized Stability Contribution
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    
    # Panel A: VIF reduction
    ax_a = axes[0]
    x_vif = np.arange(len(vif_comparison))
    w_vif = 0.35
    ax_a.bar(x_vif - w_vif/2, vif_comparison["VIF_raw"], w_vif, label="Raw Features", color="#C44E52")
    ax_a.bar(x_vif + w_vif/2, vif_comparison["VIF_orthogonalized"], w_vif, label="Orthogonalized", color="#4C72B0")
    ax_a.set_xticks(x_vif)
    ax_a.set_xticklabels(vif_comparison["feature"], rotation=15, ha="right", fontsize=9, fontweight="bold")
    ax_a.set_ylabel("Variance Inflation Factor (VIF)", fontsize=10, fontweight="bold")
    ax_a.set_title("(A) Multicollinearity Reduction (VIF)", fontsize=11, fontweight="bold")
    ax_a.axhline(5.0, color="gray", linestyle="--", linewidth=0.8, label="VIF Threshold (5.0)")
    ax_a.legend(frameon=True, facecolor="white")
    ax_a.grid(True, linestyle=":", alpha=0.5)
    
    # Panel B: Delta R2 Comparison (Raw vs Orthogonalized)
    ax_b = axes[1]
    y_pos = np.arange(len(eval_records))
    labels = [r["model"] for r in eval_records]
    
    ax_b.errorbar(
        [r["delta_r2_raw"] for r in eval_records], y_pos - 0.15,
        xerr=[
            [r["delta_r2_raw"] - r["delta_r2_raw_ci95_low"] for r in eval_records],
            [r["delta_r2_raw_ci95_high"] - r["delta_r2_raw"] for r in eval_records]
        ],
        fmt="o", color="#C44E52", ecolor="#C44E52", elinewidth=2, capsize=4, label="Raw Stability"
    )
    ax_b.errorbar(
        [r["delta_r2_orthogonalized"] for r in eval_records], y_pos + 0.15,
        xerr=[
            [r["delta_r2_orthogonalized"] - r["delta_r2_orth_ci95_low"] for r in eval_records],
            [r["delta_r2_orth_ci95_high"] - r["delta_r2_orthogonalized"] for r in eval_records]
        ],
        fmt="s", color="#4C72B0", ecolor="#4C72B0", elinewidth=2, capsize=4, label="Orthogonalized Stability"
    )
    ax_b.axvline(0, color="black", linestyle="--", linewidth=0.9)
    ax_b.set_yticks(y_pos)
    ax_b.set_yticklabels(labels, fontsize=10, fontweight="bold")
    ax_b.set_xlabel(r"Unique Incremental $\Delta R^2$ ($M2a - M1$)", fontsize=10, fontweight="bold")
    ax_b.set_title(r"(B) Unique Predictive Skill of Climate Stability", fontsize=11, fontweight="bold")
    ax_b.legend(frameon=True, facecolor="white")
    ax_b.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    fig_path = figures_dir / "orthogonalized_stability_comparison.png"
    fig.savefig(fig_path, dpi=300)
    fig.savefig(ml_figures_dir / "orthogonalized_stability_comparison.png", dpi=300)
    plt.close(fig)
    print(f"[OK] Saved orthogonalized stability figure to {fig_path}")
    
    return eval_df, vif_comparison


if __name__ == "__main__":
    args = parse_args()
    run_orthogonalized_stability_evaluation(
        source=args.source,
        resolution=args.resolution,
        target=args.target,
        fast=args.fast
    )
