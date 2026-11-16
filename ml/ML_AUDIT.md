# STAGE 1: Codebase & Data Audit for Machine Learning Extension

**Project**: Palaeoclimate Stability and Modern Biodiversity (EST Course Project, Problem 24)  
**Scientific Question**: *"Does palaeoclimate stability improve prediction of species richness beyond what sampling effort, latitude and topography already explain, and in what functional shape?"*  
**Date**: November 16, 2026  
**Auditor**: ML Layer Assistant  

---

## A. Final Cell-Level Analysis Tables

The existing statistical and spatial regression pipeline (`integration_v2/run_phase6.py`) operates on integrated grid tables located in `integration_v2/processed/`. Earlier benchmarks from the mid-evaluation were saved in `integration/figures/`.

### 1. `integration_v2/processed/data_5deg.csv` (Primary Analysis Grid: 5° Resolution)
- **File Path**: `integration_v2/processed/data_5deg.csv`
- **Row Count**: 375 rows (188 cells meet the sampling filter $n \ge 10$ records; 187 cells have $1 \le n < 10$)
- **Column Count**: 58 columns
- **Coordinate Extent**:
  - `cell_lat`: Minimum = $-52.5^\circ$, Maximum = $+72.5^\circ$
  - `cell_lon`: Minimum = $-157.5^\circ$, Maximum = $+177.5^\circ$
- **Grid Resolution**: $5.0^\circ \times 5.0^\circ$
  - Inferred from coordinate spacing: $\Delta \text{lat} = 5.0^\circ$ (unique values = 25), $\Delta \text{lon} = 5.0^\circ$ (unique values = 56).
- **Missing Values (NaNs)**: 0 missing values across all 58 columns.
- **Column Inventory & Data Types**:
  - `int64` (3 columns): `richness`, `n_records`, `pixel_count`
  - `object` / `str` (1 column): `spatial_block_20deg`
  - `float64` (54 columns):
    - Spatial & Sampling: `cell_lat`, `cell_lon`, `abs_lat`, `log_n`
    - DEM Elevation & Topography: `elevation_mean`, `elevation_sd`, `elevation_min`, `elevation_max`, `relief_range`, `topographic_heterogeneity`
    - Raster Coverage Fractions: `valid_fraction_x`, `valid_fraction_y`
    - PaleoClim Climatologies & Metrics (11 metrics + 6 baseline levels): `pc_temp_present`, `pc_temp_holocene`, `pc_temp_lgm`, `pc_precip_present`, `pc_precip_holocene`, `pc_precip_lgm`, `pc_bio4_present`, `pc_bio4_lgm`, `pc_bio15_present`, `pc_bio15_lgm`, `pc_temp_lgm_change`, `pc_temp_holo_change`, `pc_temp_instability`, `pc_precip_lgm_change_abs`, `pc_precip_lgm_change_rel`, `pc_precip_holo_change_abs`, `pc_precip_holo_change_rel`, `pc_precip_instability`, `pc_bio4_change`, `pc_bio15_change`, `pc_composite_instability`
    - WorldClim Climatologies & Metrics (11 metrics + 6 baseline levels): `wc_temp_present`, `wc_temp_holocene`, `wc_temp_lgm`, `wc_precip_present`, `wc_precip_holocene`, `wc_precip_lgm`, `wc_bio4_present`, `wc_bio4_lgm`, `wc_bio15_present`, `wc_bio15_lgm`, `wc_temp_lgm_change`, `wc_temp_holo_change`, `wc_temp_instability`, `wc_precip_lgm_change_abs`, `wc_precip_lgm_change_rel`, `wc_precip_holo_change_abs`, `wc_precip_holo_change_rel`, `wc_precip_instability`, `wc_bio4_change`, `wc_bio15_change`, `wc_composite_instability`

### 2. `integration_v2/processed/data_2deg.csv` (High-Resolution Comparison Grid: 2° Resolution)
- **File Path**: `integration_v2/processed/data_2deg.csv`
- **Row Count**: 894 rows (264 cells meet the sampling filter $n \ge 10$ records; 630 cells have $1 \le n < 10$)
- **Column Count**: 58 columns (identical column schema to `data_5deg.csv`)
- **Coordinate Extent**:
  - `cell_lat`: Minimum = $-53.0^\circ$, Maximum = $+71.0^\circ$
  - `cell_lon`: Minimum = $-165.0^\circ$, Maximum = $+177.0^\circ$
