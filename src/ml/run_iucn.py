"""
run_iucn.py
-----------
Executes the Machine Learning pipeline on IUCN targets (iucn_log_richness, iucn_small_range, iucn_endemism)
across spatial resolutions (5deg and 2deg) using data_v3_5deg.csv and data_v3_2deg.csv.

Feature Sets:
  M1: abs_lat, elevation_mean, topographic_heterogeneity,
      contemporary climate (pc_temp_present, pc_precip_present, pc_bio4_present, pc_bio15_present)
  M2: M1 + log10_velocity_temp + refugial_area_fraction + temp_anomaly + precip_rel_change

Controls:
  log_n and GBIF effort are dropped entirely.

Validation:
  - 20° spatial-block CV with nested GroupKFold(3) inner tuning.
  - Paired delta R2 (M2 minus M1) with cluster block-bootstrap 95% CIs (B=1000).
  - Leave-One-Continent-Out (LOCO) generalization assessment across all 6 continents.

Models:
  - OLS Reference (StandardScaler + LinearRegression)
  - Ridge (inner CV on alphas)
  - Random Forest (inner CV on max_depth, min_samples_leaf, max_features)
  - HistGradientBoosting (inner CV on learning_rate, max_depth, min_samples_leaf, max_iter)

Outputs saved to ml/outputs/iucn_5deg/, ml/outputs/iucn_2deg/, and ml/outputs/iucn_*.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold, GridSearchCV, RandomizedSearchCV

from src.ml.spatial import block_id
from src.ml.cv import spatial_outer_folds, assert_no_group_overlap
from src.ml.data import load_dataset
from src.ml.metrics import calc_r2, calc_rmse, calc_spearman, pooled_out_of_fold_r2, block_bootstrap_ci


def get_model_and_grid(model_name: str, seed: int = 42, fast: bool = False):
    """Factory returning base estimator and search object for inner tuning."""
    model_name = model_name.lower()
    if model_name in ["ols", "ols_reference"]:
        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression())
        ])
        return pipe, None
        
    elif model_name == "ridge":
        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(random_state=seed))
        ])
        alphas = np.logspace(-3, 3, 7 if fast else 13)
        grid = {"model__alpha": alphas}
        return pipe, ("grid", grid)
        
    elif model_name == "rf":
        pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(n_estimators=100, random_state=seed, n_jobs=-1))
        ])
        if fast:
            p_dist = {
                "model__max_depth": [4, 8],
                "model__min_samples_leaf": [1, 5],
                "model__max_features": [0.6, 1.0]
            }
            n_iter = 4
        else:
            p_dist = {
                "model__max_depth": [4, 8, 12, None],
                "model__min_samples_leaf": [1, 3, 5, 10],
                "model__max_features": [0.33, 0.6, 1.0]
            }
            n_iter = 8
        return pipe, ("random", p_dist, n_iter)
        
    elif model_name == "hgb":
        pipe = Pipeline([
            ("model", HistGradientBoostingRegressor(early_stopping=False, random_state=seed))
        ])
        if fast:
            p_dist = {
                "model__learning_rate": [0.03, 0.1],
                "model__max_depth": [3, 5],
                "model__max_iter": [100]
            }
            n_iter = 4
        else:
            p_dist = {
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__max_depth": [3, 5, 8],
                "model__min_samples_leaf": [10, 20, 50],
                "model__max_iter": [100, 200]
            }
            n_iter = 8
        return pipe, ("random", p_dist, n_iter)
    else:
        raise ValueError(f"Unknown model_name '{model_name}'")


def fit_with_inner_tuning(pipe, search_spec, X_tr, y_tr, tr_groups, seed: int = 42):
    """Fits estimator with inner 3-fold spatial GroupKFold tuning."""
    if search_spec is None:
        pipe.fit(X_tr, y_tr)
        return pipe, {}
        
    cv_inner = GroupKFold(n_splits=3)
    # Verify inner groups have at least 3 distinct blocks
    n_unique_grps = len(np.unique(tr_groups))
    splits = min(3, max(2, n_unique_grps))
    if splits < 3:
        cv_inner = GroupKFold(n_splits=splits)
        
    if search_spec[0] == "grid":
        _, grid = search_spec
        search = GridSearchCV(pipe, grid, cv=cv_inner, scoring="r2", n_jobs=-1)
    else:
        _, p_dist, n_iter = search_spec
        search = RandomizedSearchCV(pipe, p_dist, n_iter=n_iter, cv=cv_inner, scoring="r2", random_state=seed, n_jobs=-1)
        
    search.fit(X_tr, y_tr, groups=tr_groups)
    return search.best_estimator_, search.best_params_


def run_spatial_cv_for_target(
    df: pd.DataFrame,
    target_name: str,
    resolution: str,
    feature_sets: Dict[str, List[str]],
    models: List[str] = ["ols", "ridge", "rf", "hgb"],
    seed: int = 42,
    fast: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Runs 20° spatial-block CV for one target and resolution."""
    print(f"\n=======================================================")
    print(f"  SPATIAL CV: Resolution={resolution}, Target={target_name}")
    print(f"=======================================================")
    
    y = df["y"].values
    blocks = block_id(df["lon"].values, df["lat"].values, size=20.0, offset=0.0)
    blocks = pd.Series(blocks, index=df.index)
    
    # Generate outer 5 folds
    gkf = GroupKFold(n_splits=5)
    folds = list(gkf.split(df, groups=blocks))
    
    # Assert zero train/test block overlap
    for f_idx, (tr, te) in enumerate(folds):
        assert_no_group_overlap(blocks.iloc[tr], blocks.iloc[te])
        
    m1_cols = feature_sets["M1"]
    m2_cols = feature_sets["M2"]
    
    oof_rows = []
    best_params_rows = []
    fold_metric_rows = []
    delta_rows = []
    
    # Storage for predictions: (model, fset) -> array of length len(df)
    pred_store = {}
    
    for model_name in models:
        oof_m1 = np.zeros(len(df))
        oof_m2 = np.zeros(len(df))
        
        for f_idx, (tr, te) in enumerate(folds):
            tr_grps = blocks.iloc[tr]
            
            # 1. Fit M1
            pipe_m1, search_m1 = get_model_and_grid(model_name, seed=seed + f_idx, fast=fast)
            fitted_m1, bp_m1 = fit_with_inner_tuning(pipe_m1, search_m1, df.iloc[tr][m1_cols], y[tr], tr_grps, seed=seed)
            pred_te_m1 = fitted_m1.predict(df.iloc[te][m1_cols])
            oof_m1[te] = pred_te_m1
            
            # 2. Fit M2
            pipe_m2, search_m2 = get_model_and_grid(model_name, seed=seed + f_idx, fast=fast)
            fitted_m2, bp_m2 = fit_with_inner_tuning(pipe_m2, search_m2, df.iloc[tr][m2_cols], y[tr], tr_grps, seed=seed)
            pred_te_m2 = fitted_m2.predict(df.iloc[te][m2_cols])
            oof_m2[te] = pred_te_m2
            
            # Per-fold metrics
            r2_fold_m1 = calc_r2(y[te], pred_te_m1)
            r2_fold_m2 = calc_r2(y[te], pred_te_m2)
            rmse_m1 = calc_rmse(y[te], pred_te_m1)
            rmse_m2 = calc_rmse(y[te], pred_te_m2)
            rho_m1, p_m1 = calc_spearman(y[te], pred_te_m1)
            rho_m2, p_m2 = calc_spearman(y[te], pred_te_m2)
            
            fold_metric_rows.append({
                "target": target_name,
                "resolution": resolution,
                "fold": f_idx + 1,
                "model": model_name,
                "feature_set": "M1",
                "r2": r2_fold_m1,
                "rmse": rmse_m1,
                "spearman_rho": rho_m1,
                "spearman_p": p_m1
            })
            fold_metric_rows.append({
                "target": target_name,
                "resolution": resolution,
                "fold": f_idx + 1,
                "model": model_name,
                "feature_set": "M2",
                "r2": r2_fold_m2,
                "rmse": rmse_m2,
                "spearman_rho": rho_m2,
                "spearman_p": p_m2
            })
            
            if bp_m1:
                best_params_rows.append({
                    "target": target_name, "resolution": resolution, "fold": f_idx + 1,
                    "model": model_name, "feature_set": "M1", **bp_m1
                })
            if bp_m2:
                best_params_rows.append({
                    "target": target_name, "resolution": resolution, "fold": f_idx + 1,
                    "model": model_name, "feature_set": "M2", **bp_m2
                })
                
            for i_loc, idx_val in enumerate(te):
                oof_rows.append({
                    "target": target_name,
                    "resolution": resolution,
                    "cell_idx": int(idx_val),
                    "lon": float(df.iloc[idx_val]["lon"]),
                    "lat": float(df.iloc[idx_val]["lat"]),
                    "continent": str(df.iloc[idx_val]["continent"]),
                    "block": str(blocks.iloc[idx_val]),
                    "fold": f_idx + 1,
                    "model": model_name,
                    "y_true": float(y[idx_val]),
                    "y_pred_m1": float(pred_te_m1[i_loc]),
                    "y_pred_m2": float(pred_te_m2[i_loc])
                })
                
        pred_store[(model_name, "M1")] = oof_m1
        pred_store[(model_name, "M2")] = oof_m2
        
        pooled_r2_m1 = pooled_out_of_fold_r2(y, oof_m1)
        pooled_r2_m2 = pooled_out_of_fold_r2(y, oof_m2)
        pooled_delta = pooled_r2_m2 - pooled_r2_m1
        
        # Block-bootstrap CI for delta R2 (1000 resamples)
        pt_est, ci_low, ci_high = block_bootstrap_ci(
            y, oof_m1, oof_m2, blocks, metric="r2", n=1000, seed=seed
        )
        
        # Paired fold delta mean and std
        m_folds_m1 = [r["r2"] for r in fold_metric_rows if r["model"] == model_name and r["feature_set"] == "M1" and r["target"] == target_name]
        m_folds_m2 = [r["r2"] for r in fold_metric_rows if r["model"] == model_name and r["feature_set"] == "M2" and r["target"] == target_name]
        paired_deltas = np.array(m_folds_m2) - np.array(m_folds_m1)
        
        delta_rows.append({
            "target": target_name,
            "resolution": resolution,
            "model": model_name,
            "comparison": "M2_minus_M1",
            "m1_pooled_r2": round(pooled_r2_m1, 4),
            "m2_pooled_r2": round(pooled_r2_m2, 4),
            "pooled_delta_r2": round(pooled_delta, 4),
            "mean_fold_delta_r2": round(float(np.mean(paired_deltas)), 4),
            "std_fold_delta_r2": round(float(np.std(paired_deltas, ddof=1)), 4),
            "boot_ci_low_95": round(ci_low, 4),
            "boot_ci_high_95": round(ci_high, 4),
            "ci_includes_zero": bool(ci_low <= 0.0 <= ci_high)
        })
        
        print(f"[{model_name:13s}] M1 R2={pooled_r2_m1:.4f} | M2 R2={pooled_r2_m2:.4f} | Delta R2={pooled_delta:+.4f} | 95% Block CI=[{ci_low:+.4f}, {ci_high:+.4f}]")
        
    return pd.DataFrame(delta_rows), pd.DataFrame(fold_metric_rows), pd.DataFrame(oof_rows), pd.DataFrame(best_params_rows)


