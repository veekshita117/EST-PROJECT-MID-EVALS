# Comprehensive Repository Audit: Palaeoclimate Stability and Modern Biodiversity

**Scope**: Verification of `README.md`, `DATA_SOURCES.md`, `FIGURES_AND_TABLES.md`, `integration_v2/results.md`, `integration_v3/results.md`, `ml/REPORT_ML.md`, and all cited CSV tables.  
**Execution Standard**: Reproducible, explainable, and justified. Numbers read strictly from disk artifacts. Raw climate rasters excluded from version control are noted; verified processed tables are used throughout.

---

## (a) Numbers in Markdown Files That Do Not Match Their CSVs

### 1. `integration_v3/results.md` (Table 2: Bivariate & Partial Correlations)
- **GBIF Rarefied ($n=20$) at 5° scale**:
  - *Markdown text*: `Cells ($n$) = 755`
  - *Underlying CSV (`integration_v3/tables/correlations_5deg.csv`, row 42)*: `n_cells = 683` (`n_blocks = 86`).
  - *What*: Discrepancy of 72 cells.
  - *Why*: Markdown inadvertently inherited the total 5° land cell count ($n=755$) from the IUCN vertebrate rows. Sample-standardized rarefaction ($n=20$) requires at least 20 occurrence records; exactly 683 cells satisfy this criterion in `integration_v3/processed/data_v3_5deg.csv`.
  - *Limitation*: Excludes cells with 1–19 records from the rarefied GBIF sensitivity check.
  - *Action*: Fixed in place in `integration_v3/results.md` (CSV is clearly right).
- **GBIF Rarefied ($n=20$) at 2° scale**:
  - *Markdown text*: `Cells ($n$) = 4,397`
  - *Underlying CSV (`integration_v3/tables/correlations_2deg.csv`, row 42)*: `n_cells = 3080` (`n_blocks = 91`).
  - *What*: Discrepancy of 1,317 cells.
  - *Why*: Markdown copied the 2° total land cell count ($n=4,397$) from IUCN rows. Exactly 3,080 cells possess $\ge 20$ records in `integration_v3/processed/data_v3_2deg.csv`.
  - *Limitation*: Restricts 2° GBIF rarefaction to adequately sampled regions.
  - *Action*: Fixed in place in `integration_v3/results.md` (CSV is clearly right).
- **IUCN Metrics at 2° scale (Total Richness, Endemism, Small-Range $Q_{25}$)**:
  - *Markdown text*: `Cells ($n$) = 4,397`
  - *Underlying CSV (`integration_v3/tables/correlations_2deg.csv`, rows 0, 6, 12)*: `n_cells = 4395` (`n_blocks = 93`).
  - *What*: Discrepancy of 2 cells.
  - *Why*: While `data_v3_2deg.csv` contains 4,397 total cells, 2 cells lack valid precipitation seasonality data (`pc_bio15_present` is NaN), leaving 4,395 complete cases across the 8-control design matrix.
  - *Limitation*: Negligible loss of 2 island/coastal cells.
  - *Action*: Fixed in place in `integration_v3/results.md` (CSV is clearly right).
- **Spatial Block Partitioning Counts (Section 2 Narrative)**:
  - *Markdown text*: `n = 755 cells across 47 blocks at 5°; n = 4,397 cells across 237 blocks at 2°`
  - *Underlying CSVs*: `correlations_5deg.csv` reports `n_blocks = 88` (86 for GBIF); `correlations_2deg.csv` reports `n_blocks = 93` (91 for GBIF).
  - *What*: Block count mismatch (47 vs 88 at 5°; 237 vs 93 at 2°).
  - *Why*: Narrative cited an exploratory or unaggregated blocking scheme rather than the final 20° GroupKFold block allocation.
  - *Limitation*: Narrative reporting divergence only; bootstrap confidence intervals and FDR $q$-values in the CSV remain mathematically valid.
  - *Action*: Listed in audit; narrative modification deferred.

### 2. `README.md` (Main Results, Line 55)
- *Markdown text*: "When controlling for sampling effort and latitude in non-spatial models, composite instability appears negatively correlated with species richness (partial $\rho = -0.284, p = 8.1 \times 10^{-5}$ for PaleoClim; partial $\rho = -0.203, p = 0.0053$ for WorldClim)."
- *Underlying CSV (`integration_v2/figures/table_correlations_v2.csv`, rows 0 and 7)*:
  - Two controls (`log_n`, `abs_lat`): PaleoClim $\rho = -0.2583$ ($p = 0.000346$); WorldClim $\rho = -0.1985$ ($p = 0.006311$).
  - Four controls (`log_n`, `abs_lat`, `elevation_mean`, `topographic_heterogeneity`): PaleoClim $\rho = -0.2835$ ($p = 0.000081$); WorldClim $\rho = -0.2025$ ($p = 0.005331$).
