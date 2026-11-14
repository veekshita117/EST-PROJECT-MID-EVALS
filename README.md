# Palaeoclimate Stability and Modern Biodiversity

**Question:** Are biodiversity-rich regions disproportionately associated with long-term Quaternary climatic stability?

---

## Data

- **PaleoClim**: Global paleoclimate surfaces at 2.5 arc-minutes resolution across Present (1979–2013), Late Holocene (sub-Boreal, 4.2–0.3 ka BP), and Last Glacial Maximum (LGM, ~21 ka BP) for Annual Mean Temperature (`BIO1`), Annual Precipitation (`BIO12`), Temperature Seasonality (`BIO4`), and Precipitation Seasonality (`BIO15`).
- **WorldClim**: Global paleoclimate surfaces from the Community Climate System Model (CCSM4) across Present (1960–1990), Mid-Holocene (~6 ka BP), and Last Glacial Maximum (~22 ka BP) for `BIO1`, `BIO12`, `BIO4`, and `BIO15`.
- **Copernicus DEM (GLO-90)**: Global 90-meter digital elevation model streamed from AWS Open Data public bucket `s3://copernicus-dem-90m/`, computing cell-level elevation mean, standard deviation, and relief range ($\text{elevation}_{\max} - \text{elevation}_{\min}$).
- **GBIF Primary Biodiversity Records**: 17,396 cleaned occurrence records covering 6,080 species globally across 6 continents (capped sample download, provenance not verified; see [`GBIF/raw/GBIF_METADATA.md`](GBIF/raw/GBIF_METADATA.md)), aggregated to 375 cells with records (compared to 1,473 5° land cells in PaleoClim and 1,121 in WorldClim; 893 2° cells with records compared to 7,285 and 5,359), with sampling effort controlled via $\ln(\text{n\_records})$.
- **IUCN Red List Spatial Data (Not Yet Used)**: Terrestrial range map ingestion pipeline specified in [`integration_v2/PLAN.md`](integration_v2/PLAN.md) (raw shapefiles were not placed in `IUCN/raw/`).

---

## Method

1. **Spatial Grid Definitions**:
   - Primary scale: 5° $\times$ 5° grid cells (375 cells with GBIF records, compared to 1,473 land cells in PaleoClim and 1,121 in WorldClim; $n = 188$ cells with $\ge 10$ records analysed).
   - Robustness scale: 2° $\times$ 2° grid cells (893 cells with GBIF records, compared to 7,285 in PaleoClim and 5,359 in WorldClim; $n = 264$ cells with $\ge 10$ records analysed).
2. **Climate Stability Metrics**:
   - Temperature Instability: Standard deviation of BIO1 across three time slices (°C).
   - Temperature LGM Change: $|\text{BIO1}_{\text{present}} - \text{BIO1}_{\text{lgm}}|$ (°C).
   - Precipitation Relative Change: $|\ln((P_{\text{lgm}}+1)/(P_{\text{present}}+1))|$.
   - Precipitation Absolute Change: $|P_{\text{present}} - P_{\text{lgm}}|$ (mm).
   - Seasonality Changes: $|\text{BIO4}_{\text{present}} - \text{BIO4}_{\text{lgm}}|$ and $|\text{BIO15}_{\text{present}} - \text{BIO15}_{\text{lgm}}|$.
   - Composite Climatic Instability Index: Mean of standardized z-scores of temperature instability and relative precipitation change.
   - Computed via single-pass zonal raster statistics (`cell_zonal_stats`) over all valid land pixels per cell.
3. **Topographic Heterogeneity & Controls**:
   - Mean elevation (`elevation_mean`) and topographic heterogeneity (`relief_range` = max - min elevation within cell) derived from Copernicus DEM GLO-90.
   - Absolute latitude ($|\text{lat}|$) and sampling effort ($\ln(\text{n\_records})$).
4. **Non-Parametric Rank Analysis**:
   - Bivariate Spearman $\rho$ and partial Spearman rank correlation controlling for $\ln N$, $|\text{lat}|$, `elevation_mean`, and `topographic_heterogeneity`.
   - 95% spatial-block bootstrap confidence intervals computed by resampling 20° $\times$ 20° spatial blocks with replacement (300 iterations).
   - Multiple testing correction via the Benjamini-Hochberg (BH) False Discovery Rate (FDR) procedure.
