# Results: Integration v2 (Phase 6)
**Project**: Palaeoclimate Stability and Modern Biodiversity (EST Topic 24)  
**Date**: November 2026  
**Branch**: `future-implementations`  
**Analysis Plan**: [`PLAN.md`](PLAN.md)

---

## 1. Executive Summary & Core Research Question

> **Core Research Question**: Are biodiversity-rich regions disproportionately associated with long-term Quaternary climatic stability after controlling for elevation, latitude, sampling effort, and spatial autocorrelation?

### Direct Answer
1. **In non-spatial models (OLS and rank correlations)**:
   - When controlling only for sampling effort ($\ln(N)$) and absolute latitude ($|\text{lat}|$), Quaternary climatic instability exhibits a statistically significant negative association with species richness ($\text{partial } \rho = -0.258, p = 0.00035$ for PaleoClim composite instability; $\text{partial } \rho = -0.198, p = 0.0063$ for WorldClim).
   - In standardized OLS regressions, composite instability appears significant ($\beta = -0.128, p = 0.00014$ for PaleoClim; $\beta = -0.121, p = 0.0010$ for WorldClim).
2. **However, OLS residuals exhibit severe spatial autocorrelation**:
   - Moran's $I$ of OLS residuals is $0.1985$ ($p = 0.001$), violating the Gauss-Markov independence assumption and inflating nominal test statistics.
3. **When spatial autocorrelation is modeled (Spatial Error Model)**:
   - The Spatial Error Model substantially improves model fit over OLS ($\Delta \text{AIC} = -22.70$ for PaleoClim, $\Delta \text{AIC} = -25.08$ for WorldClim), and the filtered innovations show no remaining spatial autocorrelation ($I = 0.0012, p = 0.395$), as expected from the model design.
   - The estimated spatial autoregressive parameter is strong ($\lambda = 0.5350, p = 2.10 \times 10^{-9}$ for PaleoClim; $\lambda = 0.5542, p = 1.37 \times 10^{-10}$ for WorldClim).
   - **The Quaternary instability effect attenuates substantially**:
     - PaleoClim composite instability attenuates by 37% to $\beta = -0.0810$ ($p = 0.0625$, FDR $q = 0.0834$), losing statistical significance at the conventional $\alpha = 0.05$ threshold.
     - WorldClim composite instability attenuates by 50% to $\beta = -0.0609$ ($p = 0.178$, FDR $q = 0.200$).
4. **Topographic Heterogeneity & Microclimatic Refugia Dominate Macro-Stability**:
   - Copernicus DEM topographic heterogeneity (relief range within cell) remains a robust, statistically significant positive predictor of species richness across all models ($\beta = +0.0766, p = 0.0140$ in Spatial Error Model; $\beta = +0.0848, p = 0.0055$ in Spatial Lag Model), even after spatial error correction.
5. **Spatial Cross-Validation Confirms Negligible Predictive Contribution**:
   - Under 5-fold 20° spatial-block cross-validation, adding Quaternary stability yields an incremental $\Delta R^2_{\text{CV}} = +0.0079$ (less than $0.8\%$ additional out-of-sample variance explained).

---

## 2. Integrated Dataset & Baseline Verification

The integrated dataset merges four independent streams:
1. **Biodiversity Response**: Standardized GBIF species richness (`richness`) and record count (`n_records`), with $\ln(\text{n\_records})$ controlling for uneven sampling effort.
2. **Copernicus DEM GLO-90**: High-resolution digital elevation metrics (`elevation_mean`, `elevation_sd`, `relief_range` as `topographic_heterogeneity`).
3. **PaleoClim (Primary Climate)**: Present, Late Holocene, and LGM rasters for BIO1 (°C), BIO12 (mm), BIO4 (SD $\times$ 100), and BIO15 (CV %), yielding `temp_instability`, `precip_lgm_change_rel`, and `composite_instability`.
4. **WorldClim / CCSM4 (Comparative Climate)**: Present, Mid-Holocene, and LGM rasters processed with identical zonal aggregation.