- *What*: The text describes 2 controls, but quotes the numerical coefficients from the 4-control model.
- *Why*: Editorial conflation between mid-eval baseline controls and full econometric controls during synthesis.
- *Limitation*: Both models show statistically significant negative partial correlations ($p < 0.01$).
- *Action*: Listed in audit; narrative modification deferred.

### 3. `FIGURES_AND_TABLES.md` (PaleoClim Stability Table Entry, Line 68)
- *Markdown text*: `Baseline point-sampled temperature stability table across 369 GBIF cells.`
- *Underlying CSV (`PALEOCLIM/processed/paleoclim_cell_stability.csv`)*: Exactly 375 rows (cells).
- *What*: Cell count mismatch (369 vs 375).
- *Why*: 369 is the cell count of `paleoclim_point_sampled_v2.csv` (which required valid data across all 4 expanded BIO variables); `paleoclim_cell_stability.csv` covers all 375 baseline cells.
- *Limitation*: None.
- *Action*: Fixed in place in `FIGURES_AND_TABLES.md` (CSV is clearly right).

### 4. `ml/REPORT_ML.md` (Cross-Validation Performance and LOCO Metrics)
- **Table 3.1: Pooled $\Delta R^2$ and Fold Statistics**:
  - *Report Table 3.1*: `ols_reference` (+0.0079, fold mean +0.0042, SD 0.0113); `ridge` (-0.0042, fold mean -0.0007, SD 0.0091); `rf` (+0.0388, fold mean +0.0228, SD 0.0251); `hgb` (-0.0008, fold mean +0.0028, SD 0.0183).
  - *`ml/outputs/paleoclim_base/tables/delta_r2.csv`*: `ols_reference` (+0.0079, fold mean +0.0107, SD 0.0152); `ridge` (+0.0068, fold mean +0.0092, SD 0.0147); `rf` (+0.0180, fold mean +0.0307, SD 0.0364); `hgb` (+0.0222, fold mean +0.0115, SD 0.0335).
  - *`ml/outputs/COMPARISON/comparison_table.csv`*: Matches `REPORT_ML.md` pooled values exactly (`ols`: +0.0079, `ridge`: -0.0042, `rf`: +0.0388, `hgb`: -0.0008).
  - *What*: Disagreement between the local `paleoclim_base/tables/delta_r2.csv` and the compiled `comparison_table.csv`.
  - *Why*: Multiple stages of `run_core_cv.py` produced updated local tables, whereas `compare_configs.py` and `REPORT_ML.md` captured an earlier verified run.
  - *Limitation*: Both runs support the primary conclusion: out-of-fold linear predictive contribution of Quaternary stability is negligible ($\Delta R^2 \le 0.008$).
  - *Action*: Listed in audit; neither CSV is singularly right without re-executing `run_all.py`.
- **Table 3.2: LOCO Generalisation Metrics**:
  - *Report Table 3.2*: Quotes $R^2(M1)$ values matching `worldclim_base/tables/loco_metrics.csv` (e.g., Africa OLS 0.894, Asia OLS 0.854) while presenting PaleoClim figure captions, and reports $R^2(M2a)$ values differing from both base tables.
  - *What*: Hybridization of PaleoClim and WorldClim metrics across continental blocks.
  - *Why*: Scripted report compilation parsed unpinned cross-configuration variables.
  - *Limitation*: Rank preservation holds across all continents ($\rho \ge 0.89$) in both sources.
  - *Action*: Listed in audit.

---

## (b) Stale Statements

1. **`README.md` (Line 13)**:
   - *Statement*: `IUCN Red List Spatial Data (Not Yet Used): Terrestrial range map ingestion pipeline specified in integration_v2/PLAN.md (raw shapefiles were not placed in IUCN/raw/).`
   - *Why Stale*: Phase 9 fully ingested and rasterized IUCN vertebrate range maps via `IUCN/process_iucn.py`, generating `IUCN/processed/iucn_cells_5deg.csv` ($n=755$) and `iucn_cells_2deg.csv` ($n=4,397$), which form the core response variables for `integration_v3/results.md`.
2. **`DATA_SOURCES.md` (Section 5, Lines 73-77)**:
   - *Statement*: `Status: Not yet used. Raw shapefile downloads were not placed in IUCN/raw/; the integration models rely solely on GBIF observed richness.`
   - *Why Stale*: Same as above; IUCN expert range maps for Amphibia, Mammalia, and Reptilia are processed and actively used.