- **Grid Resolution**: $2.0^\circ \times 2.0^\circ$
  - Inferred from coordinate spacing: $\Delta \text{lat} = 2.0^\circ$ (unique values = 64), $\Delta \text{lon} = 2.0^\circ$ (unique values = 141).
- **Missing Values (NaNs)**: 0 missing values across all 58 columns.
- **Column Inventory & Data Types**: Identical to `data_5deg.csv`.

### 3. `integration/figures/table_integrated_cells.csv` (Phase 1 / Mid-Evaluation Benchmark Table)
- **File Path**: `integration/figures/table_integrated_cells.csv`
- **Row Count**: 188 rows (pre-filtered to $n \ge 10$)
- **Column Count**: 10 columns (`cell_lat`, `cell_lon`, `richness`, `n_records`, `pc_lgm_change`, `pc_instability`, `wc_lgm_change`, `wc_instability`, `abs_lat`, `log_n`)
- **Grid Resolution**: $5.0^\circ \times 5.0^\circ$
- **Missing Values (NaNs)**: 0 missing values.

### Summary of Existing Resolutions
The repository contains data at two standardized spatial resolutions:
1. **5-degree grid (`base`)**: $5^\circ \times 5^\circ$ cell centers (e.g., $-52.5^\circ, -47.5^\circ, \dots, +72.5^\circ$). Primary target for mid-eval comparability and global macroecological modeling.
2. **2-degree grid (`2deg`)**: $2^\circ \times 2^\circ$ cell centers (e.g., $-53.0^\circ, -51.0^\circ, \dots, +71.0^\circ$). High-resolution sensitivity layer re-extracted from raw point occurrences.

---

## B. Column Mapping and Metric Definitions

### 1. Standard Column Mapping
- **Cell Identifier**: No single integer column exists. The cell is uniquely identified by the coordinate pair `(cell_lat, cell_lon)`. For spatial cross-validation, the 20° block ID is stored in `spatial_block_20deg` (e.g., `"-20_-100"`, `"60_60"`).
- **Longitude**: `cell_lon` (degrees East, $[-180, 180]$).
- **Latitude**: `cell_lat` (degrees North, $[-90, 90]$).
- **Species Richness**: `richness` (count of distinct species recorded in the cell).
- **Sampling Effort**:
  - `n_records`: Raw occurrence record count from GBIF per cell.
  - `log_n`: Natural logarithm of raw occurrence count, $\ln(\text{n\_records})$.
- **Elevation**: `elevation_mean` (mean topographic elevation in meters above sea level derived from Copernicus DEM GLO-90). Also available: `elevation_sd`, `elevation_min`, `elevation_max`.
- **Topographic Relief**:
  - `relief_range`: Maximum elevation minus minimum elevation ($\text{elevation}_{\max} - \text{elevation}_{\min}$, meters) within the cell.
  - `topographic_heterogeneity`: Identical to `relief_range`.
- **Continent**: **Not present** in `data_5deg.csv` or `data_2deg.csv`.

---

### 2. Palaeoclimate Stability Metrics Definition
All palaeoclimate stability metrics were computed in `run_phase2_climate_expansion.py` (lines 109–135) and merged in `integration_v2/run_phase6.py`. The two climate sources are **PaleoClim** (prefix `pc_`) and **WorldClim** (prefix `wc_`).

