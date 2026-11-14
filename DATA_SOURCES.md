# Data Sources and Citations

This document provides bibliographic citations, access protocols, time slices, spatial resolutions, and licensing terms for the datasets utilized in the "Palaeoclimate Stability and Modern Biodiversity" research repository.

---

## 1. PaleoClim

- **Description**: High-resolution, bioclimatically downscaled paleoclimate surfaces derived from CHELSA baseline climatology and PMIP3/CMIP5 paleoclimate simulations.
- **Variables Used**:
  - `BIO1`: Annual Mean Temperature (°C $\times$ 10 rescaled to °C)
  - `BIO12`: Annual Precipitation (mm)
  - `BIO4`: Temperature Seasonality (standard deviation $\times$ 100)
  - `BIO15`: Precipitation Seasonality (coefficient of variation %)
- **Time Periods**:
  - Present: 1979–2013 baseline climatology (CHELSA 1.2)
  - Late Holocene: Sub-Boreal chronozone (4.2–0.3 ka BP)
  - Last Glacial Maximum (LGM): ~21 ka BP (PMIP3 multi-model ensemble)
- **Spatial Resolution**: 2.5 arc-minutes (raw rasters reprojected/aligned to uniform global grids).
- **Primary Citations**:
  - Brown, J. L., Hill, D. J., Dolan, A. M., Carnaval, A. C., & Haywood, A. M. (2018). *PaleoClim, high-resolution paleoclimate surfaces for global land areas*. **Scientific Data**, 5, 180254. https://doi.org/10.1038/sdata.2018.254
  - Karger, D. N., Conrad, O., Böhner, J., Kawohl, T., Kreft, H., Soria-Auza, R. W., Zimmermann, N. E., Linder, H. P., & Kessler, M. (2017). *Climatologies at high resolution for the earth’s land surface areas*. **Scientific Data**, 4, 170122. https://doi.org/10.1038/sdata.2017.122
- **Website**: http://www.paleoclim.org
- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0).

---

## 2. WorldClim

- **Description**: Global gridded climate surfaces representing historical baseline conditions and paleoclimate projections simulated by the Community Climate System Model (CCSM4).
- **Variables Used**:
  - `BIO1`: Annual Mean Temperature (°C $\times$ 10 rescaled to °C)
  - `BIO12`: Annual Precipitation (mm)
  - `BIO4`: Temperature Seasonality (standard deviation $\times$ 100)
  - `BIO15`: Precipitation Seasonality (coefficient of variation %)
- **Time Periods**:
  - Present: 1960–1990 baseline climatology
  - Mid-Holocene: ~6 ka BP (CCSM4)
  - Last Glacial Maximum (LGM): ~22 ka BP (CCSM4)
- **Spatial Resolution**: 2.5 arc-minutes and 10 arc-minutes (resampled/aggregated to 5° and 2° analysis cells).
- **Primary Citations**:
  - Hijmans, R. J., Cameron, S. E., Parra, J. L., Jones, P. G., & Jarvis, A. (2005). *Very high resolution interpolated climate surfaces for global land areas*. **International Journal of Climatology**, 25(15), 1965–1978. https://doi.org/10.1002/joc.1276
  - Gent, P. R., Danabasoglu, G., Donner, L. J., Holland, M. M., Hunke, E. C., Jayne, S. R., Lawrence, D. M., Neale, R. B., Rasch, P. J., Vertenstein, M., Worley, P. H., Yang, Z. L., & Zhang, M. (2011). *The Community Climate System Model Version 4*. **Journal of Climate**, 24(19), 4973–4991. https://doi.org/10.1175/2011JCLI4083.1
- **Website**: https://www.worldclim.org
- **Licence**: Free for non-commercial academic research and education.

---

## 3. Copernicus DEM GLO-90

- **Description**: High-resolution Digital Elevation Model (DEM) derived from WorldDEM radar interferometry data, providing global elevation and relief measurements.
- **Variables Derived**:
  - `elevation_mean`: Mean elevation above sea level (meters)
  - `elevation_sd`: Standard deviation of elevation within cell (meters)
  - `relief_range`: Topographic heterogeneity ($\text{elevation}_{\max} - \text{elevation}_{\min}$, meters)
- **Access Protocol**: AWS Open Data Program, unsigned public S3 bucket: `s3://copernicus-dem-90m/` (Region: `eu-central-1`).
- **STAC Catalogue**: https://copernicus-dem-90m-stac.s3.amazonaws.com/
- **Native Resolution**: 90 meters (3 arc-seconds), streamed via decimated overview reads at ~0.01° resolution per intersecting tile.
- **Primary Citation**:
  - European Space Agency (ESA) & Airbus Defence and Space (2020). *Copernicus Global Digital Elevation Model (GLO-90)*. Distributed via OpenTopography / AWS Open Data Sponsorship Program. https://doi.org/10.5069/G9028PQB
- **Licence & Terms**: Open access governed by the European Commission Copernicus Data and Information Policy (free, full, and open access).

---

## 4. GBIF (Global Biodiversity Information Facility)

- **Description**: Capped sample download, provenance not verified (see [`GBIF/raw/GBIF_METADATA.md`](GBIF/raw/GBIF_METADATA.md)).
- **Dataset Character**: Mixed-taxonomic sample from six regional raw CSV files with unequal continental caps (Africa 5,000, Asia 5,000, Europe 5,000, North America 1,000, South America 1,000, Oceania 1,000; total 18,000 raw rows). Cleaned down to 17,396 records and 6,080 species across 375 5° cells with records.
- **Licence**: Creative Commons Attribution (CC BY 4.0) and CC0 1.0 Universal (Public Domain).

---

## 5. IUCN Red List Spatial Data (Not Yet Used)

- **Status**: Not yet used. Raw shapefile downloads were not placed in `IUCN/raw/`; the integration models rely solely on GBIF observed richness.
- **Target Groups**: Terrestrial vertebrate range map shapefiles (`MAMMALS.zip`, `AMPHIBIANS.zip`, `REPTILES.zip`) from the IUCN spatial download portal (https://www.iucnredlist.org/resources/spatial-data-download).
- **Licence & Terms**: IUCN Red List Terms and Conditions of Use (non-commercial scientific and conservation use permitted with citation).
