# Figures and Tables Inventory

This document provides a comprehensive inventory of all final figures and tables produced across the repository, categorized by analysis module.

---

## 1. Primary Statistical Integration (`integration_v2/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`tables/integration_v2/coef_plot.png`](tables/integration_v2/coef_plot.png) | Standardized regression coefficients ($\beta \pm 95\%$ CI) comparing OLS, Spatial Error, and Spatial Lag models (PaleoClim 5° grid, $n=188$). |
| [`tables/integration_v2/moran_scatter.png`](tables/integration_v2/moran_scatter.png) | Moran scatter plots for raw species richness ($I = 0.125, p = 0.005$) and OLS model residuals ($I = 0.199, p = 0.001$). |
| [`tables/integration_v2/residual_maps.png`](tables/integration_v2/residual_maps.png) | Global geographic distribution of spatially autocorrelated OLS residuals versus Spatial Error filtered innovations ($\varepsilon = u - \lambda W u$, $I = 0.0012, p = 0.395$). |
| [`tables/integration_v2/observed_vs_predicted.png`](tables/integration_v2/observed_vs_predicted.png) | Observed versus predicted $\ln(1 + \text{richness})$ with 1:1 line calibration ($R^2 = 0.876$). |

### Tables
| File Path | Description / Caption |
|---|---|
| [`tables/integration_v2/table_correlations_v2.csv`](tables/integration_v2/table_correlations_v2.csv) | Bivariate and partial Spearman correlations across all 14 climate metrics at 5° and 2° with spatial-block bootstrap 95% CIs and Benjamini-Hochberg FDR $q$-values. |
| [`tables/integration_v2/table_models_comparison.csv`](tables/integration_v2/table_models_comparison.csv) | Full econometric regression table comparing OLS, Maximum Likelihood Spatial Error, and Spatial Lag models across PaleoClim and WorldClim with AIC, pseudo-$R^2$, and residual Moran's $I$. |
| [`tables/integration_v2/table_vif.csv`](tables/integration_v2/table_vif.csv) | Variance Inflation Factors (VIF) for all predictors and controls, confirming absence of severe multicollinearity ($\text{VIF} < 2.05$). |
| [`tables/integration_v2/table_quartiles_v2.csv`](tables/integration_v2/table_quartiles_v2.csv) | Species richness and occurrence record distributions (count, mean, median, SD, min, max, mean records) across stability quartiles, illustrating the effort confound. |
| [`tables/integration_v2/table_dataset_agreement.csv`](tables/integration_v2/table_dataset_agreement.csv) | Rank concordance (Spearman $\rho$ and $p$-values) between PaleoClim and WorldClim climate stability metrics across analysed cells. |
| [`tables/integration_v2/table_hotspots_v2.csv`](tables/integration_v2/table_hotspots_v2.csv) | 2x2 contingency table classifying cells into rich-and-stable, rich-and-unstable, poor-and-stable, and poor-and-unstable. |
| [`tables/integration_v2/table_spatial_cv.csv`](tables/integration_v2/table_spatial_cv.csv) | 5-fold 20° spatial-block cross-validation performance ($R^2_{\text{CV}}$ and $\text{RMSE}_{\text{CV}}$) for full model versus controls-only model. |
| [`../data/integration_v2/data_5deg.csv`](../data/integration_v2/data_5deg.csv) | Master integrated analytical table at 5° grid cell resolution merging GBIF richness, Copernicus DEM elevation, PaleoClim, and WorldClim climate metrics ($n = 375$ cells with records). |
| [`../data/integration_v2/data_2deg.csv`](../data/integration_v2/data_2deg.csv) | Master integrated analytical table at 2° grid cell resolution for spatial robustness checks ($n = 893$ cells with records). |

---

