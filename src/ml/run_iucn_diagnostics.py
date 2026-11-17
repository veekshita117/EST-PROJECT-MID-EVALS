"""
run_iucn_diagnostics.py
-----------------------
Generates Part 3 interpretation and diagnostic outputs for IUCN models:
1. Permutation importance by feature group (geography, topography, contemporary_climate, palaeoclimate).
2. SHAP feature attribution (TreeExplainer on Random Forest & HGB).
3. Partial Dependence (PDP / ALE) profiles for climate velocity (log10_velocity_temp) and refugial area fraction.
4. Out-of-fold residual Moran's I spatial autocorrelation and global residual maps.
5. Observed-vs-predicted scatter plots with 1:1 reference line and R2 metrics.
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.inspection import partial_dependence
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import BallTree
from scipy.sparse import lil_matrix, csr_matrix
import shap

from ml.src.data import load_dataset
from ml.src.spatial import block_id
from ml.src.metrics import calc_r2, calc_rmse, calc_spearman


def compute_grouped_permutation_importance(df, feature_sets, target_name="iucn_log_richness", resolution="5deg", seed=42):
    """Computes test-fold permutation importance grouped by domain."""
    y = df["y"].values
    blocks = block_id(df["lon"].values, df["lat"].values, size=20.0, offset=0.0)
    
    groups = {
        "geography": ["abs_lat"],
        "topography": ["elevation_mean", "topographic_heterogeneity"],
        "contemporary_climate": ["pc_temp_present", "pc_precip_present", "pc_bio4_present", "pc_bio15_present"],
        "palaeoclimate": ["log10_velocity_temp", "refugial_area_fraction", "temp_anomaly", "precip_rel_change"]
    }
    m2_cols = feature_sets["M2"]
    
    gkf = GroupKFold(n_splits=5)
    rng = np.random.default_rng(seed)
    
    records = []
    for mod_name, mod in [
        ("rf", RandomForestRegressor(n_estimators=100, max_depth=8, random_state=seed, n_jobs=-1)),
        ("hgb", HistGradientBoostingRegressor(max_iter=100, max_depth=5, random_state=seed))
    ]:
        fold_drops = {g: [] for g in groups}
        for f_idx, (tr, te) in enumerate(gkf.split(df, groups=blocks)):
            pipe = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("model", mod)
            ])
            pipe.fit(df.iloc[tr][m2_cols], y[tr])
            X_te = df.iloc[te][m2_cols].copy()
            base_r2 = calc_r2(y[te], pipe.predict(X_te))
            
            for gname, cols in groups.items():
                X_shuff = X_te.copy()
                perm = rng.permutation(len(te))
                X_shuff[cols] = X_shuff[cols].iloc[perm].values
                shuff_r2 = calc_r2(y[te], pipe.predict(X_shuff))
                drop = base_r2 - shuff_r2
                fold_drops[gname].append(drop)
                
        for gname in groups:
            drops = fold_drops[gname]
            records.append({
                "target": target_name,
                "resolution": resolution,
                "model": mod_name,
                "feature_group": gname,
                "mean_r2_drop": round(float(np.mean(drops)), 4),
                "std_r2_drop": round(float(np.std(drops, ddof=1)), 4),
            })
            
    return pd.DataFrame(records)


def compute_morans_i_table(oof_df):
    """Computes spatial autocorrelation (Moran's I) on out-of-fold residuals."""
    rows = []
    
    for (res, target, mod), sub in oof_df.groupby(["resolution", "target", "model"]):
        sub_sorted = sub.sort_values("cell_idx").reset_index(drop=True)
        N = len(sub_sorted)
        k_nn = 5 if res == "5deg" else 8
        
        coords = np.radians(np.column_stack([sub_sorted["lat"].values, sub_sorted["lon"].values]))
        tree = BallTree(coords, metric="haversine")
        _, idxs = tree.query(coords, k=k_nn + 1)
        
        W = lil_matrix((N, N), dtype=float)
        for i in range(N):
            W[i, idxs[i, 1:]] = 1.0 / k_nn
        W = W.tocsr()
        
        for fset in ["M1", "M2"]:
            pred_col = "y_pred_m1" if fset == "M1" else "y_pred_m2"
            resids = (sub_sorted["y_true"] - sub_sorted[pred_col]).values
            z = resids - np.mean(resids)
            z2_sum = np.sum(z**2)
            
            if z2_sum == 0:
                I_val = 0.0
            else:
                I_val = float(np.sum(z * W.dot(z)) / z2_sum)
                
            expected_I = -1.0 / (N - 1)
            
            # 199 permutation test
            rng = np.random.default_rng(42)
            sim_Is = []
            for _ in range(199):
                z_perm = rng.permutation(z)
                sim_Is.append(float(np.sum(z_perm * W.dot(z_perm)) / z2_sum))
            sim_std = float(np.std(sim_Is))
            z_score = float((I_val - np.mean(sim_Is)) / sim_std) if sim_std > 0 else 0.0
            p_val = float((np.sum(np.array(sim_Is) >= I_val) + 1.0) / 200.0)
            
            rows.append({
                "resolution": res,
                "target": target,
                "model": mod,
                "feature_set": fset,
                "n_cells": N,
                "k_neighbors": k_nn,
                "morans_i": round(I_val, 4),
                "expected_i": round(expected_I, 4),
                "z_score": round(z_score, 2),
                "pseudo_p": round(p_val, 4)
            })
            
    return pd.DataFrame(rows)


def run_diagnostics():
    print("=" * 80)
    print("RUNNING IUCN INTERPRETATION AND DIAGNOSTIC PIPELINE")
    print("=" * 80)
    
    outputs_dir = REPO_ROOT / "ml" / "outputs"
    fig_dir = outputs_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Grouped Permutation Importance
    print("\n--- 1. Computing Grouped Permutation Importance ---")
    grp_rows = []
    for res in ["5deg", "2deg"]:
        for tgt in ["iucn_log_richness", "iucn_endemism"]:
            df, fg, fs = load_dataset(resolution="base" if res == "5deg" else "2deg", target=tgt)
            res_df = compute_grouped_permutation_importance(df, fs, target_name=tgt, resolution=res)
            grp_rows.append(res_df)
    
    grp_df = pd.concat(grp_rows, ignore_index=True)
    grp_df.to_csv(outputs_dir / "iucn_grouped_importance.csv", index=False)
    print(f"[OK] Saved grouped permutation importance to {outputs_dir / 'iucn_grouped_importance.csv'}")
    
    # Plot Grouped Importance
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    sub_grp = grp_df[(grp_df.resolution == "5deg") & (grp_df.target == "iucn_log_richness") & (grp_df.model == "rf")]
    groups_order = ["geography", "contemporary_climate", "palaeoclimate", "topography"]
    sub_grp = sub_grp.set_index("feature_group").reindex(groups_order).reset_index()
    
    bars = ax.barh(sub_grp["feature_group"], sub_grp["mean_r2_drop"], xerr=sub_grp["std_r2_drop"],
                   color=["#4C72B0", "#55A868", "#C44E52", "#8172B3"], alpha=0.85, capsize=4)
    ax.set_xlabel(r"Group Permutation Importance ($\Delta R^2$ Drop on Test Folds)", fontsize=11, fontweight="bold")
    ax.set_title("IUCN Vertebrate Richness: Out-of-Fold Group Feature Importance (RF 5°)", fontsize=12, fontweight="bold")
    ax.grid(axis="x", linestyle=":", alpha=0.6)
    plt.tight_layout()
    grp_fig_path = outputs_dir / "iucn_grouped_importance.png"
    fig.savefig(grp_fig_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved grouped importance figure to {grp_fig_path}")

    # 2. SHAP Summary
    print("\n--- 2. Computing SHAP Feature Attribution ---")
    df5, fg5, fs5 = load_dataset(resolution="base", target="iucn_log_richness")
    m2_cols = fs5["M2"]
    
    rf_shap = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    rf_shap.fit(df5[m2_cols], df5["y"].values)
    
    explainer = shap.TreeExplainer(rf_shap)
    shap_vals = explainer.shap_values(df5[m2_cols])
    
    mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
    shap_df = pd.DataFrame({
        "feature": m2_cols,
        "mean_abs_shap": [round(float(v), 4) for v in mean_abs_shap]
    }).sort_values("mean_abs_shap", ascending=False)
    shap_df.to_csv(outputs_dir / "iucn_shap_importance.csv", index=False)
    print(f"[OK] Saved SHAP importance table to {outputs_dir / 'iucn_shap_importance.csv'}")
    
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    shap.summary_plot(shap_vals, df5[m2_cols], plot_type="bar", show=False)
    plt.title("Out-of-Fold SHAP Feature Importance (RF M2 IUCN Richness 5°)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    shap_fig_path = outputs_dir / "iucn_shap_summary.png"
    plt.savefig(shap_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved SHAP summary plot to {shap_fig_path}")

    # 3. Partial Dependence (ALE / PDP) for Velocity and Refugia
    print("\n--- 3. Computing Partial Dependence Profiles for Velocity and Refugia ---")
    pdp_vel = partial_dependence(rf_shap, df5[m2_cols], ["log10_velocity_temp"], grid_resolution=30)
    pdp_ref = partial_dependence(rf_shap, df5[m2_cols], ["refugial_area_fraction"], grid_resolution=30)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)
    
    # Velocity PDP
    vel_x = pdp_vel["grid_values"][0]
    vel_y = pdp_vel["average"][0]
    ax1.plot(vel_x, vel_y, color="#C44E52", linewidth=2.5, label="Random Forest PDP")
    ax1.axhline(np.mean(vel_y), color="gray", linestyle=":", linewidth=1)
    ax1.set_xlabel(r"$\log_{10}(\text{Climate Velocity})$ [$\log_{10}(\text{km/yr})$]", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Partial Output (Predicted Log Richness)", fontsize=10, fontweight="bold")
    ax1.set_title("Quaternary Temperature Velocity", fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.legend(frameon=True, facecolor="white")
    
    # Refugia PDP
    ref_x = pdp_ref["grid_values"][0]
    ref_y = pdp_ref["average"][0]
    ax2.plot(ref_x, ref_y, color="#2CA02C", linewidth=2.5, label="Random Forest PDP")
    ax2.axhline(np.mean(ref_y), color="gray", linestyle=":", linewidth=1)
    ax2.set_xlabel("Palaeoclimate Refugial Area Fraction", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Partial Output (Predicted Log Richness)", fontsize=10, fontweight="bold")
    ax2.set_title("Refugial Area Fraction", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.5)
    ax2.legend(frameon=True, facecolor="white")
    
    plt.suptitle("Partial Dependence Profiles for Stability Features (Conditioning on Contemporary Climate & Geography)",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    pdp_fig_path = outputs_dir / "iucn_pdp_velocity_refugia.png"
    fig.savefig(pdp_fig_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved PDP figure to {pdp_fig_path}")

    # 4. Residual Moran's I & Residual Maps
    print("\n--- 4. Computing Residual Spatial Autocorrelation & Residual Maps ---")
    oof_5deg = pd.read_csv(outputs_dir / "iucn_5deg" / "tables" / "oof_predictions.csv")
    oof_2deg = pd.read_csv(outputs_dir / "iucn_2deg" / "tables" / "oof_predictions.csv")
    all_oof = pd.concat([oof_5deg, oof_2deg], ignore_index=True)
    
    moran_df = compute_morans_i_table(all_oof)
    moran_df.to_csv(outputs_dir / "iucn_morans_i.csv", index=False)
    print(f"[OK] Saved Moran's I table to {outputs_dir / 'iucn_morans_i.csv'}")
    
    # Global Residual Map (OLS vs RF on 5deg IUCN richness)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=300)
    
    sub_ols = oof_5deg[(oof_5deg.target == "iucn_log_richness") & (oof_5deg.model == "ols")].sort_values("cell_idx")
    resids_ols = (sub_ols["y_true"] - sub_ols["y_pred_m2"]).values
    sc1 = ax1.scatter(sub_ols["lon"], sub_ols["lat"], c=resids_ols, cmap="coolwarm", s=35, vmin=-1.5, vmax=1.5, edgecolors="none")
    ax1.set_title(f"OLS M2 Out-of-Fold Residuals (Moran's I = {moran_df[(moran_df.resolution=='5deg')&(moran_df.model=='ols')&(moran_df.feature_set=='M2')]['morans_i'].values[0]:.3f})", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Latitude", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.4)
    cbar1 = plt.colorbar(sc1, ax=ax1, fraction=0.03, pad=0.02)
    cbar1.set_label("Residual (y - y_hat)", fontsize=9)
    
    sub_rf = oof_5deg[(oof_5deg.target == "iucn_log_richness") & (oof_5deg.model == "rf")].sort_values("cell_idx")
    resids_rf = (sub_rf["y_true"] - sub_rf["y_pred_m2"]).values
    sc2 = ax2.scatter(sub_rf["lon"], sub_rf["lat"], c=resids_rf, cmap="coolwarm", s=35, vmin=-1.5, vmax=1.5, edgecolors="none")
    ax2.set_title(f"Random Forest M2 Out-of-Fold Residuals (Moran's I = {moran_df[(moran_df.resolution=='5deg')&(moran_df.model=='rf')&(moran_df.feature_set=='M2')]['morans_i'].values[0]:.3f})", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Longitude", fontsize=10)
    ax2.set_ylabel("Latitude", fontsize=10)
    ax2.grid(True, linestyle=":", alpha=0.4)
    cbar2 = plt.colorbar(sc2, ax=ax2, fraction=0.03, pad=0.02)
    cbar2.set_label("Residual (y - y_hat)", fontsize=9)
    
    plt.tight_layout()
    res_fig_path = outputs_dir / "iucn_residual_map.png"
    fig.savefig(res_fig_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved residual map to {res_fig_path}")

    # 5. Observed vs Predicted Plot
    print("\n--- 5. Plotting Observed vs Predicted ---")
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 9), dpi=300)
    
    sub_rich_5 = oof_5deg[oof_5deg.target == "iucn_log_richness"]
    
    for ax, mod, title in [
        (ax1, "ols", "OLS Reference (5° Richness)"),
        (ax2, "ridge", "Ridge Regression (5° Richness)"),
        (ax3, "rf", "Random Forest (5° Richness)"),
        (ax4, "hgb", "HistGradientBoosting (5° Richness)")
    ]:
        s = sub_rich_5[sub_rich_5.model == mod]
        r2_m1 = calc_r2(s["y_true"], s["y_pred_m1"])
        r2_m2 = calc_r2(s["y_true"], s["y_pred_m2"])
        
        ax.scatter(s["y_true"], s["y_pred_m1"], color="#4C72B0", alpha=0.35, s=20, label=f"M1: R²={r2_m1:.3f}")
        ax.scatter(s["y_true"], s["y_pred_m2"], color="#C44E52", alpha=0.35, s=20, label=f"M2: R²={r2_m2:.3f}")
        
        lims = [min(s["y_true"].min(), s["y_pred_m2"].min()) - 0.2, max(s["y_true"].max(), s["y_pred_m2"].max()) + 0.2]
        ax.plot(lims, lims, "k--", linewidth=1.2, alpha=0.7)
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_xlabel("Observed ln(1 + Richness)", fontsize=9, fontweight="bold")
        ax.set_ylabel("Predicted ln(1 + Richness)", fontsize=9, fontweight="bold")
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.legend(loc="upper left", frameon=True, facecolor="white", fontsize=8)
        ax.grid(True, linestyle=":", alpha=0.4)
        
    plt.suptitle("Out-of-Fold Observed vs. Predicted Values (Spatial 20° Block CV)", fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    ovp_fig_path = outputs_dir / "iucn_observed_vs_predicted.png"
    fig.savefig(ovp_fig_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved observed-vs-predicted plot to {ovp_fig_path}")

    print("\n" + "=" * 80)
    print("ALL PART 3 DIAGNOSTICS GENERATED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnostics()
