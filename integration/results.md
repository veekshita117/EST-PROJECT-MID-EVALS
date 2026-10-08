# Results (5° grid)

## Data used
- Grid: 5° x 5° cells (changed from 2° so each cell holds more GBIF records).
- GBIF cells with climate values after merging all three sources: 374.
- Cells analysed: 188 (each with at least 10 GBIF records).
- Richness = unique species per 5° cell. Stability = |Present - LGM| BIO1 change and SD across 3 time slices (lower = more stable).

## Correlations (Spearman, richness vs stability metric)
| Dataset | Metric | n | rho | p | partial rho | partial p |
|---|---|---|---|---|---|---|
| PaleoClim | LGM change | 188 | -0.053 | 0.468 | -0.207 | 0.004 |
| PaleoClim | Instability | 188 | -0.046 | 0.530 | -0.212 | 0.003 |
| WorldClim | LGM change | 188 | 0.011 | 0.880 | -0.114 | 0.120 |
| WorldClim | Instability | 188 | 0.029 | 0.696 | -0.102 | 0.163 |

- Partial correlation controls for sampling effort (log records per cell) and absolute latitude.
- A negative rho means richer cells are more climatically stable (supports the hypothesis).

## Mean richness by stability quartile (47 cells each)
| Dataset | Most stable | Q2 | Q3 | Least stable |
|---|---|---|---|---|
| PaleoClim (mean) | 54.0 | 56.5 | 53.9 | 34.3 |
| PaleoClim (median) | 24 | 31 | 25 | 25 |
| WorldClim (mean) | 51.7 | 57.4 | 54.8 | 34.7 |
| WorldClim (median) | 24 | 21 | 31 | 26 |

## Key findings
1. **No raw relationship.** Without controls, rho is about zero (-0.053 to 0.029, p > 0.46) for both datasets and both metrics.
2. **PaleoClim shows a weak negative relationship after controls.** Partial rho is -0.207 and -0.212 (p ≤ 0.004). Richer cells are slightly more climatically stable, as the hypothesis predicts, but the effect is weak.
3. **WorldClim is in the same direction but not significant.** Partial rho is -0.114 and -0.102 (p = 0.12 and 0.16), so it does not confirm the PaleoClim result on its own.
4. **Quartiles.** The least stable quartile has clearly lower mean richness (about 34 species) than the other three (about 52-57) in both datasets. The three more stable quartiles are similar, and the richest one is Q2, not the most stable. Medians are close in all quartiles, so the means are pulled up by a few very rich cells.
5. **Dataset agreement.** PaleoClim and WorldClim LGM change correlate at rho = 0.75, so the two sources broadly agree on which areas were stable.
6. **Hotspots.** 15 cells are rich and stable, and 32 are rich but unstable (int_hotspots.png). Most rich and stable cells are in the southern hemisphere (South Africa, southern South America, Australia and New Zealand), and a few are in the north. About twice as many rich cells are in unstable climates, so richness hotspots are not restricted to stable cells.

## Comparison with the 2° run
| | 2° | 5° |
|---|---|---|
| Cells after merge | 889 | 374 |
| Cells analysed | 264 | 188 |
| Partial rho (PaleoClim, LGM change) | -0.209 (p = 0.001) | -0.207 (p = 0.004) |
| Partial rho (WorldClim, LGM change) | -0.176 (p = 0.004) | -0.114 (p = 0.120) |
| Dataset agreement rho | 0.718 | 0.75 |
| Rich + stable / rich + unstable cells | 17 / 50 | 15 / 32 |
- The PaleoClim result is almost identical at both grid sizes, so it is robust to cell size.
- The WorldClim result weakens and loses significance at 5°, so the evidence is weaker than at 2°. Part of this is the smaller sample (188 vs 264 cells).
- The direction (negative partial rho) is the same in every case, but the strength depends on the dataset and the grid.

## Interpretation
- There is weak, partial support for the hypothesis. After controlling for sampling effort and latitude, richness is slightly higher in more stable climates, with solid significance for PaleoClim and the same direction but no significance for WorldClim.
- The clearest pattern is that the least stable cells (strongly glaciated regions) have the lowest richness. Among the other cells, stability does not separate richness well.
- Stable climate is not a strong predictor of richness at this scale. Partial rho of about -0.2 means it explains only a small share of the variation.

## Limitations
- Sampled GBIF data (17,396 records), with uneven effort across regions.
- Richness is a lower bound, so it is partly a sampling artefact.
- Temperature only (BIO1). 5° cells average over wide climate gradients, which hides local refugia.
- Stability uses 3 time slices. WorldClim is a single GCM (CCSM4).
- Only 188 cells are analysed at 5°, so the tests have less power than at 2°.

## Next steps (remaining 40%)
- Add precipitation (BIO12) as a second stability metric.
- Add IUCN range maps and the Copernicus DEM (elevation as a refugia proxy).
- Use the full GBIF download and rarefied (sample-standardised) richness.
- Analyse single taxonomic groups.