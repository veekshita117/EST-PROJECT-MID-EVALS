#!/usr/bin/env python3
"""
Phase 8: Richer Palaeoclimate Stability Metrics Processing Pipeline.
Computes climate-change velocity, refugial area fraction, and PCA composite
for PaleoClim and WorldClim across all global land cells at 5° and 2° resolutions.
Generates publication diagnostic maps, scale sensitivity analyses, and notes_v3.md.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.decomposition import PCA
import rasterio
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.ml.spatial import assign_continents_to_df

PALEOCLIM_DIR = REPO_ROOT / "PALEOCLIM"
WORLDCLIM_DIR = REPO_ROOT / "WORLDCLIM"
INTEGRATION_V3_DIR = REPO_ROOT / "integration_v3"

INTEGRATION_V3_DIR.mkdir(parents=True, exist_ok=True)
(PALEOCLIM_DIR / "processed").mkdir(parents=True, exist_ok=True)
(PALEOCLIM_DIR / "figures").mkdir(parents=True, exist_ok=True)
(WORLDCLIM_DIR / "processed").mkdir(parents=True, exist_ok=True)
(WORLDCLIM_DIR / "figures").mkdir(parents=True, exist_ok=True)

EPS_GRAD = 1e-4  # Minimum spatial gradient floor in °C/km or km^-1
R_EARTH = 6371.0 # Earth mean radius in km

def compute_spatial_gradient(arr_2d, res_deg, bounds, eps=EPS_GRAD):
    """
    Computes spatial gradient magnitude on a spherical equirectangular grid
    with cosine-of-latitude correction and minimum gradient floor.
    """
    height, width = arr_2d.shape
    lats = np.linspace(bounds.top - res_deg / 2.0, bounds.bottom + res_deg / 2.0, height)
    dy = R_EARTH * np.radians(res_deg)
    cos_lats = np.clip(np.cos(np.radians(lats)), 0.05, 1.0)
    dx_grid = dy * cos_lats[:, None]

    # Fill NaNs with median of valid data for gradient computation at boundaries
    valid_mask = ~np.isnan(arr_2d)
    med_val = np.nanmedian(arr_2d)
    arr_filled = np.where(valid_mask, arr_2d, med_val)

    gy, gx = np.gradient(arr_filled)
    gy = np.abs(gy) / dy
    gx = np.abs(gx) / dx_grid
    gmag = np.sqrt(gx**2 + gy**2)
    return np.maximum(gmag, eps)

def aggregate_raster_to_cells(pixel_df, res_macro, offset_macro, min_valid_pixels=25):
    """
    Aggregates pixel-level metrics into macro-cells (5° or 2°).
    Only keeps cells with >= min_valid_pixels.
    """
    # Assign macro-cell coordinate centers
    pixel_df["cell_lon"] = np.floor(pixel_df["lon"] / res_macro) * res_macro + offset_macro
    pixel_df["cell_lat"] = np.floor(pixel_df["lat"] / res_macro) * res_macro + offset_macro

    # Group by macro cell
    grouped = pixel_df.groupby(["cell_lon", "cell_lat"])
    
    rows = []
    for (c_lon, c_lat), grp in grouped:
        n_px = len(grp)
        if n_px < min_valid_pixels:
            continue
            
        vel_t = grp["vel_temp"].values
        vel_p = grp["vel_precip"].values
        
        row = {
            "cell_lon": c_lon,
            "cell_lat": c_lat,
            "n_valid_pixels": n_px,
            "temp_anomaly": float(np.nanmedian(grp["temp_anom"])),
            "velocity_temp_median": float(np.nanmedian(vel_t)),
            "log10_velocity_temp": float(np.log10(np.maximum(np.nanmedian(vel_t), 1e-6))),
            "velocity_precip_median": float(np.nanmedian(vel_p)),
            "log10_velocity_precip": float(np.log10(np.maximum(np.nanmedian(vel_p), 1e-6))),
            "refugial_area_fraction": float(np.mean(grp["is_refugia"])),
            "precip_rel_change": float(np.nanmedian(grp["precip_rel"])),
            "temp_sd": float(np.nanmedian(grp["temp_sd"])),
            "precip_sd": float(np.nanmedian(grp["precip_sd"])),
            "bio4_change": float(np.nanmedian(grp["bio4_change"])),
            "bio15_change": float(np.nanmedian(grp["bio15_change"])),
        }
        rows.append(row)
        
    df_cells = pd.DataFrame(rows)
    return df_cells

def run_pca_composite(df, source_name, res_name):
    """
    Computes PCA composite stability metric (PC1 of z-scores).
    """
    cols = ["temp_anomaly", "log10_velocity_temp", "precip_rel_change"]
    X = df[cols].dropna().values
    
    # Standardize
    X_z = (X - X.mean(axis=0)) / X.std(axis=0)
    
    pca = PCA(n_components=3)
    pca.fit(X_z)
    
    pc1 = pca.transform(X_z)[:, 0]
    # Ensure positive loading orientation (higher PC1 = higher instability)
    if pca.components_[0, 0] < 0:
        pc1 = -pc1
        loadings = -pca.components_[0]
    else:
        loadings = pca.components_[0]
        
    df["pca_composite"] = np.nan
    df.loc[df[cols].dropna().index, "pca_composite"] = pc1
    
    var_exp = pca.explained_variance_ratio_[0]
    print(f"[{source_name} {res_name}] PCA Composite: PC1 explained variance = {var_exp*100:.1f}%")
    print(f"  Loadings on {cols}: {loadings.round(4)}")
    
    return loadings, var_exp

def process_source(source):
    print(f"\n=======================================================")
    print(f"PROCESSING {source.upper()} RASTERS")
    print(f"=======================================================")
    
    if source == "paleoclim":
        base_dir = PALEOCLIM_DIR / "raw"
        f_pres_t = base_dir / "paleoclim_current_BIO1.tif"
        f_lgm_t  = base_dir / "paleoclim_LGM_BIO1_aligned.tif"
        f_holo_t = base_dir / "paleoclim_late_holocene_BIO1_aligned.tif"
        
        f_pres_p = base_dir / "paleoclim_current_BIO12.tif"
        f_lgm_p  = base_dir / "paleoclim_LGM_BIO12_aligned.tif"
        f_holo_p = base_dir / "paleoclim_late_holocene_BIO12_aligned.tif"
        
        f_pres_b4 = base_dir / "paleoclim_current_BIO4.tif"
        f_lgm_b4  = base_dir / "paleoclim_LGM_BIO4_aligned.tif"
        
        f_pres_b15 = base_dir / "paleoclim_current_BIO15.tif"
        f_lgm_b15  = base_dir / "paleoclim_LGM_BIO15_aligned.tif"
        scale_t = 0.1
    else:
        base_dir = WORLDCLIM_DIR / "raw"
        f_pres_t = base_dir / "present" / "bio" / "bio_1" / "hdr.adf"
        f_lgm_t  = base_dir / "lgm" / "cclgmbi1.tif"
        f_holo_t = base_dir / "mid_holocene" / "ccmidbi1.tif"
        
        f_pres_p = base_dir / "present" / "bio" / "bio_12" / "hdr.adf"
        f_lgm_p  = base_dir / "lgm" / "cclgmbi12.tif"
        f_holo_p = base_dir / "mid_holocene" / "ccmidbi12.tif"
        
        f_pres_b4 = base_dir / "present" / "bio" / "bio_4" / "hdr.adf"
        f_lgm_b4  = base_dir / "lgm" / "cclgmbi4.tif"
        
        f_pres_b15 = base_dir / "present" / "bio" / "bio_15" / "hdr.adf"
        f_lgm_b15  = base_dir / "lgm" / "cclgmbi15.tif"
        scale_t = 0.1

    # Load temperature
    with rasterio.open(f_pres_t) as s_pres_t, rasterio.open(f_lgm_t) as s_lgm_t, rasterio.open(f_holo_t) as s_holo_t:
        pres_t = s_pres_t.read(1).astype(float)
        lgm_t  = s_lgm_t.read(1).astype(float)
        holo_t = s_holo_t.read(1).astype(float)
        
        pres_t[pres_t == s_pres_t.nodata] = np.nan
        lgm_t[lgm_t == s_lgm_t.nodata] = np.nan
        holo_t[holo_t == s_holo_t.nodata] = np.nan
        
        pres_t *= scale_t
        lgm_t  *= scale_t
        holo_t *= scale_t
        
        bounds = s_pres_t.bounds
        res_deg = s_pres_t.res[0]
        height, width = pres_t.shape

    # Load precipitation
    with rasterio.open(f_pres_p) as s_pres_p, rasterio.open(f_lgm_p) as s_lgm_p, rasterio.open(f_holo_p) as s_holo_p:
        pres_p = s_pres_p.read(1).astype(float)
        lgm_p  = s_lgm_p.read(1).astype(float)
        holo_p = s_holo_p.read(1).astype(float)
        
        pres_p[pres_p == s_pres_p.nodata] = np.nan
        lgm_p[lgm_p == s_lgm_p.nodata] = np.nan
        holo_p[holo_p == s_holo_p.nodata] = np.nan
        
        # Enforce non-negative precipitation
        pres_p = np.maximum(pres_p, 0.0)
        lgm_p  = np.maximum(lgm_p, 0.0)
        holo_p = np.maximum(holo_p, 0.0)

    # Load BIO4 and BIO15
    with rasterio.open(f_pres_b4) as s1, rasterio.open(f_lgm_b4) as s2:
        pres_b4 = s1.read(1).astype(float)
        lgm_b4  = s2.read(1).astype(float)
        pres_b4[pres_b4 == s1.nodata] = np.nan
        lgm_b4[lgm_b4 == s2.nodata] = np.nan

    with rasterio.open(f_pres_b15) as s1, rasterio.open(f_lgm_b15) as s2:
        pres_b15 = s1.read(1).astype(float)
        lgm_b15  = s2.read(1).astype(float)
        pres_b15[pres_b15 == s1.nodata] = np.nan
        lgm_b15[lgm_b15 == s2.nodata] = np.nan

    # Compute valid land pixel mask
    valid_mask = (~np.isnan(pres_t)) & (~np.isnan(lgm_t)) & (~np.isnan(pres_p)) & (~np.isnan(lgm_p))
    print(f"[{source}] Valid land pixels: {valid_mask.sum():,d}")

    # 1. Temperature metrics
    temp_anom = np.abs(pres_t - lgm_t)
    temp_rate = temp_anom / 21000.0  # °C / yr
    
    grad_t = compute_spatial_gradient(pres_t, res_deg, bounds)
    vel_temp = np.full_like(pres_t, np.nan)
    vel_temp[valid_mask] = temp_rate[valid_mask] / grad_t[valid_mask]
    
    # Global 25th percentile for refugia
    q25_vel = float(np.percentile(vel_temp[valid_mask], 25))
    is_refugia = np.zeros_like(pres_t, dtype=int)
    is_refugia[valid_mask] = (vel_temp[valid_mask] <= q25_vel).astype(int)
    print(f"[{source}] Global Q25 Temperature Velocity: {q25_vel:.6f} km/yr ({q25_vel*1000:.2f} m/yr)")

    # 2. Precipitation velocity (using ln(P+1))
    ln_pres_p = np.log1p(pres_p)
    ln_lgm_p  = np.log1p(lgm_p)
    precip_rate = np.abs(ln_pres_p - ln_lgm_p) / 21000.0
    
    grad_p = compute_spatial_gradient(ln_pres_p, res_deg, bounds)
    vel_precip = np.full_like(pres_p, np.nan)
    vel_precip[valid_mask] = precip_rate[valid_mask] / grad_p[valid_mask]

    # 3. Relative precipitation change & temporal SDs
    precip_rel = np.abs(np.log1p(lgm_p) - np.log1p(pres_p))
    
    # 3-slice temporal SD
    stack_t = np.stack([pres_t, holo_t, lgm_t], axis=0)
    temp_sd = np.nanstd(stack_t, axis=0, ddof=1)
    
    stack_p = np.stack([pres_p, holo_p, lgm_p], axis=0)
    precip_sd = np.nanstd(stack_p, axis=0, ddof=1)

    bio4_change = np.abs(pres_b4 - lgm_b4)
    bio15_change = np.abs(pres_b15 - lgm_b15)

    # 4. Flatten pixel grid to DataFrame
    lats = np.linspace(bounds.top - res_deg / 2.0, bounds.bottom + res_deg / 2.0, height)
    lons = np.linspace(bounds.left + res_deg / 2.0, bounds.right - res_deg / 2.0, width)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    df_pixels = pd.DataFrame({
        "lon": lon_grid[valid_mask],
        "lat": lat_grid[valid_mask],
        "temp_anom": temp_anom[valid_mask],
        "vel_temp": vel_temp[valid_mask],
        "is_refugia": is_refugia[valid_mask],
        "vel_precip": vel_precip[valid_mask],
        "precip_rel": precip_rel[valid_mask],
        "temp_sd": temp_sd[valid_mask],
        "precip_sd": precip_sd[valid_mask],
        "bio4_change": bio4_change[valid_mask],
        "bio15_change": bio15_change[valid_mask],
    })

    # 5. Aggregate to 5° and 2° grids
    # At 5° (min_pixels = 225 out of 900, 25%)
    df_5deg = aggregate_raster_to_cells(df_pixels, 5.0, 2.5, min_valid_pixels=225)
    df_5deg = assign_continents_to_df(df_5deg, lat_col="cell_lat", lon_col="cell_lon")
    loadings_5, var_exp_5 = run_pca_composite(df_5deg, source, "5deg")
    
    out_5deg = (PALEOCLIM_DIR if source == "paleoclim" else WORLDCLIM_DIR) / "processed" / f"{source}_stability_v3_5deg.csv"
    df_5deg.to_csv(out_5deg, index=False)
    print(f"[{source}] Saved 5° table to {out_5deg} ({len(df_5deg)} cells)")

    # At 2° (min_pixels = 36 out of 144, 25%)
    df_2deg = aggregate_raster_to_cells(df_pixels, 2.0, 1.0, min_valid_pixels=36)
    df_2deg = assign_continents_to_df(df_2deg, lat_col="cell_lat", lon_col="cell_lon")
    loadings_2, var_exp_2 = run_pca_composite(df_2deg, source, "2deg")
    
    out_2deg = (PALEOCLIM_DIR if source == "paleoclim" else WORLDCLIM_DIR) / "processed" / f"{source}_stability_v3_2deg.csv"
    df_2deg.to_csv(out_2deg, index=False)
    print(f"[{source}] Saved 2° table to {out_2deg} ({len(df_2deg)} cells)")

    # 6. Scale sensitivity test: aggregate raster 2x2 (to 20 arc-min) and compute velocity rank change
    print(f"\n--- [{source}] Scale Sensitivity: Native (10') vs Aggregated (20') ---")
    # Downsample by 2
    h2, w2 = height // 2, width // 2
    pres_t_20 = pres_t[:h2*2, :w2*2].reshape(h2, 2, w2, 2).mean(axis=(1, 3))
    lgm_t_20  = lgm_t[:h2*2, :w2*2].reshape(h2, 2, w2, 2).mean(axis=(1, 3))
    valid_20 = (~np.isnan(pres_t_20)) & (~np.isnan(lgm_t_20))
    
    grad_t_20 = compute_spatial_gradient(pres_t_20, res_deg * 2, bounds)
    vel_t_20 = np.full_like(pres_t_20, np.nan)
    vel_t_20[valid_20] = (np.abs(pres_t_20[valid_20] - lgm_t_20[valid_20]) / 21000.0) / grad_t_20[valid_20]
    
    lats_20 = np.linspace(bounds.top - res_deg, bounds.bottom + res_deg, h2)
    lons_20 = np.linspace(bounds.left + res_deg, bounds.right - res_deg, w2)
    lon_grid_20, lat_grid_20 = np.meshgrid(lons_20, lats_20)
    
    df_px_20 = pd.DataFrame({
        "lon": lon_grid_20[valid_20],
        "lat": lat_grid_20[valid_20],
        "temp_anom": np.abs(pres_t_20 - lgm_t_20)[valid_20],
        "vel_temp": vel_t_20[valid_20],
        "is_refugia": (vel_t_20[valid_20] <= np.percentile(vel_t_20[valid_20], 25)).astype(int),
        "vel_precip": np.zeros(valid_20.sum()), # dummy
        "precip_rel": np.zeros(valid_20.sum()),
        "temp_sd": np.zeros(valid_20.sum()),
        "precip_sd": np.zeros(valid_20.sum()),
        "bio4_change": np.zeros(valid_20.sum()),
        "bio15_change": np.zeros(valid_20.sum()),
    })
    df_5deg_20 = aggregate_raster_to_cells(df_px_20, 5.0, 2.5, min_valid_pixels=50)
    
    # Compare rank order across common cells
    common = pd.merge(df_5deg, df_5deg_20, on=["cell_lon", "cell_lat"], suffixes=("_native", "_20arcmin"))
    rho_scale, p_scale = stats.spearmanr(common["log10_velocity_temp_native"], common["log10_velocity_temp_20arcmin"])
    print(f"[{source}] Spearman rho across 5° cells between native (10') and 20' velocity: {rho_scale:+.4f} (p={p_scale:.2e})")

    # 7. Generate Publication Maps
    print(f"\n--- [{source}] Generating Publication Maps (300 DPI) ---")
    fig_dir = (PALEOCLIM_DIR if source == "paleoclim" else WORLDCLIM_DIR) / "figures"
    
    # Map 1: Primary Predictor (log10 Velocity)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    sc = ax.scatter(
        df_5deg["cell_lon"], df_5deg["cell_lat"],
        c=df_5deg["log10_velocity_temp"],
        cmap="Spectral_r",
        s=40,
        alpha=0.9,
        edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="log10(Temperature Velocity [km/yr])", shrink=0.7)
    ax.set_title(f"Quaternary Climate Velocity ({source.upper()}, LGM to Present, 5° Grid)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, linestyle="--", alpha=0.4)
    map1_path = fig_dir / f"{source}_log10_velocity_temp_5deg.png"
    plt.savefig(map1_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {map1_path}")

    # Map 2: Refugial Area Fraction
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    sc = ax.scatter(
        df_5deg["cell_lon"], df_5deg["cell_lat"],
        c=df_5deg["refugial_area_fraction"],
        cmap="YlGnBu",
        s=40,
        alpha=0.9,
        edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="Refugial Area Fraction (Pixels <= Q25 Velocity)", shrink=0.7)
    ax.set_title(f"Palaeoclimate Refugial Buffering ({source.upper()}, 5° Grid)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, linestyle="--", alpha=0.4)
    map2_path = fig_dir / f"{source}_refugial_fraction_5deg.png"
    plt.savefig(map2_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {map2_path}")

    return {
        "df_5deg": df_5deg,
        "df_2deg": df_2deg,
        "q25_vel": q25_vel,
        "loadings": loadings_5,
        "var_exp": var_exp_5,
        "rho_scale": rho_scale
    }

def write_notes_v3(source, res_data, comp_df):
    target_dir = PALEOCLIM_DIR if source == "paleoclim" else WORLDCLIM_DIR
    notes_file = target_dir / "notes_v3.md"
    
    df5 = res_data["df_5deg"]
    q25 = res_data["q25_vel"]
    loadings = res_data["loadings"]
    var_exp = res_data["var_exp"]
    rho_scale = res_data["rho_scale"]
    
    content = f"""# {source.upper()} Notes v3: Climate Velocity & Richer Stability Metrics

