"""
run_loco.py
-----------
Leave-One-Continent-Out (LOCO) Cross-Validation and Generalisation Assessment.
Part A of Stage 4.

Evaluates out-of-continent transferability across feature sets (M0, M1, M2a, M2b)
and model architectures (ridge, rf, hgb, ols_reference).
Uses inner GroupKFold(3) on 20-degree blocks strictly within the training continents.
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
from sklearn.model_selection import GroupKFold, GridSearchCV, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression

from src.ml.config import load_config
from src.ml.data import load_dataset
from src.ml.spatial import block_id
from src.ml.models import get_regressor, get_param_grid
from src.ml.metrics import calc_r2, calc_rmse, calc_spearman

warnings.filterwarnings("ignore")


def run_loco(source: str = "paleoclim", resolution: str = "base", fast: bool = False):
    print(f"\n=======================================================")
    print(f"  RUNNING LOCO EVALUATION: source={source}, res={resolution}, fast={fast}")
    print(f"=======================================================\n")
    
    cfg = load_config()
    min_cells = cfg.get("loco", {}).get("min_cells_per_continent", 15)
    
    # Load dataset
    df, feature_groups, feature_sets = load_dataset(source, resolution)
    df = df.copy()
    
    # Create spatial block IDs for inner tuning
    df["block"] = block_id(df["lon"].values, df["lat"].values, size=20, offset=0.0)
    
    # Setup directories
    tables_dir = REPO_ROOT / "results" / "tables"
    ml_out_dir = REPO_ROOT / "results" / "ml" / f"{source}_{resolution}"
    ml_tables_dir = ml_out_dir / "tables"
    ml_figures_dir = ml_out_dir / "figures"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    
    # Continents audit
    continent_counts = df["continent"].value_counts().to_dict()
    all_continents = sorted(continent_counts.keys())
    
    eval_continents = [c for c in all_continents if continent_counts[c] >= min_cells]
    skipped_continents = [c for c in all_continents if continent_counts[c] < min_cells]
    
    print(f"Continent Cell Counts (min_cells_per_continent = {min_cells}):")
    for c in all_continents:
        status = "EVALUATE" if c in eval_continents else "SKIP"
        print(f"  - {c:15s}: {continent_counts[c]:3d} cells [{status}]")
        
    models_to_run = ["ols_reference", "ridge", "rf", "hgb"]
    feature_tiers = ["M0", "M1", "M2a", "M2b"]
    
    results = []
    
    # Record skipped continents
    for c in skipped_continents:
        results.append({
            "source": source,
            "resolution": resolution,
            "continent": c,
            "status": "skipped",
            "n_cells": continent_counts[c],
            "model": "all",
            "feature_set": "all",
            "r2": np.nan,
            "rmse": np.nan,
            "spearman_rho": np.nan,
            "spearman_p": np.nan,
            "delta_r2_m2a_minus_m1": np.nan,
            "delta_r2_m2b_minus_m1": np.nan
        })
        
    for c_idx, test_continent in enumerate(eval_continents):
        n_c = continent_counts[test_continent]
        print(f"\n[{c_idx + 1}/{len(eval_continents)}] Held-out Continent: {test_continent} (n={n_c})")
        
        test_mask = (df["continent"] == test_continent).values
        train_mask = ~test_mask
        
        df_tr = df[train_mask]
        df_te = df[test_mask]
        
        groups_tr = df_tr["block"].values
        y_tr = df_tr["y"].values
        y_te = df_te["y"].values
        
        # Verify training set has enough blocks for inner CV
        unique_tr_blocks = np.unique(groups_tr)
        n_inner = min(3, len(unique_tr_blocks))
        assert n_inner >= 3, f"Not enough blocks ({len(unique_tr_blocks)}) in training continents for 3-fold inner CV!"
        
        # Store predictions per model & feature set for this continent
        cont_preds = {}
        cont_metrics = {}
        
        for model_name in models_to_run:
            for fset_name in feature_tiers:
                f_cols = feature_sets[fset_name]
                X_tr = df_tr[f_cols]
                X_te = df_te[f_cols]
                
                if model_name == "ols_reference":
                    pipe = Pipeline([
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                        ("model", LinearRegression())
                    ])
                    pipe.fit(X_tr, y_tr)
                    fitted_model = pipe
                elif model_name == "ridge":
                    pipe = get_regressor("ridge", random_state=cfg["seed"])
                    p_grid = get_param_grid("ridge", fast=fast)
                    cv_inner = GroupKFold(n_splits=n_inner)
                    tuner = GridSearchCV(pipe, p_grid, cv=cv_inner, scoring="r2", n_jobs=-1)
                    tuner.fit(X_tr, y_tr, groups=groups_tr)
                    fitted_model = tuner.best_estimator_
                elif model_name in ["rf", "hgb"]:
                    pipe = get_regressor(model_name, random_state=cfg["seed"])
                    p_grid = get_param_grid(model_name, fast=fast)
                    cv_inner = GroupKFold(n_splits=n_inner)
                    n_it = 6 if fast else 15
                    tuner = RandomizedSearchCV(
                        pipe, p_grid, n_iter=n_it, cv=cv_inner, scoring="r2",
                        random_state=cfg["seed"], n_jobs=-1
                    )
                    tuner.fit(X_tr, y_tr, groups=groups_tr)
                    fitted_model = tuner.best_estimator_
                    
                y_pred = fitted_model.predict(X_te)
                cont_preds[(model_name, fset_name)] = y_pred
                
                r2 = calc_r2(y_te, y_pred)
                rmse = calc_rmse(y_te, y_pred)
                rho, p_val = calc_spearman(y_te, y_pred)
                
                cont_metrics[(model_name, fset_name)] = {
                    "r2": r2,
                    "rmse": rmse,
                    "spearman_rho": rho,
                    "spearman_p": p_val
                }
                
            # Compute deltas for this model
            r2_m1 = cont_metrics[(model_name, "M1")]["r2"]
            r2_m2a = cont_metrics[(model_name, "M2a")]["r2"]
            r2_m2b = cont_metrics[(model_name, "M2b")]["r2"]
            delta_a = r2_m2a - r2_m1
            delta_b = r2_m2b - r2_m1
            
            for fset_name in feature_tiers:
                m = cont_metrics[(model_name, fset_name)]
                results.append({
                    "source": source,
                    "resolution": resolution,
                    "continent": test_continent,
                    "status": "evaluated",
                    "n_cells": n_c,
                    "model": model_name,
                    "feature_set": fset_name,
                    "r2": m["r2"],
                    "rmse": m["rmse"],
                    "spearman_rho": m["spearman_rho"],
                    "spearman_p": m["spearman_p"],
                    "delta_r2_m2a_minus_m1": delta_a if fset_name == "M2a" else np.nan,
                    "delta_r2_m2b_minus_m1": delta_b if fset_name == "M2b" else np.nan
                })
                
            print(f"  {model_name:14s} | M1 R2: {r2_m1:+.3f} | M2a R2: {r2_m2a:+.3f} (Δ={delta_a:+.3f}) | M1 Rho: {cont_metrics[(model_name, 'M1')]['spearman_rho']:.3f}")

    res_df = pd.DataFrame(results)
    
    # Save CSV tables
    out_csv = tables_dir / "loco_metrics.csv"
    ml_out_csv = ml_tables_dir / "loco_metrics.csv"
    res_df.to_csv(out_csv, index=False)
    res_df.to_csv(ml_out_csv, index=False)
    print(f"\n[OK] Saved LOCO metrics to {out_csv} and {ml_out_csv}")
    
    # -------------------------------------------------------------
    # FIGURES
    # -------------------------------------------------------------
    eval_df = res_df[res_df["status"] == "evaluated"].copy()
    
    # Determine best model by mean R2 on M2a
    m2a_means = eval_df[eval_df["feature_set"] == "M2a"].groupby("model")["r2"].mean()
    best_model = m2a_means.idxmax() if not m2a_means.empty else "rf"
    print(f"\nBest model for LOCO heatmap: {best_model} (Mean M2a R2 = {m2a_means.get(best_model, 0.0):.3f})")
    
    # 1. Heatmap of R2 (continent by feature set) for best model
    best_df = eval_df[eval_df["model"] == best_model]
    pivot_r2 = best_df.pivot(index="continent", columns="feature_set", values="r2")[["M0", "M1", "M2a", "M2b"]]
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    cax = ax.matshow(pivot_r2.values, cmap="RdYlBu_r", vmin=-1.0, vmax=1.0)
    fig.colorbar(cax, ax=ax, label=r"Held-Out Continent $R^2$")
    
    ax.set_xticks(range(len(pivot_r2.columns)))
    ax.set_xticklabels(pivot_r2.columns, fontsize=11, fontweight="bold")
    ax.set_yticks(range(len(pivot_r2.index)))
    ax.set_yticklabels(pivot_r2.index, fontsize=11)
    
    # Text annotations
    for i in range(len(pivot_r2.index)):
        for j in range(len(pivot_r2.columns)):
            val = pivot_r2.values[i, j]
            txt = f"{val:+.2f}"
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, txt, ha="center", va="center", color=color, fontweight="bold", fontsize=10)
            
    ax.set_title(f"LOCO Generalisation $R^2$ by Continent ({best_model.upper()})", fontsize=12, fontweight="bold", pad=15)
    plt.tight_layout()
    heatmap_path = ml_figures_dir / "loco_heatmap_r2.png"
    plt.savefig(heatmap_path, dpi=300)
    plt.close()
    print(f"[OK] Saved LOCO heatmap to {heatmap_path}")
    
    # 2. Bar chart of delta R2 (M2a - M1) by continent
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    
    m2a_deltas = eval_df[eval_df["feature_set"] == "M2a"].copy()
    continents = sorted(m2a_deltas["continent"].unique())
    x = np.arange(len(continents))
    width = 0.2
    
    models_to_plot = [m for m in ["ols_reference", "ridge", "rf", "hgb"] if m in m2a_deltas["model"].unique()]
    palette = ["#4C72B0", "#55A868", "#C44E52", "#8172B3"]
    
    for i, mod in enumerate(models_to_plot):
        sub = m2a_deltas[m2a_deltas["model"] == mod].set_index("continent").reindex(continents)
        deltas = sub["delta_r2_m2a_minus_m1"].values
        ax.bar(x + (i - len(models_to_plot)/2 + 0.5) * width, deltas, width, label=mod, color=palette[i % len(palette)], alpha=0.85)
        
    ax.axhline(0, color="black", linestyle="--", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(continents, fontsize=11)
    ax.set_ylabel(r"$\Delta R^2$ ($M2a - M1$)", fontsize=12, fontweight="bold")
    ax.set_title(r"LOCO Transferability: Stability Value ($\Delta R^2$) by Continent", fontsize=13, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", edgecolor="none")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    bar_path = ml_figures_dir / "loco_delta_r2.png"
    plt.savefig(bar_path, dpi=300)
    plt.close()
    print(f"[OK] Saved LOCO delta R2 bar chart to {bar_path}")
    
    return res_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 4 Part A: Leave-One-Continent-Out Cross-Validation")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode with smaller search grid")
    args = parser.parse_args()
    
    run_loco(source=args.source, resolution=args.resolution, fast=args.fast)