### Sample Sizes & Data Tables
- **5° Resolution (Primary)**: 375 cells with GBIF records (compared to 1,473 total land cells in PaleoClim and 1,121 in WorldClim); $n = 188$ cells with $\ge 10$ records (saved at [`processed/data_5deg.csv`](processed/data_5deg.csv)).
- **2° Resolution (Robustness)**: 893 cells with GBIF records (compared to 7,285 total land cells in PaleoClim and 5,359 in WorldClim); $n = 264$ cells with $\ge 10$ records (saved at [`processed/data_2deg.csv`](processed/data_2deg.csv)).

### Reproduction Check (Mid-Eval Benchmark)
- **Mid-Eval Point-Sampled Benchmark**: PaleoClim LGM change partial $\rho = -0.207$ ($p = 0.0044$).
- **Pipeline Verification on $n = 188$**: Partial $\rho = -0.2067$ ($p = 0.00442$), exactly matching the benchmark within $\pm 0.0003$.

---

## 3. Multicollinearity Diagnostics (VIF Table)

Variance Inflation Factors (VIF) computed on the full covariate set demonstrate absence of severe multicollinearity (all $\text{VIF} < 2.1$, well below the threshold of 5.0):

| Variable | VIF | Interpretation |
|---|---|---|
| `pc_composite_instability` | 1.9740 | Low multicollinearity |
| `abs_lat` | 2.0438 | Moderate correlation with climate gradients |
| `elevation_mean` | 1.5942 | Low multicollinearity |
| `topographic_heterogeneity` | 1.7108 | Low multicollinearity |
| `log_n` | 1.0412 | Completely orthogonal sampling effort |

---

## 4. Correlation Analysis & Multiple Testing Correction

Rank correlations were evaluated across all 14 climate metrics at both 5° ($n = 188$) and 2° ($n = 264$), with 95% spatial-block bootstrap confidence intervals (resampling 20° spatial blocks with replacement, 300 iterations) and Benjamini-Hochberg (BH) False Discovery Rate (FDR) control.

### Primary Results Table (5° Primary Grid, $n = 188$)

| Dataset | Metric | Raw $\rho$ ($p$) | Partial $\rho_{\text{mid-eval}}$ ($p$) | Partial $\rho_{\text{full}}$ ($p$) | FDR $q$ (Full) | Spatial Bootstrap 95% CI |
|---|---|---|---|---|---|---|
| **PaleoClim** | **Composite Instability** | -0.081 (0.268) | **-0.258** (0.0003) | **-0.284** (0.00008) | **0.0011** | [-0.443, -0.074] |
| PaleoClim | Temp Instability | -0.057 (0.436) | **-0.257** (0.0004) | **-0.256** (0.0004) | **0.0019** | [-0.448, -0.015] |
| PaleoClim | Temp LGM Change | -0.064 (0.386) | **-0.255** (0.0004) | **-0.255** (0.0004) | **0.0019** | [-0.442, -0.005] |
| PaleoClim | Precip LGM Change (Rel) | -0.096 (0.188) | **-0.209** (0.0040) | **-0.245** (0.0007) | **0.0024** | [-0.369, -0.046] |
| PaleoClim | Precip LGM Change (Abs) | -0.169 (0.020) | -0.135 (0.065) | **-0.183** (0.0118) | **0.0235** | [-0.293, +0.033] |
| PaleoClim | Seasonality (BIO4) Change | -0.049 (0.503) | -0.142 (0.052) | -0.120 (0.101) | 0.1179 | [-0.271, +0.071] |
| PaleoClim | Seasonality (BIO15) Change | +0.046 (0.530) | -0.121 (0.098) | -0.142 (0.052) | 0.0731 | [-0.322, +0.020] |
| **WorldClim** | **Composite Instability** | -0.045 (0.535) | **-0.198** (0.0063) | **-0.202** (0.0053) | **0.0149** | [-0.339, +0.006] |
| WorldClim | Temp Instability | -0.027 (0.717) | **-0.181** (0.0130) | **-0.178** (0.0146) | **0.0255** | [-0.365, +0.034] |
| WorldClim | Temp LGM Change | -0.038 (0.606) | **-0.179** (0.0139) | **-0.187** (0.0100) | **0.0234** | [-0.366, +0.041] |
| WorldClim | Precip LGM Change (Rel) | -0.076 (0.302) | -0.139 (0.058) | **-0.170** (0.0195) | **0.0303** | [-0.300, +0.015] |
| WorldClim | Precip LGM Change (Abs) | -0.144 (0.048) | -0.052 (0.482) | -0.096 (0.192) | 0.1919 | [-0.246, +0.071] |

