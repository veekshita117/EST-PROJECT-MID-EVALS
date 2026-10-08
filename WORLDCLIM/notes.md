# WorldClim notes (5° grid)

## Data
- Variable: BIO1 (mean annual temperature), 10 arc-min resolution.
- Present: bio_10m_esri (raw/present/bio/bio_1, ESRI grid).
- Mid-Holocene: ccmidbi1.tif (from ccmidbi_10m.zip, CCSM4 simulation).
- LGM: cclgmbi1.tif (from cclgmbi_10m.zip, CCSM4 simulation).
- Values auto-scaled from °C*10 to °C.

## Sanity check (global values, °C)
| Period | Min | Max | Mean |
|---|---|---|---|
| Present | -23.70 | 30.80 | 8.15 |
| Mid-Holocene | -24.50 | 29.70 | 7.09 |
| LGM | -37.10 | 30.60 | -2.03 |
- Values are realistic and ordered correctly: LGM is the coldest, mid-Holocene is slightly cooler than present.
- These statistics come from a 2° display grid used only for the global maps. They do not depend on the 5° analysis grid.
- Antarctica is not covered in these rasters, so the means are higher than in PaleoClim and the two are not directly comparable.
- Means are plain grid averages, not area-weighted, so do not quote them as true global means.

## Method
- Same stability metrics and same 5° cells as GBIF and PaleoClim:
  - lgm_change = |Present - LGM|
  - holo_change = |Present - Mid-Holocene|
  - instability = SD of BIO1 across the 3 time slices
- Lower values mean more stable climate.
- Values are sampled at GBIF record locations (17,396 points) and averaged per 5° x 5° cell, giving 374 cells with climate values (PaleoClim: 375; one cell has no WorldClim value).

## Climate at the GBIF cells (°C)
| Variable | Min | Median | Mean | Max |
|---|---|---|---|---|
| Present BIO1 | -6.8 | 18.7 | 17.1 | 28.5 |
| Mid-Holocene BIO1 | -8.5 | 17.9 | 16.3 | 27.4 |
| LGM BIO1 | -28.5 | 14.5 | 10.7 | 25.8 |

## Stability metrics across the 374 cells
| Metric | Min | Median | Mean | Max |
|---|---|---|---|---|
| LGM change (°C) | 1.60 | 3.85 | 6.47 | 27.60 |
| Mid-Holocene change (°C) | 0.00 | 0.78 | 0.83 | 2.43 |
| Instability (SD, °C) | 0.82 | 2.02 | 3.55 | 15.65 |
- LGM change quartiles: Q1 = 3.3 °C, Q3 = 6.5 °C.
- Stable cells (LGM change < 10 °C): 314 (84%). Moderate (10-20 °C): 31. Unstable (> 20 °C): 29.
- Mid-Holocene change is at most 2.4 °C (median 0.78 °C), so it adds little information. LGM change is the main stability measure.

## Link with latitude
- Spearman correlation between LGM change and |latitude| is 0.69 (PaleoClim: 0.52), so higher-latitude cells were less stable, and the link is even stronger here.
- This is why the integration step controls for latitude in the partial correlation.

## Key observations
- On the global map, the largest LGM change (about 25-30 °C) is in northern North America and northern Eurasia, where ice sheets were (wc_lgm_change.png).
- The tropics (Amazon, central Africa, Southeast Asia, northern Australia) show the smallest change (under about 10 °C) and are the most stable.
- The global change distribution is right-skewed, with a sharp peak at about 4-5 °C and a long tail up to about 30 °C (wc_change_hist.png). The GBIF cells follow this pattern: most are stable and a small group is strongly affected by glaciation.
- Mid-Holocene change is small everywhere, so LGM change is the main stability measure.

## Comparison with PaleoClim (same 374 cells)
| | WorldClim | PaleoClim |
|---|---|---|
| Source | CCSM4 climate model simulation | CHELSA-based reconstruction |
| Cells with climate values | 374 | 375 |
| Mean LGM change (°C) | 6.47 | 7.30 |
| Max LGM change (°C) | 27.6 | 33.9 |
| Unstable cells (> 20 °C) | 29 | 34 |
| Correlation of LGM change with latitude | 0.69 | 0.52 |
- Cell-level agreement: Spearman rho = 0.78 for LGM change across the 374 shared cells, so the two sources rank cells similarly.
- PaleoClim shows larger changes at high latitudes, and its global distribution is bimodal (peaks near 5 °C and 20-25 °C), while WorldClim has a single sharp peak and a tail.
- Holocene period differs: mid-Holocene (about 6 ka) here, Late Holocene in PaleoClim.

## Interpretation
- Both datasets agree that most GBIF cells are climatically stable and that instability is concentrated at high latitudes.
- Stability in WorldClim is even more tied to latitude (rho = 0.69), so latitude must be controlled to isolate any effect on richness.

## Limitations
- Temperature only (BIO1). Precipitation not used yet.
- Based on a single GCM (CCSM4), so model-specific bias is possible.
- 10 arc-min resolution and 5° cell averaging are coarse for local refugia.
- Stability is estimated from only 3 time slices.
- Values at GBIF points depend on where records are, so unsampled areas have no value.

## Outputs
- processed/: wc_lgm_change_2deg.npy (2° display grid, name kept), wc_summary.csv, worldclim_cell_stability.csv (5° cells), wc_cell_stats.csv
- figures/: wc_bio1_present.png, wc_bio1_holocene.png, wc_bio1_lgm.png, wc_lgm_change.png, wc_change_hist.png