# Copernicus DEM notes (GLO-90 Elevation & Topographic Heterogeneity)

## Citation & Data Source
- Dataset: ESA Copernicus Digital Elevation Model GLO-90.
- DOI: 10.5069/G9028PQB (OpenTopography).
- Distribution: AWS Open Data Registry (`s3://copernicus-dem-90m/`, unsigned access, region `eu-central-1`).
- Format: Cloud-Optimized GeoTIFFs (COGs) organized in 1° x 1° tiles (GLO-90 DGED product).
- Native resolution: 3 arc-seconds (~90 m at equator).
- Decimated resolution used: 0.01° (~1 km), yielding 100 x 100 samples per 1° tile, or ~250,000 elevation samples per 5° analysis cell.

## Definitions
- `elevation_mean`: Area-weighted average elevation (meters above sea level) of all valid land pixels within the grid cell ($\sum x / N$). Used as a macro-environmental control variable for lapse-rate cooling and highland environmental barriers.
- `topographic_heterogeneity`: Topographic relief range ($\text{elevation}_{\max} - \text{elevation}_{\min}$, in meters) across the cell, alongside elevation standard deviation (`elevation_sd`). Serves as a primary proxy for microclimatic refugia, steep vertical environmental gradients, and habitat diversity that facilitate species persistence during glacial-interglacial cycles.

## Method
- 7,302 1° x 1° land tiles intersecting the 375 analysis cells were read directly from S3 using decimated COG overviews (`out_shape=(100, 100)`).
- Ocean areas without tiles are treated as masked missing data, not as zero elevation.
- Tiles are cached in `COPERNICUS_DEM/raw/tiles/` (total folder size: 199.38 MB, 215 MB disk space allocated across 7,302 files) with metadata logged to `tile_stats_cache.csv`.
- Statistics aggregated strictly using sums, sums of squares, and extrema:
  - $\text{elevation\_mean} = \sum x / N$
  - $\text{elevation\_sd} = \sqrt{\frac{\sum x^2 - (\sum x)^2 / N}{N - 1}}$
  - $\text{relief\_range} = \max(x) - \min(x)$
- Evaluated at 5° (375 cells) and 2° (2,231 cells) grid resolutions.

## Summary Table (5° Grid, 375 Cells)
| Measure | Min | Median | Mean | Max |
|---|---|---|---|---|
| Pixel count per cell | 10,000 | 240,000 | 194,720 | 250,000 |
| Mean elevation (m) | 0.01 | 241.92 | 463.78 | 3,363.56 |
| Elevation SD (m) | 0.15 | 217.27 | 333.08 | 2,290.25 |
| Minimum elevation (m) | -427.00 | -0.31 | 57.38 | 1,183.67 |
| Maximum elevation (m) | 9.48 | 1,929.29 | 2,255.44 | 8,498.48 |
| Relief range (m) | 9.68 | 1,895.98 | 2,198.06 | 8,487.98 |

## Top 10 Highest Relief Cells (Himalaya & Andes)
| Cell Centre (lat, lon) | Relief Range (m) | Mean Elevation (m) | Elevation SD (m) | Region |
|---|---|---|---|---|
| 27.5, 87.5 | 8,488.0 | 2,536.4 | 2,290.3 | Central Himalaya / Mount Everest |
| 27.5, 82.5 | 7,824.8 | 1,217.1 | 1,786.3 | Central Himalaya / Nepal |
| 27.5, 92.5 | 7,374.4 | 2,316.1 | 1,971.4 | Eastern Himalaya / Bhutan |
| 32.5, 77.5 | 7,219.2 | 3,363.6 | 1,959.6 | NW Himalaya / Karakoram / Ladakh |
| 27.5, 97.5 | 6,774.4 | 2,363.6 | 1,569.1 | Eastern Himalaya / Hengduan |
| -32.5, -72.5 | 6,738.4 | 1,209.6 | 1,383.2 | Central Andes / Chile / Aconcagua |
| 27.5, 102.5 | 6,712.2 | 2,262.4 | 1,058.9 | Hengduan Mountains, SW China |
| -7.5, -77.5 | 6,530.0 | 1,377.9 | 1,345.6 | Peruvian Andes / Cordillera Blanca |
| -27.5, -67.5 | 6,498.6 | 2,624.1 | 1,526.0 | Southern Andes / Ojos del Salado |
| -22.5, -67.5 | 6,273.0 | 3,332.5 | 1,110.0 | Central Andes / Altiplano |

