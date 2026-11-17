# GBIF notes (5° grid)

## Data
- Source: GBIF occurrence records (see raw/GBIF_METADATA.md).
- File used: raw/gbif_all_continents.csv (sampled records, 1000-5000 per continent).
- Columns used: speciesKey (species ID), decimalLatitude, decimalLongitude.

## Cleaning
- Renamed decimalLatitude/decimalLongitude to lat/lon.
- Used speciesKey as the species identifier.
- Dropped rows with missing species or coordinates, duplicates, invalid coordinates and (0,0) points.
- Result: 17,396 clean records and 6,080 unique species (unchanged by the grid size).

## Method
- World divided into 5° x 5° grid cells (changed from 2° so each cell holds more records).
- Species richness = number of unique species per cell.
- n_records (records per cell) kept to control for sampling bias in the integration step.

## Summary table
| Measure | Value |
|---|---|
| Clean records | 17,396 |
| Unique species | 6,080 |
| Grid cells with records | 375 |
| Richness per cell: median / mean / max | 9 / 26.6 / 453 |
| Records per cell: median / mean / max | 10 / 46.4 / 1,757 |
| Cells with >= 10 records | 188 |
| Cells with >= 20 records | 125 |
| Cells with < 10 records | 187 |

## Top 10 richest cells
| Cell centre (lat, lon) | Richness | Records | Approx. region |
|---|---|---|---|
| -27.5, 32.5 | 453 | 619 | NE South Africa / S Mozambique |
| -32.5, 17.5 | 451 | 756 | Western Cape, South Africa |
| -22.5, 32.5 | 437 | 662 | Kruger / S Mozambique |
| -27.5, 27.5 | 373 | 556 | Interior South Africa |
| 22.5, 122.5 | 312 | 422 | Taiwan |
| 2.5, 102.5 | 289 | 445 | Peninsular Malaysia / Singapore |
| -32.5, 27.5 | 240 | 351 | Eastern Cape, South Africa |
| -32.5, 22.5 | 224 | 302 | Southern South Africa |
| 27.5, -17.5 | 195 | 301 | Canary Islands |
| 27.5, 122.5 | 170 | 224 | East China coast |

## Key observations
- Records cover all continents, but are denser in North America, Europe, South Africa, India and eastern Australia (gbif_records_map.png).
- Richness is highly skewed: the median cell has 9 species but the richest has 453 (gbif_richness_map.png).
- Six of the 10 richest cells are in South Africa. The others are Taiwan, Malaysia, the Canary Islands and the East China coast.
- Richest cells are also among the best-sampled (about 220-760 records each), so richness and sampling effort are strongly linked.
- Mean richness by latitude has one large peak near 30°S (about 80 species, from gbif_richness_latitude.png), driven by the South African cells. Elsewhere it is roughly 15-30 species, with a small rise near 60°N. There is no clean tropical peak.
- Sampling effort is very uneven: the median cell has 10 records, but a few have over 500 and the maximum is 1,757 (gbif_records_per_cell.png, log scale).

## Interpretation
- The high-richness cells are mainly well-sampled cells, so richness here partly reflects sampling effort and not only true biodiversity.
- The 30°S peak and the lack of a tropical peak are mainly a sampling effect.
- At 5° about half the cells (187 of 375) still have fewer than 10 records, and these are unreliable. This is why the integration step keeps only cells with at least 10 records (188 cells) and uses partial correlation controlling for sampling effort and latitude.

## Limitations
- Sampled download, not the full GBIF dataset.
- South Africa, Europe and North America are likely over-sampled.
- No taxonomic group filter, so all taxa are mixed.
- Richness per cell is a lower bound, and 5° cells can mix different habitats and climates.

## Outputs
- processed/: gbif_points_clean.csv, gbif_richness_cells.csv, gbif_summary.csv, gbif_top10_cells.csv
- figures/: gbif_records_map.png, gbif_richness_map.png, gbif_richness_latitude.png, gbif_records_per_cell.png