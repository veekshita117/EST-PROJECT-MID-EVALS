# WorldClim notes v2 (Multivariate Climate Stability & Zonal Statistics)

## Data
- Source: WorldClim v1.4 at 10 arc-minute resolution.
- Periods: Present (1960–1990), Mid-Holocene (~6 ka, CCSM4 simulation), Last Glacial Maximum (LGM, ~21 ka, CCSM4 simulation).
- Variables:
  - BIO1: Mean annual temperature. Raw values in °C*10, scaled by 0.1 to °C.
  - BIO12: Annual precipitation. Raw values in mm (range 1.44 to 5,133 mm at 5° zonal scale). Unscaled.
  - BIO4: Temperature seasonality (standard deviation of temperature * 100). Unscaled.
  - BIO15: Precipitation seasonality (coefficient of variation, %). Unscaled.
- Extent: Global coverage from -180° to 180° longitude and -60° to 90° latitude (Antarctica not covered).

## Method
- True zonal cell statistics computed using `cell_zonal_stats()` over all valid land pixels inside 5° x 5° (1,121 valid land cells) and 2° x 2° (5,359 valid land cells) grid cells.
- Cell center definition: `floor(coord/cell)*cell + cell/2`.
- Temperature stability metrics:
  - `temp_lgm_change` = |Present - LGM| BIO1 in °C.
  - `temp_holo_change` = |Present - Mid-Holocene| BIO1 in °C.
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
  - Computed at 17,396 GBIF points and averaged across the 374 shared 5° GBIF cells.

## Temperature Validation: Zonal vs Point-Sampled (374 shared GBIF cells)
| Metric | Point-Sampled Mean | Zonal Mean | Pearson r | Spearman rho |
|---|---|---|---|---|
| LGM change (°C) | 6.47 | 6.28 | 0.9869 | 0.9048 |
| Mid-Holocene change (°C) | 0.83 | 0.84 | 0.9507 | 0.9256 |
| Instability (SD, °C) | 3.55 | 3.44 | 0.9874 | 0.9072 |

- The zonal cell means match the point-sampled temperature values closely (r > 0.98 for LGM change and instability), confirming stability rankings are robust to spatial aggregation method.

## Global 5° Zonal Climate Summary (1,121 land cells)
| Variable / Metric | Min | Median | Mean | Max |
|---|---|---|---|---|
| Present BIO1 (°C) | -23.70 | 12.87 | 10.74 | 30.00 |
| LGM BIO1 (°C) | -37.10 | 6.21 | 2.11 | 28.50 |
| Temp LGM change (°C) | 1.10 | 7.42 | 9.07 | 28.80 |
| Temp Instability (SD, °C) | 0.61 | 4.09 | 4.99 | 16.03 |
| Present BIO12 (mm) | 1.44 | 634.35 | 949.98 | 5,132.60 |
| LGM BIO12 (mm) | 1.31 | 509.84 | 840.25 | 7,568.41 |
| Precip LGM change (abs, mm) | 0.00 | 120.82 | 176.24 | 2,457.99 |
| Precip LGM change (rel) | 0.00 | 0.22 | 0.35 | 1.83 |
| Precip Instability (SD, mm) | 0.01 | 75.60 | 110.92 | 1,408.22 |
| BIO4 LGM change (SD*100) | 0.00 | 512.96 | 1,336.29 | 9,399.86 |
| BIO15 LGM change (CV %) | 0.01 | 6.17 | 9.74 | 95.62 |
| Composite instability index | -0.97 | -0.34 | 0.00 | 3.30 |

## Comparison with PaleoClim (1,091 shared 5° land cells)
| Metric | PaleoClim Mean | WorldClim Mean | Pearson r | Spearman rho | p-value |
|---|---|---|---|---|---|
| Temperature LGM Change (°C) | 10.87 | 9.17 | 0.955 | 0.940 | < 0.0001 |
| Temperature Instability (SD, °C) | 6.04 | 5.04 | 0.953 | 0.932 | < 0.0001 |
| Relative Precip Change | 0.44 | 0.35 | 0.925 | 0.873 | < 0.0001 |
| Absolute Precip Change (mm) | 148.06 | 178.68 | 0.650 | 0.780 | < 0.0001 |
| Precip Instability (mm) | 86.44 | 112.44 | 0.647 | 0.738 | < 0.0001 |
| BIO4 Change (SD*100) | 1,372.68 | 1,351.46 | 0.896 | 0.778 | < 0.0001 |
| BIO15 Change (CV %) | 15.01 | 9.87 | 0.677 | 0.736 | < 0.0001 |
| Composite Instability Index | 0.02 | 0.00 | 0.966 | 0.927 | < 0.0001 |

- Both sources agree on relative precipitation change (rho = 0.873) and composite instability (rho = 0.927), showing that long-term stability gradients are consistent between CHELSA and CCSM4 simulations.
- WorldClim has slightly lower temperature change at high latitudes due to the absence of Antarctica and differing ice-sheet boundary conditions in CCSM4.

## Limitations
- Single GCM simulation (CCSM4), introducing model-specific moisture biases.
- Coverage truncates at 60°S (excluding Antarctica).
- 5° resolution averages distinct precipitation zones along mountain chains.

## Outputs
- processed/: `worldclim_zonal_5deg.csv`, `worldclim_zonal_2deg.csv`, `worldclim_point_sampled_v2.csv`, `wc_summary_v2.csv`.
- figures/: `wc_precip_change.png`, `wc_composite_stability.png`, `wc_precip_change_hist.png`, `wc_composite_hist.png`.
- integration/figures/: `agreement_precip_change.png`, `agreement_composite_index.png`, `table_metric_agreement.csv`.
