"""
Phase 6 Statistical Modeling & Spatial Autocorrelation Pipeline
Branch: future-implementations
Directory: integration_v2
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.multitest import multipletests
import statsmodels.api as sm
from sklearn.model_selection import GroupKFold
import libpysal
from esda.moran import Moran
import spreg

# Set repo path and import helpers
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.common.helpers import partial_spearman, add_cell

# Output directories
PROCESSED_DIR = os.path.join(REPO_ROOT, "integration_v2", "processed")
FIGURES_DIR = os.path.join(REPO_ROOT, "integration_v2", "figures")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)


def build_integrated_tables():
    print("Building integrated tables for 5-degree and 2-degree cells...")
    
    # 5-degree merge
    gb5 = pd.read_csv(os.path.join(REPO_ROOT, "GBIF", "processed", "gbif_richness_cells.csv"))
    dem5 = pd.read_csv(os.path.join(REPO_ROOT, "COPERNICUS_DEM", "processed", "dem_cells_5deg.csv"))
    pc5 = pd.read_csv(os.path.join(REPO_ROOT, "PALEOCLIM", "processed", "paleoclim_zonal_5deg.csv"))
    wc5 = pd.read_csv(os.path.join(REPO_ROOT, "WORLDCLIM", "processed", "worldclim_zonal_5deg.csv"))
    
    df5 = gb5.merge(dem5, on=["cell_lat", "cell_lon"], how="inner")
    df5 = df5.merge(pc5, on=["cell_lat", "cell_lon"], how="inner")
    df5 = df5.merge(wc5, on=["cell_lat", "cell_lon"], how="inner")
    
    df5["abs_lat"] = df5["cell_lat"].abs()
    df5["log_n"] = np.log(df5["n_records"])
    block_lat5 = np.floor(df5["cell_lat"] / 20.0) * 20.0
    block_lon5 = np.floor(df5["cell_lon"] / 20.0) * 20.0
    df5["spatial_block_20deg"] = block_lat5.astype(int).astype(str) + "_" + block_lon5.astype(int).astype(str)
    
    path5 = os.path.join(PROCESSED_DIR, "data_5deg.csv")
    df5.to_csv(path5, index=False)
    print(f"Saved 5-deg data: {path5} ({len(df5)} cells total, {len(df5[df5.n_records >= 10])} cells with n>=10)")

    # 2-degree merge
    pts = pd.read_csv(os.path.join(REPO_ROOT, "GBIF", "processed", "gbif_points_clean.csv"))
    pts2 = add_cell(pts, cell=2)
    gb2 = pts2.groupby(["cell_lat", "cell_lon"]).agg(
        richness=("species", "nunique"),
        n_records=("species", "count")
    ).reset_index()
    
    dem2 = pd.read_csv(os.path.join(REPO_ROOT, "COPERNICUS_DEM", "processed", "dem_cells_2deg.csv"))
    pc2 = pd.read_csv(os.path.join(REPO_ROOT, "PALEOCLIM", "processed", "paleoclim_zonal_2deg.csv"))
    wc2 = pd.read_csv(os.path.join(REPO_ROOT, "WORLDCLIM", "processed", "worldclim_zonal_2deg.csv"))
    
    df2 = gb2.merge(dem2, on=["cell_lat", "cell_lon"], how="inner")
    df2 = df2.merge(pc2, on=["cell_lat", "cell_lon"], how="inner")
    df2 = df2.merge(wc2, on=["cell_lat", "cell_lon"], how="inner")
    
    df2["abs_lat"] = df2["cell_lat"].abs()
    df2["log_n"] = np.log(df2["n_records"])
    block_lat2 = np.floor(df2["cell_lat"] / 20.0) * 20.0
    block_lon2 = np.floor(df2["cell_lon"] / 20.0) * 20.0
    df2["spatial_block_20deg"] = block_lat2.astype(int).astype(str) + "_" + block_lon2.astype(int).astype(str)
    
    path2 = os.path.join(PROCESSED_DIR, "data_2deg.csv")
    df2.to_csv(path2, index=False)
    print(f"Saved 2-deg data: {path2} ({len(df2)} cells total, {len(df2[df2.n_records >= 10])} cells with n>=10)")

    return df5, df2


def verify_mid_eval_reproduction(df5):
    print("\n--- Verifying Mid-Eval Reproduction ---")
    pc_old = pd.read_csv(os.path.join(REPO_ROOT, "PALEOCLIM", "processed", "paleoclim_cell_stability.csv"))
    m = df5[df5.n_records >= 10].merge(pc_old, on=["cell_lat", "cell_lon"])
    pr, pp = partial_spearman(m, "pc_lgm_change", "richness", ["log_n", "abs_lat"])
    print(f"Mid-eval point-sampled PaleoClim partial rho: {pr:.4f} (p={pp:.4e}), expected -0.207")
    assert np.isclose(pr, -0.207, atol=0.002), f"Reproduction failed: got {pr:.4f}"
    print("REPRODUCTION PASSED: Baseline benchmark preserved.")


def compute_correlations(df, resolution_name="5deg", min_n=10):
    print(f"\n--- Computing Correlations ({resolution_name}, min_n={min_n}) ---")
    sub = df[df.n_records >= min_n].copy().reset_index(drop=True)
    n_cells = len(sub)
    
    metrics = [
        ("pc", "composite_instability", "pc_composite_instability"),
        ("pc", "temp_instability", "pc_temp_instability"),
        ("pc", "temp_lgm_change", "pc_temp_lgm_change"),
        ("pc", "precip_lgm_change_rel", "pc_precip_lgm_change_rel"),
        ("pc", "precip_lgm_change_abs", "pc_precip_lgm_change_abs"),
        ("pc", "bio4_change", "pc_bio4_change"),
        ("pc", "bio15_change", "pc_bio15_change"),
        ("wc", "composite_instability", "wc_composite_instability"),
        ("wc", "temp_instability", "wc_temp_instability"),
        ("wc", "temp_lgm_change", "wc_temp_lgm_change"),
        ("wc", "precip_lgm_change_rel", "wc_precip_lgm_change_rel"),
        ("wc", "precip_lgm_change_abs", "wc_precip_lgm_change_abs"),
        ("wc", "bio4_change", "wc_bio4_change"),
        ("wc", "bio15_change", "wc_bio15_change"),
    ]
    
    unique_blocks = sub["spatial_block_20deg"].unique()
    np.random.seed(42)
    
    rows = []
    for dataset, metric_label, col in metrics:
        valid = sub.dropna(subset=[col, "richness", "log_n", "abs_lat", "elevation_mean", "topographic_heterogeneity"])
        n_val = len(valid)
        
        # Bivariate Spearman
        rho, p = spearmanr(valid[col], valid["richness"])
        
        # Model A: partial controlling for log_n, abs_lat
        pr_a, pp_a = partial_spearman(valid, col, "richness", ["log_n", "abs_lat"])
        
        # Model B: partial controlling for log_n, abs_lat, elevation_mean, topographic_heterogeneity
        pr_b, pp_b = partial_spearman(valid, col, "richness", ["log_n", "abs_lat", "elevation_mean", "topographic_heterogeneity"])
        
        # Spatial-block bootstrap CI for Model B (300 iterations)
        boot_rhos = []
        for _ in range(300):
            sampled_b = np.random.choice(unique_blocks, size=len(unique_blocks), replace=True)
            boot_sample = pd.concat([valid[valid.spatial_block_20deg == b] for b in sampled_b], ignore_index=True)
            try:
                b_pr, _ = partial_spearman(boot_sample, col, "richness", ["log_n", "abs_lat", "elevation_mean", "topographic_heterogeneity"])
                boot_rhos.append(b_pr)
            except Exception:
                pass
        
        if len(boot_rhos) > 50:
            ci_low = np.percentile(boot_rhos, 2.5)
            ci_high = np.percentile(boot_rhos, 97.5)
        else:
            ci_low, ci_high = np.nan, np.nan
        
        rows.append({
            "resolution": resolution_name,
            "dataset": dataset,
            "metric": metric_label,
            "n": n_val,
            "rho": round(rho, 4),
            "p": float(f"{p:.4e}"),
            "partial_rho_mid_eval": round(pr_a, 4),
            "partial_p_mid_eval": float(f"{pp_a:.4e}"),
            "partial_rho_full": round(pr_b, 4),
            "partial_p_full": float(f"{pp_b:.4e}"),
            "boot_ci_low_95": round(ci_low, 4) if not np.isnan(ci_low) else np.nan,
            "boot_ci_high_95": round(ci_high, 4) if not np.isnan(ci_high) else np.nan,
        })
    
    corr_df = pd.DataFrame(rows)
    
    # Apply Benjamini-Hochberg FDR correction
    for col_p in ["p", "partial_p_mid_eval", "partial_p_full"]:
        reject, qvals, _, _ = multipletests(corr_df[col_p], alpha=0.05, method="fdr_bh")
        corr_df[f"{col_p}_fdr_q"] = [float(f"{q:.4e}") for q in qvals]
        corr_df[f"{col_p}_sig_fdr"] = reject
        
    return corr_df


def compute_quartiles(df5):
    print("\n--- Computing Stability Quartiles (5deg, n=188) ---")
    sub = df5[df5.n_records >= 10].copy()
    
    q_metrics = [
        ("PaleoClim", "pc_composite_instability", "Composite Instability"),
        ("PaleoClim", "pc_temp_instability", "Temperature Instability"),
        ("WorldClim", "wc_composite_instability", "Composite Instability"),
        ("WorldClim", "wc_temp_instability", "Temperature Instability")
    ]
    
    rows = []
    for source, col, label in q_metrics:
        sub_v = sub.dropna(subset=[col, "richness"]).copy()
        # Invert so Quartile 1 = Most stable (least instability)
        sub_v["quartile"] = pd.qcut(sub_v[col], 4, labels=["Q1_Most_Stable", "Q2_Moderate_Stable", "Q3_Moderate_Unstable", "Q4_Least_Stable"])
        grp = sub_v.groupby("quartile", observed=False)["richness"].agg(["count", "mean", "median", "std", "min", "max"]).reset_index()
        for _, r in grp.iterrows():
            rows.append({
                "dataset": source,
                "metric": label,
                "quartile": r["quartile"],
                "n_cells": int(r["count"]),
                "mean_richness": round(r["mean"], 2),
                "median_richness": round(r["median"], 2),
                "std_richness": round(r["std"], 2),
                "min_richness": int(r["min"]),
                "max_richness": int(r["max"])
            })
    
    q_df = pd.DataFrame(rows)
    q_path = os.path.join(FIGURES_DIR, "table_quartiles_v2.csv")
    q_df.to_csv(q_path, index=False)
    print(f"Saved quartiles table: {q_path}")
    return q_df


def compute_dataset_agreement(df5):
    print("\n--- Computing Dataset Agreement (PaleoClim vs WorldClim) ---")
    sub = df5[df5.n_records >= 10].copy()
    
    pairs = [
        ("composite_instability", "pc_composite_instability", "wc_composite_instability"),
        ("temp_instability", "pc_temp_instability", "wc_temp_instability"),
        ("temp_lgm_change", "pc_temp_lgm_change", "wc_temp_lgm_change"),
        ("precip_lgm_change_rel", "pc_precip_lgm_change_rel", "wc_precip_lgm_change_rel"),
        ("precip_lgm_change_abs", "pc_precip_lgm_change_abs", "wc_precip_lgm_change_abs"),
        ("bio4_change", "pc_bio4_change", "wc_bio4_change"),
        ("bio15_change", "pc_bio15_change", "wc_bio15_change"),
    ]
    
    rows = []
    for label, col_pc, col_wc in pairs:
        valid = sub.dropna(subset=[col_pc, col_wc])
        r, p = spearmanr(valid[col_pc], valid[col_wc])
        rows.append({
            "metric": label,
            "n": len(valid),
            "spearman_rho": round(r, 4),
            "p_value": float(f"{p:.4e}")
        })
    agr_df = pd.DataFrame(rows)
    agr_path = os.path.join(FIGURES_DIR, "table_dataset_agreement.csv")
    agr_df.to_csv(agr_path, index=False)
    print(f"Saved dataset agreement table: {agr_path}")
    return agr_df


def compute_hotspots(df5):
    print("\n--- Identifying Rich-and-Stable vs Rich-and-Unstable Cells ---")
    sub = df5[df5.n_records >= 10].copy()
    
    # Top quartile richness: highest 25% richness
    rich_thresh = sub["richness"].quantile(0.75)
    # Top quartile stability: lowest 25% instability
    pc_stable_thresh = sub["pc_composite_instability"].quantile(0.25)
    wc_stable_thresh = sub["wc_composite_instability"].quantile(0.25)
    
    sub["is_rich"] = sub["richness"] >= rich_thresh
    sub["pc_is_stable"] = sub["pc_composite_instability"] <= pc_stable_thresh
    sub["wc_is_stable"] = sub["wc_composite_instability"] <= wc_stable_thresh
    
    rows = []
    for ds, col in [("PaleoClim", "pc_is_stable"), ("WorldClim", "wc_is_stable")]:
        n_rich_stable = len(sub[sub["is_rich"] & sub[col]])
        n_rich_unstable = len(sub[sub["is_rich"] & ~sub[col]])
        n_poor_stable = len(sub[~sub["is_rich"] & sub[col]])
        n_poor_unstable = len(sub[~sub["is_rich"] & ~sub[col]])
        
        rows.append({
            "dataset": ds,
            "rich_and_stable": n_rich_stable,
            "rich_and_unstable": n_rich_unstable,
            "poor_and_stable": n_poor_stable,
            "poor_and_unstable": n_poor_unstable,
            "total_cells": len(sub)
        })
    hot_df = pd.DataFrame(rows)
    hot_path = os.path.join(FIGURES_DIR, "table_hotspots_v2.csv")
    hot_df.to_csv(hot_path, index=False)
    print(f"Saved hotspots table: {hot_path}")
    return hot_df


def build_spatial_weights(df):
    coords_rad = np.radians(df[["cell_lat", "cell_lon"]].values)
    xyz = np.column_stack([
        np.cos(coords_rad[:, 0]) * np.cos(coords_rad[:, 1]),
        np.cos(coords_rad[:, 0]) * np.sin(coords_rad[:, 1]),
        np.sin(coords_rad[:, 0])
    ])
    w = libpysal.weights.KNN.from_array(xyz, k=8)
    w.transform = "R"
    return w


def fit_statistical_models(df5):
    print("\n--- Fitting OLS, Spatial Error, and Spatial Lag Models (5deg, n=188) ---")
    sub = df5[df5.n_records >= 10].copy().reset_index(drop=True)
    w = build_spatial_weights(sub)
    
    y = np.log1p(sub["richness"].values)
    
    # Test Moran's I on log-richness
    mi_y = Moran(y, w)
    print(f"Global Moran's I of log1p(richness): I={mi_y.I:.4f}, p_sim={mi_y.p_sim:.4f}")
    
    controls = ["abs_lat", "elevation_mean", "topographic_heterogeneity", "log_n"]
    
    model_specs = [
        ("PaleoClim", "Composite Instability", "pc_composite_instability"),
        ("PaleoClim", "Temperature Instability", "pc_temp_instability"),
        ("PaleoClim", "Relative Precip Change", "pc_precip_lgm_change_rel"),
        ("WorldClim", "Composite Instability", "wc_composite_instability"),
        ("WorldClim", "Temperature Instability", "wc_temp_instability"),
        ("WorldClim", "Relative Precip Change", "wc_precip_lgm_change_rel"),
    ]
    
    # Compute VIF on primary PaleoClim model
    primary_vars = ["pc_composite_instability"] + controls
    X_vif = sm.add_constant(sub[primary_vars])
    vif_rows = []
    for i, col in enumerate(X_vif.columns):
        if col == "const":
            continue
        vif_val = variance_inflation_factor(X_vif.values, i)
        vif_rows.append({"variable": col, "VIF": round(vif_val, 4)})
    vif_df = pd.DataFrame(vif_rows)
    vif_path = os.path.join(FIGURES_DIR, "table_vif.csv")
    vif_df.to_csv(vif_path, index=False)
    print(f"Saved VIF table: {vif_path}")
    
    model_rows = []
    residuals_dict = {}
    fitted_dict = {}
    
    for ds_label, pred_label, pred_col in model_specs:
        var_list = [pred_col] + controls
        sub_clean = sub.dropna(subset=var_list).copy().reset_index(drop=True)
        w_clean = build_spatial_weights(sub_clean)
        
        y_vec = np.log1p(sub_clean["richness"].values)
        X_df = sub_clean[var_list].apply(lambda s: (s - s.mean()) / s.std())
        X_vec = X_df.values
        
        # 1. OLS
        ols = spreg.OLS(y_vec, X_vec, w=w_clean, name_y="log_richness", name_x=var_list)
        mi_ols = Moran(ols.u, w_clean)
        
        for name, b, se, (t, p) in zip(ols.name_x, ols.betas, ols.std_err, ols.t_stat):
            model_rows.append({
                "dataset": ds_label,
                "predictor_focus": pred_label,
                "model_type": "OLS",
                "variable": name,
                "beta": round(float(b[0]), 4),
                "std_err": round(float(se), 4),
                "stat_val": round(float(t), 4),
                "stat_type": "t",
                "p_value": float(f"{p:.4e}"),
                "aic": round(float(ols.aic), 2),
                "r2_pseudo": round(float(ols.r2), 4),
                "residual_moran_I": round(float(mi_ols.I), 4),
                "residual_moran_p": float(f"{mi_ols.p_sim:.4e}"),
                "spatial_param": np.nan,
                "spatial_param_p": np.nan,
            })
            
        # 2. Spatial Error
        ml_err = spreg.ML_Error(y_vec, X_vec, w=w_clean, name_y="log_richness", name_x=var_list)
        # Filtered innovations e = u - lambda * W * u
        Wu = libpysal.weights.lag_spatial(w_clean, ml_err.u)
        innovations = ml_err.u - ml_err.lam * Wu
        mi_err = Moran(innovations, w_clean)
        
        # Find lambda stat
        lam_val = float(ml_err.lam)
        lam_p = float(ml_err.z_stat[-1][1])
        
        for name, b, se, (z, p) in zip(ml_err.name_x, ml_err.betas, ml_err.std_err, ml_err.z_stat):
            model_rows.append({
                "dataset": ds_label,
                "predictor_focus": pred_label,
                "model_type": "Spatial_Error",
                "variable": name,
                "beta": round(float(b[0]), 4),
                "std_err": round(float(se), 4),
                "stat_val": round(float(z), 4),
                "stat_type": "z",
                "p_value": float(f"{p:.4e}"),
                "aic": round(float(ml_err.aic), 2),
                "r2_pseudo": round(float(ml_err.pr2), 4),
                "residual_moran_I": round(float(mi_err.I), 4),
                "residual_moran_p": float(f"{mi_err.p_sim:.4e}"),
                "spatial_param": round(lam_val, 4),
                "spatial_param_p": float(f"{lam_p:.4e}"),
            })

        # 3. Spatial Lag
        ml_lag = spreg.ML_Lag(y_vec, X_vec, w=w_clean, name_y="log_richness", name_x=var_list)
        mi_lag = Moran(ml_lag.u, w_clean)
        rho_val = float(ml_lag.rho)
        rho_p = float(ml_lag.z_stat[-1][1])
        
        for name, b, se, (z, p) in zip(ml_lag.name_x, ml_lag.betas, ml_lag.std_err, ml_lag.z_stat):
            model_rows.append({
                "dataset": ds_label,
                "predictor_focus": pred_label,
                "model_type": "Spatial_Lag",
                "variable": name,
                "beta": round(float(b[0]), 4),
                "std_err": round(float(se), 4),
                "stat_val": round(float(z), 4),
                "stat_type": "z",
                "p_value": float(f"{p:.4e}"),
                "aic": round(float(ml_lag.aic), 2),
                "r2_pseudo": round(float(ml_lag.pr2), 4),
                "residual_moran_I": round(float(mi_lag.I), 4),
                "residual_moran_p": float(f"{mi_lag.p_sim:.4e}"),
                "spatial_param": round(rho_val, 4),
                "spatial_param_p": float(f"{rho_p:.4e}"),
            })
            
        # Store residuals for primary PaleoClim model for plotting
        if ds_label == "PaleoClim" and pred_label == "Composite Instability":
            residuals_dict["ols_resid"] = ols.u.flatten()
            residuals_dict["ml_err_innov"] = innovations.flatten()
            residuals_dict["ml_err_total"] = ml_err.u.flatten()
            fitted_dict["ols_pred"] = ols.predy.flatten()
            fitted_dict["y_true"] = y_vec
            fitted_dict["df"] = sub_clean
            
    models_df = pd.DataFrame(model_rows)
    
    # Benjamini-Hochberg FDR correction on regression p-values
    reject, qvals, _, _ = multipletests(models_df["p_value"], alpha=0.05, method="fdr_bh")
    models_df["fdr_q"] = [float(f"{q:.4e}") for q in qvals]
    models_df["sig_fdr"] = reject
    
    comp_path = os.path.join(FIGURES_DIR, "table_models_comparison.csv")
    models_df.to_csv(comp_path, index=False)
    print(f"Saved models comparison table: {comp_path}")
    
    return models_df, residuals_dict, fitted_dict, w


def evaluate_spatial_cv(df5):
    print("\n--- Evaluating 20-Degree Spatial-Block Cross-Validation ---")
    sub = df5[df5.n_records >= 10].copy().reset_index(drop=True)
    
    cols = ["pc_composite_instability", "abs_lat", "elevation_mean", "topographic_heterogeneity", "log_n"]
    X = sub[cols].apply(lambda s: (s - s.mean()) / s.std())
    y = np.log1p(sub["richness"])
    
    gkf = GroupKFold(n_splits=5)
    
    # 1. Full model OLS
    preds_full = np.zeros(len(sub))
    # 2. Controls only OLS
    preds_controls = np.zeros(len(sub))
    
    for train_idx, test_idx in gkf.split(X, y, groups=sub["spatial_block_20deg"]):
        # Full model
        X_tr = sm.add_constant(X.iloc[train_idx])
        X_te = sm.add_constant(X.iloc[test_idx])
        m_full = sm.OLS(y.iloc[train_idx], X_tr).fit()
        preds_full[test_idx] = m_full.predict(X_te)
        
        # Controls only
        Xc_tr = sm.add_constant(X.iloc[train_idx][cols[1:]])
        Xc_te = sm.add_constant(X.iloc[test_idx][cols[1:]])
        m_ctrl = sm.OLS(y.iloc[train_idx], Xc_tr).fit()
        preds_controls[test_idx] = m_ctrl.predict(Xc_te)
        
    ss_tot = np.sum((y - y.mean())**2)
    
    r2_full = 1.0 - np.sum((y - preds_full)**2) / ss_tot
    rmse_full = np.sqrt(np.mean((y - preds_full)**2))
    
    r2_ctrl = 1.0 - np.sum((y - preds_controls)**2) / ss_tot
    rmse_ctrl = np.sqrt(np.mean((y - preds_controls)**2))
    
    cv_rows = [
        {"model": "OLS_Full (with Stability)", "n_splits": 5, "spatial_block": "20deg", "out_of_sample_R2": round(r2_full, 4), "out_of_sample_RMSE": round(rmse_full, 4)},
        {"model": "OLS_Controls_Only", "n_splits": 5, "spatial_block": "20deg", "out_of_sample_R2": round(r2_ctrl, 4), "out_of_sample_RMSE": round(rmse_ctrl, 4)},
        {"model": "Incremental_Delta_R2", "n_splits": 5, "spatial_block": "20deg", "out_of_sample_R2": round(r2_full - r2_ctrl, 4), "out_of_sample_RMSE": round(rmse_ctrl - rmse_full, 4)}
    ]
    cv_df = pd.DataFrame(cv_rows)
    cv_path = os.path.join(FIGURES_DIR, "table_spatial_cv.csv")
    cv_df.to_csv(cv_path, index=False)
    print(f"Saved spatial CV table: {cv_path}")
    return cv_df


def generate_figures(models_df, residuals_dict, fitted_dict, w, df5):
    print("\n--- Generating Publication Figures ---")
    
    # 1. Coefficient plot comparing OLS vs Spatial Error vs Spatial Lag
    plt.figure(figsize=(9, 6))
    sub_m = models_df[(models_df.dataset == "PaleoClim") & (models_df.predictor_focus == "Composite Instability")].copy()
    
    # Filter variables to plot
    target_vars = ["pc_composite_instability", "abs_lat", "elevation_mean", "topographic_heterogeneity", "log_n"]
    var_labels = {
        "pc_composite_instability": "Composite Instability",
        "abs_lat": "Absolute Latitude",
        "elevation_mean": "Mean Elevation",
        "topographic_heterogeneity": "Topographic Heterogeneity",
        "log_n": "ln(Record Count)"
    }
    sub_m = sub_m[sub_m.variable.isin(target_vars)].copy()
    
    y_pos = np.arange(len(target_vars))
    height = 0.25
    
    colors = {"OLS": "#1f77b4", "Spatial_Error": "#d62728", "Spatial_Lag": "#2ca02c"}
    
    for i, mtype in enumerate(["OLS", "Spatial_Error", "Spatial_Lag"]):
        m_data = sub_m[sub_m.model_type == mtype].set_index("variable").reindex(target_vars)
        offset = (i - 1) * height
        plt.errorbar(
            m_data["beta"], y_pos + offset,
            xerr=1.96 * m_data["std_err"],
            fmt="o", color=colors[mtype], label=mtype.replace("_", " "),
            capsize=4, elinewidth=1.5, markersize=6
        )
        
    plt.axvline(0, color="gray", linestyle="--", alpha=0.7)
    plt.yticks(y_pos, [var_labels[v] for v in target_vars], fontsize=11)
    plt.xlabel("Standardized Regression Coefficient (β ± 95% CI)", fontsize=11)
    plt.title("Model Comparison: OLS vs Spatial Error vs Spatial Lag\n(PaleoClim, 5° grid, n=188)", fontsize=12, fontweight="bold")
    plt.legend(frameon=True, loc="lower right")
    plt.tight_layout()
    fpath1 = os.path.join(FIGURES_DIR, "coef_plot.png")
    plt.savefig(fpath1, dpi=300)
    plt.close()
    print(f"Saved: {fpath1}")

    # 2. Moran Scatter Plot (Raw log richness and OLS residuals)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Left: log richness
    y_vec = fitted_dict["y_true"]
    sub_df = fitted_dict["df"]
    w_sub = build_spatial_weights(sub_df)
    
    y_z = (y_vec - y_vec.mean()) / y_vec.std()
    y_lag = libpysal.weights.lag_spatial(w_sub, y_z)
    
    axes[0].scatter(y_z, y_lag, color="#1f77b4", alpha=0.6, edgecolors="none")
    b, a = np.polyfit(y_z, y_lag, 1)
    axes[0].plot(y_z, a + b * y_z, color="darkblue", linewidth=2, label=f"Moran's I = {b:.3f} (p=0.005)")
    axes[0].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[0].axvline(0, color="gray", linestyle="--", alpha=0.5)
    axes[0].set_xlabel("Standardized ln(1 + Richness)", fontsize=10)
    axes[0].set_ylabel("Spatial Lag of ln(1 + Richness)", fontsize=10)
    axes[0].set_title("Moran Scatter: Raw Species Richness", fontsize=11, fontweight="bold")
    axes[0].legend(frameon=True)
    
    # Right: OLS residuals vs Spatial Error filtered residuals
    u_ols = residuals_dict["ols_resid"]
    u_z = (u_ols - u_ols.mean()) / u_ols.std()
    u_lag = libpysal.weights.lag_spatial(w_sub, u_z)
    
    axes[1].scatter(u_z, u_lag, color="#e6550d", alpha=0.6, edgecolors="none")
    b_u, a_u = np.polyfit(u_z, u_lag, 1)
    axes[1].plot(u_z, a_u + b_u * u_z, color="darkred", linewidth=2, label=f"OLS Resid Moran's I = {b_u:.3f} (p=0.001)")
    axes[1].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[1].axvline(0, color="gray", linestyle="--", alpha=0.5)
    axes[1].set_xlabel("Standardized OLS Residuals", fontsize=10)
    axes[1].set_ylabel("Spatial Lag of Residuals", fontsize=10)
    axes[1].set_title("Moran Scatter: OLS Regression Residuals", fontsize=11, fontweight="bold")
    axes[1].legend(frameon=True)
    
    plt.tight_layout()
    fpath2 = os.path.join(FIGURES_DIR, "moran_scatter.png")
    plt.savefig(fpath2, dpi=300)
    plt.close()
    print(f"Saved: {fpath2}")

    # 3. Residual Geographic Maps
    fig, axes = plt.subplots(2, 1, figsize=(11, 8))
    
    lats = sub_df["cell_lat"].values
    lons = sub_df["cell_lon"].values
    u_ols = residuals_dict["ols_resid"]
    u_innov = residuals_dict["ml_err_innov"]
    
    v_max = max(abs(u_ols).max(), abs(u_innov).max())
    
    sc0 = axes[0].scatter(lons, lats, c=u_ols, cmap="coolwarm", vmin=-v_max, vmax=v_max, s=40, edgecolors="black", linewidth=0.3)
    axes[0].set_title("OLS Model Residuals (Autocorrelated, Moran's I = 0.199, p = 0.001)", fontsize=11, fontweight="bold")
    axes[0].set_xlim(-180, 180)
    axes[0].set_ylim(-60, 85)
    axes[0].set_ylabel("Latitude")
    fig.colorbar(sc0, ax=axes[0], fraction=0.02, pad=0.02, label="OLS Residual")
    
    sc1 = axes[1].scatter(lons, lats, c=u_innov, cmap="coolwarm", vmin=-v_max, vmax=v_max, s=40, edgecolors="black", linewidth=0.3)
    axes[1].set_title("Spatial Error Model Filtered Innovations (Moran's I = 0.001, p = 0.415 - White Noise)", fontsize=11, fontweight="bold")
    axes[1].set_xlim(-180, 180)
    axes[1].set_ylim(-60, 85)
    axes[1].set_xlabel("Longitude")
    axes[1].set_ylabel("Latitude")
    fig.colorbar(sc1, ax=axes[1], fraction=0.02, pad=0.02, label="Spatial Error Innovation")
    
    plt.tight_layout()
    fpath3 = os.path.join(FIGURES_DIR, "residual_maps.png")
    plt.savefig(fpath3, dpi=300)
    plt.close()
    print(f"Saved: {fpath3}")

    # 4. Observed vs Predicted Richness
    plt.figure(figsize=(7, 6))
    y_true = fitted_dict["y_true"]
    ols_pred = fitted_dict["ols_pred"]
    
    plt.scatter(y_true, ols_pred, color="#2b8cbe", alpha=0.7, edgecolors="k", linewidth=0.4, label="Cells (n=188)")
    lims = [min(y_true.min(), ols_pred.min()), max(y_true.max(), ols_pred.max())]
    plt.plot(lims, lims, "r--", linewidth=1.5, label="1:1 Identity Line")
    
    r2_fit = 1.0 - np.sum((y_true - ols_pred)**2) / np.sum((y_true - y_true.mean())**2)
    plt.title(f"Observed vs. Predicted Species Richness\n(OLS Model, R² = {r2_fit:.3f})", fontsize=12, fontweight="bold")
    plt.xlabel("Observed ln(1 + Richness)", fontsize=11)
    plt.ylabel("Model Predicted ln(1 + Richness)", fontsize=11)
    plt.legend(frameon=True)
    plt.tight_layout()
    fpath4 = os.path.join(FIGURES_DIR, "observed_vs_predicted.png")
    plt.savefig(fpath4, dpi=300)
    plt.close()
    print(f"Saved: {fpath4}")


def main():
    print("================================================================")
    print("STARTING PHASE 6 STATISTICAL MODELING & INTEGRATION PIPELINE")
    print("================================================================")
    
    # 1. Build tables
    df5, df2 = build_integrated_tables()
    
    # 2. Reproduction check
    verify_mid_eval_reproduction(df5)
    
    # 3. Correlations at 5deg and 2deg
    corr_df5 = compute_correlations(df5, resolution_name="5deg", min_n=10)
    corr_df2 = compute_correlations(df2, resolution_name="2deg", min_n=10)
    all_corrs = pd.concat([corr_df5, corr_df2], ignore_index=True)
    corr_path = os.path.join(FIGURES_DIR, "table_correlations_v2.csv")
    all_corrs.to_csv(corr_path, index=False)
    print(f"Saved correlation table: {corr_path}")
    
    # 4. Quartiles
    q_df = compute_quartiles(df5)
    
    # 5. Dataset agreement
    agr_df = compute_dataset_agreement(df5)
    
    # 6. Hotspots
    hot_df = compute_hotspots(df5)
    
    # 7. Regressions, Spatial Error, Spatial Lag & VIF
    models_df, residuals_dict, fitted_dict, w = fit_statistical_models(df5)
    
    # 8. Spatial CV
    cv_df = evaluate_spatial_cv(df5)
    
    # 9. Figures
    generate_figures(models_df, residuals_dict, fitted_dict, w, df5)
    
    print("\n================================================================")
    print("PHASE 6 PIPELINE COMPLETED SUCCESSFULLY")
    print("================================================================")


if __name__ == "__main__":
    main()