## 2. Copernicus DEM GLO-90 Elevation & Heterogeneity (`COPERNICUS_DEM/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`figures/dem/dem_mean_elevation.png`](figures/dem/dem_mean_elevation.png) | Global map of mean cell elevation (meters) aggregated from Copernicus GLO-90 DEM tiles across 5° land cells. |
| [`figures/dem/dem_heterogeneity.png`](figures/dem/dem_heterogeneity.png) | Global map of topographic heterogeneity (relief range = $\text{elevation}_{\max} - \text{elevation}_{\min}$) across 5° cells. |
| [`figures/dem/dem_histograms.png`](figures/dem/dem_histograms.png) | Frequency distributions of cell mean elevation, elevation standard deviation, and relief range. |
| [`figures/dem/dem_vs_lgm_change.png`](figures/dem/dem_vs_lgm_change.png) | Scatter plots showing relationships between topographic metrics (elevation mean and relief range) and Quaternary climate stability. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`../data/dem/dem_cells_5deg.csv`](../data/dem/dem_cells_5deg.csv) | Cell-level elevation statistics (mean, SD, min, max, relief range, pixel count) for 375 grid cells at 5° resolution. |
| [`../data/dem/dem_cells_2deg.csv`](../data/dem/dem_cells_2deg.csv) | Cell-level elevation statistics for 2,231 grid cells at 2° resolution. |
| [`../data/dem/table_elevation_correlations.csv`](../data/dem/table_elevation_correlations.csv) | Pearson and Spearman correlation coefficients between elevation metrics, climate instability, and absolute latitude. |

---

## 3. Climate Stability Expansion (`PALEOCLIM/` and `WORLDCLIM/`)