| Metric Key | PaleoClim Column | WorldClim Column | Mathematical Definition & Source Code Implementation |
|---|---|---|---|
| **Composite Instability** | `pc_composite_instability` | `wc_composite_instability` | Equal-weighted composite index of normalized temperature instability and relative precipitation change: $\frac{z(\text{temp\_instability}) + z(\text{precip\_lgm\_change\_rel})}{2.0}$. |
| **Temperature LGM Anomaly** | `pc_temp_lgm_change` | `wc_temp_lgm_change` | Absolute change in Annual Mean Temperature (BIO1, °C) between Present and LGM (~21 ka BP): $\| T_{\text{present}} - T_{\text{LGM}} \|$. |
| **Temperature Holocene Anomaly** | `pc_temp_holo_change` | `wc_temp_holo_change` | Absolute change in Annual Mean Temperature (BIO1, °C) between Present and Holocene: $\| T_{\text{present}} - T_{\text{Holocene}} \|$. |
| **Temperature Instability (Temporal SD)** | `pc_temp_instability` | `wc_temp_instability` | Sample standard deviation of Annual Mean Temperature across the three Quaternary time slices: $\text{std}(T_{\text{present}}, T_{\text{Holocene}}, T_{\text{LGM}})$. |
| **Precipitation LGM Anomaly (Relative)** | `pc_precip_lgm_change_rel` | `wc_precip_lgm_change_rel` | Relative proportional change in Annual Precipitation (BIO12, mm) on log scale: $\| \ln(P_{\text{LGM}} + 1) - \ln(P_{\text{present}} + 1) \|$. |
| **Precipitation LGM Anomaly (Absolute)** | `pc_precip_lgm_change_abs` | `wc_precip_lgm_change_abs` | Absolute difference in Annual Precipitation (BIO12, mm): $\| P_{\text{present}} - P_{\text{LGM}} \|$. |
| **Precipitation Holocene Anomaly (Relative)**| `pc_precip_holo_change_rel`| `wc_precip_holo_change_rel`| Relative change in Annual Precipitation between Present and Holocene: $\| \ln(P_{\text{Holocene}} + 1) - \ln(P_{\text{present}} + 1) \|$. |
| **Precipitation Holocene Anomaly (Absolute)**| `pc_precip_holo_change_abs`| `wc_precip_holo_change_abs`| Absolute difference in Annual Precipitation between Present and Holocene: $\| P_{\text{present}} - P_{\text{Holocene}} \|$. |
| **Precipitation Instability (Temporal SD)** | `pc_precip_instability` | `wc_precip_instability` | Sample standard deviation of Annual Precipitation across the three time slices: $\text{std}(P_{\text{present}}, P_{\text{Holocene}}, P_{\text{LGM}})$. |
| **Temperature Seasonality Change** | `pc_bio4_change` | `wc_bio4_change` | Absolute change in Temperature Seasonality (BIO4, standard deviation $\times$ 100) between Present and LGM: $\| \text{BIO4}_{\text{present}} - \text{BIO4}_{\text{LGM}} \|$. |
| **Precipitation Seasonality Change** | `pc_bio15_change` | `wc_bio15_change` | Absolute change in Precipitation Seasonality (BIO15, coefficient of variation, %) between Present and LGM: $\| \text{BIO15}_{\text{present}} - \text{BIO15}_{\text{LGM}} \|$. |

---

## C. Existing Regression Methodology and Results

### 1. Transformations
- **Target Response**: $\ln(1 + \text{richness})$, implemented via `np.log1p(sub["richness"])` to eliminate heavy positive skewness and stabilize residual variance.
- **Effort Control**: Natural log of occurrence records, $\ln(\text{n\_records})$ (`log_n = np.log(df["n_records"])`).
- **Latitude Control**: Absolute latitude, $| \text{cell\_lat} |$ (`abs_lat = df["cell_lat"].abs()`).
- **Feature Normalization**: In regression modeling, all continuous predictors are standardized via z-score transformation: $x^* = (x - \bar{x}) / s_x$.

### 2. Sample Filters & Exclusions
- **Sampling Effort Threshold**: Minimum of 10 GBIF records per cell (`n_records >= 10`).
  - At 5° resolution: 375 merged land cells $\rightarrow$ 188 cells retained (187 cells excluded).
  - At 2° resolution: 894 merged land cells $\rightarrow$ 264 cells retained (630 cells excluded).
- **Land Mask**: Ocean cells are filtered out at the zonal raster stage via GeoTIFF nodata masking. Only terrestrial cells with valid DEM and climate pixel intersections are retained during `inner` merging.

### 3. Spatial Cross-Validation Design
- **Spatial Block Partitioning**:
  ```python
  block_lat = np.floor(df["cell_lat"] / 20.0) * 20.0
  block_lon = np.floor(df["cell_lon"] / 20.0) * 20.0
  df["spatial_block_20deg"] = (
      block_lat.astype(int).astype(str)
      + "_"
      + block_lon.astype(int).astype(str)
  )
  ```
  - Offset: 0.0° anchor (floor division by 20° bins: $[-20^\circ, 0^\circ)$, $[0^\circ, 20^\circ)$, etc.).
- **Cross-Validation Splitter**: `GroupKFold(n_splits=5)` grouped strictly by `spatial_block_20deg`.
  - Ensures that all grid cells falling into the same $20^\circ \times 20^\circ$ contiguous geographic block are assigned exclusively to either the training set or the test set in each outer fold.

### 4. 2-Degree Grid Richness Construction
- **Verification Evidence**: In `integration_v2/run_phase6.py` (lines 58–64):
  ```python
  pts = pd.read_csv(
      os.path.join(REPO_ROOT, "GBIF", "processed", "gbif_points_clean.csv")
  )
  pts2 = add_cell(pts, cell=2)
  gb2 = (
      pts2.groupby(["cell_lat", "cell_lon"])
      .agg(richness=("species", "nunique"), n_records=("species", "count"))
      .reset_index()
  )
  ```
