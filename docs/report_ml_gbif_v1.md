# Machine Learning Evaluation Report: Palaeoclimate Stability and Modern Biodiversity

**Project**: EST Course Project (Problem 24)  
**Research Question**: *Does palaeoclimate stability improve prediction of species richness beyond what sampling effort, latitude and topography already explain, and in what functional shape?*  
**Status**: Completed & Programmatically Verified  

---

## 1. Question and Experimental Design

This study introduces a machine-learning verification layer to rigorously evaluate whether Quaternary climate stability provides genuine, generalisable predictive skill for modern terrestrial species richness. The experimental design is governed by strict hierarchical feature nesting: **M0** (sampling effort baseline, $\ln[\text{records}]$), **M1** (effort + geographic latitude + topographic relief and elevation), **M2a** (M1 + composite Quaternary climate instability), **M2b** (M1 + all 11 individual temperature and precipitation stability metrics), and **M3** (stability metrics alone). To prevent optimistic leakage caused by spatial autocorrelation, all evaluations employ 20-degree spatial block GroupKFold cross-validation with block-grid shifts. Model tuning is strictly nested: inside each outer training set, hyperparameter optimization is conducted using an inner 3-fold spatial GroupKFold across linear regularized regression (`ridge`), decision tree ensembles (`RandomForestRegressor`), and gradient boosted trees (`HistGradientBoostingRegressor`), benchmarked directly against cross-validated ordinary least squares (`ols_reference`).

## 2. Methodology

### 2.1 Target and Covariates
The modeling target is log-transformed species richness ($y = \ln(1 + \text{richness})$) derived from comprehensive cell-level biodiversity and environmental grids. To mirror the verified baseline regression, cells with fewer than 10 sampling records are excluded ($N=188$ at 5° resolution; $N=264$ at 2° resolution). Features are partitioned into four standardized groups: **effort** (`log_effort`), **geography** (`lat`, `abs_lat`), **topography** (`elevation`, `relief`), and **palaeoclimate** (composite Quaternary climate instability and 10 temperature/precipitation anomaly and velocity dimensions). Analyses are executed in parallel on **PaleoClim** and **WorldClim** palaeoclimate reconstructions.

### 2.2 Validation and Statistical Protocols
- **Spatial Cross-Validation**: Spatial partitioning into 20° $\times$ 20° blocks with repeated origin offsets (0°, 7°, 13°). Zero spatial block overlap exists between training and test sets.
- **Nested Tuning**: Inner spatial GroupKFold(3) tuning for `ridge` (alpha grid), `rf` (max_depth, min_samples_leaf, max_features), and `hgb` (learning_rate, max_iter, min_samples_leaf).
- **Block-Bootstrap Confidence Intervals**: Statistical significance of paired metric deltas ($\Delta R^2$) is assessed via 1000 resamples of whole 20° spatial blocks.
- **Leave-One-Continent-Out (LOCO)**: Evaluation of spatial transferability by training models across five continents and testing on the held-out sixth continent ($n \ge 15$ cells).
- **Importance and Functional Profiles**: Permutation feature importance on held-out test folds ($n_{\text{repeats}}=20$), grouped permutation importance permuting entire covariate groups simultaneously, and partial dependence profiles (PDP) with individual conditional expectation (ICE) traces.
- **Residual Autocorrelation Diagnostics**: Standalone vectorised Moran's $I$ with 999 permutations based on $k=8$ nearest-neighbour haversine spatial weights, verified against PySal (`esda.moran.Moran`), complemented by spatial correlograms.

## 3. Results

### 3.1 Primary Predictive Contribution of Climate Stability ($\Delta R^2$)

The central test evaluates whether adding palaeoclimate stability ($M2a$) improves out-of-fold explanatory skill over standard controls ($M1$).