### PaleoClim Figures & Tables
| File Path | Description / Caption |
|---|---|
| [`figures/paleoclim/pc_precip_change.png`](figures/paleoclim/pc_precip_change.png) | Global map of PaleoClim relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$) across 5° land cells. |
| [`figures/paleoclim/pc_composite_stability.png`](figures/paleoclim/pc_composite_stability.png) | Global map of PaleoClim composite climatic instability index (mean of temperature instability and relative precipitation change z-scores). |
| [`figures/paleoclim/pc_precip_change_hist.png`](figures/paleoclim/pc_precip_change_hist.png) | Distribution of PaleoClim absolute and relative precipitation changes from LGM to Present. |
| [`figures/paleoclim/pc_composite_hist.png`](figures/paleoclim/pc_composite_hist.png) | Histogram of the PaleoClim composite climatic instability index across 1,473 global land cells. |
| [`figures/paleoclim/pc_bio1_present.png`](figures/paleoclim/pc_bio1_present.png) | Mean annual temperature (BIO1, °C) at Present from PaleoClim. |
| [`figures/paleoclim/pc_bio1_holocene.png`](figures/paleoclim/pc_bio1_holocene.png) | Mean annual temperature (BIO1, °C) in the Late Holocene (sub-Boreal) from PaleoClim. |
| [`figures/paleoclim/pc_bio1_lgm.png`](figures/paleoclim/pc_bio1_lgm.png) | Mean annual temperature (BIO1, °C) at Last Glacial Maximum from PaleoClim. |
| [`figures/paleoclim/pc_lgm_change.png`](figures/paleoclim/pc_lgm_change.png) | Absolute temperature change ($|\text{Present} - \text{LGM}|$, °C) across 5° cells from PaleoClim. |
| [`figures/paleoclim/pc_change_hist.png`](figures/paleoclim/pc_change_hist.png) | Histogram of LGM temperature change and Holocene change across GBIF cells. |
| [`../data/paleoclim/paleoclim_zonal_5deg.csv`](../data/paleoclim/paleoclim_zonal_5deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 1,473 global land cells at 5° resolution. |
| [`../data/paleoclim/paleoclim_zonal_2deg.csv`](../data/paleoclim/paleoclim_zonal_2deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 7,285 global land cells at 2° resolution. |
| [`../data/paleoclim/paleoclim_point_sampled_v2.csv`](../data/paleoclim/paleoclim_point_sampled_v2.csv) | Expanded point-sampled metrics for temperature, precipitation, and seasonality across 369 GBIF cells. |
| [`../data/paleoclim/paleoclim_cell_stability.csv`](../data/paleoclim/paleoclim_cell_stability.csv) | Baseline point-sampled temperature stability table across 375 GBIF cells. |
| [`../data/paleoclim/pc_summary_v2.csv`](../data/paleoclim/pc_summary_v2.csv) | Global summary statistics for all expanded PaleoClim variables. |

### WorldClim Figures & Tables
| File Path | Description / Caption |
|---|---|
| [`figures/worldclim/wc_precip_change.png`](figures/worldclim/wc_precip_change.png) | Global map of WorldClim relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$) across 5° land cells. |
| [`figures/worldclim/wc_composite_stability.png`](figures/worldclim/wc_composite_stability.png) | Global map of WorldClim composite climatic instability index across 5° land cells. |
| [`figures/worldclim/wc_precip_change_hist.png`](figures/worldclim/wc_precip_change_hist.png) | Histogram of WorldClim absolute and relative precipitation changes from LGM to Present. |
| [`figures/worldclim/wc_composite_hist.png`](figures/worldclim/wc_composite_hist.png) | Histogram of WorldClim composite climatic instability index across 1,121 global land cells. |
| [`figures/worldclim/wc_bio1_present.png`](figures/worldclim/wc_bio1_present.png) | Mean annual temperature (BIO1, °C) at Present from WorldClim. |
| [`figures/worldclim/wc_bio1_holocene.png`](figures/worldclim/wc_bio1_holocene.png) | Mean annual temperature (BIO1, °C) in the Mid-Holocene from WorldClim (CCSM4). |
| [`figures/worldclim/wc_bio1_lgm.png`](figures/worldclim/wc_bio1_lgm.png) | Mean annual temperature (BIO1, °C) at Last Glacial Maximum from WorldClim (CCSM4). |
| [`figures/worldclim/wc_lgm_change.png`](figures/worldclim/wc_lgm_change.png) | Absolute temperature change ($|\text{Present} - \text{LGM}|$, °C) across 5° cells from WorldClim. |
| [`figures/worldclim/wc_change_hist.png`](figures/worldclim/wc_change_hist.png) | Histogram of WorldClim LGM temperature change and Mid-Holocene change. |
| [`../data/worldclim/worldclim_zonal_5deg.csv`](../data/worldclim/worldclim_zonal_5deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 1,121 global land cells at 5° resolution. |
| [`../data/worldclim/worldclim_zonal_2deg.csv`](../data/worldclim/worldclim_zonal_2deg.csv) | Zonal statistics for BIO1, BIO12, BIO4, BIO15, and derived stability metrics across 5,359 global land cells at 2° resolution. |
| [`../data/worldclim/worldclim_point_sampled_v2.csv`](../data/worldclim/worldclim_point_sampled_v2.csv) | Expanded point-sampled metrics for temperature, precipitation, and seasonality across 374 GBIF cells. |
| [`../data/worldclim/worldclim_cell_stability.csv`](../data/worldclim/worldclim_cell_stability.csv) | Baseline point-sampled temperature stability table across 374 GBIF cells. |
| [`../data/worldclim/wc_summary_v2.csv`](../data/worldclim/wc_summary_v2.csv) | Global summary statistics for all expanded WorldClim variables. |

---

## 4. Modern Biodiversity & Occurrence Records (`GBIF/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`figures/gbif/gbif_records_map.png`](figures/gbif/gbif_records_map.png) | Global scatter plot of 17,396 cleaned GBIF occurrence points. |
| [`figures/gbif/gbif_richness_map.png`](figures/gbif/gbif_richness_map.png) | Global map of unique species richness per 5° grid cell. |
| [`figures/gbif/gbif_richness_latitude.png`](figures/gbif/gbif_richness_latitude.png) | Mean species richness across 10° latitudinal bands showing prominent southern hemisphere peak. |
| [`figures/gbif/gbif_records_per_cell.png`](figures/gbif/gbif_records_per_cell.png) | Distribution of occurrence records per cell on logarithmic scale illustrating uneven sampling effort. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`../data/gbif/gbif_points_clean.csv`](../data/gbif/gbif_points_clean.csv) | Cleaned occurrence records with validated coordinates and cell assignments (17,396 records, 6,080 species). |
| [`../data/gbif/gbif_richness_cells.csv`](../data/gbif/gbif_richness_cells.csv) | Species richness and record counts aggregated across 375 grid cells at 5° resolution. |
| [`../data/gbif/gbif_summary.csv`](../data/gbif/gbif_summary.csv) | Global summary metrics of cleaned GBIF dataset (total records, species, cells, median and max richness). |
| [`../data/gbif/gbif_top10_cells.csv`](../data/gbif/gbif_top10_cells.csv) | Top 10 cells ranked by observed species richness. |

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

---

## 6. IUCN Terrestrial Vertebrate Range Data (`IUCN/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`figures/iucn/iucn_richness_5deg.png`](figures/iucn/iucn_richness_5deg.png) | Global vertebrate richness map from expert range maps at 5° resolution ($n = 755$ land cells). |
| [`figures/iucn/iucn_endemism_5deg.png`](figures/iucn/iucn_endemism_5deg.png) | Global range-size weighted endemism (CRI) map across 5° land cells. |
| [`figures/iucn/iucn_small_range_5deg.png`](figures/iucn/iucn_small_range_5deg.png) | Global distribution of small-range vertebrate richness (bottom quartile range size) at 5° resolution. |
| [`figures/iucn/iucn_vs_gbif_scatter.png`](figures/iucn/iucn_vs_gbif_scatter.png) | Scatter plot comparing IUCN expert range richness versus GBIF sampled occurrence richness across shared cells. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`../data/iucn/iucn_cells_5deg.csv`](../data/iucn/iucn_cells_5deg.csv) | Cell-level vertebrate richness, endemism, and taxonomic metrics across 755 global land cells at 5° resolution. |
| [`../data/iucn/iucn_cells_2deg.csv`](../data/iucn/iucn_cells_2deg.csv) | Cell-level vertebrate richness, endemism, and taxonomic metrics across 4,397 global land cells at 2° resolution. |

