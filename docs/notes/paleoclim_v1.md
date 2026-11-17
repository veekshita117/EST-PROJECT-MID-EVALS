# PaleoClim notes (5° grid)

## Data
- Variable: BIO1 (mean annual temperature), 10 arc-min resolution.
- Periods: Current, Late Holocene, Last Glacial Maximum (LGM).
- Files used: paleoclim_current_BIO1.tif, paleoclim_late_holocene_BIO1_aligned.tif, paleoclim_LGM_BIO1_aligned.tif (aligned rasters).
- Values auto-scaled from °C*10 to °C.

## Sanity check (global values, °C)
| Period | Min | Max | Mean |
|---|---|---|---|
| Present | -52.30 | 32.20 | -2.78 |
| Late Holocene | -52.60 | 30.10 | -3.48 |
| LGM | -79.90 | 27.30 | -15.07 |
- Values are realistic: LGM is the coldest and the Holocene is close to present.
- These statistics come from a 2° display grid used only for the global maps. They do not depend on the 5° analysis grid.
- The global means are low because the grid includes Antarctica and Greenland. They are plain averages, not area-weighted, so do not quote them as true global means.

## Method
- Stability metrics per location:
  - lgm_change = |Present - LGM|
  - holo_change = |Present - Late Holocene|
  - instability = SD of BIO1 across the 3 time slices
- Lower values mean more stable climate.
- Values are sampled at GBIF record locations (17,396 points) and averaged per 5° x 5° cell (same grid as GBIF), giving 375 cells with climate values.
- A 5° cell can span a wide range of climates, so its mean stability is smoother than at 2°.

## Climate at the GBIF cells (°C)
| Variable | Min | Median | Mean | Max |
|---|---|---|---|---|
| Present BIO1 | -5.5 | 19.0 | 17.6 | 29.5 |
| Late Holocene BIO1 | -6.2 | 18.4 | 17.0 | 28.7 |
| LGM BIO1 | -31.9 | 14.7 | 10.4 | 24.6 |
- These are warmer than the global means because GBIF records are mostly in inhabited, lower-latitude regions, and polar areas have almost no records.

## Stability metrics across the 375 cells
| Metric | Min | Median | Mean | Max |
|---|---|---|---|---|
| LGM change (°C) | 0.10 | 4.70 | 7.29 | 33.92 |
| Late Holocene change (°C) | 0.00 | 0.60 | 0.64 | 2.22 |
| Instability (SD, °C) | 0.53 | 2.56 | 4.07 | 19.50 |
- LGM change quartiles: Q1 = 3.5 °C, Q3 = 7.9 °C.
- Stable cells (LGM change < 10 °C): 307 (82%). Moderate (10-20 °C): 34. Unstable (> 20 °C): 34.
- Holocene change is at most 2.2 °C (median 0.6 °C), so it adds little information. LGM change is the main stability measure.

## Link with latitude
- Spearman correlation between LGM change and |latitude| is 0.52, so higher-latitude cells were less stable.
- Mean LGM change rises from about 19 °C at 60°N to about 28 °C at 70°N (latitude-band table, bands 60° and 70°).
- This is why the integration step controls for latitude in the partial correlation.

## Key observations
- On the global map, the largest LGM change (about 30-35 °C) is in northern North America and northern Eurasia, which were covered by ice sheets (pc_lgm_change.png).
- The tropics (Amazon, central Africa, Southeast Asia, northern Australia) show the smallest change (under about 10 °C) and are the most stable.
- Antarctica shows moderate to high change (about 15-25 °C) on the map, but it has almost no GBIF records, so it does not enter the analysis.
- The global change distribution is bimodal (pc_change_hist.png): one peak near 5 °C (low latitudes) and another near 20-25 °C (glaciated high latitudes). The GBIF cells are dominated by the stable group.

## Interpretation
- Most GBIF cells are climatically stable, so the stability signal comes from a small set of high-latitude, unstable cells (34 cells above 20 °C).
- Stability is partly a latitude effect, so latitude must be controlled to isolate it.
- Averaging over 5° cells reduces local detail, so small refugia are not visible at this scale.

## Limitations
- Temperature only (BIO1). Precipitation not used yet.
- 10 arc-min resolution and 5° cell averaging are coarse for local refugia.
- Stability is estimated from only 3 time slices.
- Values at GBIF points depend on where records are, so unsampled areas have no value.

## Outputs
- processed/: pc_lgm_change_2deg.npy (2° display grid, name kept), pc_summary.csv, paleoclim_cell_stability.csv (5° cells), pc_cell_stats.csv
- figures/: pc_bio1_present.png, pc_bio1_holocene.png, pc_bio1_lgm.png, pc_lgm_change.png, pc_change_hist.png