*Note: Partial $\rho_{\text{mid-eval}}$ controls for `log_n` and `abs_lat`. Partial $\rho_{\text{full}}$ controls for `log_n`, `abs_lat`, `elevation_mean`, and `topographic_heterogeneity`. All bold entries are significant at FDR $q < 0.05$.*

### Robustness Scale (2° Grid, $n = 264$)
At 2° resolution, the findings are consistent:
- PaleoClim Composite Instability: Partial $\rho_{\text{full}} = -0.2368$ ($p = 0.00010$, FDR $q = 0.0014$), Bootstrap 95% CI: `[-0.390, -0.048]`.
- WorldClim Composite Instability: Partial $\rho_{\text{full}} = -0.1731$ ($p = 0.00480$, FDR $q = 0.0096$).

---

## 5. Model Comparison: OLS vs. Spatial Error vs. Spatial Lag

To test whether Quaternary climatic stability explains species richness when accounting for spatial autocorrelation, three regression specifications were fitted on $\ln(1 + \text{richness})$ with standardized predictors and controls ($z$-scores).

### Primary Model Suite (PaleoClim Composite Instability, $n = 188$)

| Parameter / Diagnostic | OLS Model | Spatial Error Model (ML) | Spatial Lag Model (ML) |
|---|---|---|---|
| **Constant ($\beta_0$)** | 3.4174 (SE 0.0234, $p < 10^{-180}$) | 3.3911 (SE 0.0460, $p < 10^{-100}$) | 2.8467 (SE 0.1948, $p < 10^{-47}$) |
| **Composite Instability ($\beta_1$)** | **-0.1282** (SE 0.0330, $p = 0.00014$) | **-0.0810** (SE 0.0435, $p = 0.0625$) | **-0.1052** (SE 0.0325, $p = 0.00120$) |
| Absolute Latitude ($\beta_2$) | -0.0227 (SE 0.0335, $p = 0.499$) | -0.0238 (SE 0.0470, $p = 0.613$) | -0.0337 (SE 0.0325, $p = 0.300$) |
| Mean Elevation ($\beta_3$) | -0.0462 (SE 0.0296, $p = 0.121$) | -0.0580 (SE 0.0302, $p = 0.0548$) | -0.0653 (SE 0.0293, $p = 0.0256$) |
| **Topographic Heterogeneity ($\beta_4$)** | **+0.0618** (SE 0.0307, $p = 0.0456$) | **+0.0766** (SE 0.0312, $p = 0.0140$) | **+0.0848** (SE 0.0305, $p = 0.00550$) |
| Sampling Effort $\ln(N)$ ($\beta_5$) | +0.8422 (SE 0.0239, $p < 10^{-80}$) | +0.8373 (SE 0.0226, $p < 10^{-200}$) | +0.8285 (SE 0.0237, $p < 10^{-200}$) |
| **Spatial Parameter ($\lambda$ or $\rho$)** | — | **$\lambda = 0.5350$** ($p = 2.10 \times 10^{-9}$) | **$\rho = 0.1627$** ($p = 0.00345$) |
| **AIC** | 112.07 | **89.37** ($\Delta \text{AIC} = -22.70$) | 106.28 ($\Delta \text{AIC} = -5.79$) |
| **Pseudo-$R^2$** | 0.8761 | 0.8736 | 0.8815 |
| **Residual Moran's $I$** | **$I = 0.1985$ ($p = 0.001$)** | **$I = 0.0012$ ($p = 0.395$)** | **$I = 0.1479$ ($p = 0.002$)** |

