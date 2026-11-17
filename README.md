# Palaeoclimate Stability and Modern Biodiversity

**Question:** Are biodiversity-rich regions disproportionately associated with long-term Quaternary climatic stability?

---

## Key Findings

When evaluated against opportunistic GBIF occurrence records, modern species richness is overwhelmingly dominated by human sampling effort ($R^2 \approx 0.83$, permutation drop $\approx 1.8$ units of $R^2$), and apparent negative relationships with Quaternary instability attenuate substantially once spatial autocorrelation is absorbed via Maximum Likelihood Spatial Error models ($\lambda \approx 0.54 - 0.95, p < 10^{-5}$) and 20° spatial-block bootstrap confidence intervals. When evaluated on expert-verified IUCN terrestrial vertebrate distributions (`rasterSp` 0.5° rasters with observer effort eliminated), Quaternary climate velocity and refugial persistence provide a statistically robust, strictly positive out-of-fold predictive increment of $+1.3\%$ to $+2.8\%$ in linear models ($p_{\text{boot}} < 0.001$), while non-linear tree ensembles demonstrate that contemporary bioclimatic seasonality and latitude already explain $91-93\%$ of global richness variance. Across scales and taxa, climate velocity operates as a non-linear threshold ceiling rather than an unconstrained linear plunge, and historical stability metrics confer their greatest macroecological value in intercontinental generalization, improving out-of-continent transferability by $+8\%$ to $+27\%$ across undersampled Southern Hemisphere landmasses.

---

## Data

- **IUCN Red List Global Grids (`rasterSp` 0.5°)**: Terrestrial vertebrate distributions derived from the `rasterSp` R package at 0.5° resolution across Mammalia, Amphibia, and Reptilia (the polar bear *Ursus maritimus* was excluded due to obligate marine sea-ice ecology). Aggregated to 5° ($N = 755$ complete land cells) and 2° ($N = 4,395$ complete land cells) grids, providing unconfounded targets for total richness, small-range richness (Q25), and weighted endemism without human collector density bias.
- **GBIF Primary Biodiversity Records**: 17,396 cleaned occurrence records covering 6,080 species globally across 6 continents, aggregated to 375 5° cells (893 2° cells). Sampling effort is explicitly tracked and controlled via $\ln(\text{n\_records})$ and individual-based rarefaction ($n=20$).
- **Copernicus DEM (GLO-90)**: Global 90-meter digital elevation model streamed from AWS Open Data public bucket `s3://copernicus-dem-90m/`, calculating cell-level elevation mean, standard deviation, and topographic relief heterogeneity.
- **PaleoClim**: Global paleoclimate surfaces at 2.5 arc-minutes resolution derived from CHELSA downscaling across Present (1979–2013), Late Holocene (sub-Boreal, 4.2–0.3 ka BP), and Last Glacial Maximum (LGM, ~21 ka BP) for temperature (`BIO1`), precipitation (`BIO12`), temperature seasonality (`BIO4`), and precipitation seasonality (`BIO15`).
- **WorldClim**: Independent global paleoclimate surfaces from CCSM4 across Present (1960–1990), Mid-Holocene (~6 ka BP), and Last Glacial Maximum (~22 ka BP) for cross-product validation.

---

## Method & Analytical Pipeline

1. **Spatial Grid Aggregation**:
   - Primary resolution: 5° $\times$ 5° grid cells ($N = 755$ IUCN complete cells; $n = 188$ GBIF benchmark cells with $\ge 10$ records).
   - Fine-grain resolution: 2° $\times$ 2° grid cells ($N = 4,395$ IUCN complete cells; $n = 264$ GBIF benchmark cells).
2. **Climate Stability & Refugia Metrics**:
   - Quaternary Climate Velocity: $\log_{10}(\text{temporal anomaly} / \text{spatial gradient})$ following Sandel et al. (2011) with a gradient floor $\epsilon = 10^{-4}$ °C/km.
   - Refugial Area Fraction: Spatial overlap of Present and LGM bioclimatic thermal envelopes.
   - Climate Anomalies: Absolute temperature change ($|\text{LGM} - \text{Present}|$) and relative precipitation change ($|\ln[(P_{\text{LGM}}+1)/(P_{\text{Present}}+1)]|$).
   - Composite Instability: Multi-metric standardized z-score index over temperature and precipitation dimensions.
3. **Spatial Econometric Regressions**:
   - Maximum Likelihood Spatial Error Model (`spreg.ML_Error`): $y = X\beta + u, \, u = \lambda W u + \varepsilon$.
   - Maximum Likelihood Spatial Lag Model (`spreg.ML_Lag`): $y = \rho W y + X\beta + \varepsilon$.
   - Conditional Quantile Regressions across $\tau \in \{0.10, 0.50, 0.75, 0.90\}$ testing upper-bound ceiling constraints.
   - Two-sided block-bootstrap $p$-values and Benjamini-Hochberg False Discovery Rate (FDR) $q$-values.
