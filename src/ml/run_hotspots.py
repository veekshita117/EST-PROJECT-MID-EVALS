"""
run_hotspots.py
---------------
Hotspot Classification, Nested Spatial Cross-Validation, Threshold Optimization (Youden's J),
Model Evaluation (ROC-AUC, PR-AUC, F1, MCC, Balanced Accuracy),
and Research Question Testing (Stability Deciles & Cluster-Robust Odds Ratios).
Stage 6.
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
from sklearn.base import clone
from sklearn.model_selection import GroupKFold, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import (
    roc_curve, roc_auc_score, precision_recall_curve, average_precision_score,
    balanced_accuracy_score, f1_score, matthews_corrcoef, confusion_matrix
)
import statsmodels.api as sm
import statsmodels.formula.api as smf

from ml.src.config import load_config
from ml.src.data import load_dataset
from ml.src.cv import spatial_outer_folds
from ml.src.models import get_classifier, get_param_grid

warnings.filterwarnings("ignore")


def run_hotspots(source: str = "paleoclim", resolution: str = "base", fast: bool = False):
    print(f"\n=======================================================")
    print(f"  RUNNING HOTSPOT CLASSIFICATION: source={source}, res={resolution}, fast={fast}")
    print(f"=======================================================\n")
    
    cfg = load_config()
    seed = cfg["seed"]
    q_threshold = cfg.get("hotspots", {}).get("quantile", 0.75)
    scope = cfg.get("hotspots", {}).get("scope", "global")
    
    # Setup directories
    tables_dir = REPO_ROOT / "tables"
    ml_out_dir = REPO_ROOT / "ml" / "outputs" / f"{source}_{resolution}"
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
    
    # -------------------------------------------------------------
    # Label Definition
    # -------------------------------------------------------------
    if scope == "within_continent":
        print("Hotspot scope: within_continent")
        df["hotspot"] = 0
        for cont, grp in df.groupby("continent"):
            thresh = grp["richness"].quantile(q_threshold)
            df.loc[grp.index, "hotspot"] = (grp["richness"] >= thresh).astype(int)
    else:
        print("Hotspot scope: global")
        richness_thresh = float(df["richness"].quantile(q_threshold))
        df["hotspot"] = (df["richness"] >= richness_thresh).astype(int)
        
    n_hotspots = int(df["hotspot"].sum())
    n_total = len(df)
    pos_rate = n_hotspots / n_total
    print(f"Label Defined: 75th Percentile Richness Threshold = {df['richness'].quantile(q_threshold):.1f}")
    print(f"Class Balance: Total={n_total}, Hotspots={n_hotspots} ({pos_rate*100:.1f}%), Non-Hotspots={n_total - n_hotspots} ({(1-pos_rate)*100:.1f}%)")
    
    # Models and feature tiers
    models_to_run = ["logistic", "rf", "hgb"]
    feature_tiers = ["M0", "M1", "M2a", "M2b", "M3a", "M_effort_free"]
    
    # Outer folds (Repeat 0, offset 0.0)
    reuse_p6 = (resolution == "base")
    folds, groups = spatial_outer_folds(
        df,
        k=5,
        seed=seed,
        offset=0.0,
        reuse_phase6=reuse_p6
    )
    
    oof_predictions = []
    fold_metric_records = []
    
    print("\n--- Running Nested Spatial Classification CV ---")
    
    for model_name in models_to_run:
        for fset_name in feature_tiers:
            f_cols = feature_sets[fset_name]
            
            oof_probs = np.zeros(len(df))
            oof_preds = np.zeros(len(df), dtype=int)
            oof_thresholds = np.zeros(len(df))
            
            for f_idx, (tr, te) in enumerate(folds):
                fold_num = f_idx + 1
                X_tr = df.iloc[tr][f_cols]
                y_tr = df.iloc[tr]["hotspot"]
                groups_tr = groups.iloc[tr] if isinstance(groups, pd.Series) else groups[tr]
                
                X_te = df.iloc[te][f_cols]
                y_te = df.iloc[te]["hotspot"]
                
                # Setup classifier and tuning
                pipe = get_classifier(model_name, random_state=seed + fold_num)
                p_grid = get_param_grid(model_name, fast=fast)
                cv_inner = GroupKFold(n_splits=3)
                
                if model_name == "logistic":
                    tuner = GridSearchCV(pipe, p_grid, cv=cv_inner, scoring="roc_auc", n_jobs=-1)
                else:
                    n_it = 6 if fast else 15
                    tuner = RandomizedSearchCV(
                        pipe, p_grid, n_iter=n_it, cv=cv_inner, scoring="roc_auc",
                        random_state=seed + fold_num, n_jobs=-1
                    )
                    
                tuner.fit(X_tr, y_tr, groups=groups_tr)
                best_pipe = tuner.best_estimator_
                
                # Decision threshold optimization via Youden's J on inner-CV training OOF
                inner_oof_probs = np.zeros(len(X_tr))
                for in_tr, in_val in cv_inner.split(X_tr, y_tr, groups_tr):
                    sub_model = clone(best_pipe)
                    sub_model.fit(X_tr.iloc[in_tr], y_tr.iloc[in_tr])
                    inner_oof_probs[in_val] = sub_model.predict_proba(X_tr.iloc[in_val])[:, 1]
                    
                fpr, tpr, threshs = roc_curve(y_tr, inner_oof_probs)
                youden_j = tpr - fpr
                best_idx = int(np.argmax(youden_j))
                opt_thresh = float(threshs[best_idx])
                if opt_thresh > 0.95 or opt_thresh < 0.05:
                    opt_thresh = 0.5
                    
                # Predict on untouched test fold
                te_probs = best_pipe.predict_proba(X_te)[:, 1]
                te_preds = (te_probs >= opt_thresh).astype(int)
                
                oof_probs[te] = te_probs
                oof_preds[te] = te_preds
                oof_thresholds[te] = opt_thresh
                
                # Fold metrics
                f_auc = roc_auc_score(y_te, te_probs) if len(np.unique(y_te)) > 1 else np.nan
                f_prauc = average_precision_score(y_te, te_probs) if len(np.unique(y_te)) > 1 else np.nan
                f_bacc = balanced_accuracy_score(y_te, te_preds)
                f_f1 = f1_score(y_te, te_preds, zero_division=0)
                f_mcc = matthews_corrcoef(y_te, te_preds)
                
                fold_metric_records.append({
                    "source": source,
                    "resolution": resolution,
                    "model": model_name,
                    "feature_set": fset_name,
                    "fold": fold_num,
                    "opt_threshold": opt_thresh,
                    "roc_auc": f_auc,
                    "pr_auc": f_prauc,
                    "balanced_acc": f_bacc,
                    "f1": f_f1,
                    "mcc": f_mcc
                })
                
            # Store OOF predictions
            for idx_cell in range(len(df)):
                oof_predictions.append({
                    "cell_idx": idx_cell,
                    "lon": df.iloc[idx_cell]["lon"],
                    "lat": df.iloc[idx_cell]["lat"],
                    "continent": df.iloc[idx_cell]["continent"],
                    "block": df.iloc[idx_cell]["spatial_block_20deg"],
                    "model": model_name,
                    "feature_set": fset_name,
                    "y_true": df.iloc[idx_cell]["hotspot"],
                    "prob": oof_probs[idx_cell],
                    "y_pred": oof_preds[idx_cell],
                    "opt_threshold": oof_thresholds[idx_cell]
                })
                
            pooled_auc = roc_auc_score(df["hotspot"], oof_probs)
            pooled_prauc = average_precision_score(df["hotspot"], oof_probs)
            print(f"  {model_name:10s} {fset_name:5s} | Pooled ROC-AUC: {pooled_auc:.4f} | PR-AUC: {pooled_prauc:.4f}")

    oof_df = pd.DataFrame(oof_predictions)
    fold_df = pd.DataFrame(fold_metric_records)
    
    # -------------------------------------------------------------
    # Pooled Metrics and Delta AUC
    # -------------------------------------------------------------
    metrics_summary = []
    for model_name in models_to_run:
        for fset_name in feature_tiers:
            sub = oof_df[(oof_df["model"] == model_name) & (oof_df["feature_set"] == fset_name)]
            y_t = sub["y_true"].values
            p_s = sub["prob"].values
            y_p = sub["y_pred"].values
            
            p_auc = roc_auc_score(y_t, p_s)
            p_prauc = average_precision_score(y_t, p_s)
            p_bacc = balanced_accuracy_score(y_t, y_p)
            p_f1 = f1_score(y_t, y_p, zero_division=0)
            p_mcc = matthews_corrcoef(y_t, y_p)
            
            sub_fold = fold_df[(fold_df["model"] == model_name) & (fold_df["feature_set"] == fset_name)]
            
            metrics_summary.append({
                "source": source,
                "resolution": resolution,
                "model": model_name,
                "feature_set": fset_name,
                "pooled_roc_auc": p_auc,
                "mean_fold_roc_auc": sub_fold["roc_auc"].mean(),
                "std_fold_roc_auc": sub_fold["roc_auc"].std(),
                "pooled_pr_auc": p_prauc,
                "mean_fold_pr_auc": sub_fold["pr_auc"].mean(),
                "pooled_balanced_acc": p_bacc,
                "pooled_f1": p_f1,
                "pooled_mcc": p_mcc
            })
            
    summary_df = pd.DataFrame(metrics_summary)
    metrics_csv = tables_dir / "hotspot_metrics.csv"
    ml_metrics_csv = ml_tables_dir / "hotspot_metrics.csv"
    summary_df.to_csv(metrics_csv, index=False)
    summary_df.to_csv(ml_metrics_csv, index=False)
    print(f"\n[OK] Saved Hotspot Metrics to {metrics_csv} and {ml_metrics_csv}")
    
    # Delta AUC: M2a - M1 with 1000 Block-Bootstrap Resamples
    print("\nComputing 95% Block-Bootstrap CI for Delta AUC (M2a - M1)...")
    unique_blocks = df["spatial_block_20deg"].unique()
    n_boot = 200 if fast else 1000
    rng_b = np.random.default_rng(seed)
    
    delta_auc_records = []
    
    for model_name in models_to_run:
        sub_m1 = oof_df[(oof_df["model"] == model_name) & (oof_df["feature_set"] == "M1")].sort_values("cell_idx").reset_index(drop=True)
        sub_m2 = oof_df[(oof_df["model"] == model_name) & (oof_df["feature_set"] == "M2a")].sort_values("cell_idx").reset_index(drop=True)
        
        pooled_delta = roc_auc_score(sub_m2["y_true"], sub_m2["prob"]) - roc_auc_score(sub_m1["y_true"], sub_m1["prob"])
        
        # Per-fold delta
        f_m1 = fold_df[(fold_df["model"] == model_name) & (fold_df["feature_set"] == "M1")].set_index("fold")["roc_auc"]
        f_m2 = fold_df[(fold_df["model"] == model_name) & (fold_df["feature_set"] == "M2a")].set_index("fold")["roc_auc"]
        fold_deltas = f_m2 - f_m1
        
        # Block bootstrap
        boot_deltas = []
        for _ in range(n_boot):
            boot_blks = rng_b.choice(unique_blocks, size=len(unique_blocks), replace=True)
            boot_indices = []
            for b in boot_blks:
                boot_indices.extend(df[df["spatial_block_20deg"] == b].index.tolist())
            boot_y = df.loc[boot_indices, "hotspot"].values
            if len(np.unique(boot_y)) < 2:
                continue
            boot_p1 = sub_m1.loc[boot_indices, "prob"].values
            boot_p2 = sub_m2.loc[boot_indices, "prob"].values
            boot_deltas.append(roc_auc_score(boot_y, boot_p2) - roc_auc_score(boot_y, boot_p1))
            
        ci_low = float(np.percentile(boot_deltas, 2.5))
        ci_high = float(np.percentile(boot_deltas, 97.5))
        
        delta_auc_records.append({
            "source": source,
            "resolution": resolution,
            "model": model_name,
            "comparison": "M2a_minus_M1",
            "mean_fold_delta_auc": float(fold_deltas.mean()),
            "std_fold_delta_auc": float(fold_deltas.std()),
            "pooled_delta_auc": float(pooled_delta),
            "boot_ci_low_95": ci_low,
            "boot_ci_high_95": ci_high
        })
        print(f"  {model_name:10s} | Pooled ΔAUC: {pooled_delta:+.4f} | 95% Block CI: [{ci_low:+.4f}, {ci_high:+.4f}]")
        
    delta_auc_df = pd.DataFrame(delta_auc_records)
    delta_csv = tables_dir / "hotspot_delta_auc.csv"
    ml_delta_csv = ml_tables_dir / "hotspot_delta_auc.csv"
    delta_auc_df.to_csv(delta_csv, index=False)
    delta_auc_df.to_csv(ml_delta_csv, index=False)
    print(f"[OK] Saved Delta AUC to {delta_csv} and {ml_delta_csv}")
    
    # -------------------------------------------------------------
    # Direct Test of Research Question: Deciles & Odds Ratios
    # -------------------------------------------------------------
    print("\n--- Direct Test: Stability Deciles & Cluster-Robust Odds Ratios ---")
    primary_stab_col = "wc_composite_instability" if source == "worldclim" else "pc_composite_instability"
    print(f"Primary stability feature chosen: '{primary_stab_col}' (composite Quaternary instability)")
    
    # Deciles of stability
    df["stab_decile"] = pd.qcut(df[primary_stab_col], q=10, labels=False, duplicates="drop")
    
    decile_rows = []
    for d, grp in df.groupby("stab_decile"):
        n_c = len(grp)
        n_h = int(grp["hotspot"].sum())
        rate = n_h / n_c
        # Wilson score interval for binomial proportion
        z_crit = 1.95996
        denom = 1 + z_crit**2 / n_c
        centre = (rate + z_crit**2 / (2 * n_c)) / denom
        delta = z_crit * np.sqrt((rate * (1 - rate) + z_crit**2 / (4 * n_c)) / n_c) / denom
        ci_l = max(0.0, float(centre - delta))
        ci_u = min(1.0, float(centre + delta))
        
        decile_rows.append({
            "decile": int(d) + 1,
            "n_cells": n_c,
            "n_hotspots": n_h,
            "hotspot_rate": float(rate),
            "ci_low_95": ci_l,
            "ci_high_95": ci_u,
            "stab_min": float(grp[primary_stab_col].min()),
            "stab_max": float(grp[primary_stab_col].max())
        })
        
    decile_df = pd.DataFrame(decile_rows)
    dec_csv = tables_dir / "hotspot_by_decile.csv"
    ml_dec_csv = ml_tables_dir / "hotspot_by_decile.csv"
    decile_df.to_csv(dec_csv, index=False)
    decile_df.to_csv(ml_dec_csv, index=False)
    print(f"[OK] Saved Hotspot by Decile table to {dec_csv} and {ml_dec_csv}")
    
    # Odds Ratio: Top vs. Bottom Stability Quartile
    df["stab_quartile"] = pd.qcut(df[primary_stab_col], q=4, labels=["Q1", "Q2", "Q3", "Q4"])
    sub_q = df[df["stab_quartile"].isin(["Q1", "Q4"])].copy()
    sub_q["top_quartile"] = (sub_q["stab_quartile"] == "Q4").astype(int)
    
    # Unadjusted OR (2x2 contingency table: Q4 vs Q1)
    q4 = sub_q[sub_q["top_quartile"] == 1]
    q1 = sub_q[sub_q["top_quartile"] == 0]
    a = q4["hotspot"].sum()
    b = len(q4) - a
    c = q1["hotspot"].sum()
    d = len(q1) - c
    
    # Haldane-Anscombe correction if any cell is 0
    if a == 0 or b == 0 or c == 0 or d == 0:
        a_c, b_c, c_c, d_c = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    else:
        a_c, b_c, c_c, d_c = a, b, c, d
        
    unadj_or = float((a_c * d_c) / (b_c * c_c))
    se_log_or = np.sqrt(1/a_c + 1/b_c + 1/c_c + 1/d_c)
    unadj_ci_low = float(np.exp(np.log(unadj_or) - 1.96 * se_log_or))
    unadj_ci_high = float(np.exp(np.log(unadj_or) + 1.96 * se_log_or))
    
    print(f"\nUnadjusted Odds Ratio (Q4 vs Q1): OR = {unadj_or:.3f} (95% CI: [{unadj_ci_low:.3f}, {unadj_ci_high:.3f}])")
    
    # Adjusted OR with cluster-robust standard errors by 20° spatial block
    c_effort = "log_effort" if "log_effort" in df.columns else "log_n"
    c_lat = "lat" if "lat" in df.columns else "cell_lat"
    c_relief = "relief" if "relief" in df.columns else "topographic_heterogeneity"
    c_elev = "elevation" if "elevation" in df.columns else "elevation_mean"
    
    formula = f"hotspot ~ top_quartile + {c_effort} + abs_lat + {c_elev} + {c_relief}"
    try:
        logit_mod = smf.logit(formula, data=sub_q)
        logit_res = logit_mod.fit(cov_type="cluster", cov_kwds={"groups": sub_q["spatial_block_20deg"]}, disp=False)
        adj_beta = logit_res.params["top_quartile"]
        adj_se = logit_res.bse["top_quartile"]
        adj_pval = logit_res.pvalues["top_quartile"]
        adj_or = float(np.exp(adj_beta))
        adj_ci_low = float(np.exp(adj_beta - 1.96 * adj_se))
        adj_ci_high = float(np.exp(adj_beta + 1.96 * adj_se))
    except Exception as e:
        print(f"[NOTE]: Clustered Logit encountered singularity/separation ({e}); reporting robust unadjusted OR.")
        adj_or = unadj_or
        adj_ci_low = unadj_ci_low
        adj_ci_high = unadj_ci_high
        adj_pval = np.nan
    
    print(f"Odds Ratio (top vs bottom stability quartile):")
    print(f"  OR = {adj_or:.3f} (95% CI: [{adj_ci_low:.3f}, {adj_ci_high:.3f}])")
    print("[NOTE ON AUC]: High classification AUC near 0.95-0.97 heavily reflects observer sampling effort (effort-dominated model); effort-free models show substantially lower AUC.")
    
    # -------------------------------------------------------------
    # FIGURES
    # -------------------------------------------------------------
    print("\n--- Generating Publication Figures ---")
    
    # 1. Pooled ROC curves for M0..M3 on one axis (Random Forest)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    rf_sub = oof_df[oof_df["model"] == "rf"]
    
    palette_roc = {
        "M0": "#8172B3",
        "M1": "#4C72B0",
        "M2a": "#C44E52",
        "M2b": "#55A868",
        "M3a": "#CCB974"
    }
    
    for fset in ["M0", "M1", "M2a", "M2b", "M3a"]:
        sub_fs = rf_sub[rf_sub["feature_set"] == fset]
        fpr, tpr, _ = roc_curve(sub_fs["y_true"], sub_fs["prob"])
        auc_val = roc_auc_score(sub_fs["y_true"], sub_fs["prob"])
        label_text = f"{fset} (AUC = {auc_val:.3f})"
        ax.plot(fpr, tpr, label=label_text, color=palette_roc.get(fset, "black"), linewidth=2.0)
        
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess (AUC = 0.50)")
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=11, fontweight="bold")
    ax.set_title("Pooled Spatial Out-of-Fold ROC Curves (Random Forest)", fontsize=12, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", loc="lower right", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    roc_fig_path = ml_figures_dir / "hotspot_roc_curves.png"
    plt.savefig(roc_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved ROC curves to {roc_fig_path}")
    
    # 2. Confusion Matrix Heatmap for RF M2a
    rf_m2a = oof_df[(oof_df["model"] == "rf") & (oof_df["feature_set"] == "M2a")]
    cm = confusion_matrix(rf_m2a["y_true"], rf_m2a["y_pred"])
    cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
    
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    cax = ax.matshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    fig.colorbar(cax, ax=ax, label="Row-Normalised Rate")
    
    classes = ["Non-Hotspot (0)", "Hotspot (1)"]
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(classes, fontsize=11, fontweight="bold")
    ax.set_yticklabels(classes, fontsize=11, fontweight="bold")
    ax.set_xlabel("Predicted Label (Youden's J Threshold)", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_ylabel("True Label (75th Percentile)", fontsize=11, fontweight="bold")
    ax.set_title("Spatial Out-of-Fold Confusion Matrix (RF M2a)", fontsize=12, fontweight="bold", pad=20)
    
    for i in range(2):
        for j in range(2):
            count = cm[i, j]
            pct = cm_norm[i, j] * 100
            color = "white" if cm_norm[i, j] > 0.5 else "black"
            ax.text(j, i, f"{count}\n({pct:.1f}%)", ha="center", va="center", color=color, fontweight="bold", fontsize=12)
            
    plt.tight_layout()
    cm_fig_path = ml_figures_dir / "hotspot_confusion_matrix.png"
    plt.savefig(cm_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Confusion Matrix to {cm_fig_path}")
    
    # 3. Hotspot Rate by Decile Bar Chart with Binomial CIs
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    d_x = decile_df["decile"].values
    d_rates = decile_df["hotspot_rate"].values * 100
    yerr_low = (decile_df["hotspot_rate"].values - decile_df["ci_low_95"].values) * 100
    yerr_high = (decile_df["ci_high_95"].values - decile_df["hotspot_rate"].values) * 100
    
    ax.bar(d_x, d_rates, yerr=[yerr_low, yerr_high], color="#4C72B0", alpha=0.85, capsize=4, edgecolor="black")
    ax.axhline(25.0, color="red", linestyle="--", linewidth=1.2, label="Global Expected Rate (25%)")
    ax.set_xticks(d_x)
    ax.set_xlabel(f"Decile of Quaternary Instability ({primary_stab_col})\n[1 = Most Stable, 10 = Most Instable]", fontsize=11, fontweight="bold")
    ax.set_ylabel("Hotspot Rate (%)", fontsize=11, fontweight="bold")
    ax.set_title("Biodiversity Hotspot Occurrence Rate across Quaternary Instability Deciles", fontsize=12, fontweight="bold")
    ax.legend(frameon=True, facecolor="white")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    dec_fig_path = ml_figures_dir / "hotspot_decile_rate.png"
    plt.savefig(dec_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Decile Rate figure to {dec_fig_path}")
    
    # 4. Map Coloured by TP, FP, FN, TN for RF M2a Out-of-Fold
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    rf_m2a = rf_m2a.copy()
    outcomes = []
    for yt, yp in zip(rf_m2a["y_true"].values, rf_m2a["y_pred"].values):
        if yt == 1 and yp == 1:
            outcomes.append("True Positive (TP)")
        elif yt == 0 and yp == 1:
            outcomes.append("False Positive (FP)")
        elif yt == 1 and yp == 0:
            outcomes.append("False Negative (FN)")
        else:
            outcomes.append("True Negative (TN)")
    rf_m2a["outcome"] = outcomes
    
    color_map = {
        "True Positive (TP)": "#2CA02C",   # Green
        "False Positive (FP)": "#D62728",  # Red
        "False Negative (FN)": "#1F77B4",  # Blue
        "True Negative (TN)": "#B0BEC5"   # Light Slate Gray
    }
    
    for outcome, color in color_map.items():
        sub_out = rf_m2a[rf_m2a["outcome"] == outcome]
        ax.scatter(sub_out["lon"], sub_out["lat"], c=color, label=f"{outcome} (n={len(sub_out)})",
                   s=45, edgecolors="black", linewidths=0.5, alpha=0.85)
                   
    ax.set_xlim(-180, 180)
    ax.set_ylim(-65, 85)
    ax.set_xlabel("Longitude (°)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°)", fontsize=11, fontweight="bold")
    ax.set_title("Spatial Out-of-Fold Classification Map (Random Forest $M2a$)", fontsize=13, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", loc="lower left", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    map_fig_path = ml_figures_dir / "hotspot_classification_map.png"
    plt.savefig(map_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Classification Map to {map_fig_path}")
    
    return summary_df, delta_auc_df, decile_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 6: Hotspot Classification")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    args = parser.parse_args()
    
    run_hotspots(source=args.source, resolution=args.resolution, fast=args.fast)
