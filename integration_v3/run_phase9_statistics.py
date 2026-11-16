#!/usr/bin/env python3
"""
Phase 9: Comprehensive Statistical Inference Pipeline (integration_v3)
=======================================================================
Conducts rigorous macroecological and econometric tests of Quaternary
palaeoclimate stability and climate velocity against modern biodiversity.

Pre-registration requirements:
- Data: All land cells with >= 25% valid land pixels.
- Primary response: IUCN total vertebrate richness.
- Secondary responses: IUCN weighted endemism, small-range richness, GBIF rarefied richness.
- Primary predictor: log10(temperature climate-change velocity).
- Controls: |lat|, BIO1, BIO12, BIO4, BIO15, elevation_mean, relief, land fraction.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg
import libpysal
import spreg

# Ensure output directories exist
os.makedirs("integration_v3/tables", exist_ok=True)
os.makedirs("integration_v3/figures", exist_ok=True)
os.makedirs("integration_v3/processed", exist_ok=True)

print("=" * 70)
print("PHASE 9: STATISTICAL INFERENCE & HYPOTHESIS TESTING (v3)")
print("=" * 70)

# Helper for partial spearman matching benchmark definition
def calc_partial_spearman(df_sub, x_col, y_col, cov_cols):
    cols = [x_col, y_col] + cov_cols
    R = df_sub[cols].apply(stats.rankdata)
    Z = np.column_stack([np.ones(len(R))] + [R[c] for c in cov_cols])
    bx = np.linalg.lstsq(Z, R[x_col], rcond=None)[0]
    by = np.linalg.lstsq(Z, R[y_col], rcond=None)[0]
    res_x = R[x_col] - Z @ bx
    res_y = R[y_col] - Z @ by
    return stats.spearmanr(res_x, res_y)

# -----------------------------------------------------------------------------
# STEP 1: REPRODUCE 188-CELL GBIF BASELINE CHECK
# -----------------------------------------------------------------------------
print("\n[Step 1] Reproducing original 188-cell GBIF baseline...")

def reproduce_188_gbif():
    gb = pd.read_csv("GBIF/processed/gbif_richness_cells.csv")
    pc = pd.read_csv("PALEOCLIM/processed/paleoclim_cell_stability.csv")[["cell_lat", "cell_lon", "pc_lgm_change", "pc_instability"]]
    wc = pd.read_csv("WORLDCLIM/processed/worldclim_cell_stability.csv")[["cell_lat", "cell_lon", "wc_lgm_change", "wc_instability"]]

    key = ["cell_lat", "cell_lon"]
    df = gb.merge(pc, on=key).merge(wc, on=key)
    df = df[df.n_records >= 10].copy()
    df["abs_lat"] = df.cell_lat.abs()
    df["log_n"] = np.log(df.n_records)

    rows = []
    for s, sname in [("pc", "PaleoClim"), ("wc", "WorldClim")]:
        for m, mname in [("lgm_change", "LGM change"), ("instability", "Instability")]:
            col = f"{s}_{m}"
            rho, p = stats.spearmanr(df[col], df.richness)
            prho, pp = calc_partial_spearman(df, col, "richness", ["log_n", "abs_lat"])
            rows.append({
                "source": sname,
                "metric": mname,
                "n_cells": len(df),
                "spearman_rho": round(rho, 3),
                "p_value": round(p, 3),
                "partial_rho": round(prho, 3),
                "partial_p": round(pp, 3)
            })
    res_df = pd.DataFrame(rows)
    res_df.to_csv("integration_v3/tables/reproduce_188_gbif.csv", index=False)
    print("Baseline 188-cell reproduction summary:")
    print(res_df.to_string(index=False))
    return res_df

reproduce_188_gbif()

# -----------------------------------------------------------------------------
# STEP 2: BUILD MASTER INTEGRATION DATASETS (5° PRIMARY & 2° SENSITIVITY)
# -----------------------------------------------------------------------------
print("\n[Step 2] Building master integration datasets (5° and 2°)...")

def build_dataset(resolution="5deg"):
    iucn = pd.read_csv(f"IUCN/processed/iucn_cells_{resolution}.csv")
    pc_v3 = pd.read_csv(f"PALEOCLIM/processed/paleoclim_stability_v3_{resolution}.csv")
    pcz = pd.read_csv(f"PALEOCLIM/processed/paleoclim_zonal_{resolution}.csv")
    dem = pd.read_csv(f"COPERNICUS_DEM/processed/dem_cells_global_{resolution}.csv")
    gbif = pd.read_csv(f"GBIF/processed/gbif_cells_{resolution}_v2.csv")

    for d in [iucn, pc_v3, pcz, dem, gbif]:
        if "cell_lat" not in d.columns and "lat" in d.columns:
            d.rename(columns={"lat": "cell_lat", "lon": "cell_lon"}, inplace=True)

    df = iucn.merge(pc_v3, on=["cell_lon", "cell_lat"], how="inner", suffixes=("", "_pc3"))
    zonal_cols = ["cell_lon", "cell_lat", "pc_temp_present", "pc_precip_present", "pc_bio4_present", "pc_bio15_present"]
    df = df.merge(pcz[zonal_cols], on=["cell_lon", "cell_lat"], how="inner")
    
    dem_cols = ["cell_lon", "cell_lat", "elevation_mean", "topographic_heterogeneity"]
    df = df.merge(dem[dem_cols], on=["cell_lon", "cell_lat"], how="inner")

    gbif_cols = ["cell_lon", "cell_lat", "n_records_total", "richness_total", 
                 "rarefied_richness_n20_total", "rarefied_richness_n50_total", "rarefied_richness_n100_total",
                 "n_records_mammalia", "richness_mammalia", "rarefied_richness_n20_mammalia",
                 "n_records_amphibia", "richness_amphibia", "rarefied_richness_n20_amphibia"]
    gbif_cols = [c for c in gbif_cols if c in gbif.columns]
    df = df.merge(gbif[gbif_cols], on=["cell_lon", "cell_lat"], how="left", suffixes=("", "_gbif"))

    # Derived covariates
    df["abs_lat"] = df["cell_lat"].abs()
    if "n_records_total" in df.columns:
        df["log1p_records_total"] = np.log1p(df["n_records_total"].fillna(0))
    else:
        df["log1p_records_total"] = 0.0
    df["land_fraction"] = df["valid_pixel_pct"]
    
    # Spatial block ID (20-degree blocks)
    block_lon = np.floor((df["cell_lon"] + 180.0) / 20.0).astype(int)
    block_lat = np.floor((df["cell_lat"] + 90.0) / 20.0).astype(int)
    df["block_id"] = block_lat * 100 + block_lon

    out_path = f"integration_v3/processed/data_v3_{resolution}.csv"
    df.to_csv(out_path, index=False)
    print(f"Master {resolution} dataset created: {len(df)} cells saved to {out_path}")
    return df

df5 = build_dataset("5deg")
df2 = build_dataset("2deg")

# -----------------------------------------------------------------------------
# STEP 3: SPEARMAN & PARTIAL SPEARMAN WITH SPATIAL-BLOCK BOOTSTRAP & BH-FDR
# -----------------------------------------------------------------------------
print("\n[Step 3] Computing Spearman & Partial Spearman correlations with 20° block-bootstrap (B=1000)...")

def run_correlations(df, resolution="5deg", n_boot=1000):
    controls = ["abs_lat", "pc_temp_present", "pc_precip_present", "pc_bio4_present", 
                "pc_bio15_present", "elevation_mean", "topographic_heterogeneity", "land_fraction"]
    
    responses = [
        ("iucn_richness_total", "richness_total", "IUCN Total Richness"),
        ("iucn_endemism_total", "weighted_endemism_total", "IUCN Total Endemism"),
        ("iucn_small_range_q25", "small_range_richness_q25", "IUCN Small Range Q25"),
        ("iucn_small_range_q10", "small_range_richness_q10", "IUCN Small Range Q10"),
        ("iucn_richness_amphibia", "amphibians_richness", "IUCN Amphibians Richness"),
        ("iucn_richness_mammalia", "mammals_richness", "IUCN Mammals Richness"),
        ("iucn_richness_reptilia", "reptiles_richness", "IUCN Reptiles Richness")
    ]
    if "rarefied_richness_n20_total" in df.columns:
        responses.append(("gbif_rarefied_n20", "rarefied_richness_n20_total", "GBIF Rarefied n=20 Total"))

    predictors = [
        ("primary_log10_velocity_temp", "log10_velocity_temp", "Primary: log10 Temp Velocity"),
        ("secondary_refugial_fraction", "refugial_area_fraction", "Secondary: Refugial Fraction"),
        ("secondary_log10_velocity_precip", "log10_velocity_precip", "Secondary: log10 Precip Velocity"),
        ("secondary_temp_anomaly", "temp_anomaly", "Secondary: Temp Anomaly"),
        ("secondary_precip_rel_change", "precip_rel_change", "Secondary: Precip Rel Change"),
        ("secondary_composite_pc1", "pca_composite", "Secondary: Composite PC1")
    ]

    records = []
    rng = np.random.default_rng(42)
    
    for r_key, r_col, r_label in responses:
        sub_controls = list(controls)
        if "gbif" in r_key:
            sub_controls = sub_controls + ["log1p_records_total"]

        valid_mask = (df[r_col].notna() & np.isfinite(df[r_col]) & 
                      df[sub_controls].notna().all(axis=1) & 
                      np.isfinite(df[sub_controls]).all(axis=1))
        df_sub = df[valid_mask].copy().reset_index(drop=True)
        sub_blocks = df_sub["block_id"].unique()
            
        block_to_idx = {b: np.where(df_sub["block_id"].values == b)[0] for b in sub_blocks}
        
        # Rank of covariates
        cov_ranks = [stats.rankdata(df_sub[c].values) for c in sub_controls]
        Z = np.column_stack([np.ones(len(df_sub))] + cov_ranks)

        y_vals = df_sub[r_col].values
        ry_vals = stats.rankdata(y_vals)
        by_z = np.linalg.lstsq(Z, ry_vals, rcond=None)[0]
        res_y = ry_vals - Z @ by_z

        for p_key, p_col, p_label in predictors:
            valid_p = df_sub[p_col].notna() & np.isfinite(df_sub[p_col])
            if not valid_p.all():
                df_sub_p = df_sub[valid_p].reset_index(drop=True)
                Z_p = Z[valid_p]
                ry_p = ry_vals[valid_p]
                res_y_p = ry_p - Z_p @ np.linalg.lstsq(Z_p, ry_p, rcond=None)[0]
                x_vals = df_sub_p[p_col].values
                rx_vals = stats.rankdata(x_vals)
                bx_z = np.linalg.lstsq(Z_p, rx_vals, rcond=None)[0]
                res_x = rx_vals - Z_p @ bx_z
                y_vals_p = df_sub_p[r_col].values
                b_to_i = {b: np.where(df_sub_p["block_id"].values == b)[0] for b in df_sub_p["block_id"].unique()}
                s_blocks = df_sub_p["block_id"].unique()
            else:
                x_vals = df_sub[p_col].values
                rx_vals = stats.rankdata(x_vals)
                bx_z = np.linalg.lstsq(Z, rx_vals, rcond=None)[0]
                res_x = rx_vals - Z @ bx_z
                res_y_p = res_y
                y_vals_p = y_vals
                b_to_i = block_to_idx
                s_blocks = sub_blocks

            # Observed correlations
            rho_obs, p_val_raw = stats.spearmanr(x_vals, y_vals_p)
            prho_obs, p_val_partial = stats.spearmanr(res_x, res_y_p)

            # Fast vectorised spatial block bootstrap
            boot_rhos = []
            boot_prhos = []
            
            for _ in range(n_boot):
                sampled_blocks = rng.choice(s_blocks, size=len(s_blocks), replace=True)
                idx = np.concatenate([b_to_i[b] for b in sampled_blocks if len(b_to_i[b]) > 0])
                if len(idx) < 15:
                    continue
                bx_samp = rx_vals[idx]
                by_samp = stats.rankdata(y_vals_p[idx])
                
                bx_m = bx_samp - np.mean(bx_samp)
                by_m = by_samp - np.mean(by_samp)
                denom = np.sqrt(np.dot(bx_m, bx_m)) * np.sqrt(np.dot(by_m, by_m))
                if denom > 0:
                    boot_rhos.append(np.dot(bx_m, by_m) / denom)
                
                rx_res = res_x[idx]
                ry_res = res_y_p[idx]
                rx_m = rx_res - np.mean(rx_res)
                ry_m = ry_res - np.mean(ry_res)
                denom_p = np.sqrt(np.dot(rx_m, rx_m)) * np.sqrt(np.dot(ry_m, ry_m))
                if denom_p > 0:
                    boot_prhos.append(np.dot(rx_m, ry_m) / denom_p)

            ci_rho_low, ci_rho_high = np.percentile(boot_rhos, [2.5, 97.5]) if boot_rhos else (np.nan, np.nan)
            ci_prho_low, ci_prho_high = np.percentile(boot_prhos, [2.5, 97.5]) if boot_prhos else (np.nan, np.nan)

            records.append({
                "resolution": resolution,
                "response": r_label,
                "predictor": p_label,
                "n_cells": len(df_sub),
                "n_blocks": len(sub_blocks),
                "raw_rho": round(rho_obs, 3),
                "raw_ci_lower": round(ci_rho_low, 3),
                "raw_ci_upper": round(ci_rho_high, 3),
                "raw_p_value": p_val_raw,
                "partial_rho": round(prho_obs, 3),
                "partial_ci_lower": round(ci_prho_low, 3),
                "partial_ci_upper": round(ci_prho_high, 3),
                "partial_p_value": p_val_partial
            })

    corr_df = pd.DataFrame(records)
    
    # Benjamini-Hochberg FDR correction across full family
    for col in ["raw_p_value", "partial_p_value"]:
        pvals = corr_df[col].values
        order = np.argsort(pvals)
        ranked = np.empty_like(order)
        ranked[order] = np.arange(1, len(pvals) + 1)
        qvals = pvals * len(pvals) / ranked
        qvals_sorted = qvals[order]
        for i in range(len(qvals_sorted) - 2, -1, -1):
            qvals_sorted[i] = min(qvals_sorted[i], qvals_sorted[i + 1])
        qvals[order] = np.minimum(qvals_sorted, 1.0)
        corr_df[col.replace("p_value", "q_fdr")] = [round(q, 4) for q in qvals]
        corr_df[col] = [round(p, 4) for p in corr_df[col]]

    out_file = f"integration_v3/tables/correlations_{resolution}.csv"
    corr_df.to_csv(out_file, index=False)
    print(f"Correlations computed and saved to {out_file} (B={n_boot} iterations)")
    return corr_df

corr_5deg = run_correlations(df5, "5deg", n_boot=1000)
corr_2deg = run_correlations(df2, "2deg", n_boot=500)

# -----------------------------------------------------------------------------
# STEP 4: HOTSPOT ENRICHMENT & SPATIALLY STRUCTURED NULL MODEL
# -----------------------------------------------------------------------------
print("\n[Step 4] Testing Hotspot Enrichment with Spatially Structured Spherical Null...")

def run_hotspot_enrichment(df, resolution="5deg", n_null=1000):
    df_sub = df[["cell_lon", "cell_lat", "block_id", "richness_total", "weighted_endemism_total", "log10_velocity_temp"]].dropna().copy()
    
    v_thresh = df_sub["log10_velocity_temp"].quantile(0.25)
    df_sub["is_refugium"] = df_sub["log10_velocity_temp"] <= v_thresh
    
    lat_rad = np.radians(df_sub["cell_lat"].values)
    lon_rad = np.radians(df_sub["cell_lon"].values)
    x = np.cos(lat_rad) * np.cos(lon_rad)
    y = np.cos(lat_rad) * np.sin(lon_rad)
    z = np.sin(lat_rad)
    xyz = np.column_stack([x, y, z])
    
    kdtree = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(xyz)
    
    results = []
    rng = np.random.default_rng(123)
    
    for resp_col, resp_label in [("richness_total", "Richness"), ("weighted_endemism_total", "Endemism")]:
        for q_top, q_label in [(0.90, "Top 10%"), (0.80, "Top 20%")]:
            r_thresh = df_sub[resp_col].quantile(q_top)
            df_sub["is_hotspot"] = df_sub[resp_col] >= r_thresh
            
            a = np.sum(df_sub["is_hotspot"] & df_sub["is_refugium"])
            b = np.sum(df_sub["is_hotspot"] & ~df_sub["is_refugium"])
            c = np.sum(~df_sub["is_hotspot"] & df_sub["is_refugium"])
            d = np.sum(~df_sub["is_hotspot"] & ~df_sub["is_refugium"])
            
            odds_ratio_obs = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
            fisher_or, fisher_p = stats.fisher_exact([[a, b], [c, d]])
            
            blocks = df_sub["block_id"].unique()
            boot_ors = []
            block_to_idx = {blk: np.where(df_sub["block_id"].values == blk)[0] for blk in blocks}
            for _ in range(1000):
                samp_blocks = rng.choice(blocks, size=len(blocks), replace=True)
                idx = np.concatenate([block_to_idx[blk] for blk in samp_blocks])
                a_b = np.sum(df_sub["is_hotspot"].values[idx] & df_sub["is_refugium"].values[idx])
                b_b = np.sum(df_sub["is_hotspot"].values[idx] & ~df_sub["is_refugium"].values[idx])
                c_b = np.sum(~df_sub["is_hotspot"].values[idx] & df_sub["is_refugium"].values[idx])
                d_b = np.sum(~df_sub["is_hotspot"].values[idx] & ~df_sub["is_refugium"].values[idx])
                or_b = ((a_b + 0.5) * (d_b + 0.5)) / ((b_b + 0.5) * (c_b + 0.5))
                boot_ors.append(or_b)
            ci_low, ci_high = np.percentile(boot_ors, [2.5, 97.5])
            
            # Spatially structured spherical rotation null distribution
            null_ors = []
            is_ref_arr = df_sub["is_refugium"].values
            is_hot_arr = df_sub["is_hotspot"].values
            
            for _ in range(n_null):
                H = rng.standard_normal((3, 3))
                Q, R_mat = np.linalg.qr(H)
                Q = Q * np.sign(np.diag(R_mat))
                if np.linalg.det(Q) < 0:
                    Q[:, 0] = -Q[:, 0]
                
                xyz_rot = xyz @ Q.T
                _, match_indices = kdtree.kneighbors(xyz_rot)
                match_indices = match_indices.ravel()
                
                is_ref_rot = is_ref_arr[match_indices]
                
                a_null = np.sum(is_hot_arr & is_ref_rot)
                b_null = np.sum(is_hot_arr & ~is_ref_rot)
                c_null = np.sum(~is_hot_arr & is_ref_rot)
                d_null = np.sum(~is_hot_arr & ~is_ref_rot)
                or_null = ((a_null + 0.5) * (d_null + 0.5)) / ((b_null + 0.5) * (c_null + 0.5))
                null_ors.append(or_null)
            
            null_ors = np.array(null_ors)
            spatial_p = (np.sum(null_ors >= odds_ratio_obs) + 1.0) / (n_null + 1.0)
            
            results.append({
                "response": resp_label,
                "hotspot_threshold": q_label,
                "n_hotspots": a + b,
                "n_refugia": a + c,
                "both_rich_and_stable": a,
                "odds_ratio": round(odds_ratio_obs, 3),
                "ci_lower": round(ci_low, 3),
                "ci_upper": round(ci_high, 3),
                "spatial_null_p": round(spatial_p, 4),
                "fisher_naive_p": round(fisher_p, 6)
            })

    enrich_df = pd.DataFrame(results)
    enrich_df.to_csv("integration_v3/tables/hotspot_enrichment.csv", index=False)
    print("Hotspot enrichment results:")
    print(enrich_df.to_string(index=False))

    plt.figure(figsize=(7, 4.5))
    plt.hist(null_ors, bins=35, density=True, color='lightgray', edgecolor='gray', label='Spatially-structured null')
    plt.axvline(odds_ratio_obs, color='crimson', linewidth=2, linestyle='--', label=f'Observed OR={odds_ratio_obs:.2f} (p={spatial_p:.3f})')
    plt.xlabel("Odds Ratio")
    plt.ylabel("Density")
    plt.title("Hotspot Enrichment: Spatial Null vs Observed (5° Grid)")
    plt.legend()
    plt.savefig("integration_v3/figures/hotspot_spatial_null.png", dpi=200, bbox_inches='tight')
    plt.close()
    return enrich_df

enrich_df = run_hotspot_enrichment(df5, "5deg", n_null=1000)

# -----------------------------------------------------------------------------
# STEP 5: QUANTILE REGRESSION (UPPER BOUND CEILING TEST)
# -----------------------------------------------------------------------------
print("\n[Step 5] Estimating Quantile Regressions at tau in [0.5, 0.75, 0.90] with Block Bootstrap...")

def run_quantile_regressions(df, resolution="5deg", n_boot=500):
    controls = ["abs_lat", "pc_temp_present", "pc_precip_present", "pc_bio4_present", 
                "pc_bio15_present", "elevation_mean", "topographic_heterogeneity", "land_fraction"]
    
    records = []
    quantiles = [0.50, 0.75, 0.90]
    rng = np.random.default_rng(789)
    blocks = df["block_id"].unique()
    block_to_idx = {b: np.where(df["block_id"].values == b)[0] for b in blocks}
    
    targets = [
        ("log1p_richness", np.log1p(df["richness_total"]), "ln(1 + IUCN Richness)"),
        ("log1p_endemism", np.log1p(df["weighted_endemism_total"]), "ln(1 + IUCN Endemism)")
    ]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[["log10_velocity_temp"] + controls].values)
    X_df = pd.DataFrame(X_scaled, columns=["velocity"] + controls)
    X_with_const = sm.add_constant(X_df)

    plt.figure(figsize=(9, 4))
    
    for ax_idx, (t_col, t_vec, t_label) in enumerate(targets, 1):
        y = t_vec.values
        slopes = []
        ci_lows = []
        ci_highs = []

        for q in quantiles:
            model = QuantReg(y, X_with_const).fit(q=q, max_iter=2000)
            beta_obs = model.params["velocity"]
            
            boot_betas = []
            for _ in range(n_boot):
                s_blocks = rng.choice(blocks, size=len(blocks), replace=True)
                idx = np.concatenate([block_to_idx[b] for b in s_blocks])
                try:
                    m_boot = QuantReg(y[idx], X_with_const.iloc[idx]).fit(q=q, max_iter=1000)
                    boot_betas.append(m_boot.params["velocity"])
                except Exception:
                    continue
            
            ci_l, ci_h = np.percentile(boot_betas, [2.5, 97.5]) if boot_betas else (np.nan, np.nan)
            slopes.append(beta_obs)
            ci_lows.append(ci_l)
            ci_highs.append(ci_h)

            records.append({
                "response": t_label,
                "quantile_tau": q,
                "velocity_slope": round(beta_obs, 4),
                "ci_lower": round(ci_l, 4),
                "ci_upper": round(ci_h, 4),
                "t_stat": round(model.tvalues["velocity"], 3),
                "p_value": round(model.pvalues["velocity"], 4)
            })

        plt.subplot(1, 2, ax_idx)
        plt.plot(quantiles, slopes, marker='o', color='#1f77b4', linewidth=2, label='Velocity Slope')
        plt.fill_between(quantiles, ci_lows, ci_highs, color='#1f77b4', alpha=0.2, label='95% Block-CI')
        plt.axhline(0, color='gray', linestyle=':')
        plt.title(f"{t_label} vs Velocity")
        plt.xlabel(r"Quantile ($\tau$)")
        plt.ylabel("Standardized Slope")
        plt.xticks(quantiles)
        plt.legend()

    plt.tight_layout()
    plt.savefig("integration_v3/figures/quantile_slopes.png", dpi=200)
    plt.close()

    q_df = pd.DataFrame(records)
    q_df.to_csv("integration_v3/tables/quantile_regression.csv", index=False)
    print("Quantile regression estimates:")
    print(q_df.to_string(index=False))
    return q_df

q_df = run_quantile_regressions(df5, "5deg", n_boot=500)

# -----------------------------------------------------------------------------
# STEP 6: SPATIAL ERROR & SPATIAL LAG MODELS (spreg, k=8 great-circle weights)
# -----------------------------------------------------------------------------
print("\n[Step 6] Estimating Spatial Error & Spatial Lag models (spreg, k=8 haversine weights)...")

def run_spatial_models(df, resolution="5deg"):
    controls = ["abs_lat", "pc_temp_present", "pc_precip_present", "pc_bio4_present", 
                "pc_bio15_present", "elevation_mean", "topographic_heterogeneity", "land_fraction"]
    
    rad_coords = np.radians(df[["cell_lat", "cell_lon"]].values)
    nn = NearestNeighbors(n_neighbors=9, metric='haversine').fit(rad_coords)
    _, indices = nn.kneighbors(rad_coords)
    neighbors = {i: list(indices[i, 1:]) for i in range(len(df))}
    
    w = libpysal.weights.W(neighbors)
    w.transform = 'R'

    scaler = StandardScaler()
    X = scaler.fit_transform(df[["log10_velocity_temp"] + controls].values)
    x_names = ["velocity"] + controls

    results = []
    
    for resp_name, resp_vals in [("IUCN_Richness", np.log1p(df["richness_total"].values)), 
                                  ("IUCN_Endemism", np.log1p(df["weighted_endemism_total"].values))]:
        y = resp_vals.reshape(-1, 1)

        # 1. OLS
        ols = spreg.OLS(y, X, w=w, name_y=resp_name, name_x=x_names)
        b_ols = ols.betas[1][0]
        se_ols = ols.std_err[1]
        t_ols = ols.t_stat[1][0]
        p_ols = ols.t_stat[1][1]
        aic_ols = ols.aic

        # 2. Maximum Likelihood Spatial Error
        ml_err = spreg.ML_Error(y, X, w=w, name_y=resp_name, name_x=x_names)
        b_err = ml_err.betas[1][0]
        se_err = ml_err.std_err[1]
        z_err = ml_err.z_stat[1][0]
        p_err = ml_err.z_stat[1][1]
        aic_err = ml_err.aic
        lambda_err = ml_err.lam

        # 3. Maximum Likelihood Spatial Lag
        ml_lag = spreg.ML_Lag(y, X, w=w, name_y=resp_name, name_x=x_names)
        b_lag = ml_lag.betas[1][0]
        se_lag = ml_lag.std_err[1]
        z_lag = ml_lag.z_stat[1][0]
        p_lag = ml_lag.z_stat[1][1]
        aic_lag = ml_lag.aic
        rho_lag = ml_lag.rho

        for m_name, b_val, se_val, stat_val, p_val, aic_val, spat_param, param_name in [
            ("OLS", b_ols, se_ols, t_ols, p_ols, aic_ols, np.nan, "None"),
            ("Spatial Error", b_err, se_err, z_err, p_err, aic_err, lambda_err, "lambda"),
            ("Spatial Lag", b_lag, se_lag, z_lag, p_lag, aic_lag, rho_lag, "rho")
        ]:
            results.append({
                "response": resp_name,
                "model_type": m_name,
                "velocity_coef": round(b_val, 4),
                "std_err": round(se_val, 4),
                "ci_lower": round(b_val - 1.96 * se_val, 4),
                "ci_upper": round(b_val + 1.96 * se_val, 4),
                "test_statistic": round(stat_val, 3),
                "p_value": round(p_val, 5),
                "aic": round(aic_val, 1),
                "spatial_parameter": round(spat_param, 3) if np.isfinite(spat_param) else "N/A",
                "parameter_type": param_name
            })

    spat_df = pd.DataFrame(results)
    spat_df.to_csv("integration_v3/tables/spatial_models.csv", index=False)
    print("Spatial autoregressive models summary:")
    print(spat_df.to_string(index=False))
    return spat_df

spat_df = run_spatial_models(df5, "5deg")

# -----------------------------------------------------------------------------
# STEP 7: MACROCLIMATIC INTERACTION TESTS
# -----------------------------------------------------------------------------
print("\n[Step 7] Testing Macroclimatic Interactions (Velocity x Precip & Velocity x Seasonality)...")

def run_interaction_tests(df, resolution="5deg"):
    controls = ["abs_lat", "pc_temp_present", "elevation_mean", "topographic_heterogeneity", "land_fraction"]
    
    scaler = StandardScaler()
    scaled_feats = scaler.fit_transform(df[["log10_velocity_temp", "pc_precip_present", "pc_bio4_present"] + controls])
    s_df = pd.DataFrame(scaled_feats, columns=["velocity", "precip", "bio4"] + controls)
    
    s_df["velocity_x_precip"] = s_df["velocity"] * s_df["precip"]
    s_df["velocity_x_seasonality"] = s_df["velocity"] * s_df["bio4"]
    
    y_rich = np.log1p(df["richness_total"].values)
    y_endem = np.log1p(df["weighted_endemism_total"].values)
    
    records = []
    
    for resp_label, y in [("IUCN Total Richness", y_rich), ("IUCN Total Endemism", y_endem)]:
        # Interaction with Precipitation
        cols1 = ["velocity", "precip", "velocity_x_precip"] + controls
        X1 = sm.add_constant(s_df[cols1])
        m1 = sm.OLS(y, X1).fit()
        
        # Interaction with Seasonality
        cols2 = ["velocity", "bio4", "velocity_x_seasonality"] + controls
        X2 = sm.add_constant(s_df[cols2])
        m2 = sm.OLS(y, X2).fit()
        
        records.append({
            "response": resp_label,
            "interaction_term": "Velocity x Precipitation",
            "interaction_coef": round(m1.params["velocity_x_precip"], 4),
            "std_err": round(m1.bse["velocity_x_precip"], 4),
            "t_stat": round(m1.tvalues["velocity_x_precip"], 3),
            "p_value": round(m1.pvalues["velocity_x_precip"], 4),
            "r_squared": round(m1.rsquared, 3),
            "hypothesized_direction": "Negative (stronger velocity penalty in high precip)",
            "supported": m1.params["velocity_x_precip"] < 0 and m1.pvalues["velocity_x_precip"] < 0.05
        })
        
        records.append({
            "response": resp_label,
            "interaction_term": "Velocity x Seasonality",
            "interaction_coef": round(m2.params["velocity_x_seasonality"], 4),
            "std_err": round(m2.bse["velocity_x_seasonality"], 4),
            "t_stat": round(m2.tvalues["velocity_x_seasonality"], 3),
            "p_value": round(m2.pvalues["velocity_x_seasonality"], 4),
            "r_squared": round(m2.rsquared, 3),
            "hypothesized_direction": "Positive (stronger velocity penalty in low seasonality)",
            "supported": m2.params["velocity_x_seasonality"] > 0 and m2.pvalues["velocity_x_seasonality"] < 0.05
        })

    inter_df = pd.DataFrame(records)
    inter_df.to_csv("integration_v3/tables/interactions.csv", index=False)
    print("Interaction tests summary:")
    print(inter_df.to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    
    p_grid, v_grid = np.meshgrid(np.linspace(-2, 2, 50), np.linspace(-2, 2, 50))
    grid_df1 = pd.DataFrame(0.0, index=range(2500), columns=X1.columns)
    grid_df1["const"] = 1.0
    grid_df1["velocity"] = v_grid.ravel()
    grid_df1["precip"] = p_grid.ravel()
    grid_df1["velocity_x_precip"] = v_grid.ravel() * p_grid.ravel()
    pred_rich = m1.predict(grid_df1).values.reshape(50, 50)
    
    cs1 = axes[0].contourf(v_grid, p_grid, pred_rich, levels=15, cmap='viridis')
    axes[0].set_xlabel("Standardized Temperature Velocity")
    axes[0].set_ylabel("Standardized Annual Precipitation")
    axes[0].set_title("Predicted ln(Richness)")
    plt.colorbar(cs1, ax=axes[0])
    
    s_grid, v_grid2 = np.meshgrid(np.linspace(-2, 2, 50), np.linspace(-2, 2, 50))
    grid_df2 = pd.DataFrame(0.0, index=range(2500), columns=X2.columns)
    grid_df2["const"] = 1.0
    grid_df2["velocity"] = v_grid2.ravel()
    grid_df2["bio4"] = s_grid.ravel()
    grid_df2["velocity_x_seasonality"] = v_grid2.ravel() * s_grid.ravel()
    pred_rich2 = m2.predict(grid_df2).values.reshape(50, 50)
    
    cs2 = axes[1].contourf(v_grid2, s_grid, pred_rich2, levels=15, cmap='magma')
    axes[1].set_xlabel("Standardized Temperature Velocity")
    axes[1].set_ylabel("Standardized Temperature Seasonality")
    axes[1].set_title("Predicted ln(Richness)")
    plt.colorbar(cs2, ax=axes[1])
    
    plt.tight_layout()
    plt.savefig("integration_v3/figures/interaction_surfaces.png", dpi=200)
    plt.close()
    return inter_df

inter_df = run_interaction_tests(df5, "5deg")

# -----------------------------------------------------------------------------
# STEP 8: TAXONOMIC COMPARISON (AMPHIBIANS VS REPTILES VS MAMMALS)
# -----------------------------------------------------------------------------
print("\n[Step 8] Evaluating Pre-Registered Taxonomic Contrast (Sandel et al. 2011)...")

def run_taxa_comparison(df, resolution="5deg"):
    controls = ["abs_lat", "pc_temp_present", "pc_precip_present", "pc_bio4_present", 
                "pc_bio15_present", "elevation_mean", "topographic_heterogeneity", "land_fraction"]
    
    scaler = StandardScaler()
    X = scaler.fit_transform(df[["log10_velocity_temp"] + controls].values)
    X_aug = sm.add_constant(X)
    
    taxa = [
        ("Amphibians", np.log1p(df["amphibians_richness"].values), np.log1p(df["amphibians_weighted_endemism"].values)),
        ("Reptiles", np.log1p(df["reptiles_richness"].values), np.log1p(df["reptiles_weighted_endemism"].values)),
        ("Mammals", np.log1p(df["mammals_richness"].values), np.log1p(df["mammals_weighted_endemism"].values)),
        ("All Vertebrates", np.log1p(df["richness_total"].values), np.log1p(df["weighted_endemism_total"].values))
    ]
    
    records = []
    
    for t_name, y_rich, y_endem in taxa:
        m_r = sm.OLS(y_rich, X_aug).fit()
        b_r = m_r.params[1]
        se_r = m_r.bse[1]
        p_r = m_r.pvalues[1]
        
        m_e = sm.OLS(y_endem, X_aug).fit()
        b_e = m_e.params[1]
        se_e = m_e.bse[1]
        p_e = m_e.pvalues[1]
        
        pr_r, pp_r = calc_partial_spearman(
            pd.DataFrame({"x": df["log10_velocity_temp"], "y": y_rich, **{c: df[c] for c in controls}}),
            "x", "y", controls
        )
        pr_e, pp_e = calc_partial_spearman(
            pd.DataFrame({"x": df["log10_velocity_temp"], "y": y_endem, **{c: df[c] for c in controls}}),
            "x", "y", controls
        )
        
        records.append({
            "taxon": t_name,
            "predicted_rank": "1 (Highest)" if t_name == "Amphibians" else ("2 (Medium)" if t_name == "Reptiles" else ("3 (Lowest)" if t_name == "Mammals" else "Reference")),
            "richness_std_coef": round(b_r, 4),
            "richness_ci_lower": round(b_r - 1.96 * se_r, 4),
            "richness_ci_upper": round(b_r + 1.96 * se_r, 4),
            "richness_partial_rho": round(pr_r, 3),
            "richness_p_value": round(p_r, 4),
            "endemism_std_coef": round(b_e, 4),
            "endemism_ci_lower": round(b_e - 1.96 * se_e, 4),
            "endemism_ci_upper": round(b_e + 1.96 * se_e, 4),
            "endemism_partial_rho": round(pr_e, 3),
            "endemism_p_value": round(p_e, 4)
        })

    taxa_df = pd.DataFrame(records)
    taxa_df.to_csv("integration_v3/tables/taxa_comparison.csv", index=False)
    print("Taxonomic comparison summary:")
    print(taxa_df.to_string(index=False))

    plt.figure(figsize=(8, 4.5))
    x_pos = np.arange(len(taxa))
    w = 0.35
    
    plt.bar(x_pos - w/2, [r["richness_std_coef"] for r in records], width=w, yerr=[1.96 * (r["richness_ci_upper"] - r["richness_std_coef"])/1.96 for r in records],
            capsize=5, label='Richness', color='#2ca02c')
    plt.bar(x_pos + w/2, [r["endemism_std_coef"] for r in records], width=w, yerr=[1.96 * (r["endemism_ci_upper"] - r["endemism_std_coef"])/1.96 for r in records],
            capsize=5, label='Weighted Endemism', color='#d62728')
    
    plt.axhline(0, color='gray', linestyle='--')
    plt.xticks(x_pos, [r["taxon"] for r in records])
    plt.ylabel("Standardized Velocity Effect (Slope)")
    plt.title("Taxon Sensitivity to Climate Velocity (5° Grid)")
    plt.legend()
    plt.savefig("integration_v3/figures/taxa_comparison.png", dpi=200, bbox_inches='tight')
    plt.close()
    return taxa_df

taxa_df = run_taxa_comparison(df5, "5deg")

print("\n" + "=" * 70)
print("PHASE 9 STATISTICAL PIPELINE COMPLETE.")
print("=" * 70)