---

## 7. Synthesis & Statistical Inference (`integration_v3/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`figures/integration_v3/hotspot_spatial_null.png`](figures/integration_v3/hotspot_spatial_null.png) | Empirical odds ratios versus 1,000 spherical-rotation null permutations for richness and endemism hotspot enrichment. |
| [`figures/integration_v3/quantile_slopes.png`](figures/integration_v3/quantile_slopes.png) | Conditional quantile regression slopes across $\tau \in \{0.50, 0.75, 0.90\}$ illustrating the upper-bound ceiling constraint. |
| [`figures/integration_v3/interaction_surfaces.png`](figures/integration_v3/interaction_surfaces.png) | 2D interaction surfaces showing velocity effect modulation by contemporary precipitation and seasonality. |
| [`figures/integration_v3/taxa_comparison.png`](figures/integration_v3/taxa_comparison.png) | Standardized sensitivity coefficients and partial rank correlations comparing Amphibia, Mammalia, and Reptilia. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`tables/integration_v3/reproduce_188_gbif.csv`](tables/integration_v3/reproduce_188_gbif.csv) | Exact re-estimation benchmark replicating the 188-cell GBIF regression results. |
| [`tables/integration_v3/correlations_5deg.csv`](tables/integration_v3/correlations_5deg.csv) | Bivariate and partial rank correlations across 755 5° land cells with 20° block-bootstrap CIs and BH-FDR $q$-values. |
| [`tables/integration_v3/correlations_2deg.csv`](tables/integration_v3/correlations_2deg.csv) | Sensitivity rank correlations across 4,395 2° land cells with block-bootstrap CIs and BH-FDR $q$-values. |
| [`tables/integration_v3/hotspot_enrichment.csv`](tables/integration_v3/hotspot_enrichment.csv) | Hotspot overlap odds ratios comparing naive Fisher exact test against spherical rotation null model. |
| [`tables/integration_v3/quantile_regression.csv`](tables/integration_v3/quantile_regression.csv) | Quantile regression parameter estimates and block-bootstrap standard errors across quantiles $\tau \in \{0.50, 0.75, 0.90\}$. |
| [`tables/integration_v3/spatial_models.csv`](tables/integration_v3/spatial_models.csv) | Maximum Likelihood Spatial Error ($\lambda$) and Spatial Lag ($\rho$) regression tables with AIC comparisons. |
| [`tables/integration_v3/interactions.csv`](tables/integration_v3/interactions.csv) | OLS regression estimates for macroclimatic interaction terms (velocity $\times$ precipitation, velocity $\times$ seasonality). |
| [`tables/integration_v3/taxa_comparison.csv`](tables/integration_v3/taxa_comparison.csv) | Taxonomic hierarchy comparison testing the Sandel et al. (2011) vulnerability ordering. |
| [`integration_v3/source_concordance_v3.csv`](integration_v3/source_concordance_v3.csv) | Cross-source rank concordance between PaleoClim and WorldClim derived velocity and anomaly metrics. |
| [`../data/integration/data_v3_5deg.csv`](../data/integration/data_v3_5deg.csv) | Master Phase 9 synthesis table at 5° resolution merging IUCN, GBIF, PaleoClim, WorldClim, and Copernicus DEM ($n = 755$). |
| [`../data/integration/data_v3_2deg.csv`](../data/integration/data_v3_2deg.csv) | Master Phase 9 synthesis table at 2° resolution ($n = 4,397$). |