- **Confirmation**: Species richness at 2 degrees was **recomputed from raw occurrence points** as the number of unique species (`nunique`) within each 2° cell, and effort was recomputed as the record count (`count`). It was **NOT** spatially averaged or interpolated from 5-degree or finer grid cells.

### 5. Existing Model Comparisons
The existing study implemented the following model progression:
- **Baseline Non-parametric**: Bivariate Spearman rank correlations ($\rho$).
- **Partial Spearman Model A**: Controlling for sampling effort ($\ln(\text{n\_records})$) and absolute latitude ($| \text{cell\_lat} |$).
- **Partial Spearman Model B**: Controlling for sampling effort, latitude, mean elevation (`elevation_mean`), and topographic relief (`topographic_heterogeneity`).
- **Spatial Block Bootstrap**: 300-iteration cluster bootstrap resampling 20° spatial blocks with replacement to generate 95% confidence intervals for partial $\rho$.
- **Spatial Autoregressive Models**:
  - Maximum Likelihood Spatial Error Model (`ML_Error`) using $k=8$ nearest neighbor spatial weights ($W$).
  - Maximum Likelihood Spatial Lag Model (`ML_Lag`) using $k=8$ spatial weights ($W$).
- **5-Fold Spatial-Block CV**: Out-of-sample prediction comparing OLS with controls only vs. OLS with controls plus composite climate instability.

---

## D. Reproduction of Headline Regression Number

We reproduced the exact 5-fold 20-degree spatial-block cross-validation reported in `integration_v2/results.md` and `integration_v2/figures/table_spatial_cv.csv` on `integration_v2/processed/data_5deg.csv` ($n = 188$ cells with $\text{n\_records} \ge 10$):

- **Target**: $\ln(1 + \text{richness})$
- **Controls**: `log_n`, `abs_lat`, `elevation_mean`, `topographic_heterogeneity` (all standardized)
- **Predictor**: `pc_composite_instability` (standardized)
- **Splitter**: `GroupKFold(n_splits=5)` on `spatial_block_20deg`

### Empirical Results Table

| Model Specification | Reported in `results.md` | Recomputed in Stage 1 Audit | Discrepancy |
|---|---|---|---|
| **OLS Full Model (with Stability)** | Out-of-sample $R^2 = 0.8493$<br>$\text{RMSE} = 0.3483$ | Out-of-sample $R^2 = 0.8493$<br>$\text{RMSE} = 0.3483$ | **0.0000** |
| **OLS Controls Only** | Out-of-sample $R^2 = 0.8414$<br>$\text{RMSE} = 0.3572$ | Out-of-sample $R^2 = 0.8414$<br>$\text{RMSE} = 0.3572$ | **0.0000** |
| **Incremental Contribution ($\Delta$)** | **$\Delta R^2 = +0.0079 \approx +0.008$**<br>$\Delta \text{RMSE} = -0.0089$ | **$\Delta R^2 = +0.0079$**<br>$\Delta \text{RMSE} = -0.0089$ | **0.0000** |

**Finding**: The headline result reproduced exactly with 0.0000 discrepancy. Palaeoclimate stability contributes only $+0.0079$ ($< 0.8\%$) to out-of-sample $R^2$ beyond sampling effort, latitude, and topography.

---

## E. Availability of Relief, Continent, and Effort

An audit of `integration_v2/processed/data_5deg.csv` and `data_2deg.csv` indicates:

1. **Relief**: **AVAILABLE**.
   - Available in both tables as `relief_range` and `topographic_heterogeneity` (both represent $\text{elevation}_{\max} - \text{elevation}_{\min}$ in meters from Copernicus DEM GLO-90).
2. **Effort**: **AVAILABLE**.
   - Available in both tables as `n_records` (raw GBIF occurrence counts) and `log_n` ($\ln(\text{n\_records})$).
3. **Continent**: **NOT AVAILABLE**.
   - The processed files `data_5deg.csv` and `data_2deg.csv` do not contain a continent column.
   - *Source for derivation*: Can be derived by mapping cell coordinates to the regional GBIF raw files in `GBIF/raw/` (`gbif_africa_5000.csv`, `gbif_asia_5000.csv`, `gbif_europe_5000.csv`, `gbif_north_america_1000.csv`, `gbif_south_america_1000.csv`, `gbif_oceania_1000.csv`) or via spatial polygon join. As instructed, it has not been derived yet.


