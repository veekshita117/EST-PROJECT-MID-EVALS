# Phase 9: Synthesis & Statistical Inference Results (v3b)

**Document Location**: `integration_v3/results_v3b.md`  
**Git Branch**: `future-implementations`  
**Protocol Status**: Fully executed with two-sided spatial block-bootstrap inference, scale/gradient sensitivity evaluation, residual autocorrelation diagnostics, and model-family AIC constraints.

---

## 1. Benchmark Continuity & Reproduction Check

Before evaluating Phase 9 extensions, the unified pipeline re-estimated the original 188-cell GBIF benchmark regression to verify numerical reproducibility.

*Table traceable to [`integration_v3/tables/reproduce_188_gbif_v3b.csv`](tables/reproduce_188_gbif_v3b.csv):*

| Climate Source | Metric | Cells ($n$) | Raw Spearman $\rho$ | Raw $p$ | Partial Spearman $\rho$ | Partial $p$ | Benchmark Match |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **PaleoClim** | LGM change | 188 | -0.053 | 0.468 | -0.207 | 0.004 | **Exact (0.000 error)** |
| **PaleoClim** | Instability | 188 | -0.046 | 0.530 | -0.212 | 0.003 | **Exact (0.000 error)** |
| **WorldClim** | LGM change | 188 | +0.011 | 0.880 | -0.114 | 0.120 | **Exact (0.000 error)** |
| **WorldClim** | Instability | 188 | +0.029 | 0.696 | -0.102 | 0.163 | **Exact (0.000 error)** |

The original results are replicated to 3 decimal places. Without controls, temperature change has no relationship with GBIF richness ($\rho \approx 0$). When controlling for sampling effort ($\ln \text{records}$) and absolute latitude, PaleoClim exhibits a weak negative partial correlation ($\rho = -0.207, p = 0.004$).

---

## 2. Bivariate & Partial Correlations (5° Primary and 2° Sensitivity)

Analyses were conducted on all global land cells with complete environmental controls ($n = 755$ across 88 blocks at 5°; $n = 4{,}395$ across 93 blocks at 2°; GBIF rarefied evaluated on cells with $\ge 20$ records: $n = 683$ at 5° and $n = 3{,}080$ at 2°). 95% confidence intervals were computed using 20° spatial-block bootstrapping ($B = 1{,}000$ iterations at 5°; $B = 500$ at 2°). Two-sided block-bootstrap $p$-values ($p_{\text{boot}}$, share of bootstrap draws crossing zero) and Benjamini-Hochberg False Discovery Rate ($q_{\text{FDR, boot}}$) were evaluated across the complete hypothesis family alongside naive asymptotic $p$-values.

*Table traceable to [`integration_v3/tables/correlations_5deg_v3b.csv`](tables/correlations_5deg_v3b.csv) and [`integration_v3/tables/correlations_2deg_v3b.csv`](tables/correlations_2deg_v3b.csv):*

### Primary Predictor: $\log_{10}(\text{Temperature Climate Velocity})$