def run_loco_for_target(
    df: pd.DataFrame,
    target_name: str,
    resolution: str,
    feature_sets: Dict[str, List[str]],
    models: List[str] = ["ols", "ridge", "rf", "hgb"],
    seed: int = 42,
    fast: bool = False
) -> pd.DataFrame:
    """Runs Leave-One-Continent-Out (LOCO) CV for one target and resolution."""
    print(f"\n--- LOCO EVALUATION: Resolution={resolution}, Target={target_name} ---")
    
    y = df["y"].values
    blocks = block_id(df["lon"].values, df["lat"].values, size=20.0, offset=0.0)
    blocks = pd.Series(blocks, index=df.index)
    
    continents = sorted(df["continent"].unique())
    m1_cols = feature_sets["M1"]
    m2_cols = feature_sets["M2"]
    
    loco_rows = []
    
    for cont in continents:
        test_mask = (df["continent"] == cont).values
        te_idx = np.where(test_mask)[0]
        tr_idx = np.where(~test_mask)[0]
        
        assert set(tr_idx).isdisjoint(set(te_idx))
        tr_grps = blocks.iloc[tr_idx]
        
        y_te = y[te_idx]
        
        for model_name in models:
            # 1. Fit M1 on 5 continents with inner tuning on blocks
            pipe_m1, search_m1 = get_model_and_grid(model_name, seed=seed, fast=fast)
            fitted_m1, _ = fit_with_inner_tuning(pipe_m1, search_m1, df.iloc[tr_idx][m1_cols], y[tr_idx], tr_grps, seed=seed)
            pred_m1 = fitted_m1.predict(df.iloc[te_idx][m1_cols])
            
            # 2. Fit M2 on 5 continents with inner tuning on blocks
            pipe_m2, search_m2 = get_model_and_grid(model_name, seed=seed, fast=fast)
            fitted_m2, _ = fit_with_inner_tuning(pipe_m2, search_m2, df.iloc[tr_idx][m2_cols], y[tr_idx], tr_grps, seed=seed)
            pred_m2 = fitted_m2.predict(df.iloc[te_idx][m2_cols])
            
            r2_m1 = calc_r2(y_te, pred_m1)
            r2_m2 = calc_r2(y_te, pred_m2)
            rmse_m1 = calc_rmse(y_te, pred_m1)
            rmse_m2 = calc_rmse(y_te, pred_m2)
            rho_m1, p_m1 = calc_spearman(y_te, pred_m1)
            rho_m2, p_m2 = calc_spearman(y_te, pred_m2)
            delta_r2 = r2_m2 - r2_m1
            
            loco_rows.append({
                "target": target_name,
                "resolution": resolution,
                "continent": cont,
                "n_cells": len(te_idx),
                "model": model_name,
                "m1_r2": round(r2_m1, 4),
                "m2_r2": round(r2_m2, 4),
                "delta_r2": round(delta_r2, 4),
                "m1_rmse": round(rmse_m1, 4),
                "m2_rmse": round(rmse_m2, 4),
                "m1_spearman_rho": round(rho_m1, 4),
                "m2_spearman_rho": round(rho_m2, 4)
            })
            
            print(f"  LOCO [{cont:14s} (n={len(te_idx):4d}) | {model_name:6s}] M1 R2={r2_m1:+.4f} | M2 R2={r2_m2:+.4f} | Delta R2={delta_r2:+.4f}")
            
    return pd.DataFrame(loco_rows)


