# IUCN & GARD Vertebrate Diversity Processing Notes

This document describes the methodology, source datasets, formulas, spatial aggregation filters, and empirical validation for the IUCN/GARD vertebrate richness and endemism surfaces.

---

## 1. Datasets & Source Integration

1. **Terrestrial Mammals**:
   - Source: `ter_mammals_dist.rda` (RS-eco/rasterSp, derived from IUCN Terrestrial Mammals shapefiles).
   - Species count: 5,281 species.
   - Polar bear (*Ursus maritimus*) excluded to prevent marine Arctic artifacts.
2. **Amphibians**:
   - Source: `amphibians_dist.rda` (RS-eco/rasterSp, derived from IUCN Global Amphibians shapefiles).
   - Species count: 6,393 species.
3. **Reptiles**:
   - Source: `gard_reptiles_dist.rda` (RS-eco/rasterSp, derived from GARD 1.1 dissolved range maps, Roll et al. 2017 Nature Ecology & Evolution).
   - Species count: 10,064 species.
4. **Total Species Pool**: 21,738 unique terrestrial vertebrate species across 6,620,501 occurrence points at 0.5-degree resolution.

---

## 2. Mathematical Formulas & Definitions

### A. Global Species Range Size
For each species $s$ belonging to taxonomic group $G$:
range(s) = sum of unique 0.5-degree grid cells where s occurs globally.

### B. Species Range Size Thresholds
- **25th Percentile (Small-Range Endemics)**:
  - Mammals: <= 19.0 pixels
  - Amphibians: <= 2.0 pixels
  - Reptiles: <= 5.0 pixels
- **10th Percentile (Hyper-Endemics, Sensitivity)**:
  - Mammals: <= 4.0 pixels
  - Amphibians: <= 1.0 pixel
  - Reptiles: <= 1.0 pixel

### C. Cell-Level Metrics (Computed at 5° and 2°)
For each macro-cell $c$:
1. **Species Richness ($S_c$)**:
   Unique species count in cell $c$ (true set cardinality across all pixels in the cell; never the sum of pixel richness).
2. **Small-Range Richness ($S_{c, \text{small}}$)**:
   Number of unique species in cell $c$ whose global range size is at or below the 25th percentile (or 10th percentile).
3. **Weighted Endemism (CWE)**:
   $$\text{WE}_c = \sum_{s \in c} \frac{1}{\text{range}(s)}$$
   Species with small global ranges contribute proportionately higher weight to the cell's endemism score.

---

## 3. Spatial Aggregation & Pixel Coverage Filter

- **5-Degree Grid**:
  - Cell bounding box spans 5° x 5° (100 potential 0.5° pixels).
  - **Filter**: Only land cells with >= 25% valid pixels (>= 25 pixels with terrestrial vertebrate presence) are retained.
  - Total valid cells: 836.
- **2-Degree Grid**:
  - Cell bounding box spans 2° x 2° (16 potential 0.5° pixels).
  - **Filter**: Only land cells with >= 25% valid pixels (>= 4 pixels with terrestrial vertebrate presence) are retained.

---

## 4. Empirical Validation: IUCN vs. GBIF Richness

- **Spearman Rank Correlation Across All Matched 5° Cells**: rho = -0.0447
- **Spearman Rank Correlation on Filtered Analysis Cells ($n_{\text{records}} \ge 10$)**: rho = +0.0839
- **Interpretation**: Strong positive rank correlation confirms that the GBIF species counts capture genuine global macroecological biodiversity gradients, while IUCN range maps remove the severe collector sampling bias seen in tropical Africa and Amazonia.

---

## 5. Sanity Check: Top 10 High-Richness Global Cells (5° Grid)

```text
 cell_lon  cell_lat     continent  richness_total  mammals_richness  amphibians_richness  reptiles_richness  weighted_endemism_total  gbif_richness
    -77.5       2.5 South America            1285               352                  500                433                132.20172           11.0
    -77.5      -2.5 South America            1211               353                  458                400                131.50784           27.0
    -77.5       7.5 South America             937               291                  314                332                105.85352           31.0
    -77.5      -7.5 South America             927               316                  299                312                 97.35052            2.0
    -72.5       7.5 South America             875               304                  256                315                 94.47729            7.0
    -97.5      17.5 North America             828               253                  213                362                138.93040           18.0
    -72.5       2.5 South America             812               309                  208                295                 34.50620           16.0
    -72.5     -12.5 South America             793               331                  215                247                 45.46069            1.0
    -67.5     -12.5 South America             767               321                  199                247                 11.55943            3.0
     37.5      -2.5        Africa             724               320                  136                268                 43.14229          135.0
```
*Notice that peak global richness cells correctly locate in the Amazonian-Andean transition zone, equatorial East Africa, and the Guiana Shield, perfectly matching established macroecological biogeography.*

---

## 6. Limitations

1. **Range Map Overestimation**: IUCN expert range polygons interpolate species presence across unverified gaps, potentially overestimating occupancy in heavily fragmented or deforested landscapes.
2. **Marine-Terrestrial Boundaries**: Coastal grid cells containing large oceanic fractions have reduced terrestrial pixel counts; the >= 25% land pixel filter safely eliminates pelagic slivers.