---

## 8. Machine Learning Evaluation (`ml/`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`ml/paleoclim_base/figures/cv_r2_comparison.png`](ml/paleoclim_base/figures/cv_r2_comparison.png) | Cross-validated $R^2$ performance across model classes (OLS, Ridge, RF, HGB) and feature hierarchies. |
| [`ml/paleoclim_base/figures/forest_delta_r2.png`](ml/paleoclim_base/figures/forest_delta_r2.png) | Forest plot of incremental $\Delta R^2$ with 95% spatial-block bootstrap confidence intervals. |
| [`ml/paleoclim_base/figures/loco_heatmap_r2.png`](ml/paleoclim_base/figures/loco_heatmap_r2.png) | Heatmap of Leave-One-Continent-Out (LOCO) generalization $R^2$ scores across continental landmasses. |
| [`ml/paleoclim_base/figures/loco_delta_r2.png`](ml/paleoclim_base/figures/loco_delta_r2.png) | Bar chart of incremental LOCO $\Delta R^2$ per held-out continent. |
| [`ml/paleoclim_base/figures/grouped_importance_bars.png`](ml/paleoclim_base/figures/grouped_importance_bars.png) | Grouped permutation feature importance on held-out test folds showing effort overdominance. |
| [`ml/paleoclim_base/figures/pdp_ice_profiles.png`](ml/paleoclim_base/figures/pdp_ice_profiles.png) | Partial dependence and individual conditional expectation (ICE) traces for composite climate instability. |
| [`ml/paleoclim_base/figures/pdp_2d_stability_relief.png`](ml/paleoclim_base/figures/pdp_2d_stability_relief.png) | 2D partial dependence surface showing non-linear interaction between climate stability and relief range. |
| [`ml/paleoclim_base/figures/moran_correlogram.png`](ml/paleoclim_base/figures/moran_correlogram.png) | Spatial correlogram of out-of-fold residuals demonstrating persistent positive spatial autocorrelation. |
| [`ml/paleoclim_base/figures/residual_map_best_m2.png`](ml/paleoclim_base/figures/residual_map_best_m2.png) | Geographic map of cross-validated residuals from the best-performing stability model. |
| [`ml/COMPARISON/figures/forest_delta_r2_all_configs.png`](ml/COMPARISON/figures/forest_delta_r2_all_configs.png) | Master forest plot comparing $\Delta R^2$ across resolutions (PaleoClim 5° vs 2°). Note: the committed image predates the cleanup and still shows the removed WorldClim ML rows. |
| [`ml/COMPARISON/figures/heatmap_cross_configuration.png`](ml/COMPARISON/figures/heatmap_cross_configuration.png) | Cross-resolution robustness heatmap (PaleoClim 5° vs 2°). Note: the committed image predates the cleanup and still shows the removed WorldClim ML rows. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`ml/COMPARISON/comparison_table.csv`](ml/COMPARISON/comparison_table.csv) | Master synthesis table compiling performance metrics for the PaleoClim 5° and 2° configurations. |
| [`ml/COMPARISON/source_difference.csv`](ml/COMPARISON/source_difference.csv) | Frozen record of the earlier paired block-bootstrap PaleoClim vs WorldClim ML comparison (WorldClim ML runs removed; no longer regenerated). |
| [`ml/COMPARISON/resolution_difference.csv`](ml/COMPARISON/resolution_difference.csv) | Paired comparison of predictive skill between 5° base and 2° fine grid resolutions. |
| [`ml/paleoclim_base/tables/delta_r2.csv`](ml/paleoclim_base/tables/delta_r2.csv) | Pooled and fold-level incremental $\Delta R^2$ values with 95% spatial block bootstrap intervals. |
| [`ml/paleoclim_base/tables/loco_metrics.csv`](ml/paleoclim_base/tables/loco_metrics.csv) | Leave-One-Continent-Out transfer metrics ($R^2$, RMSE, Spearman $\rho$) across continents. |
| [`ml/paleoclim_base/tables/grouped_importance.csv`](ml/paleoclim_base/tables/grouped_importance.csv) | Out-of-fold grouped feature permutation importance across effort, geography, topography, and climate. |
| [`ml/paleoclim_base/tables/morans_i.csv`](ml/paleoclim_base/tables/morans_i.csv) | Moran's $I$ spatial autocorrelation tests on out-of-fold prediction residuals. |

