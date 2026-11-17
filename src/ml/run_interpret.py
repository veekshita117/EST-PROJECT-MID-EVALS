"""
run_interpret.py
----------------
Model Interpretation, Permutation Importance, Grouped Feature Importance,
Partial Dependence (PDP & ICE), 2D Interaction PDPs, and SHAP Diagnostics.
Stage 5.

Evaluates Random Forest and HistGradientBoosting on feature tiers M2a and M2b.
Refits each outer fold on training data using exact best hyperparameters from tables/best_params.csv.
Permutation importance and grouped importance are evaluated strictly on untouched test folds.
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
from sklearn.inspection import permutation_importance, partial_dependence

from src.ml.config import load_config
from src.ml.data import load_dataset
from src.ml.cv import spatial_outer_folds
from src.ml.models import get_regressor
from src.ml.metrics import calc_r2

warnings.filterwarnings("ignore")


def refit_fold_model(model_name: str, params_row: pd.Series, X_tr: pd.DataFrame, y_tr: pd.Series, seed: int):
    """
    Instantiate pipeline and configure with tuned parameters from best_params.csv, then fit on train data.
    """
    pipe = get_regressor(model_name, random_state=seed)
    
    # Extract model__ parameters
    int_params = [
        "model__n_estimators", "model__min_samples_leaf", "model__max_depth",
        "model__max_leaf_nodes", "model__max_iter"
    ]
    settable_params = {}
    for col in params_row.index:
        if col.startswith("model__"):
            val = params_row[col]
            if pd.notna(val):
                if col in int_params:
                    settable_params[col] = int(val)
                else:
                    settable_params[col] = float(val)
                    
    pipe.set_params(**settable_params)
    pipe.fit(X_tr, y_tr)
    return pipe


def run_interpretation(source: str = "paleoclim", resolution: str = "base", fast: bool = False):
    print(f"\n=======================================================")
    print(f"  RUNNING INTERPRETATION LAYER: source={source}, res={resolution}, fast={fast}")
    print(f"=======================================================\n")
    
    cfg = load_config()
    seed = cfg["seed"]
    
    # Directory setup
    tables_dir = REPO_ROOT / "results" / "tables"
    ml_out_dir = REPO_ROOT / "results" / "ml" / f"{source}_{resolution}"
    ml_tables_dir = ml_out_dir / "tables"
    ml_figures_dir = ml_out_dir / "figures"
    ml_logs_dir = ml_out_dir / "logs"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    ml_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df, feature_groups, feature_sets = load_dataset(source, resolution)
    df = df.copy()
    
    # Load best hyperparameters
    bp_path = tables_dir / "best_params.csv"
    if not bp_path.exists():
        bp_path = ml_tables_dir / "best_params.csv"
    assert bp_path.exists(), f"Could not find best_params.csv at {bp_path}!"
    best_params_df = pd.read_csv(bp_path)
    
    # Outer folds for Repeat 0 (offset 0)
    reuse_p6 = (resolution == "base")
    folds, groups = spatial_outer_folds(
        df,
        k=5,
        seed=seed,
        offset=0.0,
        reuse_phase6=reuse_p6
    )
    
    models_to_run = ["rf", "hgb"]
    feature_tiers = ["M2a", "M2b"]
    n_perm_repeats = 5 if fast else 20
    
    perm_records = []
    impurity_records = []
    grouped_records = []
    
    # Fitted models store: (model_name, fset_name, fold_idx) -> fitted_pipe
    fitted_models = {}
    
    print("--- 1 & 2. Refitting Models and Computing Permutation & Grouped Importance ---")
    for model_name in models_to_run:
        for fset_name in feature_tiers:
            f_cols = feature_sets[fset_name]
            
            # Map columns to feature groups using standardized feature_groups
            group_defs = {}
            for grp in ["effort", "geography", "topography", "palaeoclimate"]:
                canonical = set(feature_groups.get(grp, []))
                if grp == "effort":
                    canonical.update(["log_n", "log_effort", "effort", "n_records"])
                elif grp == "geography":
                    canonical.update(["lat", "abs_lat", "cell_lat", "lon", "cell_lon"])
                elif grp == "topography":
                    canonical.update(["elevation", "relief", "elevation_mean", "topographic_heterogeneity"])
                elif grp == "palaeoclimate":
                    canonical.update([c for c in f_cols if c.startswith(("pc_", "wc_"))])
                group_defs[grp] = [c for c in f_cols if c in canonical]
            
            fold_perm_drops = {col: [] for col in f_cols}
            fold_group_drops = {grp: [] for grp in group_defs.keys() if len(group_defs[grp]) > 0}
            
            for f_idx, (tr, te) in enumerate(folds):
                fold_num = f_idx + 1
                
                # Retrieve best hyperparams for this fold
                sub_bp = best_params_df[
                    (best_params_df["repeat"] == 0) &
                    (best_params_df["fold"] == fold_num) &
                    (best_params_df["model"] == model_name) &
                    (best_params_df["feature_set"] == fset_name)
                ]
                assert len(sub_bp) > 0, f"No params found for {model_name} {fset_name} fold {fold_num}!"
                param_row = sub_bp.iloc[0]
                
                X_tr = df.iloc[tr][f_cols]
                y_tr = df.iloc[tr]["y"]
                X_te = df.iloc[te][f_cols]
                y_te = df.iloc[te]["y"]
                
                # Refit model
                pipe = refit_fold_model(model_name, param_row, X_tr, y_tr, seed=seed + fold_num)
                fitted_models[(model_name, fset_name, fold_num)] = pipe
                
                # Built-in impurity importance (RF only) for comparison only
                if model_name == "rf":
                    est = pipe.named_steps["model"]
                    if hasattr(est, "feature_importances_"):
                        for c, imp in zip(f_cols, est.feature_importances_):
                            impurity_records.append({
                                "source": source,
                                "resolution": resolution,
                                "fold": fold_num,
                                "model": model_name,
                                "feature_set": fset_name,
                                "feature": c,
                                "impurity_importance": float(imp)
                            })
                            
                # Permutation Importance on TEST fold only
                res_pi = permutation_importance(
                    pipe, X_te, y_te,
                    n_repeats=n_perm_repeats,
                    scoring="r2",
                    random_state=seed + fold_num,
                    n_jobs=-1
                )
                
                for idx_col, c in enumerate(f_cols):
                    mean_drop = float(res_pi.importances_mean[idx_col])
                    fold_perm_drops[c].append(mean_drop)
                    
                # Grouped Permutation Importance on TEST fold
                # Permute all columns in a group TOGETHER with identical row permutation
                base_r2 = calc_r2(y_te.values, pipe.predict(X_te))
                rng_grp = np.random.default_rng(seed + fold_num)
                
                for grp_name, grp_cols in group_defs.items():
                    if len(grp_cols) == 0:
                        continue
                    rep_drops = []
                    for _ in range(n_perm_repeats):
                        X_te_perm = X_te.copy()
                        perm_idx = rng_grp.permutation(len(X_te))
                        X_te_perm[grp_cols] = X_te[grp_cols].iloc[perm_idx].values
                        perm_r2 = calc_r2(y_te.values, pipe.predict(X_te_perm))
                        rep_drops.append(base_r2 - perm_r2)
                    fold_group_drops[grp_name].append(float(np.mean(rep_drops)))
                    
            # Aggregate Permutation Importance across folds
            for c in f_cols:
                drops = fold_perm_drops[c]
                perm_records.append({
                    "source": source,
                    "resolution": resolution,
                    "model": model_name,
                    "feature_set": fset_name,
                    "feature": c,
                    "mean_drop_r2": float(np.mean(drops)),
                    "std_drop_r2": float(np.std(drops)),
                    "fold_drops": drops
                })
                
            # Aggregate Grouped Importance across folds
            for grp_name in fold_group_drops.keys():
                drops = fold_group_drops[grp_name]
                grouped_records.append({
                    "source": source,
                    "resolution": resolution,
                    "model": model_name,
                    "feature_set": fset_name,
                    "group": grp_name,
                    "mean_drop_r2": float(np.mean(drops)),
                    "std_drop_r2": float(np.std(drops))
                })
                
    # Save Permutation Importance
    perm_df = pd.DataFrame(perm_records)
    perm_csv = tables_dir / "perm_importance.csv"
    ml_perm_csv = ml_tables_dir / "perm_importance.csv"
    perm_df.to_csv(perm_csv, index=False)
    perm_df.to_csv(ml_perm_csv, index=False)
    print(f"[OK] Saved Permutation Importance to {perm_csv} and {ml_perm_csv}")
    
    # Save Impurity Importance (for comparison only)
    if len(impurity_records) > 0:
        imp_df = pd.DataFrame(impurity_records)
        imp_agg = imp_df.groupby(["model", "feature_set", "feature"])["impurity_importance"].agg(["mean", "std"]).reset_index()
        imp_csv = tables_dir / "impurity_importance_for_comparison_only.csv"
        ml_imp_csv = ml_tables_dir / "impurity_importance_for_comparison_only.csv"
        imp_agg.to_csv(imp_csv, index=False)
        imp_agg.to_csv(ml_imp_csv, index=False)
        print(f"[OK] Saved impurity importance (for comparison only) to {imp_csv}")
        
    # Save Grouped Importance
    grp_df = pd.DataFrame(grouped_records)
    grp_csv = tables_dir / "grouped_importance.csv"
    ml_grp_csv = ml_tables_dir / "grouped_importance.csv"
    grp_df.to_csv(grp_csv, index=False)
    grp_df.to_csv(ml_grp_csv, index=False)
    print(f"[OK] Saved Grouped Importance to {grp_csv} and {ml_grp_csv}")
    
    # -------------------------------------------------------------
    # FIGURES: Permutation & Grouped Importance Bar Charts
    # -------------------------------------------------------------
    # 1. Permutation Importance Horizontal Bar Chart for RF M2a and M2b
    for fset_plot in ["M2a", "M2b"]:
        sub_p = perm_df[(perm_df["model"] == "rf") & (perm_df["feature_set"] == fset_plot)].sort_values("mean_drop_r2", ascending=True)
        if len(sub_p) == 0:
            continue
        fig, ax = plt.subplots(figsize=(8, max(4, int(len(sub_p)*0.4))), dpi=300)
        ax.barh(sub_p["feature"], sub_p["mean_drop_r2"], xerr=sub_p["std_drop_r2"], color="#4C72B0", alpha=0.85, capsize=4)
        ax.set_xlabel(r"Drop in Test Fold $R^2$ (Permutation Importance)", fontsize=11, fontweight="bold")
        ax.set_title(f"Permutation Feature Importance on Held-Out Folds (RF {fset_plot})", fontsize=12, fontweight="bold")
        ax.grid(axis="x", linestyle=":", alpha=0.6)
        plt.tight_layout()
        fname = f"perm_importance_{fset_plot.lower()}.png"
        plt.savefig(ml_figures_dir / fname, dpi=300)
        if fset_plot == "M2a":
            plt.savefig(ml_figures_dir / "permutation_importance.png", dpi=300)
        plt.close()
        
    print(f"[OK] Saved Permutation Importance figures to {ml_figures_dir}")
    
    # 2. Grouped Importance Clean Bar Chart (Primary Question Figure)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    grp_m2a = grp_df[(grp_df["feature_set"] == "M2a")].copy()
    groups_order = ["effort", "geography", "topography", "palaeoclimate"]
    
    x = np.arange(len(groups_order))
    width = 0.35
    
    rf_drops = [grp_m2a[(grp_m2a["model"] == "rf") & (grp_m2a["group"] == g)]["mean_drop_r2"].values[0] for g in groups_order]
    rf_stds = [grp_m2a[(grp_m2a["model"] == "rf") & (grp_m2a["group"] == g)]["std_drop_r2"].values[0] for g in groups_order]
    
    hgb_drops = [grp_m2a[(grp_m2a["model"] == "hgb") & (grp_m2a["group"] == g)]["mean_drop_r2"].values[0] for g in groups_order]
    hgb_stds = [grp_m2a[(grp_m2a["model"] == "hgb") & (grp_m2a["group"] == g)]["std_drop_r2"].values[0] for g in groups_order]
    
    ax.bar(x - width/2, rf_drops, width, yerr=rf_stds, label="Random Forest", color="#4C72B0", alpha=0.85, capsize=4)
    ax.bar(x + width/2, hgb_drops, width, yerr=hgb_stds, label="HistGradientBoosting", color="#C44E52", alpha=0.85, capsize=4)
    
    ax.set_xticks(x)
    ax.set_xticklabels(["Effort\n(Sampling)", "Geography\n(Latitude)", "Topography\n(Elev + Heterog)", "Palaeoclimate\n(Instability)"], fontsize=11, fontweight="bold")
    ax.set_ylabel(r"Drop in Test $R^2$ when Permuted Together", fontsize=11, fontweight="bold")
    ax.set_title("Grouped Feature Importance on Untouched Spatial Folds ($M2a$)", fontsize=13, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", fontsize=11)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    grp_fig_path = ml_figures_dir / "grouped_importance_bars.png"
    plt.savefig(grp_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Grouped Importance figure to {grp_fig_path}")
    
    # -------------------------------------------------------------
    # 3. PARTIAL DEPENDENCE (PDP & ICE)
    # -------------------------------------------------------------
    print("\n--- 3. Partial Dependence Profiles & ICE Curves ---")
    
    # Identify top two stability features from M2b permutation importance on RF
    m2b_perm = perm_df[(perm_df["model"] == "rf") & (perm_df["feature_set"] == "M2b")]
    stab_perm = m2b_perm[m2b_perm["feature"].str.startswith(("pc_", "wc_"))].sort_values("mean_drop_r2", ascending=False)
    
    default_comp = "wc_composite_instability" if source == "worldclim" else "pc_composite_instability"
    default_temp = "wc_temp_instability" if source == "worldclim" else "pc_temp_instability"
    top_stab_1 = stab_perm.iloc[0]["feature"] if len(stab_perm) > 0 else default_comp
    top_stab_2 = stab_perm.iloc[1]["feature"] if len(stab_perm) > 1 else default_temp
    print(f"Top 2 Palaeoclimate Features from RF M2b: '{top_stab_1}', '{top_stab_2}'")
    
    # Resolve column names for PDP features
    f_cols_m2b = feature_sets["M2b"]
    c_relief = "relief" if "relief" in f_cols_m2b else "topographic_heterogeneity"
    c_elev = "elevation" if "elevation" in f_cols_m2b else "elevation_mean"
    c_lat = "abs_lat" if "abs_lat" in f_cols_m2b else ("lat" if "lat" in f_cols_m2b else "cell_lat")
    c_eff = "log_effort" if "log_effort" in f_cols_m2b else "log_n"

    # 6 features to plot: top_stab_1, top_stab_2, relief, elevation, latitude, log_effort
    pdp_features = [
        (top_stab_1, f"Stability 1 ({top_stab_1})"),
        (top_stab_2, f"Stability 2 ({top_stab_2})"),
        (c_relief, "Topographic Relief"),
        (c_elev, "Elevation (m)"),
        (c_lat, "Absolute Latitude (|°|)"),
        (c_eff, "Effort (ln[1+effort])")
    ]
    X_full = df[f_cols_m2b]
    
    # Use RF fold 1 as primary representative model, and overlay all 5 folds
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), dpi=300)
    axes = axes.flatten()
    
    subsample_n = min(200, len(df))
    rng_sub = np.random.default_rng(seed)
    sub_indices = rng_sub.choice(len(df), size=subsample_n, replace=False)
    X_sub = X_full.iloc[sub_indices]
    
    shape_descriptions = {}
    
    for ax_idx, (feat, label) in enumerate(pdp_features):
        ax = axes[ax_idx]
        
        # Overlay PDP curves across all 5 folds (thin translucent lines)
        grid_vals_ref = None
        fold_pdp_lines = []
        
        for fold_num in range(1, 6):
            pipe_fold = fitted_models[("rf", "M2b", fold_num)]
            pdp_fold = partial_dependence(
                pipe_fold, X_full,
                features=[feat],
                grid_resolution=50,
                percentiles=(0.05, 0.95),
                kind="average"
            )
            g_vals = pdp_fold["grid_values"][0]
            avg_pdp = pdp_fold["average"][0]
            grid_vals_ref = g_vals
            fold_pdp_lines.append(avg_pdp)
            ax.plot(g_vals, avg_pdp, color="#4C72B0", alpha=0.35, linewidth=1.2)
            
        # Overall average across folds
        mean_pdp_curve = np.mean(fold_pdp_lines, axis=0)
        
        # ICE curves from fold 1 model on the 200 subsampled rows
        pdp_ice = partial_dependence(
            fitted_models[("rf", "M2b", 1)], X_sub,
            features=[feat],
            grid_resolution=50,
            percentiles=(0.05, 0.95),
            kind="both"
        )
        ice_curves = pdp_ice["individual"][0] # (200, 50)
        for i in range(min(50, len(ice_curves))):
            ax.plot(pdp_ice["grid_values"][0], ice_curves[i], color="gray", alpha=0.15, linewidth=0.6)
            
        # Draw prominent mean PDP line
        ax.plot(grid_vals_ref, mean_pdp_curve, color="#C44E52", linewidth=2.5, label="Mean PDP across folds")
        
        # Rug plot at bottom
        vals_data = df[feat].values
        ax.plot(vals_data, np.full_like(vals_data, mean_pdp_curve.min() - 0.15 * (mean_pdp_curve.max() - mean_pdp_curve.min() + 1e-5)),
                "|", color="black", alpha=0.5, markersize=8)
                
        ax.set_xlabel(label, fontsize=10, fontweight="bold")
        ax.set_ylabel("Predicted log(1+richness)", fontsize=10)
        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.5)
        if ax_idx == 0:
            ax.legend(frameon=True, facecolor="white", fontsize=8)
            
        # Characterise functional shape strictly (do not use monotonic unless curve is strictly monotonic)
        diffs = np.diff(mean_pdp_curve)
        if np.all(diffs > 0):
            shape_desc = "strictly monotonic increasing"
        elif np.all(diffs < 0):
            shape_desc = "strictly monotonic decreasing"
        elif np.max(mean_pdp_curve) - mean_pdp_curve[0] > 0.05 and np.max(mean_pdp_curve) - mean_pdp_curve[-1] > 0.05:
            shape_desc = "unimodal / humped"
        else:
            shape_desc = "non-monotonic (plateau / fluctuating)"
        shape_descriptions[feat] = shape_desc
        
    # Check sign of PDP/ALE for composite instability against Spearman direction
    from scipy import stats
    comp_spearman_rho, comp_spearman_p = stats.spearmanr(df[top_stab_1], df["richness"])
    spearman_dir = "negative (higher instability -> lower richness)" if comp_spearman_rho < 0 else "positive"
    print(f"\n[SIGN CHECK]: Empirical Spearman correlation of '{top_stab_1}' with richness: rho = {comp_spearman_rho:.3f} ({spearman_dir})")
    print(f"[SIGN CHECK]: PDP functional shape for '{top_stab_1}': {shape_descriptions.get(top_stab_1, 'unknown')}")
        
    plt.suptitle("Partial Dependence Profiles & ICE Curves across Outer Folds (Random Forest M2b)\n"
                 "[Thin blue: individual outer folds; Thick red: mean PDP; Gray: ICE curves; Rug: empirical distribution]",
                 fontsize=12, fontweight="bold", y=0.99)
    plt.tight_layout()
    pdp_path = ml_figures_dir / "pdp_ice_profiles.png"
    plt.savefig(pdp_path, dpi=300)
    plt.close()
    print(f"[OK] Saved 1D PDP profiles to {pdp_path}")
    
    # -------------------------------------------------------------
    # 3b. ACCUMULATED LOCAL EFFECTS (ALE)
    # -------------------------------------------------------------
    print("\n--- 3b. Computing Accumulated Local Effects (ALE) ---")
    ale_records = []
    fig_ale, axes_ale = plt.subplots(2, 3, figsize=(15, 9), dpi=300)
    axes_ale = axes_ale.flatten()
    
    rep_model = fitted_models[("rf", "M2b", 1)]
    
    for ax_idx, (feat, label) in enumerate(pdp_features):
        ax_a = axes_ale[ax_idx]
        x_feat = df[feat].values
        # 20 quantile bins
        q_grid = np.unique(np.quantile(x_feat, np.linspace(0.02, 0.98, 21)))
        
        ale_diffs = []
        ale_centers = []
        
        for k in range(len(q_grid) - 1):
            z_l = q_grid[k]
            z_r = q_grid[k + 1]
            mask_bin = (x_feat >= z_l) & (x_feat <= z_r)
            if not np.any(mask_bin):
                continue
            X_bin = X_full[mask_bin].copy()
            
            X_r = X_bin.copy()
            X_r[feat] = z_r
            X_l = X_bin.copy()
            X_l[feat] = z_l
            
            p_r = rep_model.predict(X_r)
            p_l = rep_model.predict(X_l)
            diff_mean = float(np.mean(p_r - p_l))
            ale_diffs.append(diff_mean)
            ale_centers.append(0.5 * (z_l + z_r))
            
        ale_vals = np.concatenate([[0.0], np.cumsum(ale_diffs)])
        ale_vals = ale_vals - np.mean(ale_vals) # zero-centered
        ale_grid = np.array([q_grid[0]] + ale_centers)
        
        ax_a.plot(ale_grid, ale_vals, color="#2CA02C", linewidth=2.5, marker="o", markersize=4, label="ALE Effect")
        ax_a.axhline(0, color="gray", linestyle=":", alpha=0.7)
        ax_a.set_xlabel(label, fontsize=10, fontweight="bold")
        ax_a.set_ylabel("Accumulated Local Effect", fontsize=10)
        ax_a.set_title(f"ALE: {label}", fontsize=11, fontweight="bold")
        ax_a.grid(True, linestyle=":", alpha=0.5)
        
        # Save to records
        for g_pt, a_pt in zip(ale_grid, ale_vals):
            ale_records.append({
                "source": source,
                "resolution": resolution,
                "feature": feat,
                "feature_value": float(g_pt),
                "ale_effect": float(a_pt)
            })
            
    plt.suptitle("Accumulated Local Effects (ALE) Profiles (Random Forest M2b)\n"
                 "[Avoids off-manifold extrapolation by evaluating local differences within quantile intervals]",
                 fontsize=12, fontweight="bold", y=0.99)
    plt.tight_layout()
    ale_fig_path = ml_figures_dir / "ale_profiles.png"
    plt.savefig(ale_fig_path, dpi=300)
    plt.close()
    
    ale_df = pd.DataFrame(ale_records)
    ale_csv = ml_tables_dir / "ale_profiles.csv"
    ale_df.to_csv(ale_csv, index=False)
    ale_df.to_csv(tables_dir / "ale_profiles.csv", index=False)
    print(f"[OK] Saved ALE profiles to {ale_csv} and {ale_fig_path}")
    
    # 2D Partial Dependence Plot: Top Stability Feature against Relief
    print(f"\nComputing 2D PDP of '{top_stab_1}' vs '{c_relief}'...")
    pdp_2d = partial_dependence(
        fitted_models[("rf", "M2b", 1)], X_full,
        features=[top_stab_1, c_relief],
        grid_resolution=30,
        percentiles=(0.05, 0.95),
        kind="average"
    )
    grid_stab = pdp_2d["grid_values"][0]
    grid_relief = pdp_2d["grid_values"][1]
    Z_pdp = pdp_2d["average"][0] # shape (30, 30)
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    CS = ax.contourf(grid_stab, grid_relief, Z_pdp.T, levels=15, cmap="viridis")
    cbar = fig.colorbar(CS, ax=ax)
    cbar.set_label("Predicted log(1 + richness)", fontsize=11, fontweight="bold")
    
    ax.scatter(df[top_stab_1], df[c_relief], color="black", alpha=0.3, s=15, label="Observed Cells")
    ax.set_xlabel(f"Top Stability Feature: {top_stab_1}", fontsize=11, fontweight="bold")
    ax.set_ylabel(f"Topographic Relief ({c_relief})", fontsize=11, fontweight="bold")
    ax.set_title(f"2D Partial Dependence: Quaternary Stability × Topographic Relief", fontsize=12, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    pdp2d_path = ml_figures_dir / "pdp_2d_stability_relief.png"
    plt.savefig(pdp2d_path, dpi=300)
    plt.close()
    print(f"[OK] Saved 2D PDP to {pdp2d_path}")
    
    # -------------------------------------------------------------
    # 4. SHAP (TreeExplainer on Out-of-Fold Data for RF & HGB)
    # -------------------------------------------------------------
    print("\n--- 4. SHAP Analysis (TreeExplainer on Out-of-Fold Data) ---")
    shap_records = []
    try:
        import shap
        print("shap package imported successfully. Running TreeExplainer across all out-of-fold test partitions...")
        
        for m_name in ["rf", "hgb"]:
            oof_shap_list = []
            oof_idx_list = []
            
            for f_idx, (tr, te) in enumerate(folds):
                fold_num = f_idx + 1
                pipe_fold = fitted_models[(m_name, "M2b", fold_num)]
                X_te = df.iloc[te][f_cols_m2b]
                
                # Regressor step
                reg_model = pipe_fold.named_steps["model"]
                
                # Transform test features with scaler/imputer
                if "scaler" in pipe_fold.named_steps:
                    X_te_trans = pipe_fold.named_steps["scaler"].transform(
                        pipe_fold.named_steps["imputer"].transform(X_te) if "imputer" in pipe_fold.named_steps else X_te
                    )
                else:
                    X_te_trans = X_te.values
                    
                explainer = shap.TreeExplainer(reg_model)
                shap_vals = explainer.shap_values(X_te_trans)
                oof_shap_list.append(shap_vals)
                oof_idx_list.append(te)
                
            all_oof_shap = np.vstack(oof_shap_list)
            all_oof_idx = np.concatenate(oof_idx_list)
            # Sort back to original order
            sorted_order = np.argsort(all_oof_idx)
            all_oof_shap = all_oof_shap[sorted_order]
            
            mean_abs_shap = np.mean(np.abs(all_oof_shap), axis=0)
            for feat_name, s_val in zip(f_cols_m2b, mean_abs_shap):
                shap_records.append({
                    "source": source,
                    "resolution": resolution,
                    "model": m_name,
                    "feature": feat_name,
                    "mean_abs_shap": float(s_val)
                })
                
            # Summary plot for RF
            if m_name == "rf":
                plt.figure(figsize=(8, 6), dpi=300)
                shap.summary_plot(all_oof_shap, df[f_cols_m2b], plot_type="bar", show=False)
                plt.title("Out-of-Fold SHAP Feature Importance (RF M2b)", fontsize=12, fontweight="bold")
                plt.tight_layout()
                plt.savefig(ml_figures_dir / "shap_bar_summary.png", dpi=300)
                plt.close()
                
                plt.figure(figsize=(9, 6), dpi=300)
                shap.summary_plot(all_oof_shap, df[f_cols_m2b], show=False)
                plt.title("Out-of-Fold SHAP Beeswarm Plot (RF M2b)", fontsize=12, fontweight="bold")
                plt.tight_layout()
                plt.savefig(ml_figures_dir / "shap_beeswarm.png", dpi=300)
                plt.close()
                
        shap_df = pd.DataFrame(shap_records)
        shap_csv = ml_tables_dir / "shap_importance.csv"
        shap_df.to_csv(shap_csv, index=False)
        shap_df.to_csv(tables_dir / "shap_importance.csv", index=False)
        print(f"[OK] Saved Out-of-Fold SHAP table to {shap_csv}")
        print("[INTERPRETATION NOTE]: Both SHAP and permutation importance describe internal model behavior on the dataset, not physical or ecological causes.")
    except Exception as e:
        shap_msg = f"SHAP error: {e}"
        print(f"[SHAP NOTICE] {shap_msg}")
        with open(ml_logs_dir / "shap_status.log", "w") as f:
            f.write(f"{shap_msg}\n")
            
    # Print functional shape observations and collinearity caution
    print("\n--- Empirical Functional Shapes from PDPs ---")
    for feat, shape in shape_descriptions.items():
        print(f"  - {feat:28s}: {shape}")
    print("\n[CAUTION]: Partial dependence plots assume feature independence. In the presence of strong collinearity "
          "(e.g., between temperature stability, precipitation stability, and latitudinal gradients), PDP marginal profiles "
          "can force extrapolation into unobserved feature space and must be interpreted with caution.")
          
    return grp_df, perm_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 5: Model Interpretation and Importance")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    args = parser.parse_args()
    
    run_interpretation(source=args.source, resolution=args.resolution, fast=args.fast)
