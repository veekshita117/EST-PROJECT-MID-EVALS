# Figures and Tables Inventory

This document provides a comprehensive inventory of all final figures and tables produced across the repository, categorized by analysis module.

---

## 1. Primary Statistical Integration (`integration_v2/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`integration_v2/figures/coef_plot.png`](integration_v2/figures/coef_plot.png) | Standardized regression coefficients ($\beta \pm 95\%$ CI) comparing OLS, Spatial Error, and Spatial Lag models (PaleoClim 5° grid, $n=188$). |
| [`integration_v2/figures/moran_scatter.png`](integration_v2/figures/moran_scatter.png) | Moran scatter plots for raw species richness ($I = 0.125, p = 0.005$) and OLS model residuals ($I = 0.199, p = 0.001$). |
| [`integration_v2/figures/residual_maps.png`](integration_v2/figures/residual_maps.png) | Global geographic distribution of spatially autocorrelated OLS residuals versus Spatial Error filtered innovations ($\varepsilon = u - \lambda W u$, $I = 0.0012, p = 0.395$). |
| [`integration_v2/figures/observed_vs_predicted.png`](integration_v2/figures/observed_vs_predicted.png) | Observed versus predicted $\ln(1 + \text{richness})$ with 1:1 line calibration ($R^2 = 0.876$). |

### Tables
| File Path | Description / Caption |
|---|---|
| [`integration_v2/figures/table_correlations_v2.csv`](integration_v2/figures/table_correlations_v2.csv) | Bivariate and partial Spearman correlations across all 14 climate metrics at 5° and 2° with spatial-block bootstrap 95% CIs and Benjamini-Hochberg FDR $q$-values. |
| [`integration_v2/figures/table_models_comparison.csv`](integration_v2/figures/table_models_comparison.csv) | Full econometric regression table comparing OLS, Maximum Likelihood Spatial Error, and Spatial Lag models across PaleoClim and WorldClim with AIC, pseudo-$R^2$, and residual Moran's $I$. |
| [`integration_v2/figures/table_vif.csv`](integration_v2/figures/table_vif.csv) | Variance Inflation Factors (VIF) for all predictors and controls, confirming absence of severe multicollinearity ($\text{VIF} < 2.05$). |
| [`integration_v2/figures/table_quartiles_v2.csv`](integration_v2/figures/table_quartiles_v2.csv) | Species richness and occurrence record distributions (count, mean, median, SD, min, max, mean records) across stability quartiles, illustrating the effort confound. |
| [`integration_v2/figures/table_dataset_agreement.csv`](integration_v2/figures/table_dataset_agreement.csv) | Rank concordance (Spearman $\rho$ and $p$-values) between PaleoClim and WorldClim climate stability metrics across analysed cells. |
| [`integration_v2/figures/table_hotspots_v2.csv`](integration_v2/figures/table_hotspots_v2.csv) | 2x2 contingency table classifying cells into rich-and-stable, rich-and-unstable, poor-and-stable, and poor-and-unstable. |
| [`integration_v2/figures/table_spatial_cv.csv`](integration_v2/figures/table_spatial_cv.csv) | 5-fold 20° spatial-block cross-validation performance ($R^2_{\text{CV}}$ and $\text{RMSE}_{\text{CV}}$) for full model versus controls-only model. |
| [`integration_v2/processed/data_5deg.csv`](integration_v2/processed/data_5deg.csv) | Master integrated analytical table at 5° grid cell resolution merging GBIF richness, Copernicus DEM elevation, PaleoClim, and WorldClim climate metrics ($n = 375$ cells with records). |
| [`integration_v2/processed/data_2deg.csv`](integration_v2/processed/data_2deg.csv) | Master integrated analytical table at 2° grid cell resolution for spatial robustness checks ($n = 893$ cells with records). |

---