| Biodiversity Response | Scale | Cells ($n$) | Raw $\rho$ [95% CI] | Raw $p_{\text{naive}}$ | Raw $p_{\text{boot}}$ | Partial $\rho$ [95% CI] | Partial Block CI Zero? | Partial $p_{\text{naive}}$ | Partial $p_{\text{boot}}$ | Partial $q_{\text{FDR, boot}}$ | Controls Applied |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **IUCN Total Richness** | 5° | 755 | -0.389 [-0.505, -0.271] | <0.0001 | 0.000 | **-0.295 [-0.422, -0.153]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Total Richness** | 2° | 4,395 | -0.329 [-0.416, -0.230] | <0.0001 | 0.000 | **-0.302 [-0.380, -0.169]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Total Endemism** | 5° | 755 | -0.520 [-0.635, -0.405] | <0.0001 | 0.000 | **-0.326 [-0.459, -0.269]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Total Endemism** | 2° | 4,395 | -0.492 [-0.583, -0.372] | <0.0001 | 0.000 | **-0.327 [-0.404, -0.248]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Small-Range $Q_{25}$** | 5° | 755 | -0.575 [-0.654, -0.489] | <0.0001 | 0.000 | **-0.259 [-0.377, -0.175]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Small-Range $Q_{25}$** | 2° | 4,395 | -0.491 [-0.562, -0.428] | <0.0001 | 0.000 | **-0.128 [-0.206, -0.092]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Reptiles Richness** | 5° | 755 | -0.388 [-0.506, -0.257] | <0.0001 | 0.000 | **-0.322 [-0.440, -0.187]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Reptiles Richness** | 2° | 4,395 | -0.337 [-0.446, -0.208] | <0.0001 | 0.000 | **-0.346 [-0.421, -0.217]** | **No** | <0.0001 | 0.000 | **<0.0001** | Full 8 controls |
| **IUCN Mammals Richness** | 5° | 755 | -0.372 [-0.477, -0.253] | <0.0001 | 0.000 | -0.157 [-0.319, -0.012] | No | <0.0001 | 0.044 | 0.0621 (ns) | Full 8 controls |
| **IUCN Mammals Richness** | 2° | 4,395 | -0.288 [-0.376, -0.184] | <0.0001 | 0.000 | -0.129 [-0.232, +0.011] | **Yes (Crosses 0)** | <0.0001 | 0.076 | 0.0986 (ns) | Full 8 controls |
| **IUCN Amphibians Richness**| 5° | 755 | -0.288 [-0.407, -0.150] | <0.0001 | 0.000 | -0.103 [-0.236, +0.017] | **Yes (Crosses 0)** | 0.0046 | 0.080 | 0.0960 (ns) | Full 8 controls |
| **IUCN Amphibians Richness**| 2° | 4,395 | -0.204 [-0.324, -0.093] | <0.0001 | 0.000 | -0.104 [-0.209, +0.029] | **Yes (Crosses 0)** | <0.0001 | 0.128 | 0.1575 (ns) | Full 8 controls |
| **GBIF Rarefied ($n=20$)** | 5° | 683 | -0.305 [-0.420, -0.174] | <0.0001 | 0.000 | -0.034 [-0.121, +0.061] | **Yes (Crosses 0)** | 0.3746 | 0.520 | 0.5547 (ns) | Controls + $\ln(\text{records})$ |
| **GBIF Rarefied ($n=20$)** | 2° | 3,080 | -0.144 [-0.263, -0.030] | <0.0001 | 0.028 | +0.020 [-0.028, +0.099] | **Yes (Crosses 0)** | 0.2681 | 0.284 | 0.3246 (ns) | Controls + $\ln(\text{records})$ |

### Key Correlation Insights & Cautious Wording:
1. **Robust Vertebrate Endemism & Reptile Sensitivity**: Total richness, weighted endemism, small-range richness ($Q_{25}$), and reptile richness demonstrate robust, strictly negative partial correlations with climate velocity at both 5° and 2° scales where 95% spatial-block bootstrap intervals exclude zero and bootstrap FDR $q < 0.0001$.
2. **Amphibian and Mammal Effects Are Fragile (CI Crosses Zero)**:
   - For amphibians, the 95% block-bootstrap CI crosses zero at both 5° (`[-0.236, +0.017]`, $p_{\text{boot}} = 0.080$) and 2° (`[-0.209, +0.029]`, $p_{\text{boot}} = 0.128$). Once spatial block clustering and contemporary moisture/temperature are controlled for, the empirical association between Quaternary velocity and amphibian richness is statistically indistinguishable from zero ($q_{\text{FDR, boot}} \ge 0.096$).
   - For mammals, while the 5° partial correlation CI narrowly excludes zero (`[-0.319, -0.012]`), the bootstrap FDR is non-significant ($q = 0.0621$), and at 2° the block CI includes zero (`[-0.232, +0.011]`, $p_{\text{boot}} = 0.076$).
3. **GBIF Sampling Noise**: Standardized GBIF rarefied richness shows zero partial relationship with climate velocity ($p_{\text{boot}} = 0.520$ at 5°; $p_{\text{boot}} = 0.284$ at 2°), with confidence intervals spanning zero in both configurations.

---

## 3. Hotspot Enrichment & Spatially Structured Null Testing

We tested whether biodiversity hotspots (top 10% and top 20% of response) are disproportionately enriched within Quaternary climatically stable refugia (lowest 25% of temperature velocity).

*Table traceable to [`integration_v3/tables/hotspot_enrichment_v3b.csv`](tables/hotspot_enrichment_v3b.csv):*

