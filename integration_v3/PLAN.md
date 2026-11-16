# Phase 8 Pre-Registration Plan: Richer Palaeoclimate Stability Metrics

**Document Type**: Pre-Registration Protocol  
**Repository Branch**: `future-implementations`  
**Location**: `integration_v3/PLAN.md`  
**Execution Order Requirement**: This plan is committed alone to version control **before** performing any statistical association or modelling touching species richness.

---

## 1. Research Question & Rationale

Prior evaluation (Stages 1–9) revealed that simple scalar macroclimatic anomalies (e.g., $|\text{BIO1}_{\text{present}} - \text{BIO1}_{\text{LGM}}|$) provide negligible predictive increments beyond latitude and topography ($\Delta R^2 \le +0.008$ at 5° and negative at 2°). 

Phase 8 evaluates whether **physically and ecologically richer palaeoclimate stability formulations**—specifically **climate-change velocity** (Loarie et al. 2009 Nature; Sandel et al. 2011 Science) and **refugial area buffering**—provide stronger explanatory power for modern biodiversity patterns. Climate velocity accounts for the local topographic slope: in steep montane terrain, a species needs only disperse a short distance upslope to track its thermal niche, whereas in flat lowlands, tracking climate requires migrating hundreds of kilometres.

---

## 2. Hypothesis & Predictor Hierarchy

To maintain rigorous statistical inference and avoid $p$-hacking or post-hoc metric cherry-picking, we pre-specify a strict two-tier hierarchy:

### PRIMARY PREDICTOR
- **Metric**: $\log_{10}(\text{LGM-to-Present Temperature Climate-Change Velocity})$ ($\log_{10} V_{\text{temp}}$)
- **Units**: $\log_{10}(\text{km / yr})$ or $\log_{10}(\text{km / 1,000 yr})$
- **Definition**: The median over valid raster pixels within each macro-cell of the ratio between temporal temperature change rate ($|\Delta T| / 21{,}000\text{ yr}$) and the local contemporary spatial temperature gradient magnitude ($\|\nabla T\|$).
- **Primary Hypothesis**: Areas of low climate velocity acted as stable Quaternary microrefugia, promoting species persistence and accumulation of narrow-range endemics.

### SECONDARY PREDICTORS (Exploratory / Sensitivity Family)
All secondary metrics will be subject to Benjamini-Hochberg (FDR) false discovery rate adjustments across the complete metric family:
1. **Temperature Anomaly**: $|\text{BIO1}_{\text{present}} - \text{BIO1}_{\text{LGM}}|$ (°C).
2. **Precipitation Climate-Change Velocity**: $\log_{10}(V_{\text{precip}})$, computed using transformed precipitation $\ln(P + 1)$ to handle multiplicative moisture scaling.
3. **Refugial Area Fraction**: The proportion of valid land pixels within a macro-cell exhibiting climate velocity strictly below the global 25th percentile ($Q_{25}$ calculated globally across all land pixels).
4. **Precipitation Relative Change**: $|\ln(P_{\text{LGM}} + 1) - \ln(P_{\text{present}} + 1)|$.
5. **Temporal Temperature Instability**: Sample standard deviation of BIO1 across the three chronological time slices (Present, Mid/Late Holocene, LGM).
6. **Temporal Precipitation Instability**: Sample standard deviation of BIO12 across the three chronological time slices.
7. **Temperature Seasonality Change**: $|\text{BIO4}_{\text{present}} - \text{BIO4}_{\text{LGM}}|$.
8. **Precipitation Seasonality Change**: $|\text{BIO15}_{\text{present}} - \text{BIO15}_{\text{LGM}}|$.
9. **PCA-Based Composite Stability Index**: First principal component (PC1) extracted from the correlation matrix of z-scored temperature anomaly, $\log_{10}(V_{\text{temp}})$, and relative precipitation change.

---

## 3. Mathematical Formulations & Spatial Algorithms

### A. Climate-Change Velocity
Following Loarie et al. (2009) and Sandel et al. (2011), the instantaneous velocity of climate change $V$ at pixel $(i, j)$ is:
$$V(i, j) = \frac{\left| \frac{\partial T}{\partial t} \right|}{\| \nabla T(i, j) \|}$$

Where:
1. **Temporal Rate**:
   $$\left| \frac{\partial T}{\partial t} \right| = \frac{|\text{BIO1}_{\text{present}}(i, j) - \text{BIO1}_{\text{LGM}}(i, j)|}{21{,}000 \text{ years}}$$
   (representing 21 ka to 0 ka BP).