### Comparative Suite (WorldClim Composite Instability, $n = 188$)

| Parameter / Diagnostic | OLS Model | Spatial Error Model (ML) | Spatial Lag Model (ML) |
|---|---|---|---|
| **Composite Instability ($\beta_1$)** | **-0.1214** (SE 0.0363, $p = 0.00100$) | **-0.0609** (SE 0.0452, $p = 0.178$) | **-0.0953** (SE 0.0356, $p = 0.00735$) |
| **Topographic Heterogeneity ($\beta_4$)** | **+0.0631** (SE 0.0310, $p = 0.0434$) | **+0.0800** (SE 0.0312, $p = 0.0103$) | **+0.0872** (SE 0.0308, $p = 0.00461$) |
| **Spatial Parameter ($\lambda$ or $\rho$)** | — | **$\lambda = 0.5542$** ($p = 1.37 \times 10^{-10}$) | **$\rho = 0.1706$** ($p = 0.00231$) |
| **AIC** | 115.86 | **90.78** ($\Delta \text{AIC} = -25.08$) | 109.42 |
| **Residual Moran's $I$** | **$I = 0.2079$ ($p = 0.001$)** | **$I = 0.0008$ ($p = 0.398$)** | **$I = 0.1536$ ($p = 0.001$)** |

---

## 6. Visual Diagnostics & Figure Summary

The four generated figures in [`figures/`](figures/) illustrate the core spatial and statistical phenomena:

1. **Coefficient Comparison Plot ([`coef_plot.png`](figures/coef_plot.png))**:
   - Visualizes standardized $\beta$ with 95% confidence intervals across OLS, Spatial Error, and Spatial Lag models.
   - Shows the attenuation of `composite_instability` in the Spatial Error model (crossing zero at $\alpha = 0.05$), while `topographic_heterogeneity` and `log_n` remain strictly positive and significant.
2. **Moran Scatter Plot ([`moran_scatter.png`](figures/moran_scatter.png))**:
   - Displays spatial lag vs standardized variable for raw log-richness ($I = 0.125, p = 0.005$) and OLS residuals ($I = 0.199, p = 0.001$), illustrating clustering of over- and under-predictions.
3. **Residual Geographic Maps ([`residual_maps.png`](figures/residual_maps.png))**:
   - Compares the spatial distribution of OLS residuals (exhibiting contiguous regional clumps in North America and Western Europe) against the Spatial Error filtered innovations ($\varepsilon = u - \lambda W u$), where the filtered innovations show no remaining autocorrelation ($I = 0.0012, p = 0.395$), as expected from the model design.
4. **Observed vs. Predicted Plot ([`observed_vs_predicted.png`](figures/observed_vs_predicted.png))**:
   - Demonstrates calibration along the 1:1 line ($R^2 = 0.876$).

---

## 7. Stability Quartiles & Hotspot Analysis

### Stability Quartile Summary (Richness Distribution, 47 cells each)