5. **Spatial Autocorrelation Diagnostics**:
   - Row-standardized K-Nearest Neighbors ($k=8$) spatial weight matrix constructed using great-circle distance on the sphere (3D Cartesian coordinates).
   - Global Moran's $I$ computed for raw species richness, $\ln(1 + \text{richness})$, and regression model residuals.
6. **Spatial Econometric Regressions**:
   - Ordinary Least Squares (OLS) regression on $\ln(1 + \text{richness})$ with standardized predictors.
   - Multicollinearity evaluated using Variance Inflation Factors (VIF).
   - Maximum Likelihood Spatial Error Model (`spreg.ML_Error`): $y = X\beta + u, \, u = \lambda W u + \varepsilon$.
   - Maximum Likelihood Spatial Lag Model (`spreg.ML_Lag`): $y = \rho W y + X\beta + \varepsilon$.
   - Model selection evaluated via AIC, Log-Likelihood, and residual spatial autocorrelation.
7. **Spatial-Block Cross-Validation**:
   - 5-fold cross-validation partitioning the globe into 20° $\times$ 20° spatial blocks ($55$ global blocks) to estimate out-of-sample $R^2_{\text{CV}}$ and $\text{RMSE}_{\text{CV}}$.

---

## Main Result

- **No Raw Relationship**: Bivariate Spearman correlations between species richness and Quaternary stability metrics are near zero ($\rho = -0.081$ to $+0.046$, $p > 0.18$).
- **Apparent Relationship in Non-Spatial Models**:
   - When controlling for sampling effort and latitude in non-spatial models, composite instability appears negatively correlated with species richness (partial $\rho = -0.284, p = 8.1 \times 10^{-5}$ for PaleoClim; partial $\rho = -0.203, p = 0.0053$ for WorldClim).
   - In standardized OLS regressions, composite instability appears statistically significant ($\beta = -0.128, p = 0.00014$ for PaleoClim; $\beta = -0.121, p = 0.0010$ for WorldClim).