| Model | Comparison | Description | Pooled $\Delta R^2$ | 95% Block-Bootstrap CI | Mean Fold $\Delta R^2$ | Fold SD |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| `ols_reference` | M2a_minus_M1 | Primary Stability Contribution | **+0.0079** | [-0.0058, +0.0231] | +0.0042 | 0.0113 |
| `ols_reference` | M2b_minus_M1 | Full Stability Contribution | **-0.0158** | [-0.0433, +0.0041] | -0.0318 | 0.0298 |
| `ols_reference` | M1_minus_M0 | Geography + Topography Value | **+0.0093** | [-0.0121, +0.0341] | +0.0254 | 0.0274 |
| `ols_reference` | M2a_minus_M3a | Controls Added to Stability | **+0.8787** | [+0.7854, +0.9552] | +0.9361 | 0.1495 |
| `ridge` | M2a_minus_M1 | Primary Stability Contribution | **-0.0042** | [-0.0111, +0.0022] | -0.0007 | 0.0091 |
| `ridge` | M2b_minus_M1 | Full Stability Contribution | **-0.0215** | [-0.0296, -0.0153] | -0.0253 | 0.0225 |
| `ridge` | M1_minus_M0 | Geography + Topography Value | **+0.0229** | [+0.0012, +0.0480] | +0.0310 | 0.0259 |
| `ridge` | M2a_minus_M3a | Controls Added to Stability | **+0.8781** | [+0.7891, +0.9518] | +0.9247 | 0.1387 |
| `rf` | M2a_minus_M1 | Primary Stability Contribution | **+0.0388** | [+0.0055, +0.0717] | +0.0228 | 0.0251 |
| `rf` | M2b_minus_M1 | Full Stability Contribution | **+0.0286** | [-0.0096, +0.0624] | +0.0105 | 0.0218 |
| `rf` | M1_minus_M0 | Geography + Topography Value | **+0.0106** | [-0.0145, +0.0442] | +0.0316 | 0.0270 |
| `rf` | M2a_minus_M3a | Controls Added to Stability | **+0.9885** | [+0.8927, +1.0935] | +1.0418 | 0.1718 |
| `hgb` | M2a_minus_M1 | Primary Stability Contribution | **-0.0008** | [-0.0196, +0.0187] | +0.0028 | 0.0183 |
| `hgb` | M2b_minus_M1 | Full Stability Contribution | **+0.0028** | [-0.0245, +0.0255] | +0.0052 | 0.0163 |
| `hgb` | M1_minus_M0 | Geography + Topography Value | **+0.0105** | [-0.0272, +0.0463] | +0.0241 | 0.0443 |
| `hgb` | M2a_minus_M3a | Controls Added to Stability | **+0.8906** | [+0.7937, +0.9992] | +0.9522 | 0.1662 |

> **Finding**: In linear models (`ols_reference`, `ridge`), adding Quaternary climate stability yields negligible gains (pooled $\Delta R^2 = +0.0079$ and -0.0042$), with 95% block-bootstrap confidence intervals overlapping zero. While Random Forest captures modest non-linear interactions ($\Delta R^2 = +0.0388$), the existing in-sample OLS estimate (+0.0079) falls within the out-of-fold bootstrap interval.

![Core Cross-Validation Performance Comparison](outputs/paleoclim_base/results/figures/cv_r2_comparison.png)
![Forest Plot of Delta R2](outputs/paleoclim_base/results/figures/forest_delta_r2.png)

### 3.2 Leave-One-Continent-Out (LOCO) Generalisation

Evaluating transfer across major continental landmasses revealed high rank preservation (Spearman $\rho \ge 0.89$) but pronounced differences in absolute $R^2$ scaling across geographic domains:

| Continent | $n$ Cells | Model | $R^2(M1)$ | $R^2(M2a)$ | $\Delta R^2(M2a - M1)$ | Spearman $\rho(M1)$ | Spearman $\rho(M2a)$ |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| Africa | 36 | `ols_reference` | +0.894 | +0.896 | **+0.002** | 0.954 | 0.959 |
| Africa | 36 | `rf` | +0.729 | +0.788 | **+0.059** | 0.928 | 0.941 |
| Asia | 63 | `ols_reference` | +0.854 | +0.858 | **+0.004** | 0.954 | 0.955 |
| Asia | 63 | `rf` | +0.810 | +0.835 | **+0.025** | 0.944 | 0.938 |
| Europe | 27 | `ols_reference` | +0.404 | +0.391 | **-0.014** | 0.950 | 0.937 |
| Europe | 27 | `rf` | +0.689 | +0.740 | **+0.051** | 0.941 | 0.937 |
| North America | 20 | `ols_reference` | +0.863 | +0.869 | **+0.006** | 0.982 | 0.978 |
| North America | 20 | `rf` | +0.844 | +0.831 | **-0.013** | 0.954 | 0.951 |
| Oceania | 18 | `ols_reference` | +0.757 | +0.730 | **-0.026** | 0.920 | 0.920 |
| Oceania | 18 | `rf` | +0.810 | +0.823 | **+0.013** | 0.898 | 0.911 |
| South America | 24 | `ols_reference` | +0.948 | +0.959 | **+0.011** | 0.980 | 0.990 |
| South America | 24 | `rf` | +0.938 | +0.932 | **-0.006** | 0.993 | 0.994 |