| Dataset | Metric | Quartile | Cells | Mean Richness | Median Richness | Std Richness | Mean Records/Cell |
|---|---|---|---|---|---|---|---|
| **PaleoClim** | Composite Instability | Q1 (Most Stable) | 47 | 66.43 | 27.0 | 109.63 | 91.77 |
| PaleoClim | Composite Instability | Q2 (Mod. Stable) | 47 | 60.89 | 24.0 | 82.94 | 82.96 |
| PaleoClim | Composite Instability | Q3 (Mod. Unstable) | 47 | 35.91 | 21.0 | 40.53 | 58.09 |
| PaleoClim | Composite Instability | Q4 (Least Stable) | 47 | 35.40 | 29.0 | 28.35 | 123.28 |
| **PaleoClim** | Temperature Instability | Q1 (Most Stable) | 47 | 51.77 | 25.0 | 89.39 | 69.13 |
| PaleoClim | Temperature Instability | Q2 (Mod. Stable) | 47 | 59.85 | 26.0 | 86.94 | 83.13 |
| PaleoClim | Temperature Instability | Q3 (Mod. Unstable) | 47 | 52.55 | 26.0 | 72.49 | 75.49 |
| PaleoClim | Temperature Instability | Q4 (Least Stable) | 47 | 34.47 | 25.0 | 31.65 | 128.34 |
| **WorldClim** | Composite Instability | Q1 (Most Stable) | 47 | 61.32 | 24.0 | 96.14 | 82.43 |
| WorldClim | Composite Instability | Q2 (Mod. Stable) | 47 | 62.45 | 26.0 | 96.75 | 86.77 |
| WorldClim | Composite Instability | Q3 (Mod. Unstable) | 47 | 40.32 | 23.0 | 46.42 | 70.85 |
| WorldClim | Composite Instability | Q4 (Least Stable) | 47 | 34.55 | 31.0 | 27.81 | 116.04 |
| **WorldClim** | Temperature Instability | Q1 (Most Stable) | 47 | 46.62 | 26.0 | 71.45 | 59.04 |
| WorldClim | Temperature Instability | Q2 (Mod. Stable) | 47 | 67.36 | 23.0 | 103.84 | 93.02 |
| WorldClim | Temperature Instability | Q3 (Mod. Unstable) | 47 | 49.40 | 25.0 | 68.83 | 80.49 |
| WorldClim | Temperature Instability | Q4 (Least Stable) | 47 | 35.26 | 26.0 | 31.54 | 123.53 |

*Key Pattern*: Mean richness in the two more stable quartiles (Q1 ~61–66 species, Q2 ~61–62 species) is substantially higher than in Q3 (~36–40 species) and Q4 (~35 species), with Q3 about equal to Q4 in PaleoClim composite instability (35.91 vs 35.40). However, mean records per cell vary substantially across quartiles (e.g. Q4 has the highest mean records at 123.3, while Q3 has 58.1), highlighting the sampling effort confound across cells. Medians remain close across quartiles (21–31 species), indicating that differences in means are driven by a minority of heavily sampled, species-rich cells rather than a broad distributional shift.

### Hotspot Discordance (Rich-and-Stable vs. Rich-and-Unstable)
Crossing top-quartile species richness (top 25%, $\ge 47$ cells) with top-quartile stability (lowest 25% instability):
- **PaleoClim**: 16 cells are rich-and-stable; **31 cells are rich-and-unstable** (ratio 1:1.9).
- **WorldClim**: 14 cells are rich-and-stable; **33 cells are rich-and-unstable** (ratio 1:2.4).
- **Inference**: Globally, richness hotspots are twice as likely to occur in climatically unstable regions (e.g., dynamic temperate mountain ranges, glaciated post-refugial recolonization fronts) as in macro-stable regions.

---

## 8. Dataset Agreement: PaleoClim vs. WorldClim

PaleoClim and WorldClim exhibit strong rank concordance across all metrics ($n = 188$ cells):
- `composite_instability`: $\rho = 0.8329$ ($p = 1.14 \times 10^{-49}$)
- `temp_instability`: $\rho = 0.7991$ ($p = 5.64 \times 10^{-43}$)
- `temp_lgm_change`: $\rho = 0.8202$ ($p = 5.56 \times 10^{-47}$)
- `precip_lgm_change_rel`: $\rho = 0.8383$ ($p = 7.14 \times 10^{-51}$)
- `precip_lgm_change_abs`: $\rho = 0.7997$ ($p = 4.54 \times 10^{-43}$)
- `bio4_change`: $\rho = 0.6273$ ($p = 5.89 \times 10^{-22}$)
- `bio15_change`: $\rho = 0.8275$ ($p = 1.63 \times 10^{-48}$)

Both climate models provide highly congruent macroclimatic stability rankings across the globe.

---

## 9. Spatial-Block Cross-Validation Performance

5-fold spatial-block cross-validation partitioning by 20° $\times$ 20° spatial blocks ($55$ global blocks) evaluates generalization to unobserved geographic regions:

| Model Specification | Out-of-Sample $R^2_{\text{CV}}$ | Out-of-Sample $\text{RMSE}_{\text{CV}}$ |
|---|---|---|
| OLS Full Model (with Composite Instability) | 0.8493 | 0.3483 |
| OLS Controls Only (without Instability) | 0.8414 | 0.3572 |
| **Incremental Contribution ($\Delta$)** | **+0.0079 (+0.79%)** | **-0.0089** |

Quaternary climatic stability explains less than 0.8% of out-of-sample variance when predicting species richness across distinct 20° geographic blocks.

---

## 10. Discussion & Synthesis: Answering the Core Research Question

### Comparison with Mid-Eval Conclusions
1. **The apparent "stability effect" in non-spatial analyses is strongly confounded by spatial autocorrelation**:
   - In the mid-eval analysis (and reproduced here with zonal statistics), partial Spearman rank correlations suggested a statistically significant negative association between climate instability and richness ($\text{partial } \rho \approx -0.21$ to $-0.26, p < 0.004$).
   - However, spatial diagnostics reveal that OLS regression residuals carry strong positive spatial autocorrelation ($I = 0.1985, p = 0.001$).
   - Fitting a Maximum Likelihood Spatial Error Model accounts for regional autocorrelation ($\lambda = 0.5350, p < 10^{-8}$) and yields filtered innovations with no remaining spatial autocorrelation ($I = 0.0012, p = 0.395$), as expected from the model design. This cuts the instability coefficient by over a third, reducing it to non-significance ($p = 0.0625$, FDR $q = 0.0834$).
2. **Topographic Heterogeneity as a Micro-Refugial Buffer**:
   - Copernicus DEM topographic heterogeneity (`relief_range`) remains consistently and positively associated with species richness across all models ($\beta = +0.0766, p = 0.014$).
   - This provides strong empirical support for the **topographic refugia hypothesis**: topographically complex terrains buffer macroclimatic swings through microclimates and steep elevational ecotones, allowing species persistence independent of coarse-scale stability.
3. **Quartile Patterns and Effort Confound**:
   - Quartile comparisons reveal that Q3 and Q4 exhibit similarly suppressed mean richness (~35–36 species in PaleoClim composite instability), with Q3 about equal to Q4 (35.91 vs 35.40).
   - However, sampling effort strongly confounds raw comparisons across quartiles (e.g. Q4 cells average 123.3 records while Q3 cells average 58.1 records), and twice as many richness hotspots lie in unstable regions as in stable regions.

---

## 11. Artifacts & Deliverables Generated

- **Analysis Plan**: [`PLAN.md`](PLAN.md)
- **Processed Tables**:
  - 5° Grid: [`processed/data_5deg.csv`](processed/data_5deg.csv)
  - 2° Grid: [`processed/data_2deg.csv`](processed/data_2deg.csv)
- **Figures**:
  - Coefficient Comparison: [`figures/coef_plot.png`](figures/coef_plot.png)
  - Moran Diagnostics: [`figures/moran_scatter.png`](figures/moran_scatter.png)
  - Residual Maps: [`figures/residual_maps.png`](figures/residual_maps.png)
  - Observed vs. Predicted: [`figures/observed_vs_predicted.png`](figures/observed_vs_predicted.png)
- **Tabular Outputs**:
  - Full Correlations with CIs & FDR: [`figures/table_correlations_v2.csv`](figures/table_correlations_v2.csv)
  - Model Comparisons: [`figures/table_models_comparison.csv`](figures/table_models_comparison.csv)
  - VIF Table: [`figures/table_vif.csv`](figures/table_vif.csv)
  - Quartiles Table: [`figures/table_quartiles_v2.csv`](figures/table_quartiles_v2.csv)
  - Dataset Agreement Table: [`figures/table_dataset_agreement.csv`](figures/table_dataset_agreement.csv)
  - Hotspots Table: [`figures/table_hotspots_v2.csv`](figures/table_hotspots_v2.csv)
  - Spatial Cross-Validation: [`figures/table_spatial_cv.csv`](figures/table_spatial_cv.csv)
