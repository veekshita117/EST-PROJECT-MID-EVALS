# Repository Audit: Palaeoclimate Stability and Modern Biodiversity

## 1. Overview and Workflow Pipeline

The repository tests whether modern species richness is associated with long-term Quaternary climatic stability at a global scale. The analysis pipeline runs in four stages:

1. **GBIF (`GBIF/gbif.ipynb`)**: Cleans occurrence records, bins points into 5° x 5° grid cells, and calculates species richness (unique `speciesKey` count) and sampling effort (`n_records`).
2. **PaleoClim (`PALEOCLIM/paleoclim.ipynb`)**: Samples mean annual temperature (BIO1) across Present, Late Holocene (~4.2–0.3 ka), and Last Glacial Maximum (LGM, ~21 ka) at GBIF record coordinates, averaging stability metrics per 5° cell.
3. **WorldClim (`WORLDCLIM/worldclim.ipynb`)**: Samples BIO1 across Present, Mid-Holocene (~6 ka, CCSM4), and LGM (~21 ka, CCSM4) at GBIF coordinates, averaging stability metrics per 5° cell.
4. **Integration (`integration/integration.ipynb`)**: Merges cell tables on `(cell_lat, cell_lon)`, filters to cells with $\ge 10$ GBIF records ($n=188$), and computes Spearman and partial Spearman correlations controlling for $\log(\text{n\_records})$ and $|\text{cell\_lat}|$.

---

## 2. Step-by-Step Audit

### `common/helpers.py`
- **`load_gbif(path)`**: Parses CSV using Python engine, standardizes coordinate column names to `lat`/`lon`, filters to valid coordinates $[-90, 90] \times [-180, 180]$, drops $(0, 0)$ and null coordinates/species.
- **`add_cell(df, cell=CELL)`**: Computes cell center coordinates using $\lfloor \text{coord} / \text{cell} \rfloor \times \text{cell} + \text{cell}/2$.
- **`find_bio1(folder)`**: Regex scanner for BIO1 GeoTIFF rasters.
- **`sample_at(path, lons, lats, scale=None, nodata_threshold=1e4)`**: Samples raster values at point coordinates using `rasterio.sample`. Applies nodata replacement and conditional temperature scaling.
- **`cell_zonal_stats(raster_path, cell=CELL, stats=..., scale=None)`**: Computes raster zonal statistics over all valid pixels within each grid cell and calculates `valid_fraction` per cell.
- **`global_grid(path, step=2, **kwargs)`**: Evaluates raster on a 2° display grid for global visualization.
- **`plot_map(arr, title, label, out, cmap)`**: Visualizes global 2D grids and exports figures.
- **`cell_climate(paths, pts, prefix, **kwargs)`**: Samples rasters at GBIF point coordinates, computes $| \text{present} - \text{lgm} |$, $| \text{present} - \text{holocene} |$, and standard deviation across periods, then averages by cell.
- **`partial_spearman(df, x, y, covs)`**: Computes partial Spearman rank correlation by projecting ranked covariates out via OLS residuals and calculating Spearman correlation of residual ranks.

### `GBIF/`
- **Notebook**: `GBIF/gbif.ipynb`
- **Method**: Cleans 18,000 raw sampled records to 17,396 clean records across 6,080 unique species in 375 5° cells.
- **Outputs**:
  - `GBIF/processed/gbif_points_clean.csv`
  - `GBIF/processed/gbif_richness_cells.csv`
  - `GBIF/processed/gbif_summary.csv`
  - `GBIF/processed/gbif_top10_cells.csv`
  - Figures: `gbif_records_map.png`, `gbif_richness_map.png`, `gbif_richness_latitude.png`, `gbif_records_per_cell.png`.

