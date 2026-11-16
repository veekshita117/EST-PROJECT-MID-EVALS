# Public Species Distribution Data Sources & Audit

This document records the probing status, access availability, metadata, and license terms of public species distribution datasets evaluated for modern vertebrate richness, small-range richness, and weighted endemism analyses.

---

## 1. Summary of Public Probes (HEAD Requests)

| Source Candidate | URL / Identifier | Probed Protocol | HTTP Status | Accessibility | Classification |
|:---|:---|:---:|:---:|:---:|:---|
| **IUCN S3 Mammals** | `http://spatial-data.s3.amazonaws.com/groups/TERRESTRIAL_MAMMALS.zip` | HTTP HEAD | `404 Not Found` | Unreachable | Original polygon range maps (discontinued bucket endpoint) |
| **IUCN S3 Amphibians** | `http://spatial-data.s3.amazonaws.com/groups/AMPHIBIANS.zip` | HTTP HEAD | `404 Not Found` | Unreachable | Original polygon range maps (discontinued bucket endpoint) |
| **IUCN S3 Reptiles** | `http://spatial-data.s3.amazonaws.com/groups/REPTILES.zip` | HTTP HEAD | `404 Not Found` | Unreachable | Original polygon range maps (discontinued bucket endpoint) |
| **GARD Reptiles** | `https://doi.org/10.5061/dryad.83s7k` | HTTPS HEAD | `302 Found` → `200 OK` (landing) / `403 Forbidden` (stream) | Blocked (Auth required) | Original range shapefiles (GARD 1.1 dissolved ranges) |
| **RS-eco/rasterSp** | `https://github.com/RS-eco/rasterSp/tree/main/data-raw` | HTTPS HEAD | `200 OK` | **Reachable (Downloaded)** | Per-species 0.5-degree presence tables (`.rda`) |
| **BiodiversityMapping** | `https://biodiversitymapping.org/index.php/download/` | HTTPS HEAD | `200 OK` (browser UA) | **Reachable (Downloaded)** | Pre-aggregated 10-km GeoTIFF richness rasters |

---

## 2. Detailed Metadata of Reachable Datasets

### A. RS-eco/rasterSp Per-Species Presence Tables (Primary Dataset)
- **Repository**: [RS-eco/rasterSp](https://github.com/RS-eco/rasterSp)
- **Author**: Dr. Matt Lewis (RS-eco)
- **Date**: 2019–2021
- **Software Version**: rasterSp v0.2.0
- **Licence**: MIT Licence (Code & derived tables) / Underlying IUCN & GARD Terms of Use
- **Dataset Description**:
  Derived 0.5-degree ($30'$) spatial presence tables containing coordinates (`x` = longitude, `y` = latitude) and binomial species names (`species`). Created by rasterizing original polygon range shapefiles using `sf` and area weighting.
- **Downloaded Files**:
  1. `amphibians_dist.rda` (299 KB compressed): 1,280,317 presence rows across global amphibians.
  2. `ter_mammals_dist.rda` (795 KB compressed): 3,394,903 presence rows across terrestrial mammals (excluding polar bear marine artifacts).
  3. `gard_reptiles_dist.rda` (741 KB compressed): 3,137,858 presence rows across global reptiles.
  4. Metadata tables: `amphibians.rda`, `ter_mammals.rda`, `gard_reptiles.rda`.
- **Analytical Utility**:
  Enables rigorous computation of cell-level unique species richness (avoiding double-counting overlapping ranges), individual species global range sizes, small-range richness thresholds (25th and 10th percentiles), and weighted endemism ($\sum \frac{1}{\text{range}}$).

### B. BiodiversityMapping.org Richness Rasters (Secondary / Validation Dataset)
- **Platform**: [BiodiversityMapping.org](https://biodiversitymapping.org)
- **Author**: Dr. Clinton N. Jenkins
- **Publication Date**: 2019-03-14 (revised February 2020)
- **Archive**: `BiodiversityMapping_TIFFs_2019_03d14_revised.zip` (14.6 MB)
- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Dataset Description**:
  Pre-aggregated raster grids at 10 km $\times$ 10 km equal-area resolution depicting total species richness, threatened species richness, and small-range species richness for global vertebrates.
- **Analytical Utility**:
  Used to compute mean local richness per macro-cell and serve as external cross-validation against the per-species spatial aggregations.

### C. GARD 1.1 Reptiles (Dryad Data Package)
- **DOI**: [10.5061/dryad.83s7k](https://doi.org/10.5061/dryad.83s7k)
- **Citation**: Roll et al. (2017) *Nature Ecology & Evolution* 1: 1677–1682; Meiri et al. (2017) *Dryad Digital Repository*.
- **Licence**: CC0 1.0 Universal
- **Access Note**: Web landing page is active; automated direct download requires authenticated Dryad credentials or session cookies. Represented completely via the derived `gard_reptiles_dist.rda` dataset from `rasterSp`.