---

## 9. Robustness & Sensitivity Inference (`integration_v3b`)

### Tables
| File Path | Description / Caption |
|---|---|
| [`tables/integration_v3/correlations_5deg_v3b.csv`](tables/integration_v3/correlations_5deg_v3b.csv) | 5° rank correlations with two-sided block-bootstrap $p$-values, naive $p$, FDR $q$-values, and zero-crossing flags. |
| [`tables/integration_v3/correlations_2deg_v3b.csv`](tables/integration_v3/correlations_2deg_v3b.csv) | 2° rank correlations ($N=4,395$) with block-bootstrap $p$, naive $p$, FDR $q$, and CI zero-crossing flags. |
| [`tables/integration_v3/quantile_regression_v3b.csv`](tables/integration_v3/quantile_regression_v3b.csv) | Quantile regressions across quantiles with 500 block-bootstrap draws, naive vs bootstrap $p$, and zero-crossing flags. |
| [`tables/integration_v3/spatial_models_v3b.csv`](tables/integration_v3/spatial_models_v3b.csv) | Spatial Error ($\lambda$) and Lag ($\rho$) models reporting residual Moran's $I$, spatial $\lambda$, and AIC family note. |
| [`tables/integration_v3/velocity_sensitivity_v3b.csv`](tables/integration_v3/velocity_sensitivity_v3b.csv) | Velocity scale-sensitivity (10' vs 20', $\rho \ge 0.963$) and gradient-floor sensitivity ($\epsilon \in [10^{-5}, 10^{-3}]$, $\rho \ge 0.996$). |
| [`tables/integration_v3/hotspot_enrichment_v3b.csv`](tables/integration_v3/hotspot_enrichment_v3b.csv) | Hotspot odds ratios tested against 1,000 spherical-rotation surrogate null distributions. |
| [`tables/integration_v3/taxa_comparison_v3b.csv`](tables/integration_v3/taxa_comparison_v3b.csv) | Vertebrate taxonomic vulnerability comparisons across Amphibia, Mammalia, and Reptilia. |
| [`tables/integration_v3/reproduce_188_gbif_v3b.csv`](tables/integration_v3/reproduce_188_gbif_v3b.csv) | Re-estimation benchmark replicating the 188-cell GBIF baseline regression. |