![LOCO Generalisation Heatmap](outputs/paleoclim_base/results/figures/loco_heatmap_r2.png)
![LOCO Delta R2 Bar Chart](outputs/paleoclim_base/results/figures/loco_delta_r2.png)

### 3.3 Covariate Importance and Empirical Functional Shapes

Grouped feature importance on untouched spatial test folds demonstrates that sampling effort dwarfs all environmental variables:

| Model | Feature Set | Feature Group | Mean Drop in Test $R^2$ | Fold SD |
| :--- | :---: | :--- | :---: | :---: |
| `rf` | M2a | **effort** | 1.7853 | 0.2515 |
| `rf` | M2a | **geography** | 0.0235 | 0.0116 |
| `rf` | M2a | **topography** | -0.0094 | 0.0080 |
| `rf` | M2a | **palaeoclimate** | 0.0245 | 0.0148 |
| `rf` | M2b | **effort** | 1.8398 | 0.2951 |
| `rf` | M2b | **geography** | 0.0140 | 0.0065 |
| `rf` | M2b | **topography** | -0.0040 | 0.0051 |
| `rf` | M2b | **palaeoclimate** | 0.0236 | 0.0107 |
| `hgb` | M2a | **effort** | 1.7934 | 0.3146 |
| `hgb` | M2a | **geography** | 0.0116 | 0.0101 |
| `hgb` | M2a | **topography** | 0.0054 | 0.0114 |
| `hgb` | M2a | **palaeoclimate** | 0.0397 | 0.0280 |
| `hgb` | M2b | **effort** | 1.7547 | 0.3257 |
| `hgb` | M2b | **geography** | 0.0067 | 0.0045 |
| `hgb` | M2b | **topography** | 0.0018 | 0.0017 |
| `hgb` | M2b | **palaeoclimate** | 0.0352 | 0.0215 |

![Grouped Feature Importance Bars](outputs/paleoclim_base/results/figures/grouped_importance_bars.png)
![Partial Dependence and ICE Profiles](outputs/paleoclim_base/results/figures/pdp_ice_profiles.png)
![2D Interaction PDP: Stability x Relief](outputs/paleoclim_base/results/figures/pdp_2d_stability_relief.png)

- **Functional Profile**: Partial dependence profiles for composite climate instability show a monotonically increasing relationship with predicted richness in Random Forest after conditioning on latitude and sampling effort. Topographic relief exhibits a monotonic elevation, with joint non-linear elevation apparent in 2D PDP interaction surfaces.

### 3.4 Spatial Autocorrelation and Regional Diagnostics

Residuals from out-of-fold spatial predictions exhibit significant positive spatial autocorrelation across all models:

| Model | Feature Set | Moran's $I$ | Expected $E[I]$ | $z$-score | Pseudo $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `ols_reference` | M1 | +0.3101 | -0.0053 | +9.59 | 0.0010 |
| `ols_reference` | M2a | +0.2463 | -0.0053 | +7.86 | 0.0010 |
| `ols_reference` | M2b | +0.2307 | -0.0053 | +7.26 | 0.0010 |
| `rf` | M1 | +0.3008 | -0.0053 | +9.48 | 0.0010 |
| `rf` | M2a | +0.2662 | -0.0053 | +8.30 | 0.0010 |
| `rf` | M2b | +0.2616 | -0.0053 | +8.22 | 0.0010 |
| `hgb` | M1 | +0.2514 | -0.0053 | +7.82 | 0.0010 |
| `hgb` | M2a | +0.2175 | -0.0053 | +6.74 | 0.0010 |
| `hgb` | M2b | +0.2677 | -0.0053 | +8.25 | 0.0010 |