def run_full_iucn_pipeline(fast: bool = False):
    """Executes full IUCN pipeline across targets, resolutions, models."""
    resolutions = ["5deg", "2deg"]
    targets = ["iucn_log_richness", "iucn_small_range", "iucn_endemism"]
    models = ["ols", "ridge", "rf", "hgb"]
    
    all_deltas = []
    all_cv_metrics = []
    all_oof = []
    all_best_params = []
    all_loco = []
    
    for res in resolutions:
        res_dir = REPO_ROOT / "results" / "ml" / f"iucn_{res}"
        res_tbl_dir = res_dir / "tables"
        res_tbl_dir.mkdir(parents=True, exist_ok=True)
        
        res_deltas = []
        res_cv_metrics = []
        res_oof = []
        res_best_params = []
        res_loco = []
        
        for target in targets:
            df, fg, fs = load_dataset(resolution="base" if res == "5deg" else "2deg", target=target)
            
            # 1. 20° Spatial-Block CV with nested tuning and block bootstrap
            d_df, m_df, oof_df, bp_df = run_spatial_cv_for_target(
                df=df,
                target_name=target,
                resolution=res,
                feature_sets=fs,
                models=models,
                fast=fast
            )
            res_deltas.append(d_df)
            res_cv_metrics.append(m_df)
            res_oof.append(oof_df)
            if not bp_df.empty:
                res_best_params.append(bp_df)
                
            # 2. Leave-One-Continent-Out CV
            l_df = run_loco_for_target(
                df=df,
                target_name=target,
                resolution=res,
                feature_sets=fs,
                models=models,
                fast=fast
            )
            res_loco.append(l_df)
            
        # Concatenate per resolution
        res_delta_df = pd.concat(res_deltas, ignore_index=True)
        res_metrics_df = pd.concat(res_cv_metrics, ignore_index=True)
        res_oof_df = pd.concat(res_oof, ignore_index=True)
        res_loco_df = pd.concat(res_loco, ignore_index=True)
        res_bp_df = pd.concat(res_best_params, ignore_index=True) if res_best_params else pd.DataFrame()
        
        # Save per resolution
        res_delta_df.to_csv(res_tbl_dir / "delta_r2.csv", index=False)
        res_metrics_df.to_csv(res_tbl_dir / "core_cv_metrics.csv", index=False)
        res_oof_df.to_csv(res_tbl_dir / "oof_predictions.csv", index=False)
        res_loco_df.to_csv(res_tbl_dir / "loco_metrics.csv", index=False)
        if not res_bp_df.empty:
            res_bp_df.to_csv(res_tbl_dir / "best_params.csv", index=False)
            
        print(f"\n[OK] Saved resolution outputs to {res_tbl_dir}")
        
        all_deltas.append(res_delta_df)
        all_cv_metrics.append(res_metrics_df)
        all_oof.append(res_oof_df)
        all_loco.append(res_loco_df)
        if not res_bp_df.empty:
            all_best_params.append(res_bp_df)
            
    # Consolidated master tables in ml/outputs/
    final_delta_df = pd.concat(all_deltas, ignore_index=True)
    final_metrics_df = pd.concat(all_cv_metrics, ignore_index=True)
    final_loco_df = pd.concat(all_loco, ignore_index=True)
    
    final_delta_df.to_csv(REPO_ROOT / "results" / "ml" / "iucn_delta_r2.csv", index=False)
    final_delta_df.to_csv(REPO_ROOT / "results" / "ml" / "iucn_summary.csv", index=False)
    final_loco_df.to_csv(REPO_ROOT / "results" / "ml" / "iucn_loco.csv", index=False)
    
    print("\n" + "=" * 80)
    print("IUCN PIPELINE EXECUTION COMPLETED")
    print("=" * 80)
    print(f"Summary table saved to: {REPO_ROOT / 'ml' / 'outputs' / 'iucn_delta_r2.csv'}")
    print(f"LOCO table saved to:    {REPO_ROOT / 'ml' / 'outputs' / 'iucn_loco.csv'}")
    
    return final_delta_df, final_loco_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run IUCN ML Pipeline")
    parser.add_argument("--fast", action="store_true", help="Run fast test mode")
    args = parser.parse_args()
    
    run_full_iucn_pipeline(fast=args.fast)
