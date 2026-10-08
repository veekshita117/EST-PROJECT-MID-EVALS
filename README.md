# Palaeoclimate Stability and Modern Biodiversity

**Question:** Are biodiversity-rich regions disproportionately associated with long-term climatic stability?

## Data
- PaleoClim (BIO1: Current, Late Holocene, LGM)
- WorldClim palaeoclimate (BIO1: present, mid-Holocene, LGM; CCSM4 simulation)
- GBIF occurrence records (17,396 clean records, 6,080 species)
- Planned: IUCN ranges, Copernicus DEM

## Method
1. Richness = unique species per 5° grid cell (GBIF): 375 cells with records.
2. Stability = |Present - LGM| BIO1 change and SD across 3 time slices (PaleoClim and WorldClim). Lower = more stable.
3. Climate values sampled at GBIF record locations and averaged per cell (375 cells for PaleoClim, 374 for WorldClim).
4. Only cells with at least 10 GBIF records are analysed (188 cells).
5. Spearman and partial Spearman correlation (controlling for sampling effort and latitude), quartile comparison, dataset agreement and a hotspot map.
6. Robustness check: the same analysis was run at 2° (264 cells) and 5° (188 cells).

## Main result
- Raw correlation between richness and stability is about zero (rho -0.05 to 0.03, p > 0.46).
- After controlling for sampling effort and latitude, PaleoClim shows a weak negative relationship: richer cells are slightly more stable (partial rho ≈ -0.21, p ≤ 0.004). WorldClim has the same direction but is not significant (partial rho ≈ -0.10 to -0.11, p > 0.12).
- The least stable quartile has clearly the lowest mean richness (about 34 species vs 52-57 in the other quartiles).
- PaleoClim and WorldClim agree on which cells are stable (rho = 0.75 on the analysed cells, 0.78 on all shared cells).
- Hotspots: 15 cells are rich and stable, and 32 are rich but unstable.
- The PaleoClim result is almost identical at 2° and 5°. WorldClim weakens at 5° (partial rho -0.18 at 2° vs -0.11 at 5°).
- Overall: weak, dataset-dependent support for the hypothesis. Stability explains only a small share of richness variation.

## Limitations
- Sampled GBIF data with uneven effort (richest cells are also the best sampled, mainly South Africa).
- Temperature only (BIO1), 3 time slices, and a single GCM for WorldClim.
- 5° cells hide local refugia.

## Next steps
- Add precipitation (BIO12), IUCN range maps and Copernicus DEM.
- Use the full GBIF download and rarefied richness.
- Analyse single taxonomic groups.

## Structure
- `common/helpers.py`: shared functions (grid size set by `CELL = 5`)
- `GBIF/`, `PALEOCLIM/`, `WORLDCLIM/`: notebook, processed data, figures, notes
- `integration/`: merged analysis, tables, figures, results.md

## Run order
GBIF/gbif.ipynb → PALEOCLIM/paleoclim.ipynb → WORLDCLIM/worldclim.ipynb → integration/integration.ipynb

## Setup
`pip install -r requirements.txt`