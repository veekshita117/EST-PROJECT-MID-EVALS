# Analysis Plan: Integration v2 (Phase 6)
**Project**: Palaeoclimate Stability and Modern Biodiversity (EST Topic 24)  
**Date**: November 2026  
**Status**: Written alongside the first run of the Phase 6 pipeline (in future phases, the plan will be committed in its own commit before any model run)

---

## 1. Research Question & Hypotheses
- **Core Research Question**: Are biodiversity-rich regions disproportionately associated with long-term Quaternary climatic stability after controlling for macroecological gradients, topographic heterogeneity, sampling effort, and spatial autocorrelation?
- **Hypothesis 1 (Quaternary Stability)**: Regions characterized by higher long-term climatic stability (lower temperature change, lower precipitation change, lower composite instability across the Quaternary) harbor higher modern species richness.
- **Null Hypothesis ($H_0$)**: There is no statistically significant association between Quaternary climatic stability and modern species richness after controlling for absolute latitude, mean elevation, topographic heterogeneity (relief range), sampling effort, and spatial autocorrelation.

---

## 2. Variables & Specification

### 2.1 Response Variables
- **Primary Response**:
  - Global observed species richness (`richness`) across standardized grid cells, with sampling effort explicitly controlled via $\ln(\text{n\_records})$.
  - Protocol specification: IUCN total terrestrial species richness (mammals, amphibians, reptiles) is the target specification; in the operational dataset where IUCN raw shapefile ingestion is pending user download, GBIF observed richness serves as the primary operational response, preserving continuity with mid-eval benchmarks.
- **Transformed Response for Regression**:
  - $\ln(1 + \text{richness})$ to normalize positive skewness and stabilize variance.

### 2.2 Predictor Variables (Climatic Stability / Instability)
- **Primary Predictor**:
  - `composite_instability`: Mean of z-scores of Quaternary temperature instability (SD across Present, Mid-Holocene, and LGM) and relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$).
- **Secondary / Component Predictors**:
  - `temp_instability`: Standard deviation of BIO1 across Present, Mid-Holocene, and LGM (°C).
  - `temp_lgm_change`: Absolute change in BIO1 between Present and LGM ($|\text{BIO1}_{\text{present}} - \text{BIO1}_{\text{lgm}}|$, °C).
  - `precip_lgm_change_rel`: Relative precipitation change ($|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$).
  - `precip_lgm_change_abs`: Absolute precipitation change ($|P_{\text{present}} - P_{\text{lgm}}|$, mm).
  - `bio4_change`: Absolute change in temperature seasonality (BIO4) from LGM to Present.
  - `bio15_change`: Absolute change in precipitation seasonality (BIO15) from LGM to Present.
- **Climate Data Sources**:
  - PaleoClim (primary palaeoclimatic reconstruction).
  - WorldClim / CCSM4 (secondary comparative reconstruction).

### 2.3 Control Variables
- `abs_lat`: Absolute latitude ($|\text{cell\_lat}|$), capturing the global latitudinal diversity gradient.
- `elevation_mean`: Mean cell elevation (meters above sea level), derived from Copernicus DEM GLO-90.
- `topographic_heterogeneity`: Relief range ($\text{elevation}_{\max} - \text{elevation}_{\min}$, meters) derived from Copernicus DEM GLO-90, proxying microclimatic buffering and local topographic refugia.
- `log_n`: Natural logarithm of occurrence records ($\ln(\text{n\_records})$), controlling for geographic sampling bias.

---

## 3. Spatial Resolution & Sample Inclusion

- **Primary Scale**: 5° $\times$ 5° grid cells.
  - Minimum records threshold: $\ge 10$ records ($n = 188$ cells, reproducing the mid-eval benchmark).
  - Full land-cells sensitivity: All cells with records ($N = 375$ cells).
- **Robustness Scale**: 2° $\times$ 2° grid cells.
  - Minimum records threshold: $\ge 10$ records ($n = 264$ cells).
  - Full land-cells sensitivity: All cells with records ($N = 893$ cells).

---

## 4. Analytical Protocol & Statistical Methods

### 4.1 Non-Parametric Rank Correlations (Mid-Eval Reproduction & Expansion)
- Bivariate Spearman rank correlation ($\rho$) between richness and each stability metric.
- Partial Spearman rank correlation controlling for:
  - Model A (Baseline mid-eval): `log_n`, `abs_lat`.
  - Model B (Full controls): `log_n`, `abs_lat`, `elevation_mean`, `topographic_heterogeneity`.
- Stability quartile analysis: Richness distribution across 4 quartiles of climatic stability.
- Concordance: PaleoClim vs WorldClim Spearman $\rho$ across all metrics.
- Bivariate classification: Rich-and-stable vs rich-and-unstable cells (top quartile richness $\times$ top quartile stability).

### 4.2 Spatial Autocorrelation Diagnosis
- Spatial Weight Matrix ($W$):
  - K-Nearest Neighbors ($k=8$) computed on cell centroids using great-circle distance (3D Cartesian projection on the unit sphere).
  - Row-standardized weights ($W_{\text{std}}$).
- Global Moran's $I$:
  - Computed for raw richness, $\ln(1 + \text{richness})$, and OLS regression residuals.
  - Pseudo $p$-values via 999 Monte Carlo permutations.

### 4.3 Parametric Regressions & Spatial Models
- Standardization: All continuous predictors and controls standardized ($z = (x - \bar{x}) / s_x$) so coefficients represent effect sizes in standard deviations.
- Multicollinearity: Variance Inflation Factor (VIF) computed for all covariates. Rule: $\text{VIF} < 5$ considered acceptable.
- Models:
  1. **OLS Regression**:
     $$\ln(1 + \text{Richness}) = \beta_0 + \beta_1 \text{Stability} + \beta_2 |\text{Lat}| + \beta_3 \text{Elev} + \beta_4 \text{Relief} + \beta_5 \ln(N) + \varepsilon$$
  2. **Spatial Error Model (SEM)**:
     $$y = X\beta + u, \quad u = \lambda W u + \varepsilon, \quad \varepsilon \sim \mathcal{N}(0, \sigma^2 I)$$
  3. **Spatial Lag Model (SLM / SAR)**:
     $$y = \rho W y + X\beta + \varepsilon, \quad \varepsilon \sim \mathcal{N}(0, \sigma^2 I)$$
- Model Comparison Criteria: AIC, Log-Likelihood, residual Moran's $I$, and pseudo-$R^2$.

### 4.4 Spatial Cross-Validation & Bootstrap
- **20° Spatial-Block Cross-Validation**:
  - Grid binned into 20° $\times$ 20° spatial blocks ($55$ blocks globally).
  - 5-fold spatial GroupKFold cross-validation partitioning by spatial blocks.
  - Evaluate out-of-sample $R^2$ and root mean square error (RMSE).
- **Spatial-Block Bootstrap**:
  - Resample 20° spatial blocks with replacement (300 iterations).
  - Compute empirical 95% confidence intervals for partial Spearman correlations and regression coefficients that account for within-block spatial dependencies.

### 4.5 Multiple Testing Correction
- Benjamini-Hochberg (BH) False Discovery Rate (FDR) applied across all primary hypothesis tests (correlations and regression coefficients).
- Report both nominal $p$-values and FDR-adjusted $q$-values with $\alpha = 0.05$ threshold.