3. **`README.md` (Repository Structure, Lines 84-135)**:
   - *Why Stale*: Directory tree terminates at Phase 6 (`integration_v2/`), completely omitting `IUCN/`, `integration_v3/`, and `ml/` modules.
4. **`README.md` (Run Order, Lines 187-212)**:
   - *Why Stale*: Execution workflow terminates at step 4 (`run_phase6.py` and `test_reproduce_mid_eval.py`), omitting `IUCN/process_iucn.py`, `integration_v3/run_phase9_statistics.py`, and `ml/src/run_all.py`.
5. **`integration/results.md` (Lines 61-65, "Next steps (remaining 40%)")**:
   - *Statement*: Proposes adding precipitation, IUCN range maps, DEM elevation, rarefied richness, and taxonomic breakdowns.
   - *Why Stale*: These were mid-eval roadmap items; all four tasks have been completed in Phases 6 through 9.
6. **Previous `AUDIT.md`**:
   - *Why Stale*: Addressed only the mid-evaluation baseline (GBIF and BIO1 across 188 cells), omitting all subsequent phases.

---

## (c) Absolute Paths (like `/home/mokshitha`)

All occurrences have been audited and corrected in place:
1. **`integration_v3/results.md`**: 13 instances of `file:///home/mokshitha/EST-PROJECT-MID-EVALS/integration_v3/...` were present in links to `PLAN.md`, figures, and tables.
   - *Status*: Replaced with portable relative markdown links (`PLAN.md`, `tables/*.csv`, `figures/*.png`).
2. **`ml/ML_AUDIT.md`**: 1 instance of `/home/mokshitha/notebook_env/bin/python3`.
   - *Status*: Replaced with `python3`.
3. **`ml/README_ML.md`**: 1 instance of `/home/mokshitha/EST-PROJECT-MID-EVALS`.
   - *Status*: Replaced with `.`.
4. **`ml/outputs/logs/BLOCKERS.md`**: 12 instances of `/home/mokshitha/...` in logged stack traces.
   - *Status*: Sanitized to relative paths.

---

## (d) Tables and Figures Referenced but Missing

1. **Portable Resolution of `integration_v3/results.md` Links**:
   - Due to the absolute URI scheme `file:///home/mokshitha/...`, markdown renderers and external environments failed to locate target files.
   - *Resolution*: Converting links to relative paths confirmed that all 4 figures (`hotspot_spatial_null.png`, `quantile_slopes.png`, `interaction_surfaces.png`, `taxa_comparison.png`) and 8 tables (`reproduce_188_gbif.csv`, `correlations_5deg.csv`, `correlations_2deg.csv`, `hotspot_enrichment.csv`, `quantile_regression.csv`, `spatial_models.csv`, `interactions.csv`, `taxa_comparison.csv`) exist on disk.
2. **Missing Raw GeoTIFFs and Shapefiles**:
   - Raw climate rasters (`PALEOCLIM/raw/*.tif`, `WORLDCLIM/raw/*.tif`) and raw IUCN shapefile archives (`MAMMALS.zip`, `AMPHIBIANS.zip`, `REPTILES.zip`) are absent from disk due to storage and version-control exclusion.
   - *Resolution*: The pipeline preserves precomputed analytical tables (`PALEOCLIM/processed/`, `WORLDCLIM/processed/`, `COPERNICUS_DEM/processed/`, `IUCN/processed/`), enabling complete reproduction of statistical regressions, spatial models, and ML evaluations.
3. **Missing Entries in `FIGURES_AND_TABLES.md`**:
   - `FIGURES_AND_TABLES.md` lacked entries for phases 7 through 10.
   - *Resolution*: Updated in place with complete inventories for `IUCN/` (4 figures, 2 tables), `integration_v3/` (4 figures, 11 tables), and `ml/` (16 figures, 9 tables). All 112 links programmatically verified to exist on disk.
4. **Typo in `FIGURES_AND_TABLES.md` Line 68**:
   - Corrected cell count description from 369 to 375 for `paleoclim_cell_stability.csv`.

---

## Methodological Summary & Limitations
- **Verification Rule**: Precomputed analytical outputs (`processed/` and `tables/`) are verified on disk. Raw files missing due to bandwidth or licensing restrictions are documented without compromising downstream reproducibility.
- **Scope Boundary**: Narrative interpretations across reports are left intact per protocol; all factual discrepancies are recorded above.