## Bottom 10 Lowest Relief Cells (Lowlands & Coastal Islands)
| Cell Centre (lat, lon) | Relief Range (m) | Mean Elevation (m) | Elevation SD (m) | Region / Feature |
|---|---|---|---|---|
| 2.5, 72.5 | 9.7 | 0.0 | 0.2 | Maldives atoll / ocean cell |
| 7.5, 72.5 | 12.8 | 0.0 | 0.2 | Laccadive Sea reef platform |
| 27.5, -77.5 | 38.7 | 0.1 | 0.9 | Bahamas carbonate platform |
| 27.5, -92.5 | 44.1 | 1.1 | 3.1 | Gulf of Mexico delta / barrier island |
| 37.5, -72.5 | 69.7 | 6.6 | 12.9 | US Mid-Atlantic coastal plain |
| 27.5, -82.5 | 105.3 | 9.6 | 13.1 | Florida peninsula lowlands |
| 57.5, 72.5 | 123.0 | 99.7 | 20.9 | West Siberian Plain (glaciated lowlands) |
| 12.5, -17.5 | 135.4 | 13.5 | 16.8 | Senegambia coastal plain |
| -7.5, -32.5 | 136.2 | 3.2 | 13.7 | Fernando de Noronha / NE Brazil coast |
| -32.5, 112.5 | 143.3 | 0.1 | 2.4 | Western Australian coastal shelf |

## Correlations with Climate Stability Metrics (188 Analysed Cells)
| Elevation Variable | Climate Metric | Pearson r | Spearman rho | p-value |
|---|---|---|---|---|
| `elevation_mean` | PaleoClim LGM change | -0.153 | -0.018 | 0.8072 |
| `elevation_mean` | PaleoClim instability | -0.152 | -0.023 | 0.7527 |
| `elevation_mean` | WorldClim LGM change | -0.156 | 0.040 | 0.5835 |
| `elevation_mean` | WorldClim instability | -0.158 | 0.026 | 0.7227 |
| `elevation_mean` | Absolute latitude | -0.108 | -0.063 | 0.3941 |
| `relief_range` | PaleoClim LGM change | -0.282 | -0.192 | 0.0085 |
| `relief_range` | PaleoClim instability | -0.283 | -0.198 | 0.0064 |
| `relief_range` | WorldClim LGM change | -0.299 | -0.209 | 0.0040 |
| `relief_range` | WorldClim instability | -0.300 | -0.215 | 0.0030 |
| `relief_range` | Absolute latitude | -0.270 | -0.256 | 0.0004 |

## Key Observations
- Topographic relief range is highest in the Himalaya (up to 8,488 m in the Everest cell) and the Andes (6,273–6,738 m).
- Relief range is lowest in the Siberian Lowlands (123 m) and broad coastal plains / delta platforms (< 150 m).
- Topographic heterogeneity (`relief_range`) correlates negatively with Quaternary temperature instability (Spearman $\rho \approx -0.19$ to $-0.22$, $p < 0.009$): high-relief cells experienced somewhat less macro-scale temperature shift than flat high-latitude lowlands.
- `relief_range` also correlates negatively with absolute latitude ($\rho = -0.256$, $p = 0.0004$), because extreme glaciation was concentrated on low-relief northern continental plains (Siberia, central Canada).
- `elevation_mean` shows no significant monotonic rank correlation with Quaternary climate instability ($\rho \approx -0.02$ to $0.04$, $p > 0.58$), confirming it functions independently as an environmental control.

## Limitations
- Digital Surface Model (DSM): Copernicus DEM reflects surface elevations including forest canopies and built infrastructure rather than bare-earth terrain (DTM).
- High-latitude interpolation: North of 60°N and across parts of 50°–60°N, original radar acquisitions were supplemented by interpolated cartographic sources.
- 0.01° decimated resolution smooths micro-topographic ravines under 100 m, though it adequately captures meso-scale relief across 5° and 2° grid cells.

## Outputs
- processed/: `dem_cells_5deg.csv`, `dem_cells_2deg.csv`, `table_elevation_correlations.csv`.
- figures/: `dem_mean_elevation.png`, `dem_heterogeneity.png`, `dem_histograms.png`, `dem_vs_lgm_change.png`.
