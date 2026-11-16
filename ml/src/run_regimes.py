"""
run_regimes.py
--------------
Palaeoclimate Stability Regime Discovery, Unsupervised Clustering,
Cluster Stability Evaluation (ARI), Regime Characterisation,
Controlled Significance Testing (Kruskal-Wallis, Pairwise MWU, Cluster-Robust OLS),
and Leakage-Free Out-of-Fold Predictive Evaluation.
Stage 7.

Clustering strictly uses palaeoclimate stability features (never coordinates, effort, or richness).
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
from scipy.stats import skew, kruskal, mannwhitneyu
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, adjusted_rand_score
from statsmodels.stats.multitest import multipletests
import statsmodels.formula.api as smf

from ml.src.config import load_config
from ml.src.data import load_dataset
from ml.src.cv import spatial_outer_folds
from ml.src.models import get_regressor
from ml.src.metrics import calc_r2

warnings.filterwarnings("ignore")


def preprocess_stability_features(df_stab: pd.DataFrame, imputer=None, scaler=None, skewed_cols=None):
    """
    Median-impute, log-transform (log1p after shifting) features with |skew| > 1.0, and StandardScaler.
    Can fit or transform.
    """
    cols = df_stab.columns.tolist()
    is_fit = (imputer is None)
    
    if is_fit:
        imputer = SimpleImputer(strategy="median")
        X_imp = imputer.fit_transform(df_stab)
        
        skewed_cols = {}
        for idx, c in enumerate(cols):
            s = skew(X_imp[:, idx])
            if abs(s) > 1.0:
                min_v = float(np.min(X_imp[:, idx]))
                shift = abs(min_v) + 1e-4 if min_v <= 0 else 0.0
                skewed_cols[c] = shift
                X_imp[:, idx] = np.log1p(X_imp[:, idx] + shift)
                
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_imp)
        return X_scaled, imputer, scaler, skewed_cols
    else:
        X_imp = imputer.transform(df_stab)
        for idx, c in enumerate(cols):
            if c in skewed_cols:
                shift = skewed_cols[c]
                X_imp[:, idx] = np.log1p(X_imp[:, idx] + shift)
        X_scaled = scaler.transform(X_imp)
        return X_scaled


def assign_descriptive_regime_name(centroid_row, all_centroids_df):
    """
    Assign a descriptive name based on centroid values relative to the cluster distributions.
    Evaluates composite instability, temperature anomaly, and precipitation anomaly.
    """
    comp_col = "wc_composite_instability" if "wc_composite_instability" in centroid_row else "pc_composite_instability"
    temp_col = "wc_temp_instability" if "wc_temp_instability" in centroid_row else "pc_temp_instability"
    precip_col = "wc_precip_instability" if "wc_precip_instability" in centroid_row else "pc_precip_instability"
    
    comp_rank = centroid_row.get(comp_col, 0.0)
    temp_rank = centroid_row.get(temp_col, comp_rank)
    precip_rank = centroid_row.get(precip_col, comp_rank)
    
    comp_med = all_centroids_df[comp_col].median() if comp_col in all_centroids_df else comp_rank
    temp_med = all_centroids_df[temp_col].median() if temp_col in all_centroids_df else comp_med
    precip_med = all_centroids_df[precip_col].median() if precip_col in all_centroids_df else comp_med
    
    if comp_rank < comp_med and temp_rank <= temp_med and precip_rank <= precip_med:
        return "High Stability (Minimal Climate Variability)"
    elif temp_rank > temp_med and precip_rank <= precip_med:
        return "Thermal Volatility (High Temperature Anomaly)"
    elif precip_rank > precip_med and temp_rank <= temp_med:
        return "Hydroclimatic Instability (Precipitation Dynamic)"
    elif comp_rank >= comp_med and (temp_rank > temp_med or precip_rank > precip_med):
        return "Severe Compound Instability (Thermal & Hydro Dynamic)"
    else:
        return "Moderate Climate Variability"


def run_regimes(source: str = "paleoclim", resolution: str = "base", fast: bool = False):
    print(f"\n=======================================================")
    print(f"  RUNNING STABILITY REGIME ANALYSIS: source={source}, res={resolution}, fast={fast}")
    print(f"=======================================================\n")
    
    cfg = load_config()
    seed = cfg["seed"]
    
    # Directory setup
    tables_dir = REPO_ROOT / "tables"
    ml_out_dir = REPO_ROOT / "ml" / "outputs" / f"{source}_{resolution}"
    ml_tables_dir = ml_out_dir / "tables"
    ml_figures_dir = ml_out_dir / "figures"
    ml_logs_dir = ml_out_dir / "logs"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    ml_figures_dir.mkdir(parents=True, exist_ok=True)
    ml_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    df, feature_groups, feature_sets = load_dataset(source, resolution)
    df = df.copy()
    
    stab_cols = feature_groups["palaeoclimate"]
    print(f"Clustering strictly using {len(stab_cols)} palaeoclimate stability features: {stab_cols}")
    
    # -------------------------------------------------------------
    # 1. Preprocessing
    # -------------------------------------------------------------
    X_scaled, imputer, scaler, skewed_info = preprocess_stability_features(df[stab_cols])
    print(f"Log-transformed skewed features (|skew| > 1.0): {list(skewed_info.keys())}")
    
    # -------------------------------------------------------------
    # 2. KMeans & GMM Model Selection (k = 2..8)
    # -------------------------------------------------------------
    print("\n--- 2. Evaluating Cluster Solutions (k = 2..8) ---")
    k_range = list(range(2, 9))
    selection_rows = []
    
    for k in k_range:
        n_init = 5 if fast else 20
        km = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X_scaled)
        sil = float(silhouette_score(X_scaled, km.labels_))
        
        counts = np.bincount(km.labels_)
        min_cluster_size = int(np.min(counts))
        min_cluster_pct = float(min_cluster_size / len(X_scaled))
        
        gmm = GaussianMixture(n_components=k, covariance_type="full", random_state=seed).fit(X_scaled)
        bic = float(gmm.bic(X_scaled))
        
        selection_rows.append({
            "source": source,
            "resolution": resolution,
            "k": k,
            "inertia": float(km.inertia_),
            "silhouette": sil,
            "min_cluster_size": min_cluster_size,
            "min_cluster_pct": round(min_cluster_pct, 4),
            "gmm_bic": bic
        })
        print(f"  k={k}: Inertia={km.inertia_:.1f} | Silhouette={sil:.4f} | MinClusterPct={min_cluster_pct*100:.1f}% | GMM BIC={bic:.1f}")
        
    k_df = pd.DataFrame(selection_rows)
    k_sel_csv = tables_dir / "regime_k_selection.csv"
    ml_k_sel_csv = ml_tables_dir / "regime_k_selection.csv"
    k_df.to_csv(k_sel_csv, index=False)
    k_df.to_csv(ml_k_sel_csv, index=False)
    print(f"[OK] Saved k selection table to {k_sel_csv} and {ml_k_sel_csv}")
    
    # Selection rule: best silhouette within 3 to 6 clusters with minimum 5% cluster size
    valid_k = k_df[(k_df["k"] >= 3) & (k_df["k"] <= 6) & (k_df["min_cluster_pct"] >= 0.05)]
    if len(valid_k) == 0:
        valid_k = k_df[(k_df["min_cluster_pct"] >= 0.05)]
    if len(valid_k) == 0:
        valid_k = k_df[(k_df["k"] >= 3) & (k_df["k"] <= 6)]
        
    best_row = valid_k.loc[valid_k["silhouette"].idxmax()]
    k_chosen = int(best_row["k"])
    sil_val = float(best_row["silhouette"])
    
    print(f"\nSelection Rule: Maximum silhouette within k in [3, 6] with min cluster size >= 5% of cells.")
    print(f"Selected k = {k_chosen} (Silhouette = {sil_val:.4f}, Min Cluster Pct = {best_row['min_cluster_pct']*100:.1f}%, GMM BIC = {best_row['gmm_bic']:.1f})")
    
    # Honest silhouette reporting
    if sil_val < 0.25:
        print(f"[NOTE ON REGIMES]: Silhouette is {sil_val:.4f} (< 0.25). Regimes reflect diffuse, continuous gradients rather than discrete, strongly separated clusters.")
    else:
        print(f"[NOTE ON REGIMES]: Silhouette is {sil_val:.4f} (>= 0.25). Regimes show moderate natural clustering.")
    
    # Plot Elbow, Silhouette, and BIC
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5), dpi=300)
    
    ax1.plot(k_df["k"], k_df["inertia"], marker="o", color="#4C72B0", linewidth=2.0)
    ax1.axvline(k_chosen, color="red", linestyle="--", alpha=0.7, label=f"Chosen k={k_chosen}")
    ax1.set_xlabel("Number of Clusters (k)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Inertia (Within-Cluster Sum of Squares)", fontsize=11, fontweight="bold")
    ax1.set_title("Elbow Method (Inertia)", fontsize=12, fontweight="bold")
    ax1.legend(frameon=True, facecolor="white")
    ax1.grid(True, linestyle=":", alpha=0.6)
    
    ax2.plot(k_df["k"], k_df["silhouette"], marker="s", color="#55A868", linewidth=2.0)
    ax2.axvline(k_chosen, color="red", linestyle="--", alpha=0.7, label=f"Chosen k={k_chosen}")
    ax2.set_xlabel("Number of Clusters (k)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Silhouette Score", fontsize=11, fontweight="bold")
    ax2.set_title("Silhouette Score Profile", fontsize=12, fontweight="bold")
    ax2.legend(frameon=True, facecolor="white")
    ax2.grid(True, linestyle=":", alpha=0.6)
    
    ax3.plot(k_df["k"], k_df["gmm_bic"], marker="^", color="#C44E52", linewidth=2.0)
    ax3.axvline(k_chosen, color="red", linestyle="--", alpha=0.7, label=f"Chosen k={k_chosen}")
    ax3.set_xlabel("Number of Clusters (k)", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Bayesian Information Criterion (BIC)", fontsize=11, fontweight="bold")
    ax3.set_title("Gaussian Mixture BIC", fontsize=12, fontweight="bold")
    ax3.legend(frameon=True, facecolor="white")
    ax3.grid(True, linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    k_fig_path = ml_figures_dir / "regime_k_selection.png"
    plt.savefig(k_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved k selection figure to {k_fig_path}")
    
    # -------------------------------------------------------------
    # 3. Cluster Stability Evaluation (Adjusted Rand Index)
    # -------------------------------------------------------------
    print("\n--- 3. Cluster Stability (Adjusted Rand Index across 10 Seeds) ---")
    base_km = KMeans(n_clusters=k_chosen, n_init=20, random_state=seed).fit(X_scaled)
    df["regime_cluster"] = base_km.labels_
    
    ari_seeds = [101, 202, 303, 404, 505, 606, 707, 808, 909, 1001]
    ari_scores = []
    for s in ari_seeds:
        km_s = KMeans(n_clusters=k_chosen, n_init=10 if fast else 20, random_state=s).fit(X_scaled)
        ari_scores.append(float(adjusted_rand_score(base_km.labels_, km_s.labels_)))
        
    mean_ari = float(np.mean(ari_scores))
    std_ari = float(np.std(ari_scores))
    print(f"Mean Adjusted Rand Index (ARI): {mean_ari:.4f} ± {std_ari:.4f}")
    if mean_ari < 0.8:
        print("[WARNING]: Cluster stability is low (mean ARI < 0.8). Flagged as sensitive to initialization.")
    else:
        print("[OK]: Clustering solution is highly stable (mean ARI >= 0.8).")
        
    # -------------------------------------------------------------
    # 4. Describe Regimes: Centroid Table & Spatial Map
    # -------------------------------------------------------------
    print("\n--- 4. Describing Stability Regimes & Centroids ---")
    centroid_rows = []
    
    # Compute centroid in original units
    regime_orig_means = df.groupby("regime_cluster")[stab_cols].mean()
    cell_counts = df["regime_cluster"].value_counts().to_dict()
    
    for c_id in range(k_chosen):
        row_dict = regime_orig_means.loc[c_id].to_dict()
        name = assign_descriptive_regime_name(row_dict, regime_orig_means)
        row_dict["regime_cluster"] = c_id
        row_dict["regime_name"] = f"Regime {c_id}: {name}"
        row_dict["n_cells"] = cell_counts.get(c_id, 0)
        row_dict["cell_pct"] = (cell_counts.get(c_id, 0) / len(df)) * 100
        centroid_rows.append(row_dict)
        print(f"  Regime {c_id}: {name:48s} (n={cell_counts.get(c_id, 0):2d}, {row_dict['cell_pct']:.1f}%)")
        
    cent_df = pd.DataFrame(centroid_rows)
    # Order columns
    first_cols = ["regime_cluster", "regime_name", "n_cells", "cell_pct"]
    cent_df = cent_df[first_cols + [c for c in cent_df.columns if c not in first_cols]]
    
    cent_csv = tables_dir / "regime_centroids.csv"
    ml_cent_csv = ml_tables_dir / "regime_centroids.csv"
    cent_df.to_csv(cent_csv, index=False)
    cent_df.to_csv(ml_cent_csv, index=False)
    print(f"[OK] Saved Centroid table to {cent_csv} and {ml_cent_csv}")
    
    # Map cluster assignments to named regimes in df
    regime_map_dict = {r["regime_cluster"]: r["regime_name"] for r in centroid_rows}
    df["regime"] = df["regime_cluster"].map(regime_map_dict)
    
    # Spatial Map of Regimes
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    palette_regimes = ["#4C72B0", "#55A868", "#C44E52", "#8172B3", "#CCB974", "#64B5CD"]
    
    for c_id in range(k_chosen):
        sub_c = df[df["regime_cluster"] == c_id]
        label_txt = f"{regime_map_dict[c_id]} (n={len(sub_c)})"
        ax.scatter(sub_c["lon"], sub_c["lat"], color=palette_regimes[c_id % len(palette_regimes)],
                   label=label_txt, s=50, edgecolors="black", linewidths=0.5, alpha=0.85)
                   
    ax.set_xlim(-180, 180)
    ax.set_ylim(-65, 85)
    ax.set_xlabel("Longitude (°)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°)", fontsize=11, fontweight="bold")
    ax.set_title(f"Global Distribution of Quaternary Climate Stability Regimes (k={k_chosen})", fontsize=13, fontweight="bold")
    ax.legend(frameon=True, facecolor="white", loc="lower left", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)
    
    plt.tight_layout()
    map_fig_path = ml_figures_dir / "regime_spatial_map.png"
    plt.savefig(map_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Regime Spatial Map to {map_fig_path}")
    
    # -------------------------------------------------------------
    # 5. Does Richness Differ Between Regimes with Effort Controlled?
    # -------------------------------------------------------------
    print("\n--- 5. Statistical Testing of Richness Differences Across Regimes ---")
    
    # (a) Kruskal-Wallis & Pairwise Mann-Whitney U with Holm correction
    groups_y = [df[df["regime_cluster"] == c_id]["y"].values for c_id in range(k_chosen)]
    kw_stat, kw_pval = kruskal(*groups_y)
    print(f"Kruskal-Wallis H-test on ln(1+richness) across regimes: H = {kw_stat:.3f}, p = {kw_pval:.4e}")
    
    pairwise_rows = []
    pairs = []
    p_raw_list = []
    for i in range(k_chosen):
        for j in range(i + 1, k_chosen):
            u_stat, p_val = mannwhitneyu(groups_y[i], groups_y[j], alternative="two-sided")
            pairs.append((i, j, u_stat, p_val))
            p_raw_list.append(p_val)
            
    # Holm correction
    _, p_holm, _, _ = multipletests(p_raw_list, method="holm")
    for (i, j, u_stat, p_raw), p_adj in zip(pairs, p_holm):
        pairwise_rows.append({
            "source": source,
            "resolution": resolution,
            "regime_A": f"Regime {i}",
            "regime_B": f"Regime {j}",
            "mann_whitney_u": float(u_stat),
            "p_raw": float(p_raw),
            "p_holm_adjusted": float(p_adj),
            "significant_05": bool(p_adj < 0.05)
        })
        
    pair_df = pd.DataFrame(pairwise_rows)
    pair_csv = tables_dir / "regime_kruskal_pairwise.csv"
    ml_pair_csv = ml_tables_dir / "regime_kruskal_pairwise.csv"
    pair_df.to_csv(pair_csv, index=False)
    pair_df.to_csv(ml_pair_csv, index=False)
    print(f"[OK] Saved pairwise test table to {pair_csv} and {ml_pair_csv}")
    
    # (b) Statsmodels OLS with 20° block-clustered standard errors
    c_effort = "log_effort" if "log_effort" in df.columns else "log_n"
    c_lat = "lat" if "lat" in df.columns else "cell_lat"
    c_relief = "relief" if "relief" in df.columns else "topographic_heterogeneity"
    c_elev = "elevation" if "elevation" in df.columns else "elevation_mean"
    
    base_m1_formula = f"y ~ {c_effort} + abs_lat + {c_elev} + {c_relief}"
    regime_formula = f"y ~ C(regime_cluster) + {c_effort} + abs_lat + {c_elev} + {c_relief}"
    
    ols_m1 = smf.ols(base_m1_formula, data=df).fit(cov_type="cluster", cov_kwds={"groups": df["spatial_block_20deg"]})
    ols_regime = smf.ols(regime_formula, data=df).fit(cov_type="cluster", cov_kwds={"groups": df["spatial_block_20deg"]})
    
    delta_r2_ols = float(ols_regime.rsquared - ols_m1.rsquared)
    
    # Joint Wald test on all regime dummies
    regime_dummy_terms = [c for c in ols_regime.params.index if "C(regime_cluster)" in c]
    wald_test = ols_regime.wald_test(regime_dummy_terms)
    wald_stat = float(np.squeeze(wald_test.statistic))
    wald_pval = float(np.squeeze(wald_test.pvalue))
    
    print(f"\nOLS with Cluster-Robust Standard Errors by Block:")
    print(f"  Base M1 R2: {ols_m1.rsquared:.4f} | M1 + Regime R2: {ols_regime.rsquared:.4f} (ΔR2 = {delta_r2_ols:+.4f})")
    print(f"  Joint Wald test on regime dummies: F/Chi2 = {wald_stat:.3f}, p = {wald_pval:.4f}")
    
    coef_rows = []
    conf_int = ols_regime.conf_int()
    for term in ols_regime.params.index:
        coef_rows.append({
            "source": source,
            "resolution": resolution,
            "term": term,
            "coef": float(ols_regime.params[term]),
            "std_err": float(ols_regime.bse[term]),
            "z_stat": float(ols_regime.tvalues[term]),
            "p_val": float(ols_regime.pvalues[term]),
            "ci_low_95": float(conf_int.loc[term, 0]),
            "ci_high_95": float(conf_int.loc[term, 1]),
            "delta_r2_joint": delta_r2_ols if "C(regime_cluster)" in term else np.nan,
            "wald_stat_joint": wald_stat if "C(regime_cluster)" in term else np.nan,
            "wald_pval_joint": wald_pval if "C(regime_cluster)" in term else np.nan
        })
        
    coef_df = pd.DataFrame(coef_rows)
    coef_csv = tables_dir / "regime_regression_coefficients.csv"
    ml_coef_csv = ml_tables_dir / "regime_regression_coefficients.csv"
    coef_df.to_csv(coef_csv, index=False)
    coef_df.to_csv(ml_coef_csv, index=False)
    print(f"[OK] Saved regime regression coefficients to {coef_csv} and {ml_coef_csv}")
    
    # (c) Boxplots of M1 out-of-fold residuals by regime
    oof_path = tables_dir / "oof_predictions.csv"
    if not oof_path.exists():
        oof_path = ml_tables_dir / "oof_predictions.csv"
    assert oof_path.exists(), f"Could not find oof_predictions.csv at {oof_path}!"
    oof_df = pd.read_csv(oof_path)
    
    # Select Repeat 0, model rf, feature_set M1
    rf_m1_oof = oof_df[(oof_df["repeat"] == 0) & (oof_df["model"] == "rf") & (oof_df["feature_set"] == "M1")].sort_values("cell_idx").reset_index(drop=True)
    df_sorted = df.sort_values("cell_idx" if "cell_idx" in df.columns else df.index.name or df.columns[0]).reset_index(drop=True)
    
    rf_m1_oof["residual"] = rf_m1_oof["y_true"] - rf_m1_oof["y_pred"]
    rf_m1_oof["regime_cluster"] = df["regime_cluster"].values
    rf_m1_oof["regime_name"] = rf_m1_oof["regime_cluster"].map(regime_map_dict)
    
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    data_by_regime = [rf_m1_oof[rf_m1_oof["regime_cluster"] == c_id]["residual"].values for c_id in range(k_chosen)]
    labels_box = [f"Regime {c_id}\n(n={len(data_by_regime[c_id])})" for c_id in range(k_chosen)]
    
    bp = ax.boxplot(data_by_regime, patch_artist=True, labels=labels_box)
    for patch, color in zip(bp["boxes"], palette_regimes):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
        
    ax.axhline(0, color="black", linestyle="--", linewidth=1.0)
    ax.set_ylabel(r"M1 Out-of-Fold Residual ($y_{\mathrm{true}} - y_{\mathrm{pred}}$)", fontsize=11, fontweight="bold")
    ax.set_title("M1 Control Residuals across Quaternary Climate Regimes (RF)", fontsize=12, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    box_fig_path = ml_figures_dir / "regime_residual_boxplots.png"
    plt.savefig(box_fig_path, dpi=300)
    plt.close()
    print(f"[OK] Saved Residual Boxplot to {box_fig_path}")
    
    # -------------------------------------------------------------
    # 6. Leakage-Free Out-of-Fold Predictive Evaluation
    # -------------------------------------------------------------
    print("\n--- 6. Out-of-Fold Predictive Check: Adding Assigned Regimes to M1 ---")
    reuse_p6 = (resolution == "base")
    folds, groups = spatial_outer_folds(df, k=5, seed=seed, offset=0.0, reuse_phase6=reuse_p6)
    
    f_cols_m1 = feature_sets["M1"]
    models_oof_test = ["rf", "hgb"]
    
    # Store predictions
    oof_m1_preds = {m: np.zeros(len(df)) for m in models_oof_test}
    oof_regime_preds = {m: np.zeros(len(df)) for m in models_oof_test}
    
    for f_idx, (tr, te) in enumerate(folds):
        fold_num = f_idx + 1
        
        # 1. Fit clustering on training cells only
        X_tr_stab = df.iloc[tr][stab_cols]
        X_te_stab = df.iloc[te][stab_cols]
        
        X_tr_s_scaled, imp_f, sc_f, sk_f = preprocess_stability_features(X_tr_stab)
        X_te_s_scaled = preprocess_stability_features(X_te_stab, imputer=imp_f, scaler=sc_f, skewed_cols=sk_f)
        
        km_f = KMeans(n_clusters=k_chosen, n_init=10 if fast else 20, random_state=seed + fold_num).fit(X_tr_s_scaled)
        tr_cluster = km_f.labels_
        te_cluster = km_f.predict(X_te_s_scaled)
        
        # One-hot encode regime clusters
        tr_dummies = pd.get_dummies(tr_cluster, prefix="regime", drop_first=True, dtype=float)
        te_dummies = pd.get_dummies(te_cluster, prefix="regime", drop_first=True, dtype=float)
        
        # Ensure all columns exist in test
        for col in tr_dummies.columns:
            if col not in te_dummies.columns:
                te_dummies[col] = 0.0
        te_dummies = te_dummies[tr_dummies.columns]
        
        X_tr_m1 = df.iloc[tr][f_cols_m1].reset_index(drop=True)
        X_te_m1 = df.iloc[te][f_cols_m1].reset_index(drop=True)
        y_tr = df.iloc[tr]["y"].reset_index(drop=True)
        y_te = df.iloc[te]["y"].reset_index(drop=True)
        
        X_tr_plus = pd.concat([X_tr_m1, tr_dummies], axis=1)
        X_te_plus = pd.concat([X_te_m1, te_dummies], axis=1)
        
        for m in models_oof_test:
            # Model with M1 only
            pipe_m1 = get_regressor(m, random_state=seed + fold_num)
            pipe_m1.fit(X_tr_m1, y_tr)
            oof_m1_preds[m][te] = pipe_m1.predict(X_te_m1)
            
            # Model with M1 + Regimes
            pipe_reg = get_regressor(m, random_state=seed + fold_num)
            pipe_reg.fit(X_tr_plus, y_tr)
            oof_regime_preds[m][te] = pipe_reg.predict(X_te_plus)
            
    # Compute pooled delta R2 and 95% block-bootstrap CIs
    unique_blocks = df["spatial_block_20deg"].unique()
    n_boot = 200 if fast else 1000
    rng_boot = np.random.default_rng(seed)
    
    delta_r2_records = []
    
    for m in models_oof_test:
        r2_base = calc_r2(df["y"].values, oof_m1_preds[m])
        r2_plus = calc_r2(df["y"].values, oof_regime_preds[m])
        delta_r2 = r2_plus - r2_base
        
        boot_deltas = []
        for _ in range(n_boot):
            boot_blks = rng_boot.choice(unique_blocks, size=len(unique_blocks), replace=True)
            boot_idx = []
            for b in boot_blks:
                boot_idx.extend(df[df["spatial_block_20deg"] == b].index.tolist())
            y_b = df.loc[boot_idx, "y"].values
            r2_b1 = calc_r2(y_b, oof_m1_preds[m][boot_idx])
            r2_b2 = calc_r2(y_b, oof_regime_preds[m][boot_idx])
            boot_deltas.append(r2_b2 - r2_b1)
            
        ci_l = float(np.percentile(boot_deltas, 2.5))
        ci_u = float(np.percentile(boot_deltas, 97.5))
        
        delta_r2_records.append({
            "source": source,
            "resolution": resolution,
            "model": m,
            "r2_m1_base": r2_base,
            "r2_m1_plus_regimes": r2_plus,
            "delta_r2": delta_r2,
            "boot_ci_low_95": ci_l,
            "boot_ci_high_95": ci_u
        })
        print(f"  {m:5s} | M1 R2: {r2_base:.4f} | M1+Regimes R2: {r2_plus:.4f} | ΔR2: {delta_r2:+.4f} (95% CI: [{ci_l:+.4f}, {ci_u:+.4f}])")
        
    delta_r2_df = pd.DataFrame(delta_r2_records)
    delta_r2_csv = tables_dir / "regime_delta_r2.csv"
    ml_delta_r2_csv = ml_tables_dir / "regime_delta_r2.csv"
    delta_r2_df.to_csv(delta_r2_csv, index=False)
    delta_r2_df.to_csv(ml_delta_r2_csv, index=False)
    print(f"[OK] Saved Regime Delta R2 table to {delta_r2_csv} and {ml_delta_r2_csv}")
    
    return k_chosen, mean_ari, coef_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 7: Stability Regime Analysis")
    parser.add_argument("--source", type=str, default="paleoclim", choices=["paleoclim", "worldclim"])
    parser.add_argument("--resolution", type=str, default="base", choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    args = parser.parse_args()
    
    run_regimes(source=args.source, resolution=args.resolution, fast=args.fast)
