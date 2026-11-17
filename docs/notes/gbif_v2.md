# GBIF Occurrence Data Processing & Rarefaction Notes (v2)

This document records the data retrieval, exact deduplication, taxonomic aggregation, and Hurlbert rarefaction procedures applied to the global GBIF occurrence archives for Mammalia and Amphibia.

---

## 1. Datasets & Download Verification

1. **Mammalia Occurrence Download**:
   - **Download Key**: `0007627-261110092616502`
   - **DOI**: [10.15468/dl.yqmpcx](https://doi.org/10.15468/dl.yqmpcx)
   - **Status**: SUCCEEDED (verified complete)
   - **Occurrences**: 40,334,722 rows
   - **Extracted Location**: `GBIF/raw/parquet_mammalia/occurrence.parquet/`
   
2. **Amphibia Occurrence Download**:
   - **Download Key**: `0007626-261110092616502`
   - **DOI**: [10.15468/dl.46xqsa](https://doi.org/10.15468/dl.46xqsa)
   - **Status**: SUCCEEDED (verified complete)
   - **Occurrences**: 8,805,881 rows
   - **Extracted Location**: `GBIF/raw/parquet_amphibia/occurrence.parquet/`
   
3. **Combined Data Volume**: 49,140,603 total raw occurrence records.

---

## 2. Deduplication Protocol

- **Exact Duplicate `gbifID` Removal**:
  In accordance with project guidelines, deduplication was executed using DuckDB's `DISTINCT ON (gbifid)`.
  This removes identical duplicate record identifiers resulting from multi-partition extraction.
- **Preservation of Repeated Species-Location Observations**:
  Multiple distinct observation events of the same species at the same geographic coordinate (possessing distinct `gbifID`s) are **strictly retained**. These repeated observations represent genuine sampling frequency and individual specimen counts required for Hurlbert rarefaction.

---

## 3. Mathematical Formulation of Hurlbert Rarefaction

To eliminate the severe confounding of sampling effort ($R^2 \approx 0.83$ driven by `log_effort`), we compute Hurlbert's (1971) expected species richness $E(S_n)$ for a standardized sample of $n$ individuals drawn at random without replacement from the cell's occurrence pool:

$$E(S_n) = \sum_{i=1}^S \left[ 1 - \frac{\binom{N - N_i}{n}}{\binom{N}{n}} \right]$$

where:
- $N$ is the total record count in the cell ($\sum_{i=1}^S N_i = N$)
- $N_i$ is the number of records for species $i$
- If $N - N_i < n$, the term is identically $1.0$.
- If $N < n$, the rarefied richness is undefined (`NaN`).

### Selection of Standardized Sample Sizes ($n$)
From the empirical records-per-cell distribution across global 5° grid cells:
- **Baseline ($n = 20$)**: Selected below the 25th percentile of records ($Q_{25} = 42$), maximizing geographic coverage across undersampled tropical and southern hemisphere regions while controlling for effort.
- **Sensitivity Checks ($n = 50$ and $n = 100$)**: Evaluates richness scaling under higher sampling depth thresholds for well-sampled cells.

---

## 4. Output Summary Statistics

### A. 5-Degree Grid (`gbif_cells_5deg_v2.csv`)
- **Total Occupied Cells**: 1990
- **Records per Cell**: Median = 568, Q25 = 42, Q75 = 4018, Max = 5,702,733
- **Observed Richness**: Median = 11, Max = 1047
- **Rarefied Richness ($n=20$)**: Valid in 1609 cells (Mean = 7.80)
- **Rarefied Richness ($n=50$)**: Valid in 1468 cells (Mean = 13.50)
- **Rarefied Richness ($n=100$)**: Valid in 1353 cells (Mean = 19.79)

### B. 2-Degree Grid (`gbif_cells_2deg_v2.csv`)
- **Total Occupied Cells**: 9631
- **Records per Cell**: Median = 97, Max = 2,528,518
- **Rarefied Richness ($n=20$)**: Valid in 6700 cells
- **Rarefied Richness ($n=50$)**: Valid in 5635 cells
- **Rarefied Richness ($n=100$)**: Valid in 4786 cells

---

## 5. File Registry

- Processed 5° Grid: `GBIF/processed/gbif_cells_5deg_v2.csv`
- Processed 2° Grid: `GBIF/processed/gbif_cells_2deg_v2.csv`
- Raw Parquet Sources: `GBIF/raw/parquet_mammalia/` and `GBIF/raw/parquet_amphibia/`
- Download Metadata & DOIs: `GBIF/raw/GBIF_DOWNLOADS.md`