- **Severe Spatial Autocorrelation in OLS**: OLS regression residuals exhibit strong positive spatial autocorrelation (Moran's $I = 0.1985, p = 0.001$), violating the assumption of independent observations and inflating nominal significance.
- **Model Comparison: Spatial Error vs. Spatial Lag vs. Bootstrap CIs**:
   - **Spatial Error Model**: The Spatial Error Model substantially improves model fit over OLS ($\Delta \text{AIC} = -22.70$ for PaleoClim, $\Delta \text{AIC} = -25.08$ for WorldClim). The filtered innovations show no remaining spatial autocorrelation ($I = 0.0012, p = 0.395$), as expected from the model design. Under this specification, the Quaternary instability effect attenuates substantially:
     - PaleoClim composite instability attenuates by 37% to $\beta = -0.0810$ ($p = 0.0625$, FDR $q = 0.0834$), losing statistical significance at $\alpha = 0.05$ (spatial error parameter $\lambda = 0.5350, p = 2.1 \times 10^{-9}$).
     - WorldClim composite instability attenuates by 50% to $\beta = -0.0609$ ($p = 0.178$, FDR $q = 0.200$, $\lambda = 0.5542, p = 1.4 \times 10^{-10}$).
   - **Spatial Lag Model**: Displays higher AIC than Spatial Error ($\text{AIC} = 106.28$ vs $89.37$ for PaleoClim; $\text{AIC} = 109.42$ vs $90.78$ for WorldClim), with significant residual spatial autocorrelation remaining in the errors ($I = 0.1479, p = 0.002$). Under Spatial Lag:
     - PaleoClim composite instability: $\beta = -0.1052$ ($p = 0.0012$, FDR $q = 0.0029$, spatial lag $\rho = 0.1627, p = 0.0034$).
     - WorldClim composite instability: $\beta = -0.0953$ ($p = 0.0074$, FDR $q = 0.0138$, $\rho = 0.1706, p = 0.0023$).
   - **Spatial-Block Bootstrap CIs (300 Iterations)**: 95% bootstrap confidence intervals for the full partial rank correlation account for within-block spatial dependencies:
     - PaleoClim composite instability: 95% CI `[-0.4432, -0.0741]`.
     - WorldClim composite instability: 95% CI `[-0.3393, +0.0063]`.
- **Topographic Heterogeneity Supports Micro-Refugia**: Copernicus DEM relief range remains a robust, statistically significant positive predictor of species richness across all models ($\beta = +0.0766, p = 0.0140$ in Spatial Error Model; $\beta = +0.0848, p = 0.0055$ in Spatial Lag Model), confirming that topographically complex landscapes provide microclimatic buffering and local refugia.
- **Negligible Out-of-Sample Predictive Contribution**: 5-fold 20° spatial-block cross-validation reveals that adding Quaternary stability provides an incremental out-of-sample $\Delta R^2_{\text{CV}} = +0.0079$ (less than $0.8\%$ additional variance explained).
- **Quartile Patterns & Hotspot Discordance**:
   - In stability quartiles, mean richness in the two more stable quartiles (Q1 ~61–66 species, Q2 ~61–62 species) is substantially higher than in Q3 (~36–40 species) and Q4 (~35 species), with Q3 about equal to Q4 in PaleoClim composite instability (35.91 vs 35.40). However, mean records per cell vary substantially across quartiles (e.g. Q4 cells average 123.3 records while Q3 cells average 58.1 records), demonstrating the effort confound across cells.
   - Richness hotspots are twice as frequent in climatically unstable regions (31 cells) as in stable regions (16 cells).

---

## Limitations

- **Sampling Effort Dominance**: Sampling effort accounts for an $R^2 = 0.8434$ in $\ln(1+\text{richness})$ on $\ln(\text{records})$ ($R^2 = 0.4237$ for raw richness on raw records) across the analysed cells, reflecting uneven global survey intensity.
- **Coarse Resolution**: 5° and 2° grid cells average over regional environmental gradients, though this is partially mitigated by incorporating Copernicus DEM relief range.
- **Paleoclimate Reconstruction Uncertainties**: Paleoclimatic surfaces rely on GCM simulations (PMIP3 ensemble and CCSM4) with known uncertainties in precipitation and localized ice-sheet dynamics.

---

## Repository Structure

```text
├── AUDIT.md                        # Codebase and data audit documentation
├── DATA_SOURCES.md                 # Bibliographic citations, DOIs, and licensing terms
├── FIGURES_AND_TABLES.md           # Master index of all figures and tables with captions
├── README.md                       # Project overview, methodology, and scientific findings
├── requirements.txt                # Python package dependencies
│
├── common/
│   └── helpers.py                  # Shared spatial aggregation, cell definition, and metrics
│
├── COPERNICUS_DEM/
│   ├── download_dem.py             # S3 tile streaming, decimated caching, and zonal stats
│   ├── figures/                    # Elevation maps, heterogeneity, and histograms
│   ├── processed/                  # dem_cells_5deg.csv and dem_cells_2deg.csv
│   └── notes.md                    # Elevation and refugia proxy documentation
│
├── PALEOCLIM/
│   ├── figures/                    # Temperature, precipitation, and composite stability maps
│   ├── processed/                  # Zonal stats at 5° and 2°, cell stability tables
│   ├── notes.md                    # Baseline temperature stability notes
│   └── notes_v2.md                 # Expanded precipitation and seasonality notes
│
├── WORLDCLIM/
│   ├── figures/                    # WorldClim stability maps and distributions
│   ├── processed/                  # Zonal stats at 5° and 2°, cell stability tables
│   ├── notes.md                    # Baseline temperature stability notes
│   └── notes_v2.md                 # Expanded precipitation and seasonality notes
│
├── GBIF/
│   ├── gbif.ipynb                  # Primary occurrence processing notebook
│   ├── figures/                    # Occurrence records, richness, and latitudinal maps
│   ├── processed/                  # Cleaned points and cell-level richness tables
│   └── notes.md                    # GBIF query, taxonomy, and sampling notes
│
├── integration/
│   ├── integration.ipynb           # Legacy mid-evaluation analysis notebook
│   ├── figures/                    # Mid-eval scatter plots, quartiles, and agreement maps
│   └── results.md                  # Mid-evaluation baseline results
│
├── integration_v2/
│   ├── PLAN.md                     # Analysis plan written alongside Phase 6 models
│   ├── run_phase6.py               # Complete spatial econometric and cross-validation pipeline
│   ├── figures/                    # Coefficient plot, Moran scatter, residual maps, and tables
│   ├── processed/                  # data_5deg.csv and data_2deg.csv
│   └── results.md                  # Comprehensive spatial modeling results and synthesis
│
└── tests/
    └── test_reproduce_mid_eval.py  # Regression test verifying mid-eval reproducibility
```

---

## Required Raw Files

The following raw files must be placed in their expected folders before running the full pipeline:

### 1. PaleoClim Rasters (`PALEOCLIM/raw/`)
Download 2.5 arc-minute GeoTIFFs from http://www.paleoclim.org:
- Present:
  - `paleoclim_current_BIO1.tif`
  - `paleoclim_current_BIO4.tif`
  - `paleoclim_current_BIO12.tif`
  - `paleoclim_current_BIO15.tif`
- Late Holocene (sub-Boreal):
  - `paleoclim_late_holocene_BIO1.tif` (reprojected to `paleoclim_late_holocene_BIO1_aligned.tif`)
  - `paleoclim_late_holocene_BIO4.tif` (reprojected to `paleoclim_late_holocene_BIO4_aligned.tif`)
  - `paleoclim_late_holocene_BIO12.tif` (reprojected to `paleoclim_late_holocene_BIO12_aligned.tif`)
  - `paleoclim_late_holocene_BIO15.tif` (reprojected to `paleoclim_late_holocene_BIO15_aligned.tif`)
- Last Glacial Maximum (LGM):
  - `paleoclim_lgm_BIO1.tif` (reprojected to `paleoclim_lgm_BIO1_aligned.tif`)
  - `paleoclim_lgm_BIO4.tif` (reprojected to `paleoclim_lgm_BIO4_aligned.tif`)
  - `paleoclim_lgm_BIO12.tif` (reprojected to `paleoclim_lgm_BIO12_aligned.tif`)
  - `paleoclim_lgm_BIO15.tif` (reprojected to `paleoclim_lgm_BIO15_aligned.tif`)

### 2. WorldClim Rasters (`WORLDCLIM/raw/`)
Download 2.5 arc-minute grids from https://www.worldclim.org:
- Present:
  - `WORLDCLIM/raw/present/bio/bio_1`
  - `WORLDCLIM/raw/present/bio/bio_4`
  - `WORLDCLIM/raw/present/bio/bio_12`
  - `WORLDCLIM/raw/present/bio/bio_15`
- Mid-Holocene (CCSM4):
  - `WORLDCLIM/raw/mid_holocene/ccmidbi1.tif`
  - `WORLDCLIM/raw/mid_holocene/ccmidbi4.tif`
  - `WORLDCLIM/raw/mid_holocene/ccmidbi12.tif`
  - `WORLDCLIM/raw/mid_holocene/ccmidbi15.tif`
- Last Glacial Maximum (CCSM4):
  - `WORLDCLIM/raw/lgm/cclgmbi1.tif`
  - `WORLDCLIM/raw/lgm/cclgmbi4.tif`
  - `WORLDCLIM/raw/lgm/cclgmbi12.tif`
  - `WORLDCLIM/raw/lgm/cclgmbi15.tif`

### 3. GBIF Occurrence Files (`GBIF/raw/`)
Regional occurrence CSV archives (tracked in repository):
- `gbif_all_continents.csv` (or the 6 regional files: `gbif_africa_5000.csv`, `gbif_asia_5000.csv`, `gbif_europe_5000.csv`, `gbif_north_america_1000.csv`, `gbif_oceania_1000.csv`, `gbif_south_america_1000.csv`).

### 4. Copernicus DEM (`COPERNICUS_DEM/raw/`)
- Streamed automatically by `COPERNICUS_DEM/download_dem.py` from AWS public bucket `s3://copernicus-dem-90m/` and cached locally in `COPERNICUS_DEM/raw/tiles/`.

---

## Run Order

To execute the complete research pipeline from clean raw data to final models:

1. **Copernicus DEM Streaming & Processing**:
   ```bash
   python3 COPERNICUS_DEM/download_dem.py
   ```
2. **Climate Metrics Expansion (PaleoClim & WorldClim)**:
   ```bash
   python3 run_phase2_climate_expansion.py
   ```
3. **Spatial Modeling & Statistical Integration (Phase 6)**:
   ```bash
   python3 integration_v2/run_phase6.py
   ```
4. **Reproducibility & Regression Test**:
   ```bash
   pytest tests/test_reproduce_mid_eval.py
   ```
5. **Legacy Mid-Evaluation Notebooks (Optional Verification)**:
   ```bash
   # Run in sequence:
   # GBIF/gbif.ipynb -> PALEOCLIM/paleoclim.ipynb -> WORLDCLIM/worldclim.ipynb -> integration/integration.ipynb
   ```

---

## Setup

```bash
# Clone repository and switch to branch
git checkout future-implementations

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
