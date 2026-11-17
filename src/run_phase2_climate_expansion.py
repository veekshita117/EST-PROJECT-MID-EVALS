import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, zscore

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from common.helpers import cell_zonal_stats, sample_at, CELL

np.random.seed(42)

# File paths
PALEOCLIM_FILES = {
    "present": {
        "bio1": "PALEOCLIM/raw/paleoclim_current_BIO1.tif",
        "bio4": "PALEOCLIM/raw/paleoclim_current_BIO4.tif",
        "bio12": "PALEOCLIM/raw/paleoclim_current_BIO12.tif",
        "bio15": "PALEOCLIM/raw/paleoclim_current_BIO15.tif",
    },
    "holocene": {
        "bio1": "PALEOCLIM/raw/paleoclim_late_holocene_BIO1_aligned.tif",
        "bio4": "PALEOCLIM/raw/paleoclim_late_holocene_BIO4_aligned.tif",
        "bio12": "PALEOCLIM/raw/paleoclim_late_holocene_BIO12_aligned.tif",
        "bio15": "PALEOCLIM/raw/paleoclim_late_holocene_BIO15_aligned.tif",
    },
    "lgm": {
        "bio1": "PALEOCLIM/raw/paleoclim_LGM_BIO1_aligned.tif",
        "bio4": "PALEOCLIM/raw/paleoclim_LGM_BIO4_aligned.tif",
        "bio12": "PALEOCLIM/raw/paleoclim_LGM_BIO12_aligned.tif",
        "bio15": "PALEOCLIM/raw/paleoclim_LGM_BIO15_aligned.tif",
    },
}

WORLDCLIM_FILES = {
    "present": {
        "bio1": "WORLDCLIM/raw/present/bio/bio_1",
        "bio4": "WORLDCLIM/raw/present/bio/bio_4",
        "bio12": "WORLDCLIM/raw/present/bio/bio_12",
        "bio15": "WORLDCLIM/raw/present/bio/bio_15",
    },
    "holocene": {
        "bio1": "WORLDCLIM/raw/mid_holocene/ccmidbi1.tif",
        "bio4": "WORLDCLIM/raw/mid_holocene/ccmidbi4.tif",
        "bio12": "WORLDCLIM/raw/mid_holocene/ccmidbi12.tif",
        "bio15": "WORLDCLIM/raw/mid_holocene/ccmidbi15.tif",
    },
    "lgm": {
        "bio1": "WORLDCLIM/raw/lgm/cclgmbi1.tif",
        "bio4": "WORLDCLIM/raw/lgm/cclgmbi4.tif",
        "bio12": "WORLDCLIM/raw/lgm/cclgmbi12.tif",
        "bio15": "WORLDCLIM/raw/lgm/cclgmbi15.tif",
    },
}


def calc_zscore(s):
    std = s.std()
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