This document formalizes the methodology, definitions, mathematical units, and empirical distributions for Phase 8 palaeoclimate stability metrics.

---

## 1. Predictor Hierarchy & Pre-Registration Summary

In accordance with `integration_v3/PLAN.md`:
- **PRIMARY PREDICTOR**: `log10_velocity_temp` (log10 of LGM-to-present temperature climate-change velocity).
- **SECONDARY PREDICTORS**: All other metrics (anomaly, precipitation velocity, refugial area fraction, PCA composite, seasonality changes).
- **Multiple Testing**: FDR control (Benjamini-Hochberg) is to be applied across the secondary metric family.

---

## 2. Metric Formulations & Units

| Metric Name | Formula / Definition | Raw Units | Ecological Role |
|:---|:---|:---:|:---|
| `log10_velocity_temp` | $\\log_{{10}}\\left( \\text{{Median}}\\left( \\frac{{|\\Delta T| / 21000}}{{\\|\\nabla T\\|}} \\right) \\right)$ | $\\log_{{10}}(\\text{{km/yr}})$ | **Primary**: Migration distance required to track thermal niche |
| `refugial_area_fraction` | Fraction of pixels with velocity $\\le Q_{{25}}$ ({q25*1000:.2f} m/yr) | Dimensionless [0, 1] | Microclimatic persistence and buffering capacity |
| `temp_anomaly` | $|\\text{{BIO1}}_{{\\text{{pres}}}} - \\text{{BIO1}}_{{\\text{{LGM}}}}|$ | °C | Gross thermal magnitude change |
| `log10_velocity_precip` | $\\log_{{10}}\\left( \\text{{Median}}\\left( \\frac{{|\\Delta \\ln(P+1)| / 21000}}{{\\|\\nabla \\ln(P+1)\\|}} \\right) \\right)$ | $\\log_{{10}}(\\text{{km/yr}})$ | Moisture shift tracking velocity |
| `precip_rel_change` | $|\\ln(P_{{\\text{{LGM}}}}+1) - \\ln(P_{{\\text{{pres}}}}+1)|$ | Dimensionless | Proportional precipitation change |
| `temp_sd` | Temporal sample SD across Present, Holocene, LGM | °C | Tri-temporal thermal instability |
| `precip_sd` | Temporal sample SD across Present, Holocene, LGM | mm | Tri-temporal moisture instability |
| `bio4_change` | $|\\text{{BIO4}}_{{\\text{{pres}}}} - \\text{{BIO4}}_{{\\text{{LGM}}}}|$ | SD * 100 | Thermal seasonality shift |
| `bio15_change` | $|\\text{{BIO15}}_{{\\text{{pres}}}} - \\text{{BIO15}}_{{\\text{{LGM}}}}|$ | CV (%) | Precipitation seasonality shift |
| `pca_composite` | PC1 of $z(\\text{{anomaly}}), z(\\log_{{10}} V_{{\\text{{temp}}}}), z(\\Delta P)$ | Dimensionless | Co-varying multidimensional macroclimatic instability |