| Response | Threshold | Hotspots | Refugia | Both Rich & Stable | Odds Ratio [95% Block-CI] | Naive Fisher $p$ | Spherical Null $p$ | Conclusion |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Richness** | Top 10% | 76 | 189 | 33 | 2.576 [1.214, 5.985] | $0.00023$ | **0.1678 (ns)** | **Not enriched beyond spatial autocorrelation** |
| **Richness** | Top 20% | 151 | 189 | 63 | 2.714 [1.552, 5.192] | $<0.00001$ | **0.1439 (ns)** | **Not enriched beyond spatial autocorrelation** |
| **Endemism** | Top 10% | 76 | 189 | 52 | **8.455 [4.491, 18.285]** | $<0.00001$ | **0.0010** | **Robustly Enriched** |
| **Endemism** | Top 20% | 151 | 189 | 86 | **6.399 [3.716, 11.799]** | $<0.00001$ | **0.0020** | **Robustly Enriched** |

*Figure: [`integration_v3/figures/hotspot_spatial_null.png`](figures/hotspot_spatial_null.png)*

### Methodological Finding:
A standard Fisher's exact test produces extreme nominal significance ($p = 0.00023$ for richness; $p < 10^{-6}$ for endemism) because it ignores spatial clustering. Evaluating against a **spatially structured spherical null model** (1,000 random 3D rotations of the stability surface) reveals that richness hotspots fail to show significant enrichment ($p = 0.1678$). In contrast, endemism hotspots exhibit decisive, robust enrichment ($\text{OR} = 8.455, p = 0.0010$), with 68.4% (52 of 76) of global endemism hotspots located in the 25% most stable Quaternary refugia.

---

## 4. Quantile Regression: The Upper-Bound Constraint Hypothesis

To evaluate whether Quaternary climate instability acts as an upper boundary ceiling, conditional quantile regressions were estimated at $\tau \in \{0.50, 0.75, 0.90\}$ with 95% spatial-block bootstrap intervals ($B=500$), reporting naive asymptotic $p$-values, block-bootstrap $p$-values ($p_{\text{boot}}$), and bootstrap FDR $q$-values.

*Table traceable to [`integration_v3/tables/quantile_regression_v3b.csv`](tables/quantile_regression_v3b.csv):*

| Response | Quantile ($\tau$) | Velocity Slope ($\beta$) | 95% Block-CI | Block CI Zero? | $t$-statistic | Naive $p$ | Boot $p$ | Boot FDR $q$ | Inference Standard |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **$\ln(1 + \text{Richness})$** | 0.50 (Median) | -0.0317 | [-0.1549, +0.0614] | **Yes (Crosses 0)** | -1.328 | 0.1847 | 0.442 | 0.4608 | Non-significant |
| **$\ln(1 + \text{Richness})$** | 0.75 | -0.0311 | [-0.1272, +0.0480] | **Yes (Crosses 0)** | -1.300 | 0.1942 | 0.384 | 0.4608 | Non-significant |
| **$\ln(1 + \text{Richness})$** | 0.90 (Ceiling) | -0.0491 | [-0.1154, +0.0330] | **Yes (Crosses 0)** | -2.177 | 0.0298 | **0.180** | **0.3000** | **Unconfirmed under spatial block bootstrap** |
| **$\ln(1 + \text{Endemism})$** | 0.50 (Median) | -0.1286 | [-0.2131, -0.0032] | **No** | -4.428 | <0.0001 | **0.044** | 0.2640 | Statistically significant negative slope |
| **$\ln(1 + \text{Endemism})$** | 0.75 | -0.0638 | [-0.2226, +0.0291] | **Yes (Crosses 0)** | -1.934 | 0.0535 | 0.200 | 0.3000 | Marginally negative; CI includes zero |
| **$\ln(1 + \text{Endemism})$** | 0.90 (Ceiling) | -0.1530 | [-0.3621, +0.0256] | **Yes (Crosses 0)** | -3.917 | 0.0001 | **0.100** | 0.3000 | Negative trend; CI includes zero |

*Figure: [`integration_v3/figures/quantile_slopes.png`](figures/quantile_slopes.png)*

### Cautious Wording on Upper-Bound Ceiling:
Under naive asymptotic inference, $\tau = 0.90$ for total richness appeared to support an upper-bound ceiling ($\beta = -0.0491, p_{\text{naive}} = 0.0298$). However, when subjected to 20° spatial-block bootstrapping, the 95% confidence interval spans zero (`[-0.1154, +0.0330]`), yielding a bootstrap $p$-value of $p_{\text{boot}} = 0.180$ and FDR $q = 0.3000$. Consequently, the upper ceiling constraint for total richness cannot be confirmed as statistically distinct from zero when spatial block dependence is respected. For weighted endemism, the negative association is strongest and excludes zero at the median ($\tau = 0.50, \beta = -0.1286, p_{\text{boot}} = 0.044$), while upper quantiles show large negative point estimates ($\beta = -0.1530$) whose block bootstrap intervals overlap zero due to regional variability.

