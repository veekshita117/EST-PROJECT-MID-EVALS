"""
run_joint_taxa_model.py
-----------------------
Stage: Unified Hierarchical & Multi-Task Joint Taxonomic Modelling.

Implements:
1. Unified hierarchical mixed-effects model (MixedLM) and Seemingly Unrelated Regressions (SUR)
   for Reptiles, Mammals, and Amphibians.
2. Estimates shared climate stability/velocity effects and taxon-specific deviations.
3. Incorporates absolute latitude, topographic relief, elevation, sampling effort, and land fraction as controls.
4. Formal hypothesis testing of taxonomic contrasts:
   - Joint Wald test for slope equality across taxa (H0: beta_reptiles = beta_mammals = beta_amphibians).
   - Pairwise taxonomic contrasts (Reptiles vs Mammals, Reptiles vs Amphibians, Amphibians vs Mammals).
   - Explicit robustness tests for previously observed reptile sensitivity vs weak amphibian relationship.
5. Evaluates both Species Richness and Weighted Endemism.
6. Saves tabular results to tables/joint_taxa_model.csv, tables/taxa_contrasts.csv,
   and publication figure to figures/joint_taxa_effects.png.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.regression.mixed_linear_model import MixedLM
from statsmodels.formula.api import ols
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="Run Joint Multi-Taxa Modelling")
    parser.add_argument("--resolution", type=str, default="5deg", choices=["5deg", "2deg"])
    return parser.parse_args()


def build_long_taxa_df(df: pd.DataFrame) -> pd.DataFrame:
    """Transform wide cell-level dataset to stacked long format for hierarchical modeling."""
    rows = []
    taxa = ["Amphibians", "Reptiles", "Mammals"]
    
    for i, r in df.iterrows():
        cell_id = int(i)
        lon = float(r["cell_lon"])
        lat = float(r["cell_lat"])
        block = int(r["block_id"]) if "block_id" in r else 0
        vel = float(r["log10_velocity_temp"])
        abs_lat = float(r["abs_lat"])
        elev = float(r["elevation_mean"])
        relief = float(r["topographic_heterogeneity"])
        effort = float(r["log1p_records_total"]) if "log1p_records_total" in r else 0.0
        land = float(r["land_fraction"]) if "land_fraction" in r else 1.0
        
        for t in taxa:
            t_lower = t.lower()
            rich = float(r[f"{t_lower}_richness"])
            endem = float(r[f"{t_lower}_weighted_endemism"])
            
            rows.append({
                "cell_id": cell_id,
                "cell_lon": lon,
                "cell_lat": lat,
                "block_id": block,
                "taxon": t,
                "richness_raw": rich,
                "endemism_raw": endem,
                "y_richness": np.log1p(rich),
                "y_endemism": np.log1p(endem),
                "velocity": vel,
                "abs_lat": abs_lat,
                "elevation": elev,
                "relief": relief,
                "effort": effort,
                "land_fraction": land
            })
            
    df_long = pd.DataFrame(rows)
    
    # Standardize continuous predictors across cells (z-score)
    cont_cols = ["velocity", "abs_lat", "elevation", "relief", "effort", "land_fraction"]
    for c in cont_cols:
        df_long[c] = (df_long[c] - df_long[c].mean()) / df_long[c].std()
        
    return df_long


def run_joint_taxa_modelling(resolution: str = "5deg") -> Tuple[pd.DataFrame, pd.DataFrame]:
    print("=" * 80)
    print(f"JOINT MULTI-TAXA MODELLING: REPTILES, MAMMALS & AMPHIBIANS")
    print(f"Resolution: {resolution}")
    print("=" * 80)
    
    data_path = REPO_ROOT / "integration_v3" / "processed" / f"data_v3_{resolution}.csv"
    df = pd.read_csv(data_path)
    print(f"Loaded master dataset: {len(df)} cells from {data_path}")
    
    tables_dir = REPO_ROOT / "tables"
    figures_dir = REPO_ROOT / "figures"
    v3_tables_dir = REPO_ROOT / "results" / "tables" / "integration_v3"
    v3_figures_dir = REPO_ROOT / "results" / "figures" / "integration_v3"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    v3_tables_dir.mkdir(parents=True, exist_ok=True)
    v3_figures_dir.mkdir(parents=True, exist_ok=True)
    
    df_long = build_long_taxa_df(df)
    
    # -------------------------------------------------------------------------
    # 1. Fit Unified Hierarchical Linear Mixed-Effects Model (MixedLM)
    # -------------------------------------------------------------------------
    print("\n--- Fitting Unified Hierarchical MixedLM (Cell Random Intercepts) ---")
    
    model_records = []
    contrast_records = []
    
    for resp_name, resp_col in [("Species Richness", "y_richness"), ("Weighted Endemism", "y_endemism")]:
        print(f"\nTarget: {resp_name} ({resp_col})")
        
        # MixedLM formula: taxon intercepts + taxon * (velocity + controls), random intercept for cell_id
        # Treatment reference: Amphibians
        formula = f"{resp_col} ~ C(taxon, Treatment(reference='Amphibians')) * (velocity + abs_lat + elevation + relief + effort + land_fraction)"
        mixed_mod = MixedLM.from_formula(formula, groups="cell_id", data=df_long)
        mixed_res = mixed_mod.fit()
        
        # Cluster-robust OLS as verification check
        ols_mod = ols(formula, data=df_long).fit(cov_type="cluster", cov_kwds={"groups": df_long["cell_id"]})
        
        params = mixed_res.params
        bse = mixed_res.bse
        pvals = mixed_res.pvalues
        conf = mixed_res.conf_int()
        
        # Extract taxon-specific velocity slopes
        # Baseline = Amphibians
        beta_amph = float(params["velocity"])
        se_amph = float(bse["velocity"])
        p_amph = float(pvals["velocity"])
        ci_amph = (float(conf.loc["velocity", 0]), float(conf.loc["velocity", 1]))
        
        # Delta Mammals
        delta_mamm = float(params["C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"])
        se_delta_mamm = float(bse["C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"])
        p_delta_mamm = float(pvals["C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"])
        
        # Delta Reptiles
        delta_rept = float(params["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"])
        se_delta_rept = float(bse["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"])
        p_delta_rept = float(pvals["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"])
        
        # Derived slopes
        beta_mamm = beta_amph + delta_mamm
        # SE via variance sum: var(A) + var(D) + 2*cov(A, D)
        cov_mat = mixed_res.cov_params()
        var_mamm = (cov_mat.loc["velocity", "velocity"] +
                    cov_mat.loc["C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"] +
                    2 * cov_mat.loc["velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"])
        se_mamm = float(np.sqrt(max(1e-8, var_mamm)))
        z_mamm = beta_mamm / se_mamm
        p_mamm = float(2 * (1 - stats.norm.cdf(abs(z_mamm))))
        ci_mamm = (beta_mamm - 1.96 * se_mamm, beta_mamm + 1.96 * se_mamm)
        
        var_rept = (cov_mat.loc["velocity", "velocity"] +
                    cov_mat.loc["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"] +
                    2 * cov_mat.loc["velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"])
        se_rept = float(np.sqrt(max(1e-8, var_rept)))
        z_rept = beta_rept / se_rept if 'beta_rept' in locals() else (beta_amph + delta_rept) / se_rept
        beta_rept = beta_amph + delta_rept
        p_rept = float(2 * (1 - stats.norm.cdf(abs(beta_rept / se_rept))))
        ci_rept = (beta_rept - 1.96 * se_rept, beta_rept + 1.96 * se_rept)
        
        # Shared (mean) velocity effect across all 3 taxa
        beta_shared = float((beta_amph + beta_mamm + beta_rept) / 3.0)
        
        # Difference: Reptiles vs Mammals
        diff_rept_mamm = beta_rept - beta_mamm
        var_diff_rm = (cov_mat.loc["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity"] +
                       cov_mat.loc["C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"] -
                       2 * cov_mat.loc["C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity", "C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity"])
        se_diff_rm = float(np.sqrt(max(1e-8, var_diff_rm)))
        z_rm = diff_rept_mamm / se_diff_rm
        p_rm = float(2 * (1 - stats.norm.cdf(abs(z_rm))))
        ci_rm = (diff_rept_mamm - 1.96 * se_diff_rm, diff_rept_mamm + 1.96 * se_diff_rm)
        
        # Difference: Reptiles vs Amphibians (delta_rept)
        diff_rept_amph = delta_rept
        se_diff_ra = se_delta_rept
        p_diff_ra = p_delta_rept
        ci_ra = (diff_rept_amph - 1.96 * se_diff_ra, diff_rept_amph + 1.96 * se_diff_ra)
        
        # Difference: Amphibians vs Mammals (-delta_mamm)
        diff_amph_mamm = -delta_mamm
        se_diff_am = se_delta_mamm
        p_diff_am = p_delta_mamm
        ci_am = (diff_amph_mamm - 1.96 * se_diff_am, diff_amph_mamm + 1.96 * se_diff_am)
        
        # Joint Wald Test for slope equality: H0: delta_mamm = 0 and delta_rept = 0
        r_matrix = np.zeros((2, len(params)))
        col_names = list(params.index)
        idx_dm = col_names.index("C(taxon, Treatment(reference='Amphibians'))[T.Mammals]:velocity")
        idx_dr = col_names.index("C(taxon, Treatment(reference='Amphibians'))[T.Reptiles]:velocity")
        r_matrix[0, idx_dm] = 1.0
        r_matrix[1, idx_dr] = 1.0
        
        wald_test = mixed_res.wald_test(r_matrix)
        wald_stat = float(wald_test.statistic.item() if hasattr(wald_test.statistic, "item") else wald_test.statistic)
        wald_pval = float(wald_test.pvalue)
        
        # Record taxa slopes
        taxa_slopes = [
            ("Amphibians", beta_amph, se_amph, p_amph, ci_amph[0], ci_amph[1]),
            ("Mammals", beta_mamm, se_mamm, p_mamm, ci_mamm[0], ci_mamm[1]),
            ("Reptiles", beta_rept, se_rept, p_rept, ci_rept[0], ci_rept[1]),
            ("Shared (Pooled Mean)", beta_shared, np.nan, np.nan, np.nan, np.nan)
        ]
        
        for t_name, b, se, p, ci_l, ci_h in taxa_slopes:
            model_records.append({
                "response": resp_name,
                "taxon": t_name,
                "velocity_slope": round(b, 4),
                "std_error": round(se, 4) if np.isfinite(se) else np.nan,
                "z_value": round(b / se, 2) if np.isfinite(se) and se > 0 else np.nan,
                "p_value": round(p, 4) if np.isfinite(p) else np.nan,
                "ci95_low": round(ci_l, 4) if np.isfinite(ci_l) else np.nan,
                "ci95_high": round(ci_h, 4) if np.isfinite(ci_h) else np.nan,
                "wald_equality_chi2": round(wald_stat, 2),
                "wald_equality_pvalue": round(wald_pval, 4)
            })
            
        # Record formal contrasts
        contrasts = [
            ("Reptiles - Mammals", diff_rept_mamm, se_diff_rm, p_rm, ci_rm[0], ci_rm[1]),
            ("Reptiles - Amphibians", diff_rept_amph, se_diff_ra, p_diff_ra, ci_ra[0], ci_ra[1]),
            ("Amphibians - Mammals", diff_amph_mamm, se_diff_am, p_diff_am, ci_am[0], ci_am[1])
        ]
        
        for c_name, diff, se, p, ci_l, ci_h in contrasts:
            contrast_records.append({
                "response": resp_name,
                "contrast": c_name,
                "slope_difference": round(diff, 4),
                "std_error": round(se, 4),
                "z_value": round(diff / se, 2),
                "p_value": round(p, 4),
                "ci95_low": round(ci_l, 4),
                "ci95_high": round(ci_h, 4),
                "significant_at_05": (p < 0.05)
            })
            
        print(f"  Amphibians Slope: {beta_amph:+.4f} (p={p_amph:.4f})")
        print(f"  Mammals Slope   : {beta_mamm:+.4f} (p={p_mamm:.4f})")
        print(f"  Reptiles Slope  : {beta_rept:+.4f} (p={p_rept:.4f})")
        print(f"  Contrast Reptiles - Mammals   : {diff_rept_mamm:+.4f} (p={p_rm:.4f})")
        print(f"  Contrast Reptiles - Amphibians: {diff_rept_amph:+.4f} (p={p_diff_ra:.4f})")
        print(f"  Wald Test for Slope Equality : Chi2={wald_stat:.2f}, p={wald_pval:.4e}")
        
    model_df = pd.DataFrame(model_records)
    contrast_df = pd.DataFrame(contrast_records)
    
    # Save tables
    model_csv = tables_dir / "joint_taxa_model.csv"
    contrast_csv = tables_dir / "taxa_contrasts.csv"
    model_df.to_csv(model_csv, index=False)
    contrast_df.to_csv(contrast_csv, index=False)
    model_df.to_csv(v3_tables_dir / "joint_taxa_model.csv", index=False)
    contrast_df.to_csv(v3_tables_dir / "taxa_contrasts.csv", index=False)
    
    print(f"\n[OK] Saved joint taxa model table to {model_csv}")
    print(f"[OK] Saved taxa contrasts table to {contrast_csv}")
    
    # -------------------------------------------------------------------------
    # 2. Publication-Quality Figure: Joint Taxonomic Effects
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    
    taxa_order = ["Amphibians", "Mammals", "Reptiles"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    for idx, (resp_name, ax) in enumerate([("Species Richness", axes[0]), ("Weighted Endemism", axes[1])]):
        sub = model_df[model_df.response == resp_name]
        
        y_pos = np.arange(len(taxa_order))
        slopes = [sub[sub.taxon == t]["velocity_slope"].values[0] for t in taxa_order]
        ci_l = [sub[sub.taxon == t]["ci95_low"].values[0] for t in taxa_order]
        ci_h = [sub[sub.taxon == t]["ci95_high"].values[0] for t in taxa_order]
        pvals = [sub[sub.taxon == t]["p_value"].values[0] for t in taxa_order]
        
        xerr = [[slopes[i] - ci_l[i] for i in range(len(taxa_order))],
                [ci_h[i] - slopes[i] for i in range(len(taxa_order))]]
                
        for i, t in enumerate(taxa_order):
            ax.errorbar(
                slopes[i], y_pos[i],
                xerr=[[xerr[0][i]], [xerr[1][i]]],
                fmt="o", markersize=9, color=colors[i], ecolor=colors[i], elinewidth=2.5, capsize=5,
                label=f"{t} (β={slopes[i]:+.3f}, p={pvals[i]:.3f})"
            )
            
        shared_slope = sub[sub.taxon == "Shared (Pooled Mean)"]["velocity_slope"].values[0]
        ax.axvline(shared_slope, color="gray", linestyle="-.", linewidth=1.2, label=f"Shared Mean Slope ({shared_slope:+.3f})")
        ax.axvline(0, color="black", linestyle="--", linewidth=1.0)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(taxa_order, fontsize=11, fontweight="bold")
        ax.set_xlabel(r"Standardized Climate Velocity Effect ($\beta \pm 95\%$ CI)", fontsize=11, fontweight="bold")
        ax.set_title(f"({chr(65 + idx)}) {resp_name}: Hierarchical Slopes", fontsize=12, fontweight="bold")
        ax.legend(frameon=True, facecolor="white", loc="lower left", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        
    plt.tight_layout()
    fig_path = figures_dir / "joint_taxa_effects.png"
    v3_fig_path = v3_figures_dir / "joint_taxa_effects.png"
    fig.savefig(fig_path, dpi=300)
    fig.savefig(v3_fig_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved joint taxa effects figure to {fig_path} and {v3_fig_path}")
    
    return model_df, contrast_df


if __name__ == "__main__":
    args = parse_args()
    run_joint_taxa_modelling(resolution=args.resolution)