---

## F. Binding Overrides & Small-Sample Methodological Framework

Following user confirmation and guidance, the following binding specifications are codified across `ml/config.yaml` and all downstream ML modules:

### 1. Data Filtering & Sample Size
- **Analysis Filter**: `n_records >= 10` applied strictly to all models across all feature tiers.
  - Primary grid (`base`, 5° resolution): **188 cells**.
  - High-resolution grid (`2deg`, 2° resolution): **264 cells**.
  - Every pipeline execution logs and programmatically verifies these exact cell counts.

### 2. Feature Sets Architecture
- **Controls & Latitude**:
  - Sampling effort feature: `log_n` ($\ln(\text{n\_records})$).
  - Latitude features: `cell_lat` (raw signed latitude) and `abs_lat` ($| \text{cell\_lat} |$).
  - Topographic features: `elevation_mean` and `topographic_heterogeneity` (`relief_range`).
  - **Rule**: `cell_lon` is strictly excluded as a direct regression predictor to prevent longitude memorization.
- **Model Tiers**:
  - **M0**: Sampling effort only (`log_n`).
  - **M1**: Controls only (`log_n`, `cell_lat`, `abs_lat`, `elevation_mean`, `topographic_heterogeneity`).
  - **M2a (Primary Response)**: M1 + single composite instability (`pc_composite_instability` / `wc_composite_instability`).
  - **M2b (Full Detail)**: M1 + all 11 palaeoclimate stability metrics. *(Note: Extreme multicollinearity / high VIF is documented and logged as expected due to linear/non-linear dependencies on composite components).*
  - **M3a**: Single composite instability alone.
  - **M3b**: All 11 stability metrics alone.

### 3. Spatial Cross-Validation Protocol
- **Fast Mode (`--fast`)**: Never subsamples cells. Configured with 1 repeat, 3 outer folds, 100 trees, and compact tuning grids.
- **Full Mode**: Evaluates 5 systematic spatial-block coordinate shifts across offsets $[0^\circ, 4^\circ, 7^\circ, 11^\circ, 13^\circ]$.
  - **Offset 0 Anchor**: Reuses the exact floor-division formula from `integration_v2/run_phase6.py` and programmatically asserts reproduction of baseline OLS $R^2$ ($0.8414$ for M1, $0.8493$ for M2a, $\Delta R^2 = +0.0079$) within 0.002 tolerance.
  - **Occupied Block Logging**: Each run records the number of occupied 20° spatial blocks and cell distributions per block.
- **Leave-One-Continent-Out (LOCO)**: Threshold set to `min_cells_per_continent = 15` (adjusted for sample sizes of 188 and 264 cells). Skipped continents are explicitly logged.
- **Spatial Autocorrelation**: Moran's $I$ uses $k=5$ nearest neighbors (haversine) at 5° and $k=8$ at 2°.

### 4. Resolution of Continent Classification
- Deterministic, rule-based classifier implemented in `ml/src/continent_rules.py` without requiring external shapefile downloads.
- Island territories deliberately assigned:
  - Canary Islands $\rightarrow$ Africa
  - Madagascar $\rightarrow$ Africa
  - Taiwan $\rightarrow$ Asia
  - Hawaii $\rightarrow$ Oceania
- Generated reference files:
  - `tables/continent_assignment.csv`: Comprehensive mapping for all 452 filtered cell entries (188 at 5°, 264 at 2°).
  - `tables/continent_boundary_cells.csv`: 34 cells located within 5° of continental transition lines for explicit manual audit.

### 5. Python Environment & Dependency Status
- **Active Interpreter**: `/home/mokshitha/notebook_env/bin/python3` (Python 3.12.3)
- **Import Verification**:
  - `scikit-learn`: Verified (v1.6.1)
  - `statsmodels`: Verified (v0.14.4)
  - `scipy`: Verified (v1.15.2)
  - `matplotlib`: Verified (v3.10.0)
  - `numpy`: Verified (v2.2.3)
  - `pandas`: Verified (v2.2.3)
  - `joblib`: Verified (v1.4.2)
  - `esda`, `libpysal`, `geopandas`, `pyarrow`: Verified
- **Missing Dependency**:
  - `pyyaml`: **NOT installed** in `notebook_env`. Flagged to user before attempting any pip installation. A zero-dependency pure-Python YAML parser fallback is implemented to ensure continuous execution without crashing.