---

## 5. Spatial Autoregressive Models (SAR Lag & Error)

We estimated Ordinary Least Squares (OLS), Maximum Likelihood Spatial Error ($\lambda W u$), and Maximum Likelihood Spatial Lag ($\rho W y$) models using row-standardized $k=8$ great-circle haversine nearest-neighbor weights ($n = 755$ land cells).

*Table traceable to [`integration_v3/tables/spatial_models_v3b.csv`](tables/spatial_models_v3b.csv):*

| Response | Model Type | Velocity Coef ($\beta$) | Std Error | 95% CI | CI Zero? | Test Stat | $p$-value | AIC | Spatial Parameter | Residual Moran's $I$ | Residual $p$ | AIC Comparability Standard |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **IUCN Richness** | OLS | -0.0781 | 0.0275 | [-0.1319, -0.0243] | No | $t = -2.846$ | 0.00455 | 975.7 | None | $I = 0.6304$ | <0.0001 | Baseline non-spatial benchmark |
| **IUCN Richness** | Spatial Error | -0.0342 | 0.0202 | [-0.0737, +0.0053] | **Yes** | $z = -1.696$ | 0.08995 | 54.6 | **$\lambda = 0.9516$** ($p < 10^{-5}$) | **$I = 0.0482$** | 0.0046 | Directly comparable to OLS ($\Delta \text{AIC} = -921.1$) |
| **IUCN Richness** | Spatial Lag | -0.0087 | 0.0143 | [-0.0367, +0.0192] | **Yes** | $z = -0.612$ | 0.54075 | 100.8 | **$\rho = 0.8572$** ($p < 10^{-5}$) | $I = 0.1143$ | <0.0001 | Not directly comparable to Error (different endogenous likelihood) |
| **IUCN Endemism** | OLS | -0.1969 | 0.0352 | [-0.2658, -0.1279] | No | $t = -5.593$ | <0.00001 | 1351.1 | None | $I = 0.4556$ | <0.0001 | Baseline non-spatial benchmark |
| **IUCN Endemism** | Spatial Error | **-0.1745** | **0.0360** | **[-0.2451, -0.1039]** | **No** | **$z = -4.845$** | **<0.00001** | **918.7** | **$\lambda = 0.8553$** ($p < 10^{-5}$) | **$I = 0.0245$** | **0.1393 (ns)** | Directly comparable to OLS ($\Delta \text{AIC} = -432.4$) |
| **IUCN Endemism** | Spatial Lag | **-0.0860** | **0.0275** | **[-0.1398, -0.0321]** | **No** | **$z = -3.130$** | **0.00175** | **1011.0** | **$\rho = 0.7206$** ($p < 10^{-5}$) | $I = 0.1025$ | <0.0001 | Not directly comparable to Error (different endogenous likelihood) |

### Econometric Interpretations:
1. **Severe OLS Residual Autocorrelation**: OLS residuals exhibit intense spatial autocorrelation ($I = 0.6304$ for richness, $I = 0.4556$ for endemism, both $p < 0.0001$), demonstrating that non-spatial OLS standard errors are heavily deflated.
2. **Total Richness Attenuation**: Modeling spatial error autocorrelation ($\lambda = 0.9516$) drastically improves model fit ($\Delta \text{AIC} = -921.1$) and reduces residual autocorrelation ($I = 0.0482$). Under this correction, the direct velocity coefficient attenuates by 56% to $\beta = -0.0342$, and its 95% confidence interval spans zero (`[-0.0737, +0.0053]`, $p = 0.08995$).
3. **Endemism Stability Holds**: For weighted endemism, the Spatial Error model filters spatial autocorrelation down to non-significance ($I = 0.0245, p = 0.1393$). In this well-specified error model, Quaternary climate velocity remains a powerful, statistically significant negative predictor ($\beta = -0.1745, p < 0.00001$, 95% CI `[-0.2451, -0.1039]`).
4. **AIC Comparability Principle**: AIC values are strictly comparable only within the same model family sharing the identical response variable structure (OLS versus Spatial Error). Comparisons between Spatial Lag and Spatial Error are informal due to differing endogenous lag specifications and Jacobian determinants.

---

## 6. Velocity Scale & Gradient-Floor Sensitivity Analysis