4. **Machine Learning Verification Layer**:
   - 20° $\times$ 20° spatial-block GroupKFold cross-validation ($k=5$) with nested inner spatial hyperparameter tuning ($k=3$) across OLS, Ridge ($\alpha \in [10^{-3}, 10^{3}]$), Random Forest (100 trees), and HistGradientBoosting.
   - Paired out-of-fold $\Delta R^2$ ($M2 - M1$) evaluated with 1,000-draw cluster block-bootstrap 95% confidence intervals.
   - Leave-One-Continent-Out (LOCO) cross-validation evaluating intercontinental generalization across 6 continents.
   - Interpretability: Grouped permutation feature importance on untouched test folds, TreeExplainer SHAP attribution, partial dependence profiles (PDP/ALE), and out-of-fold residual Moran's $I$ diagnostics.

---

## Pipeline Execution Order

To execute the entire research pipeline from raw data ingestion to final statistical and machine learning models, execute [`run_all.sh`](run_all.sh) or follow the sequential order below:

```bash
# Execute master end-to-end pipeline:
./run_all.sh
```

### Sequential Script Order
1. **Copernicus DEM Streaming & Topographic Metrics**:
   ```bash
   python3 COPERNICUS_DEM/download_dem.py
   ```
2. **PaleoClim & WorldClim Climate Metric Expansion**:
   ```bash
   python3 run_phase2_climate_expansion.py
   ```
3. **Phase 6 Spatial Econometric & Baseline Models**:
   ```bash
   python3 integration_v2/run_phase6.py
   ```
4. **Phase 9 Statistical Inference, Sensitivity, & Spatial Error Models (v3b)**:
   ```bash
   python3 integration_v3/run_phase9_statistics_v3b.py
   ```
5. **Machine Learning Baseline Evaluation (GBIF Layer)**:
   ```bash
   python3 ml/src/run_all.py --fast
   ```
6. **IUCN Machine Learning Pipeline (20° Spatial-Block CV & LOCO)**:
   ```bash
   python3 ml/src/run_iucn.py
   ```
7. **IUCN Interpretability, Grouped Importance, PDP, & Moran's I**:
   ```bash
   python3 ml/src/run_iucn_diagnostics.py
   ```
8. **Automated Verification Suites**:
   ```bash
   pytest tests/
   pytest ml/tests/
   ```

---

## Repository Structure

```text
├── AUDIT.md                        # Master audit of numerical concordances, stale text, and link paths
├── DATA_SOURCES.md                 # Bibliographic citations, rasterSp protocol, and licensing
├── FIGURES_AND_TABLES.md           # Master index of figures and tables across all project phases
├── METHODS_JUSTIFICATION.md        # Tabular justification (Choice | Why | Alternative | Limitation)
├── README.md                       # Synthesis overview, key findings, and pipeline documentation
├── requirements.txt                # Python package dependencies
├── run_all.sh                      # Master automated pipeline execution script
│
├── common/                         # Shared spatial coordinate helpers and raster aggregation
├── COPERNICUS_DEM/                 # Copernicus DEM GLO-90 tile streaming and zonal statistics
├── GBIF/                           # Cleaned primary occurrence records and rarefaction pipelines
├── PALEOCLIM/                      # CHELSA-downscaled paleoclimate surfaces and stability zonal stats
├── WORLDCLIM/                      # CCSM4 paleoclimate surfaces and stability zonal stats
├── IUCN/                           # rasterSp 0.5° ingestion and cell-level richness/endemism tables
│
├── integration_v2/                 # Phase 6 spatial econometric regressions (OLS, ML_Error, ML_Lag)
├── integration_v3/                 # Phase 9 synthesis, velocity sensitivity, and block bootstrap models
│
├── ml/                             # Machine learning verification layer
│   ├── config.yaml                 # ML experimental configurations and spatial block parameters
│   ├── REPORT_ML.md                # ML v1 report (GBIF baseline evaluation)
│   ├── REPORT_ML_v2.md             # ML v2 report (IUCN vertebrate models, PDP, SHAP, and LOCO)
│   ├── src/                        # Core ML algorithms (data, models, cv, metrics, interpret)
│   ├── tests/                      # Pytest verification suites (spatial block leakage, benchmarks)
│   └── outputs/                    # Cross-validation outputs, metrics, and figures
│
└── tests/                          # Regression benchmark tests for baseline reproducibility
```

---

## Required Raw Files

The pipeline operates on the following raw archives or falls back to pre-computed verified tables:
1. **PaleoClim Rasters (`PALEOCLIM/raw/`)**: CHELSA downscaled 2.5' GeoTIFFs across Present, Late Holocene, and LGM.
2. **WorldClim Rasters (`WORLDCLIM/raw/`)**: CCSM4 2.5' grids across Present, Mid-Holocene, and LGM.
3. **GBIF Occurrences (`GBIF/raw/`)**: Continental raw occurrence archives (`gbif_all_continents.csv`).
4. **Copernicus DEM (`COPERNICUS_DEM/raw/tiles/`)**: Streamed directly from AWS public bucket `s3://copernicus-dem-90m/`.
5. **IUCN Data (`IUCN/processed/`)**: Global 0.5° `rasterSp` pre-aggregated rasters.

---

## Setup & Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run complete research pipeline and test suites
./run_all.sh
```