2. **Spatial Gradient Magnitude ($\| \nabla T \|$)**:
   Computed on the contemporary raster grid with cosine-of-latitude spherical correction:
   $$\Delta x(i, j) = R \cdot \cos\left( \frac{\pi \cdot \text{lat}_j}{180} \right) \cdot \Delta \lambda$$
   $$\Delta y(i, j) = R \cdot \Delta \phi$$
   where $R = 6,371\text{ km}$, $\Delta \lambda$ and $\Delta \phi$ are the grid cell dimensions in radians.
   The spatial partial derivatives are computed via central differences:
   $$\frac{\partial T}{\partial x} \approx \frac{T(i+1, j) - T(i-1, j)}{2 \Delta x}, \quad \frac{\partial T}{\partial y} \approx \frac{T(i, j+1) - T(i, j-1)}{2 \Delta y}$$
   $$\| \nabla T(i, j) \| = \sqrt{\left(\frac{\partial T}{\partial x}\right)^2 + \left(\frac{\partial T}{\partial y}\right)^2}$$

3. **Gradient Floor (Regularization)**:
   In flat lowlands (e.g. Amazonian plains, West Siberian plain), spatial gradients approach zero, which would cause numerical division-by-zero artifacts.
   A documented minimum gradient floor of $\epsilon = 10^{-4}\text{ }^\circ\text{C / km}$ ($0.01^\circ\text{C / 100 km}$) is applied:
   $$\| \nabla T_{\text{floored}} \| = \max(\| \nabla T \|, \epsilon)$$

4. **Macro-Cell Aggregation**:
   Because velocities are log-normally distributed, aggregation from pixels to 5° and 2° macro-cells is performed via the **median** of pixel velocities, followed by $\log_{10}$ transformation:
   $$\log_{10} V_{\text{cell}} = \log_{10}(\text{Median}(\{ V(i, j) : (i, j) \in \text{cell} \}))$$

### B. Refugial Area Fraction
1. Compute the global 25th percentile threshold $V_{\text{refugia}} = Q_{25}(\{ V(i, j) \})$ across all valid global land pixels.
2. For each macro-cell:
   $$\text{Refugial Fraction} = \frac{\sum_{(i, j) \in \text{cell}} \mathbb{I}(V(i, j) \le V_{\text{refugia}})}{N_{\text{valid pixels in cell}}}$$

### C. PCA Composite Construction
1. Standardize candidate stability features to zero mean and unit variance ($z$-scores):
   - $z_1 = z(|\text{BIO1}_{\text{pres}} - \text{BIO1}_{\text{LGM}}|)$
   - $z_2 = z(\log_{10} V_{\text{temp}})$
   - $z_3 = z(\text{Precipitation Change})$
2. Compute Principal Component Analysis (PCA) on the standardized covariance matrix.
3. Retain PC1 as the composite instability metric, saving component loadings, eigenvalues, and explained variance ratio.

---

## 4. Multi-Scale Sensitivity & Cross-Source Evaluation

1. **Scale Sensitivity**:
   Because spatial gradients depend heavily on the scale of calculation (coarser rasters smooth out microclimatic elevation relief), velocity will be evaluated at:
   - Native 10 arc-minute resolution (~18.5 km)
   - Aggregated 20 arc-minute resolution (~37 km)
   We report the Spearman rank correlation $\rho$ between the two scales across all cells to quantify scale dependence.

2. **Palaeoclimate Model Agreement**:
   All metrics will be computed separately for:
   - **PaleoClim** (CHELSA-based LGM reconstruction)
   - **WorldClim** (CCSM4-based LGM reconstruction)
   Pairwise Spearman rank correlations between PaleoClim and WorldClim will be calculated for every metric to evaluate inter-GCM consensus.

---

## 5. Output Artifacts Specification

Outputs will be saved strictly to new, non-overlapping file paths:
- `PALEOCLIM/processed/paleoclim_stability_v3_5deg.csv`
- `PALEOCLIM/processed/paleoclim_stability_v3_2deg.csv`
- `WORLDCLIM/processed/worldclim_stability_v3_5deg.csv`
- `WORLDCLIM/processed/worldclim_stability_v3_2deg.csv`
- `PALEOCLIM/notes_v3.md` & `WORLDCLIM/notes_v3.md`
- Diagnostic maps: `PALEOCLIM/figures/*_velocity_v3.png`, `WORLDCLIM/figures/*_velocity_v3.png`