### `PALEOCLIM/`
- **Notebook**: `PALEOCLIM/paleoclim.ipynb`
- **Method**: Evaluates BIO1 across Present, Late Holocene, and LGM. Generates 2° display grids and computes 5° cell averages from sampled points (375 cells).
- **Outputs**:
  - `PALEOCLIM/processed/pc_lgm_change_2deg.npy`
  - `PALEOCLIM/processed/pc_summary.csv`
  - `PALEOCLIM/processed/paleoclim_cell_stability.csv`
  - `PALEOCLIM/processed/pc_cell_stats.csv`
  - Figures: `pc_bio1_present.png`, `pc_bio1_holocene.png`, `pc_bio1_lgm.png`, `pc_lgm_change.png`, `pc_change_hist.png`.

### `WORLDCLIM/`
- **Notebook**: `WORLDCLIM/worldclim.ipynb`
- **Method**: Extracts raw zip archives (`cclgmbi_10m.zip`, `ccmidbi_10m.zip`, `bio_10m_esri.zip`), identifies BIO1 rasters, generates 2° display grids, and computes 5° cell averages (374 cells; one cell lacking coverage).
- **Outputs**:
  - `WORLDCLIM/processed/wc_lgm_change_2deg.npy`
  - `WORLDCLIM/processed/wc_summary.csv`
  - `WORLDCLIM/processed/worldclim_cell_stability.csv`
  - `WORLDCLIM/processed/wc_cell_stats.csv`
  - Figures: `wc_bio1_present.png`, `wc_bio1_holocene.png`, `wc_bio1_lgm.png`, `wc_lgm_change.png`, `wc_change_hist.png`.

### `integration/`
- **Notebook**: `integration/integration.ipynb`
- **Method**: Merges `gbif_richness_cells.csv`, `paleoclim_cell_stability.csv`, and `worldclim_cell_stability.csv` (374 shared cells). Restricts to $n \ge 10$ records ($n=188$). Computes raw and partial Spearman correlations, stability quartiles, dataset agreement, and hotspot classification.
- **Outputs**:
  - `integration/figures/table_correlations.csv`
  - `integration/figures/table_quartiles.csv`
  - `integration/figures/table_integrated_cells.csv`
  - Figures: `int_scatter.png`, `int_quartiles.png`, `int_dataset_agreement.png`, `int_hotspots.png`.
  - Summary: `integration/results.md`.

---

## 3. Raw Files Audit

| Folder | File Name | Format | Status on Disk | Expected Source / Purpose |
|---|---|---|---|---|
| `GBIF/raw/` | `gbif_all_continents.csv` | CSV | Present (1.5 MB) | Combined occurrence sample across continents |
| `GBIF/raw/` | `gbif_africa_5000.csv` | CSV | Present (442 KB) | Sampled African records (cap: 5,000) |
| `GBIF/raw/` | `gbif_asia_5000.csv` | CSV | Present (435 KB) | Sampled Asian records (cap: 5,000) |
| `GBIF/raw/` | `gbif_europe_5000.csv` | CSV | Present (420 KB) | Sampled European records (cap: 5,000) |
| `GBIF/raw/` | `gbif_north_america_1000.csv` | CSV | Present (88 KB) | Sampled North American records (cap: 1,000) |
| `GBIF/raw/` | `gbif_south_america_1000.csv` | CSV | Present (89 KB) | Sampled South American records (cap: 1,000) |
| `GBIF/raw/` | `gbif_oceania_1000.csv` | CSV | Present (88 KB) | Sampled Oceania records (cap: 1,000) |
| `GBIF/raw/` | `GBIF_METADATA.md` | Markdown | Present (3.5 KB) | Download provenance and field descriptions |
| `PALEOCLIM/raw/` | `paleoclim_current_BIO1.tif` | GeoTIFF | Missing | CHELSA/PaleoClim BIO1 baseline raster |
| `PALEOCLIM/raw/` | `paleoclim_late_holocene_BIO1_aligned.tif` | GeoTIFF | Missing | CHELSA/PaleoClim Late Holocene BIO1 raster |
| `PALEOCLIM/raw/` | `paleoclim_LGM_BIO1_aligned.tif` | GeoTIFF | Missing | CHELSA/PaleoClim LGM BIO1 raster |
| `WORLDCLIM/raw/` | `bio_10m_esri.zip` | ZIP | Missing | WorldClim v1.4 present climate ESRI grid |
| `WORLDCLIM/raw/` | `ccmidbi_10m.zip` | ZIP | Missing | WorldClim v1.4 Mid-Holocene CCSM4 raster |
| `WORLDCLIM/raw/` | `cclgmbi_10m.zip` | ZIP | Missing | WorldClim v1.4 LGM CCSM4 raster |