To test whether climate velocity rankings are artifacts of spatial raster grain or division-by-zero flooring in flat lowlands, we evaluated sensitivity across raster resolutions (10' native vs 20' aggregated) and minimum gradient regularization thresholds ($\epsilon \in \{10^{-5}, 10^{-4}, 10^{-3}\}$ °C/km).

*Table traceable to [`integration_v3/tables/velocity_sensitivity_v3b.csv`](tables/velocity_sensitivity_v3b.csv):*

| Sensitivity Dimension | Comparison Tested | Climate Source | Evaluation Grid | Spearman Rank $\rho$ | $p$-value | Methodological Conclusion |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Scale Sensitivity** | Native (10 arc-min) vs Aggregated (20 arc-min) | PaleoClim | 5° cells | **0.9686** | $< 10^{-200}$ | Macro-cell velocity rankings are robust to 2x raster downsampling |
| **Scale Sensitivity** | Native (10 arc-min) vs Aggregated (20 arc-min) | WorldClim | 5° cells | **0.9632** | $< 10^{-200}$ | Robust across independent GCM paleoclimate simulations |
| **Gradient Floor** | $\epsilon = 10^{-5}$ vs $\epsilon = 10^{-4}$ (Baseline) | PaleoClim | 5° cells | **0.999998** | $< 10^{-200}$ | Near-perfect concordance; 10x lower floor affects $< 0.1\%$ of land cells |
| **Gradient Floor** | $\epsilon = 10^{-4}$ (Baseline) vs $\epsilon = 10^{-3}$ | PaleoClim | 5° cells | **0.996391** | $< 10^{-200}$ | Rankings remain highly stable under 10x higher floor |
| **Gradient Floor** | $\epsilon = 10^{-5}$ vs $\epsilon = 10^{-3}$ | PaleoClim | 5° cells | **0.996295** | $< 10^{-200}$ | Velocity ordering is stable across a 100-fold variation in regularization floor |

Velocity calculations are invariant to reasonable variations in both computational resolution and low-gradient flooring.

---

## 7. Macroclimatic Interaction Tests

*Table traceable to [`integration_v3/tables/interactions_v3b.csv`](tables/interactions_v3b.csv):*

| Response | Interaction Term | Interaction $\beta$ | Std Error | $t$-statistic | $p$-value | Literature Prediction | Empirically Supported? |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **IUCN Richness** | Velocity $\times$ Precipitation | +0.0734 | 0.0196 | +3.737 | 0.0002 | Negative (stronger in wet) | **No (Counter-direction)** |
| **IUCN Richness** | Velocity $\times$ Seasonality | +0.1287 | 0.0223 | +5.780 | <0.00001 | Positive (stronger in aseasonal) | **Yes** |
| **IUCN Endemism** | Velocity $\times$ Precipitation | -0.1189 | 0.0223 | -5.338 | <0.00001 | Negative (stronger in wet) | **Yes** |
| **IUCN Endemism** | Velocity $\times$ Seasonality | +0.3044 | 0.0234 | +13.003 | <0.00001 | Positive (stronger in aseasonal) | **Yes** |

*Figure: [`integration_v3/figures/interaction_surfaces.png`](figures/interaction_surfaces.png)*

---

## 8. Pre-Registered Taxonomic Contrast (Sandel et al. 2011)

*Table traceable to [`integration_v3/tables/taxa_comparison_v3b.csv`](tables/taxa_comparison_v3b.csv):*

| Taxon | Predicted Sensitivity Rank | Richness Std $\beta$ | Richness $p$-value | Richness Partial $\rho$ | Endemism Std $\beta$ | Endemism $p$-value | Endemism Partial $\rho$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Reptiles** | 2 (Medium) | **-0.2881** | **<0.0001** | **-0.322** | **-0.1470** | **<0.0001** | **-0.276** |
| **Mammals** | 3 (Lowest) | +0.0119 | 0.6986 | -0.157 | **-0.0691** | **0.0004** | **-0.326** |
| **Amphibians**| 1 (Highest) | -0.0193 | 0.6543 | -0.103 | -0.0546 | 0.1045 | -0.171 |
| **All Vertebrates** | Reference | -0.0781 | 0.0046 | -0.295 | -0.1969 | <0.0001 | -0.326 |

*Figure: [`integration_v3/figures/taxa_comparison.png`](figures/taxa_comparison.png)*

The pre-registered prediction that amphibians are the most vulnerable group is unsupported. Reptiles demonstrate the strongest negative richness sensitivity ($\beta = -0.2881, p < 0.0001$), whereas amphibian partial relationships are statistically indistinguishable from zero once modern moisture is controlled for.