---

## 3. Global 5° Summary Statistics ({len(df5)} Valid Land Cells)

- **Temperature Velocity ($V_{{\\text{{temp}}}}$)**:
  - Global Pixel $Q_{{25}}$ Threshold: {q25:.6f} km/yr ({q25*1000:.2f} m/yr)
  - Cell Median: {df5['velocity_temp_median'].median():.6f} km/yr
  - $\\log_{{10}} V_{{\\text{{temp}}}}$ Range: [{df5['log10_velocity_temp'].min():.2f}, {df5['log10_velocity_temp'].max():.2f}], Median = {df5['log10_velocity_temp'].median():.2f}
- **Refugial Area Fraction**:
  - Median: {df5['refugial_area_fraction'].median():.4f}, Max = {df5['refugial_area_fraction'].max():.4f}
- **PCA Composite (PC1)**:
  - Explained Variance: {var_exp*100:.1f}%
  - Loadings: Anomaly = {loadings[0]:.3f}, Velocity = {loadings[1]:.3f}, Precip = {loadings[2]:.3f}
- **Scale Sensitivity**:
  - Spearman $\\rho$ between 10' and 20' velocity across 5° cells: **{rho_scale:+.4f}**

---

## 4. Cross-Source Consensus (PaleoClim vs. WorldClim)

