# PaleoClim notes v2 (Multivariate Climate Stability & Zonal Statistics)

## Data
- Source: CHELSA / PaleoClim reconstructions at 10 arc-minute resolution.
- Periods: Present (current), Late Holocene (~4.2–0.3 ka), Last Glacial Maximum (LGM, ~21 ka).
- Variables:
  - BIO1: Mean annual temperature. Raw values in °C*10, scaled by 0.1 to °C.
  - BIO12: Annual precipitation. Raw values in mm (range 0.30 to 5,052 mm at 5° zonal scale). Unscaled.
  - BIO4: Temperature seasonality (standard deviation of temperature * 100). Unscaled.
  - BIO15: Precipitation seasonality (coefficient of variation, %). Unscaled.
- Alignment: LGM rasters reprojected to the present raster grid using `rasterio.warp.reproject` with bilinear resampling.

## Method
- True zonal cell statistics computed using `cell_zonal_stats()` over all valid land pixels inside 5° x 5° (1,473 valid land cells) and 2° x 2° (7,285 valid land cells) grid cells.
- Cell center definition: `floor(coord/cell)*cell + cell/2`.
- Temperature stability metrics:
  - `temp_lgm_change` = |Present - LGM| BIO1 in °C.
  - `temp_holo_change` = |Present - Late Holocene| BIO1 in °C.
  - `temp_instability` = sample SD of BIO1 across the 3 time slices.
- Precipitation stability metrics:
  - `precip_lgm_change_abs` = |Present - LGM| annual precipitation in mm.
  - `precip_lgm_change_rel` = |ln((P_lgm + 1) / (P_present + 1))| (primary precipitation metric).
  - `precip_instability` = sample SD of BIO12 across the 3 time slices.
- Seasonality variability metrics:
  - `bio4_change` = |Present - LGM| BIO4.
  - `bio15_change` = |Present - LGM| BIO15.
- Composite stability index:
  - Defined as the mean of the standardized z-scores of temperature instability and relative precipitation change:
    `composite_instability = (z(temp_instability) + z(precip_lgm_change_rel)) / 2`.
  - Higher index values mean higher climate change / instability; lower values mean greater long-term climatic stability across both temperature and moisture regimes.
- Point-sampled sensitivity run:
  - Computed at 17,396 GBIF points and averaged across the 369 shared 5° GBIF cells.

## Temperature Validation: Zonal vs Point-Sampled (369 shared GBIF cells)
| Metric | Point-Sampled Mean | Zonal Mean | Pearson r | Spearman rho |
|---|---|---|---|---|
| LGM change (°C) | 7.36 | 7.37 | 0.9819 | 0.9194 |
| Holocene change (°C) | 0.63 | 0.65 | 0.8876 | 0.8574 |
| Instability (SD, °C) | 4.10 | 4.09 | 0.9825 | 0.9190 |

- The zonal cell means match the point-sampled temperature values closely (r > 0.98 for LGM change and instability), confirming that the earlier findings were not an artifact of point sampling, while eliminating collection clustering bias.

## Global 5° Zonal Climate Summary (1,473 land cells)
| Variable / Metric | Min | Median | Mean | Max |
|---|---|---|---|---|
| Present BIO1 (°C) | -52.20 | 11.23 | 6.55 | 29.80 |
| LGM BIO1 (°C) | -79.90 | 1.15 | -5.73 | 25.10 |
| Temp LGM change (°C) | 0.10 | 9.07 | 12.30 | 36.40 |
| Temp Instability (SD, °C) | 0.52 | 5.00 | 6.84 | 20.91 |
| Present BIO12 (mm) | 0.30 | 478.95 | 802.60 | 5,052.00 |
| LGM BIO12 (mm) | 0.00 | 294.97 | 679.80 | 3,276.00 |
| Precip LGM change (abs, mm) | 0.12 | 95.98 | 145.38 | 1,776.00 |
| Precip LGM change (rel) | 0.00 | 0.35 | 0.48 | 2.27 |
| Precip Instability (SD, mm) | 0.15 | 56.29 | 84.49 | 1,006.50 |
| BIO4 LGM change (SD*100) | 0.26 | 757.61 | 1,356.68 | 8,772.57 |
| BIO15 LGM change (CV %) | 0.00 | 5.61 | 15.20 | 289.57 |
| Composite instability index | -1.13 | -0.20 | 0.02 | 2.74 |

## Key observations
- Global annual precipitation was lower at the LGM (mean 679.8 mm vs 802.6 mm at present), showing widespread glacial aridification.
- Relative precipitation change |ln((P_lgm+1)/(P_present+1))| ranges from 0.00 to 2.27 with a median of 0.35. The relative metric stabilizes variance compared to absolute change (which spans up to 1,776 mm in monsoon regions).
- Precipitation change is largest in tropical monsoon zones, Central Africa, and high-latitude glaciated margins.
- Composite instability index ranges from -1.13 (stable across both temperature and moisture regimes, such as equatorial rain forests and stable maritime refugia) to 2.74 (severely unstable, glaciated northern continents and arid shifts).

## Limitations
- CHELSA downscaling at 10 arc-minutes smooths steep micro-topography.
- LGM precipitation reconstructions carry larger uncertainty than temperature.
- 5° resolution averages distinct precipitation zones along mountain chains.

## Outputs
- processed/: `paleoclim_zonal_5deg.csv`, `paleoclim_zonal_2deg.csv`, `paleoclim_point_sampled_v2.csv`, `pc_summary_v2.csv`.
- figures/: `pc_precip_change.png`, `pc_composite_stability.png`, `pc_precip_change_hist.png`, `pc_composite_hist.png`.