---

## 10. IUCN Machine Learning Diagnostics & Extension (`ml/iucn_*`)

### Figures
| File Path | Description / Caption |
|---|---|
| [`ml/iucn_grouped_importance.png`](ml/iucn_grouped_importance.png) | Out-of-fold grouped permutation feature importance across geography, contemporary climate, palaeoclimate, and topography. |
| [`ml/iucn_shap_summary.png`](ml/iucn_shap_summary.png) | TreeExplainer SHAP feature attribution summary for Random Forest evaluating environmental predictors without observer effort. |
| [`ml/iucn_pdp_velocity_refugia.png`](ml/iucn_pdp_velocity_refugia.png) | Dual partial dependence profiles for temperature velocity and refugial area fraction conditioning on contemporary climate. |
| [`ml/iucn_residual_map.png`](ml/iucn_residual_map.png) | Global geographic map of out-of-fold prediction residuals for OLS and Random Forest models. |
| [`ml/iucn_observed_vs_predicted.png`](ml/iucn_observed_vs_predicted.png) | Out-of-fold observed versus predicted scatter plots across OLS, Ridge, Random Forest, and HistGradientBoosting. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`ml/iucn_delta_r2.csv`](ml/iucn_delta_r2.csv) | Master out-of-sample incremental $\Delta R^2$ ($M2 - M1$) across OLS, Ridge, RF, HGB, 3 targets, and 2 spatial grains with 95% block CIs. |
| [`ml/iucn_loco.csv`](ml/iucn_loco.csv) | Leave-One-Continent-Out cross-validation transferability metrics across all 6 continents. |
| [`ml/iucn_grouped_importance.csv`](ml/iucn_grouped_importance.csv) | Grouped permutation feature importance table across domains on untouched spatial test folds. |
| [`ml/iucn_shap_importance.csv`](ml/iucn_shap_importance.csv) | Mean absolute SHAP values across all 11 features for Random Forest. |
| [`ml/iucn_morans_i.csv`](ml/iucn_morans_i.csv) | Out-of-fold residual Moran's $I$ spatial autocorrelation tests across model architectures and feature tiers. |
| [`ml/iucn_summary.csv`](ml/iucn_summary.csv) | Consolidated synthesis table of spatial performance and block-bootstrap confidence intervals. |

---

## 11. Buffered Spatial Cross-Validation

### Figures
| File Path | Description / Caption |
|---|---|
| [`figures/buffered_cv_comparison.png`](figures/buffered_cv_comparison.png) | Buffered Spatial Cross-Validation: effective training sample sizes and discarded buffer cells (1000 km exclusion buffer) per fold, and out-of-fold $R^2$ compared against 20° GroupKFold. |

### Tables
| File Path | Description / Caption |
|---|---|
| [`tables/buffered_cv_diagnostics.csv`](tables/buffered_cv_diagnostics.csv) | Buffered Spatial CV fold-level diagnostics: test set counts, candidate training counts, effective training counts, discarded buffer counts, and discard rates (1000 km buffer). |
| [`tables/buffered_cv_comparison.csv`](tables/buffered_cv_comparison.csv) | Out-of-fold performance comparison between standard 20° GroupKFold and BufferedSpatialCV across model architectures. |