def compute_zonal_pipeline(file_dict, prefix, cell_size):
    print(f"--- Computing zonal pipeline for {prefix} at {cell_size}° ---")
    
    # 1. Zonal stats for each period & variable
    # BIO1: scale=None (divides by 10 to get °C)
    # BIO12: scale=1, nodata_threshold=None (mm)
    # BIO4: scale=1, nodata_threshold=None (SD * 100)
    # BIO15: scale=1, nodata_threshold=None (CV %)
    
    p_b1 = cell_zonal_stats(file_dict["present"]["bio1"], cell=cell_size, scale=None)
    h_b1 = cell_zonal_stats(file_dict["holocene"]["bio1"], cell=cell_size, scale=None)
    l_b1 = cell_zonal_stats(file_dict["lgm"]["bio1"], cell=cell_size, scale=None)
    
    p_b12 = cell_zonal_stats(file_dict["present"]["bio12"], cell=cell_size, scale=1, nodata_threshold=None)
    h_b12 = cell_zonal_stats(file_dict["holocene"]["bio12"], cell=cell_size, scale=1, nodata_threshold=None)
    l_b12 = cell_zonal_stats(file_dict["lgm"]["bio12"], cell=cell_size, scale=1, nodata_threshold=None)
    
    p_b4 = cell_zonal_stats(file_dict["present"]["bio4"], cell=cell_size, scale=1, nodata_threshold=None)
    l_b4 = cell_zonal_stats(file_dict["lgm"]["bio4"], cell=cell_size, scale=1, nodata_threshold=None)
    
    p_b15 = cell_zonal_stats(file_dict["present"]["bio15"], cell=cell_size, scale=1, nodata_threshold=None)
    l_b15 = cell_zonal_stats(file_dict["lgm"]["bio15"], cell=cell_size, scale=1, nodata_threshold=None)
    
    df = pd.DataFrame({
        "cell_lat": p_b1["cell_lat"],
        "cell_lon": p_b1["cell_lon"],
        "valid_fraction": p_b1["valid_fraction"],
        f"{prefix}_temp_present": p_b1["mean"],
        f"{prefix}_temp_holocene": h_b1["mean"],
        f"{prefix}_temp_lgm": l_b1["mean"],
        f"{prefix}_precip_present": p_b12["mean"],
        f"{prefix}_precip_holocene": h_b12["mean"],
        f"{prefix}_precip_lgm": l_b12["mean"],
        f"{prefix}_bio4_present": p_b4["mean"],
        f"{prefix}_bio4_lgm": l_b4["mean"],
        f"{prefix}_bio15_present": p_b15["mean"],
        f"{prefix}_bio15_lgm": l_b15["mean"],
    })
    
    # Keep cells with valid land observations
    df = df.dropna(subset=[f"{prefix}_temp_present", f"{prefix}_precip_present"]).copy()
    
    # Temperature metrics
    df[f"{prefix}_temp_lgm_change"] = (df[f"{prefix}_temp_present"] - df[f"{prefix}_temp_lgm"]).abs()
    df[f"{prefix}_temp_holo_change"] = (df[f"{prefix}_temp_present"] - df[f"{prefix}_temp_holocene"]).abs()
    df[f"{prefix}_temp_instability"] = df[[f"{prefix}_temp_present", f"{prefix}_temp_holocene", f"{prefix}_temp_lgm"]].std(axis=1)
    
    # Precipitation metrics
    df[f"{prefix}_precip_lgm_change_abs"] = (df[f"{prefix}_precip_present"] - df[f"{prefix}_precip_lgm"]).abs()
    # Relative change: |ln((P_lgm + 1) / (P_present + 1))|
    df[f"{prefix}_precip_lgm_change_rel"] = (
        np.log(df[f"{prefix}_precip_lgm"] + 1.0) - np.log(df[f"{prefix}_precip_present"] + 1.0)
    ).abs()
    df[f"{prefix}_precip_holo_change_abs"] = (df[f"{prefix}_precip_present"] - df[f"{prefix}_precip_holocene"]).abs()
    df[f"{prefix}_precip_holo_change_rel"] = (
        np.log(df[f"{prefix}_precip_holocene"] + 1.0) - np.log(df[f"{prefix}_precip_present"] + 1.0)
    ).abs()
    df[f"{prefix}_precip_instability"] = df[[f"{prefix}_precip_present", f"{prefix}_precip_holocene", f"{prefix}_precip_lgm"]].std(axis=1)
    
    # Variability metrics (BIO4 and BIO15 change)
    df[f"{prefix}_bio4_change"] = (df[f"{prefix}_bio4_present"] - df[f"{prefix}_bio4_lgm"]).abs()
    df[f"{prefix}_bio15_change"] = (df[f"{prefix}_bio15_present"] - df[f"{prefix}_bio15_lgm"]).abs()
    
    # Composite stability index: mean of z-scores of temperature instability and relative precipitation instability
    # Higher z-score = more change / greater instability (lower stability)
    z_temp = calc_zscore(df[f"{prefix}_temp_instability"])
    z_precip = calc_zscore(df[f"{prefix}_precip_lgm_change_rel"])
    df[f"{prefix}_composite_instability"] = (z_temp + z_precip) / 2.0
    
    return df