*Note: Raw climate rasters were excluded from version control. Precomputed processed tables (`PALEOCLIM/processed/` and `WORLDCLIM/processed/`) are preserved, allowing full reproduction of integration tests.*

---

## 4. Bugs, Risks, and Methodological Limitations

1. **Auto-rescaling heuristic in `sample_at()` (Bug - Addressed in Phase 1)**:
   - *Issue*: `sample_at()` checked `if np.nanmax(np.abs(v)) > 100: v = v / 10`. This was tailored specifically for temperature rasters stored in tenths of a degree Celsius (°C*10), but causes silent data corruption on precipitation (BIO12, mm), elevation (DEM, m), and other variables.
   - *Resolution*: Parameterized with `scale=None` (preserving legacy behavior) and `scale=1` (raw unscaled values).

2. **Hardcoded nodata threshold at `1e4` (Bug / Risk - Addressed in Phase 1)**:
   - *Issue*: `v[np.abs(v) > 1e4] = np.nan` discards valid annual precipitation values above 10,000 mm (e.g. wet tropical and monsoon zones).
   - *Resolution*: Parameterized with `nodata_threshold` defaulting to `1e4` for legacy compatibility, permitting `None` or higher thresholds for precipitation.

3. **Point-sampling climate instead of true zonal cell statistics (Methodological Risk - Addressed in Phase 1)**:
   - *Issue*: `cell_climate()` averaged climate values only across coordinates where GBIF records occurred. If records within a cell are clustered along roads, coasts, or lowland valleys, the estimated cell climate reflects collection bias rather than the true regional climate.
   - *Resolution*: Added `cell_zonal_stats()` to compute area-wide statistics and land surface fractions (`valid_fraction`) across all raster pixels within each cell.

4. **Severe GBIF sampling bias and artificial continental caps (Methodological Risk)**:
   - *Issue*: Raw GBIF files apply arbitrary caps (1,000 records for South America, North America, Oceania vs 5,000 for Africa, Asia, Europe). South Africa accounts for 6 of the top 10 richest cells due to intense local sampling effort.
   - *Impact*: Raw observed richness is heavily confounded by sampling effort ($\text{records per cell}$). While partial correlation controls for $\log(\text{n\_records})$, spatial coverage remains non-uniform.

5. **Modifiable Areal Unit Problem (MAUP) at 5° resolution (Methodological Risk)**:
   - *Issue*: A 5° grid cell spans approximately 550 km $\times$ 550 km at the equator. This coarse scale averages out topographic microrefugia (e.g. mountainous valleys) that preserve species during glacial epochs.

6. **Temporal and GCM Asymmetry between Datasets (Methodological Risk)**:
   - *Issue*: PaleoClim uses Late Holocene (~4.2–0.3 ka), while WorldClim uses Mid-Holocene (~6 ka). WorldClim relies on a single GCM (CCSM4), confounding paleoclimate signal with model-specific simulation bias.

7. **Spatial Autocorrelation in Statistical Inference (Methodological Risk)**:
   - *Issue*: Ordinary Spearman and partial Spearman p-values assume independent spatial observations. Strong spatial autocorrelation among neighboring grid cells inflates effective sample size and deflates p-values. Spatial regression (e.g. spatial error or spatial lag models via `spreg`/`libpysal`) is required to confirm robustness.