```text
{comp_df.to_string(index=False)}
```

---

## 5. Critical Ecological & Methodological Limitations

1. **GCM Reconstruction Uncertainty**: Paleoclimate simulations represent GCM ensemble averages (CHELSA / CCSM4); regional precipitation trends in arid regions carry high model divergence.
2. **Scale Dependence of Spatial Gradient**: Spatial slope magnitude depends on grid grain (~18.5 km at 10 arc-minutes). True microtopographic buffering (gorges, ravines, poleward slopes) occurs at sub-kilometer scales.
3. **No Continuous Temporal Trajectory**: Velocity assumes a linear monotonic trajectory over 21,000 years, neglecting millennial-scale Heinrich events and Younger Dryas climate reversals.
"""
    with open(notes_file, "w") as f:
        f.write(content)
    print(f"Saved: {notes_file}")

def main():
    print("=" * 80)
    print("PHASE 8: RICHER PALAEOCLIMATE STABILITY METRICS")
    print("=" * 80)
    
    res_pc = process_source("paleoclim")
    res_wc = process_source("worldclim")
    
    # Cross-Source Concordance
    print("\n=======================================================")
    print("CROSS-SOURCE CONCORDANCE (PaleoClim vs. WorldClim at 5°)")
    print("=======================================================")
    
    df_pc = res_pc["df_5deg"]
    df_wc = res_wc["df_5deg"]
    
    merged = pd.merge(df_pc, df_wc, on=["cell_lon", "cell_lat"], suffixes=("_pc", "_wc"))
    print(f"Common valid 5° land cells: {len(merged)}")
    
    metrics = [
        ("log10_velocity_temp", "PRIMARY: Log10 Temperature Velocity"),
        ("refugial_area_fraction", "Refugial Area Fraction (<= Q25)"),
        ("temp_anomaly", "Temperature Anomaly (|Pres - LGM|)"),
        ("log10_velocity_precip", "Log10 Precipitation Velocity"),
        ("precip_rel_change", "Precipitation Relative Change"),
        ("temp_sd", "Tri-Temporal Temperature SD"),
        ("precip_sd", "Tri-Temporal Precipitation SD"),
        ("bio4_change", "Temperature Seasonality Change"),
        ("bio15_change", "Precipitation Seasonality Change"),
        ("pca_composite", "PCA Composite Stability (PC1)"),
    ]
    
    comp_rows = []
    for col, desc in metrics:
        v_pc = merged[f"{col}_pc"]
        v_wc = merged[f"{col}_wc"]
        valid = v_pc.notna() & v_wc.notna()
        rho, p = stats.spearmanr(v_pc[valid], v_wc[valid])
        comp_rows.append({
            "metric": col,
            "description": desc,
            "spearman_rho": round(rho, 4),
            "p_value": f"{p:.2e}"
        })
        print(f"  {desc:38s} | rho = {rho:+.4f} (p = {p:.2e})")
        
    comp_df = pd.DataFrame(comp_rows)
    comp_csv = INTEGRATION_V3_DIR / "source_concordance_v3.csv"
    comp_df.to_csv(comp_csv, index=False)
    print(f"\nSaved cross-source concordance table to {comp_csv}")
    
    # Write notes_v3.md for both
    write_notes_v3("paleoclim", res_pc, comp_df)
    write_notes_v3("worldclim", res_wc, comp_df)
    
    print("\n[OK] Phase 8 processing complete!")

if __name__ == "__main__":
    main()