## 2. Copernicus DEM GLO-90 Elevation & Heterogeneity (`COPERNICUS_DEM/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`COPERNICUS_DEM/figures/dem_mean_elevation.png`](COPERNICUS_DEM/figures/dem_mean_elevation.png) | Global map of mean cell elevation (meters) aggregated from Copernicus GLO-90 DEM tiles across 5° land cells. |
| [`COPERNICUS_DEM/figures/dem_heterogeneity.png`](COPERNICUS_DEM/figures/dem_heterogeneity.png) | Global map of topographic heterogeneity (relief range = $\text{elevation}_{\max} - \text{elevation}_{\min}$) across 5° cells. |
| [`COPERNICUS_DEM/figures/dem_histograms.png`](COPERNICUS_DEM/figures/dem_histograms.png) | Frequency distributions of cell mean elevation, elevation standard deviation, and relief range. |
| [`COPERNICUS_DEM/figures/dem_vs_lgm_change.png`](COPERNICUS_DEM/figures/dem_vs_lgm_change.png) | Scatter plots showing relationships between topographic metrics (elevation mean and relief range) and Quaternary climate stability. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`COPERNICUS_DEM/processed/dem_cells_5deg.csv`](COPERNICUS_DEM/processed/dem_cells_5deg.csv) | Cell-level elevation statistics (mean, SD, min, max, relief range, pixel count) for 375 grid cells at 5° resolution. |
| [`COPERNICUS_DEM/processed/dem_cells_2deg.csv`](COPERNICUS_DEM/processed/dem_cells_2deg.csv) | Cell-level elevation statistics for 2,231 grid cells at 2° resolution. |
| [`COPERNICUS_DEM/processed/table_elevation_correlations.csv`](COPERNICUS_DEM/processed/table_elevation_correlations.csv) | Pearson and Spearman correlation coefficients between elevation metrics, climate instability, and absolute latitude. |

---

## 3. Climate Stability Expansion (`PALEOCLIM/` and `WORLDCLIM/`)