def compute_point_sampled_v2(file_dict, prefix, pts):
    print(f"--- Computing point-sampled v2 for {prefix} ---")
    d = pts[["lon", "lat", "cell_lat", "cell_lon"]].copy()
    
    for period in ["present", "holocene", "lgm"]:
        d[f"temp_{period}"] = sample_at(file_dict[period]["bio1"], d.lon, d.lat, scale=None)
        d[f"precip_{period}"] = sample_at(file_dict[period]["bio12"], d.lon, d.lat, scale=1, nodata_threshold=None)
    
    d["bio4_present"] = sample_at(file_dict["present"]["bio4"], d.lon, d.lat, scale=1, nodata_threshold=None)
    d["bio4_lgm"] = sample_at(file_dict["lgm"]["bio4"], d.lon, d.lat, scale=1, nodata_threshold=None)
    d["bio15_present"] = sample_at(file_dict["present"]["bio15"], d.lon, d.lat, scale=1, nodata_threshold=None)
    d["bio15_lgm"] = sample_at(file_dict["lgm"]["bio15"], d.lon, d.lat, scale=1, nodata_threshold=None)
    
    d = d.dropna()
    
    d["temp_lgm_change"] = (d["temp_present"] - d["temp_lgm"]).abs()
    d["temp_holo_change"] = (d["temp_present"] - d["temp_holocene"]).abs()
    d["temp_instability"] = d[["temp_present", "temp_holocene", "temp_lgm"]].std(axis=1)
    
    d["precip_lgm_change_abs"] = (d["precip_present"] - d["precip_lgm"]).abs()
    d["precip_lgm_change_rel"] = (np.log(d["precip_lgm"] + 1.0) - np.log(d["precip_present"] + 1.0)).abs()
    d["precip_instability"] = d[["precip_present", "precip_holocene", "precip_lgm"]].std(axis=1)
    
    d["bio4_change"] = (d["bio4_present"] - d["bio4_lgm"]).abs()
    d["bio15_change"] = (d["bio15_present"] - d["bio15_lgm"]).abs()
    
    out = (
        d.drop(columns=["lon", "lat"])
        .groupby(["cell_lat", "cell_lon"])
        .mean()
        .reset_index()
    )
    
    z_temp = calc_zscore(out["temp_instability"])
    z_precip = calc_zscore(out["precip_lgm_change_rel"])
    out["composite_instability"] = (z_temp + z_precip) / 2.0
    
    return out.rename(
        columns=lambda c: c if c.startswith("cell_") else f"{prefix}_{c}"
    )