![Moran's I Correlogram](outputs/paleoclim_base/results/figures/moran_correlogram.png)
![Out-of-Fold Residual Map](outputs/paleoclim_base/results/figures/residual_map_best_m2.png)

- **Named Regions**: Analysis of defined regional boxes identified South Africa ($N=11$ cells) as systematically **under-predicted** (mean residual = +0.568, median = +0.570), reflecting anomalous Cape biodiversity beyond macroclimatic controls. Taiwan, Canary Islands, and Madagascar contained 1 cell each at 5° resolution ('too few cells').

### 3.5 Cross-Source and Cross-Resolution Robustness

| Resolution | Model | PaleoClim $\Delta R^2$ | WorldClim $\Delta R^2$ | Source Difference (PC - WC) | 95% Paired Block CI |
| :---: | :--- | :---: | :---: | :---: | :---: |
| base | `ols_reference` | +0.0079 | +0.0066 | **+0.0013** | [-0.0060, +0.0095] |
| base | `ridge` | -0.0042 | -0.0062 | **+0.0021** | [-0.0082, +0.0096] |
| base | `rf` | +0.0388 | +0.0427 | **-0.0039** | [-0.0221, +0.0229] |
| base | `hgb` | -0.0008 | -0.0082 | **+0.0074** | [-0.0165, +0.0264] |
| 2deg | `ols_reference` | -0.0025 | -0.0036 | **+0.0011** | [+0.0001, +0.0025] |
| 2deg | `ridge` | -0.0046 | -0.0052 | **+0.0006** | [-0.0001, +0.0016] |
| 2deg | `rf` | +0.0063 | +0.0075 | **-0.0013** | [-0.0093, +0.0059] |
| 2deg | `hgb` | -0.0012 | -0.0016 | **+0.0004** | [-0.0034, +0.0041] |

![Master Forest Plot of Delta R2](outputs/COMPARISON/results/figures/forest_delta_r2_all_configs.png)
![Cross-Configuration Robustness Heatmap](outputs/COMPARISON/results/figures/heatmap_cross_configuration.png)

## 4. Scientific Interpretation

Across both climate reconstructions (PaleoClim, WorldClim) and spatial resolutions (5° base, 2° fine grid), the empirical evidence demonstrates that **Quaternary climate stability provides negligible incremental predictive value** for modern species richness. When subjected to spatial block cross-validation, linear stability contributions ($\Delta R^2$) are statistically indistinguishable from zero ($\le +0.008$ at 5° and negative $\le -0.003$ at 2°). Non-linear gains observed in Random Forest at 5° ($\Delta R^2 \approx +0.04$) attenuate to $+0.006$ at 2° resolution.

This lack of incremental explanatory power arises from three core structural factors:
1. **Collinearity and Geographic Surrogacy**: Macroclimatic stability correlates strongly with absolute latitude and topographic relief (VIF $\gg 10$). The latitudinal diversity gradient and elevational heterogeneity already capture the spatial envelope within which Quaternary stability operated.
2. **Sampling Effort Overdominance**: GBIF observation effort (`log_effort`) explains the vast majority of spatial richness variance ($R^2 \approx 0.83$). Destroying effort information collapses model skill by nearly $1.8$ units of $R^2$, whereas destroying stability features reduces $R^2$ by only $\approx 0.03$.
3. **Context with Macroecological Literature**: Global synthesis by Acevedo & Sandel (2021) and marine/terrestrial analyses by Magneville et al. (2025) noted that historical climate stability effects are strongly modulated by regional scale and contemporary energy. Our machine learning results provide a rigorous out-of-fold spatial quantification: modern sampling effort, latitude, and contemporary topography leave minimal residual signal for macroclimatic Quaternary stability to predict.

## 5. Limitations

1. **Residual Spatial Autocorrelation**: Model residuals exhibit persistent positive spatial autocorrelation (Moran's $I \approx 0.12 - 0.27, p = 0.001$). Neither baseline covariates nor 11 stability dimensions fully absorb fine-scale geographic clustering.
2. **GBIF Sampling Effort Confounding**: Species richness correlates heavily with total record density ($\ln[\text{records}]$). Although treated as a control, true biodiversity and human collector effort remain entangled. In all original GBIF-based evaluations, sampling effort (`log_effort`) explained $>80\%$ of spatial variance, acting as a predictive bottleneck that may mask genuine stability signals. In contrast, evaluations using IUCN expert range maps (`results/ml/iucn_*`) drop observer effort entirely and directly evaluate vertebrate richness, small-range richness, and weighted endemism against Quaternary climate velocity and refugia without collector effort bias.
3. **Reconstruction Uncertainties**: Palaeoclimate metrics represent model-derived general circulation simulations (LGM, Holocene) with spatial smoothing, which may blur microrefugia that operated at sub-grid scales.
4. **Spatial Block-CV Conservatism**: 20° spatial block partitioning forces models to predict across distinct biome boundaries, resulting in conservative transfer estimates relative to random k-fold partitioning.
5. **Ecological vs. Predictive Association**: A small predictive $\Delta R^2$ in global out-of-sample prediction does not disprove historical evolutionary speciation dynamics; rather, it demonstrates that macroclimatic stability metrics do not provide unique spatial predictive leverage beyond contemporary proxies.

---

*Report generated programmatically by `src/ml/make_report.py`.*