### PaleoClim Figures & Tables
| File Path | Description / Caption |
|---|---|
| [`PALEOCLIM/figures/pc_precip_change.png`](PALEOCLIM/figures/pc_precip_change.png) | Global map of PaleoClim relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$) across 5° land cells. |
| [`PALEOCLIM/figures/pc_composite_stability.png`](PALEOCLIM/figures/pc_composite_stability.png) | Global map of PaleoClim composite climatic instability index (mean of temperature instability and relative precipitation change z-scores). |
| [`PALEOCLIM/figures/pc_precip_change_hist.png`](PALEOCLIM/figures/pc_precip_change_hist.png) | Distribution of PaleoClim absolute and relative precipitation changes from LGM to Present. |
| [`PALEOCLIM/figures/pc_composite_hist.png`](PALEOCLIM/figures/pc_composite_hist.png) | Histogram of the PaleoClim composite climatic instability index across 1,473 global land cells. |
| [`PALEOCLIM/figures/pc_bio1_present.png`](PALEOCLIM/figures/pc_bio1_present.png) | Mean annual temperature (BIO1, °C) at Present from PaleoClim. |
| [`PALEOCLIM/figures/pc_bio1_holocene.png`](PALEOCLIM/figures/pc_bio1_holocene.png) | Mean annual temperature (BIO1, °C) in the Late Holocene (sub-Boreal) from PaleoClim. |
| [`PALEOCLIM/figures/pc_bio1_lgm.png`](PALEOCLIM/figures/pc_bio1_lgm.png) | Mean annual temperature (BIO1, °C) at Last Glacial Maximum from PaleoClim. |
| [`PALEOCLIM/figures/pc_lgm_change.png`](PALEOCLIM/figures/pc_lgm_change.png) | Absolute temperature change ($|\text{Present} - \text{LGM}|$, °C) across 5° cells from PaleoClim. |
| [`PALEOCLIM/figures/pc_change_hist.png`](PALEOCLIM/figures/pc_change_hist.png) | Histogram of LGM temperature change and Holocene change across GBIF cells. |
| [`PALEOCLIM/processed/paleoclim_zonal_5deg.csv`](PALEOCLIM/processed/paleoclim_zonal_5deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 1,473 global land cells at 5° resolution. |
| [`PALEOCLIM/processed/paleoclim_zonal_2deg.csv`](PALEOCLIM/processed/paleoclim_zonal_2deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 7,285 global land cells at 2° resolution. |
| [`PALEOCLIM/processed/paleoclim_point_sampled_v2.csv`](PALEOCLIM/processed/paleoclim_point_sampled_v2.csv) | Expanded point-sampled metrics for temperature, precipitation, and seasonality across 369 GBIF cells. |
| [`PALEOCLIM/processed/paleoclim_cell_stability.csv`](PALEOCLIM/processed/paleoclim_cell_stability.csv) | Baseline point-sampled temperature stability table across 369 GBIF cells. |
| [`PALEOCLIM/processed/pc_summary_v2.csv`](PALEOCLIM/processed/pc_summary_v2.csv) | Global summary statistics for all expanded PaleoClim variables. |

### WorldClim Figures & Tables
| File Path | Description / Caption |
|---|---|
| [`WORLDCLIM/figures/wc_precip_change.png`](WORLDCLIM/figures/wc_precip_change.png) | Global map of WorldClim relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$) across 5° land cells. |
| [`WORLDCLIM/figures/wc_composite_stability.png`](WORLDCLIM/figures/wc_composite_stability.png) | Global map of WorldClim composite climatic instability index across 5° land cells. |
| [`WORLDCLIM/figures/wc_precip_change_hist.png`](WORLDCLIM/figures/wc_precip_change_hist.png) | Histogram of WorldClim absolute and relative precipitation changes from LGM to Present. |
| [`WORLDCLIM/figures/wc_composite_hist.png`](WORLDCLIM/figures/wc_composite_hist.png) | Histogram of WorldClim composite climatic instability index across 1,121 global land cells. |
| [`WORLDCLIM/figures/wc_bio1_present.png`](WORLDCLIM/figures/wc_bio1_present.png) | Mean annual temperature (BIO1, °C) at Present from WorldClim. |
| [`WORLDCLIM/figures/wc_bio1_holocene.png`](WORLDCLIM/figures/wc_bio1_holocene.png) | Mean annual temperature (BIO1, °C) in the Mid-Holocene from WorldClim (CCSM4). |
| [`WORLDCLIM/figures/wc_bio1_lgm.png`](WORLDCLIM/figures/wc_bio1_lgm.png) | Mean annual temperature (BIO1, °C) at Last Glacial Maximum from WorldClim (CCSM4). |
| [`WORLDCLIM/figures/wc_lgm_change.png`](WORLDCLIM/figures/wc_lgm_change.png) | Absolute temperature change ($|\text{Present} - \text{LGM}|$, °C) across 5° cells from WorldClim. |
| [`WORLDCLIM/figures/wc_change_hist.png`](WORLDCLIM/figures/wc_change_hist.png) | Histogram of WorldClim LGM temperature change and Mid-Holocene change. |
| [`WORLDCLIM/processed/worldclim_zonal_5deg.csv`](WORLDCLIM/processed/worldclim_zonal_5deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 1,121 global land cells at 5° resolution. |
| [`WORLDCLIM/processed/worldclim_zonal_2deg.csv`](WORLDCLIM/processed/worldclim_zonal_2deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 5,359 global land cells at 2° resolution. |
| [`WORLDCLIM/processed/worldclim_point_sampled_v2.csv`](WORLDCLIM/processed/worldclim_point_sampled_v2.csv) | Expanded point-sampled metrics for temperature, precipitation, and seasonality across 374 GBIF cells. |
| [`WORLDCLIM/processed/worldclim_cell_stability.csv`](WORLDCLIM/processed/worldclim_cell_stability.csv) | Baseline point-sampled temperature stability table across 374 GBIF cells. |
| [`WORLDCLIM/processed/wc_summary_v2.csv`](WORLDCLIM/processed/wc_summary_v2.csv) | Global summary statistics for all expanded WorldClim variables. |

---

## 4. Modern Biodiversity & Occurrence Records (`GBIF/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`GBIF/figures/gbif_records_map.png`](GBIF/figures/gbif_records_map.png) | Global scatter plot of 17,396 cleaned GBIF occurrence points. |
| [`GBIF/figures/gbif_richness_map.png`](GBIF/figures/gbif_richness_map.png) | Global map of unique species richness per 5° grid cell. |
| [`GBIF/figures/gbif_richness_latitude.png`](GBIF/figures/gbif_richness_latitude.png) | Mean species richness across 10° latitudinal bands showing prominent southern hemisphere peak. |
| [`GBIF/figures/gbif_records_per_cell.png`](GBIF/figures/gbif_records_per_cell.png) | Distribution of occurrence records per cell on logarithmic scale illustrating uneven sampling effort. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`GBIF/processed/gbif_points_clean.csv`](GBIF/processed/gbif_points_clean.csv) | Cleaned occurrence records with validated coordinates and cell assignments (17,396 records, 6,080 species). |
| [`GBIF/processed/gbif_richness_cells.csv`](GBIF/processed/gbif_richness_cells.csv) | Species richness and record counts aggregated across 375 grid cells at 5° resolution. |
| [`GBIF/processed/gbif_summary.csv`](GBIF/processed/gbif_summary.csv) | Global summary metrics of cleaned GBIF dataset (total records, species, cells, median and max richness). |
| [`GBIF/processed/gbif_top10_cells.csv`](GBIF/processed/gbif_top10_cells.csv) | Top 10 cells ranked by observed species richness. |

---

## 5. Mid-Evaluation Baseline Integration (`integration/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`integration/figures/int_scatter.png`](integration/figures/int_scatter.png) | Scatter plot of species richness versus LGM temperature change for PaleoClim and WorldClim with OLS trendlines. |
| [`integration/figures/int_quartiles.png`](integration/figures/int_quartiles.png) | Mean species richness across stability quartiles (Q1 most stable to Q4 least stable). |
| [`integration/figures/int_dataset_agreement.png`](integration/figures/int_dataset_agreement.png) | Scatter plot comparing PaleoClim and WorldClim LGM temperature change across shared cells ($\rho = 0.754$). |
| [`integration/figures/int_hotspots.png`](integration/figures/int_hotspots.png) | Global map of rich-and-stable versus rich-and-unstable cells based on mid-eval temperature stability. |
| [`integration/figures/agreement_precip_change.png`](integration/figures/agreement_precip_change.png) | Agreement scatter plot between PaleoClim and WorldClim relative precipitation change ($r = 0.925, \rho = 0.873$). |
| [`integration/figures/agreement_composite_index.png`](integration/figures/agreement_composite_index.png) | Agreement scatter plot between PaleoClim and WorldClim composite climatic instability index ($r = 0.966, \rho = 0.927$). |

### Tables
| File Path | Description / Caption |
|---|---|
| [`integration/figures/table_correlations.csv`](integration/figures/table_correlations.csv) | Baseline mid-eval Spearman and partial Spearman correlations on 188 cells. |
| [`integration/figures/table_integrated_cells.csv`](integration/figures/table_integrated_cells.csv) | Baseline merged dataset of 188 cells with $\ge 10$ records containing GBIF richness and point-sampled climate stability. |
| [`integration/figures/table_quartiles.csv`](integration/figures/table_quartiles.csv) | Baseline richness summary by stability quartile. |
| [`integration/figures/table_metric_agreement.csv`](integration/figures/table_metric_agreement.csv) | Expanded concordance statistics (Pearson $r$ and Spearman $\rho$) across 1,091 shared 5° land cells. |