def plot_global_scatter_map(df, val_col, title, label, out_path, cmap="viridis", vmin=None, vmax=None):
    plt.figure(figsize=(10, 4.8))
    sc = plt.scatter(
        df["cell_lon"],
        df["cell_lat"],
        c=df[val_col],
        s=18,
        marker="s",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar(sc, label=label, shrink=0.7)
    plt.xlim(-180, 180)
    plt.ylim(-90, 90)
    plt.title(title, fontsize=12)
    plt.xlabel("Longitude (°)")
    plt.ylabel("Latitude (°)")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_histogram(series, title, xlabel, out_path, bins=40):
    plt.figure(figsize=(6, 4))
    plt.hist(series.dropna(), bins=bins, edgecolor="black", alpha=0.7)
    plt.title(title, fontsize=11)
    plt.xlabel(xlabel)
    plt.ylabel("Cell count")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    print("=== STARTING PHASE 2 EXPANSION PIPELINE ===")
    
    # 1. Zonal calculations
    pc_zonal_5 = compute_zonal_pipeline(PALEOCLIM_FILES, "pc", cell_size=5)
    pc_zonal_2 = compute_zonal_pipeline(PALEOCLIM_FILES, "pc", cell_size=2)
    
    wc_zonal_5 = compute_zonal_pipeline(WORLDCLIM_FILES, "wc", cell_size=5)
    wc_zonal_2 = compute_zonal_pipeline(WORLDCLIM_FILES, "wc", cell_size=2)
    
    # Save zonal CSVs
    pc_zonal_5.to_csv("PALEOCLIM/processed/paleoclim_zonal_5deg.csv", index=False)
    pc_zonal_2.to_csv("PALEOCLIM/processed/paleoclim_zonal_2deg.csv", index=False)
    wc_zonal_5.to_csv("WORLDCLIM/processed/worldclim_zonal_5deg.csv", index=False)
    wc_zonal_2.to_csv("WORLDCLIM/processed/worldclim_zonal_2deg.csv", index=False)
    
    # 2. Point-sampled v2 calculations
    pts = pd.read_csv("GBIF/processed/gbif_points_clean.csv")
    pc_pt_5 = compute_point_sampled_v2(PALEOCLIM_FILES, "pc", pts)
    wc_pt_5 = compute_point_sampled_v2(WORLDCLIM_FILES, "wc", pts)
    
    pc_pt_5.to_csv("PALEOCLIM/processed/paleoclim_point_sampled_v2.csv", index=False)
    wc_pt_5.to_csv("WORLDCLIM/processed/worldclim_point_sampled_v2.csv", index=False)
    
    # 3. Check for NaN-only columns
    for name, d in [
        ("pc_zonal_5", pc_zonal_5),
        ("pc_zonal_2", pc_zonal_2),
        ("wc_zonal_5", wc_zonal_5),
        ("wc_zonal_2", wc_zonal_2),
        ("pc_pt_5", pc_pt_5),
        ("wc_pt_5", wc_pt_5),
    ]:
        nan_cols = [c for c in d.columns if d[c].isna().all()]
        if nan_cols:
            raise ValueError(f"Error: NaN-only columns in {name}: {nan_cols}")
        print(f"Verified {name}: shape={d.shape}, NaN-only columns: None")
    
    # 4. Acceptance: Print comparison of zonal vs point-sampled on shared cells
    print("\n" + "=" * 60)
    print("ACCEPTANCE CHECK: TEMPERATURE RESULTS (ZONAL VS POINT-SAMPLED)")
    print("=" * 60)
    
    # PaleoClim comparison
    m_pc = pc_pt_5.merge(pc_zonal_5, on=["cell_lat", "cell_lon"])
    print(f"PaleoClim shared GBIF cells: {len(m_pc)}")
    for m in ["temp_lgm_change", "temp_holo_change", "temp_instability"]:
        pt_col = f"pc_{m}"
        zn_col = f"pc_{m}"
        # In m_pc: pt_col is from x (pc_pt_5), zn_col is from y (pc_zonal_5)
        x_val = m_pc[f"{pt_col}_x"]
        y_val = m_pc[f"{zn_col}_y"]
        r = np.corrcoef(x_val, y_val)[0, 1]
        rho, _ = spearmanr(x_val, y_val)
        print(f"PaleoClim {m:20s}: Point mean={x_val.mean():.2f} | Zonal mean={y_val.mean():.2f} | Pearson r={r:.4f} | Spearman rho={rho:.4f}")
    
    # WorldClim comparison
    m_wc = wc_pt_5.merge(wc_zonal_5, on=["cell_lat", "cell_lon"])
    print(f"\nWorldClim shared GBIF cells: {len(m_wc)}")
    for m in ["temp_lgm_change", "temp_holo_change", "temp_instability"]:
        x_val = m_wc[f"wc_{m}_x"]
        y_val = m_wc[f"wc_{m}_y"]
        r = np.corrcoef(x_val, y_val)[0, 1]
        rho, _ = spearmanr(x_val, y_val)
        print(f"WorldClim {m:20s}: Point mean={x_val.mean():.2f} | Zonal mean={y_val.mean():.2f} | Pearson r={r:.4f} | Spearman rho={rho:.4f}")
    
    # 5. Acceptance: Precipitation ranges & physical plausibility
    print("\n" + "=" * 60)
    print("ACCEPTANCE CHECK: PRECIPITATION & SEASONALITY METRIC RANGES (5° ZONAL)")
    print("=" * 60)
    for ds_name, df, pfx in [("PaleoClim", pc_zonal_5, "pc"), ("WorldClim", wc_zonal_5, "wc")]:
        print(f"\n--- {ds_name} (n={len(df)} cells) ---")
        for col in [
            f"{pfx}_precip_present", f"{pfx}_precip_holocene", f"{pfx}_precip_lgm",
            f"{pfx}_precip_lgm_change_abs", f"{pfx}_precip_lgm_change_rel", f"{pfx}_precip_instability",
            f"{pfx}_bio4_present", f"{pfx}_bio4_lgm", f"{pfx}_bio4_change",
            f"{pfx}_bio15_present", f"{pfx}_bio15_lgm", f"{pfx}_bio15_change",
            f"{pfx}_composite_instability"
        ]:
            s = df[col]
            print(f"{col:32s}: min={s.min():8.2f} | median={s.median():8.2f} | mean={s.mean():8.2f} | max={s.max():8.2f}")
    
    # 6. Figures
    print("\nGenerating figures...")
    os.makedirs("PALEOCLIM/figures", exist_ok=True)
    os.makedirs("WORLDCLIM/figures", exist_ok=True)
    os.makedirs("integration/figures", exist_ok=True)
    
    # PaleoClim figures
    plot_global_scatter_map(
        pc_zonal_5, "pc_precip_lgm_change_rel",
        "PaleoClim: Relative Annual Precipitation Change since LGM |ln((P_lgm+1)/(P_pres+1))|",
        "Relative precipitation change",
        "PALEOCLIM/figures/pc_precip_change.png",
        cmap="Blues", vmax=1.5
    )
    plot_global_scatter_map(
        pc_zonal_5, "pc_composite_instability",
        "PaleoClim: Composite Quaternary Climate Instability Index",
        "Composite index (mean z-score: Temp + Precip)",
        "PALEOCLIM/figures/pc_composite_stability.png",
        cmap="YlOrRd", vmin=-1.5, vmax=2.5
    )
    plot_histogram(
        pc_zonal_5["pc_precip_lgm_change_rel"],
        "PaleoClim: Relative Precipitation Change Distribution",
        "Relative change |ln((P_lgm+1)/(P_pres+1))|",
        "PALEOCLIM/figures/pc_precip_change_hist.png"
    )
    plot_histogram(
        pc_zonal_5["pc_composite_instability"],
        "PaleoClim: Composite Instability Index Distribution",
        "Composite index (z-score)",
        "PALEOCLIM/figures/pc_composite_hist.png"
    )
    
    # WorldClim figures
    plot_global_scatter_map(
        wc_zonal_5, "wc_precip_lgm_change_rel",
        "WorldClim: Relative Annual Precipitation Change since LGM |ln((P_lgm+1)/(P_pres+1))|",
        "Relative precipitation change",
        "WORLDCLIM/figures/wc_precip_change.png",
        cmap="Blues", vmax=1.5
    )
    plot_global_scatter_map(
        wc_zonal_5, "wc_composite_instability",
        "WorldClim: Composite Quaternary Climate Instability Index",
        "Composite index (mean z-score: Temp + Precip)",
        "WORLDCLIM/figures/wc_composite_stability.png",
        cmap="YlOrRd", vmin=-1.5, vmax=2.5
    )
    plot_histogram(
        wc_zonal_5["wc_precip_lgm_change_rel"],
        "WorldClim: Relative Precipitation Change Distribution",
        "Relative change |ln((P_lgm+1)/(P_pres+1))|",
        "WORLDCLIM/figures/wc_precip_change_hist.png"
    )
    plot_histogram(
        wc_zonal_5["wc_composite_instability"],
        "WorldClim: Composite Instability Index Distribution",
        "Composite index (z-score)",
        "WORLDCLIM/figures/wc_composite_hist.png"
    )
    
    # 7. Dataset Agreement between PaleoClim and WorldClim
    merged_zonal = pc_zonal_5.merge(wc_zonal_5, on=["cell_lat", "cell_lon"])
    print(f"\nShared land cells between PaleoClim and WorldClim at 5°: {len(merged_zonal)}")
    
    # Scatter plot: precipitation change agreement
    val_p = ~(merged_zonal["pc_precip_lgm_change_rel"].isna() | merged_zonal["wc_precip_lgm_change_rel"].isna())
    sub_p = merged_zonal[val_p]
    plt.figure(figsize=(5.5, 5))
    plt.scatter(sub_p["pc_precip_lgm_change_rel"], sub_p["wc_precip_lgm_change_rel"], s=10, alpha=0.5, color="navy")
    rho_p, p_p = spearmanr(sub_p["pc_precip_lgm_change_rel"], sub_p["wc_precip_lgm_change_rel"])
    plt.title(f"Dataset Agreement: Relative Precip Change (rho={rho_p:.2f})")
    plt.xlabel("PaleoClim |ln((P_lgm+1)/(P_pres+1))|")
    plt.ylabel("WorldClim |ln((P_lgm+1)/(P_pres+1))|")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig("integration/figures/agreement_precip_change.png", dpi=200, bbox_inches="tight")
    plt.close()
    
    # Scatter plot: composite index agreement
    val_c = ~(merged_zonal["pc_composite_instability"].isna() | merged_zonal["wc_composite_instability"].isna())
    sub_c = merged_zonal[val_c]
    plt.figure(figsize=(5.5, 5))
    plt.scatter(sub_c["pc_composite_instability"], sub_c["wc_composite_instability"], s=10, alpha=0.5, color="darkgreen")
    rho_c, p_c = spearmanr(sub_c["pc_composite_instability"], sub_c["wc_composite_instability"])
    plt.title(f"Dataset Agreement: Composite Instability (rho={rho_c:.2f})")
    plt.xlabel("PaleoClim Composite Index")
    plt.ylabel("WorldClim Composite Index")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig("integration/figures/agreement_composite_index.png", dpi=200, bbox_inches="tight")
    plt.close()
    
    # Agreement table across all metrics
    agreement_rows = []
    metric_pairs = [
        ("Temperature LGM Change", "pc_temp_lgm_change", "wc_temp_lgm_change"),
        ("Temperature Instability", "pc_temp_instability", "wc_temp_instability"),
        ("Precipitation LGM Change (Abs mm)", "pc_precip_lgm_change_abs", "wc_precip_lgm_change_abs"),
        ("Precipitation LGM Change (Rel)", "pc_precip_lgm_change_rel", "wc_precip_lgm_change_rel"),
        ("Precipitation Instability", "pc_precip_instability", "wc_precip_instability"),
        ("Temperature Seasonality Change (BIO4)", "pc_bio4_change", "wc_bio4_change"),
        ("Precipitation Seasonality Change (BIO15)", "pc_bio15_change", "wc_bio15_change"),
        ("Composite Instability Index", "pc_composite_instability", "wc_composite_instability"),
    ]
    for label, col_pc, col_wc in metric_pairs:
        valid = ~(merged_zonal[col_pc].isna() | merged_zonal[col_wc].isna())
        v_pc = merged_zonal.loc[valid, col_pc]
        v_wc = merged_zonal.loc[valid, col_wc]
        r = np.corrcoef(v_pc, v_wc)[0, 1]
        rho, p = spearmanr(v_pc, v_wc)
        agreement_rows.append({
            "metric": label,
            "n_shared_cells": int(valid.sum()),
            "pearson_r": round(r, 3),
            "spearman_rho": round(rho, 3),
            "p_value": round(p, 4)
        })
    df_agree = pd.DataFrame(agreement_rows)
    df_agree.to_csv("integration/figures/table_metric_agreement.csv", index=False)
    print("\nDataset Agreement Table (PaleoClim vs WorldClim):")
    print(df_agree.to_string(index=False))
    
    # 8. Save summaries for notes
    pc_summary_v2 = pc_zonal_5.describe().round(2)
    pc_summary_v2.to_csv("PALEOCLIM/processed/pc_summary_v2.csv")
    wc_summary_v2 = wc_zonal_5.describe().round(2)
    wc_summary_v2.to_csv("WORLDCLIM/processed/wc_summary_v2.csv")
    
    print("\nPhase 2 computation pipeline completed successfully.")


if __name__ == "__main__":
    main()
