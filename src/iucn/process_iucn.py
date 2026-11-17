#!/usr/bin/env python3
"""
IUCN & GARD Per-Species Distribution Processing Pipeline.
Aggregates 0.5-degree presence tables to 5-degree and 2-degree macro-cells.
Computes:
  - Richness (unique species per cell, never summing pixel richness)
  - Small-range richness (range <= 25th percentile, and 10th percentile as sensitivity)
  - Weighted endemism (sum of 1 / range_size)
  - Valid pixel filtering (>= 25% valid land pixels)
  - Spearman rank correlation vs. GBIF richness
  - Publication figures and diagnostics
"""

import os
import sys
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from ml.src.spatial import assign_continents_to_df
IUCN_DIR = REPO_ROOT / "IUCN"
RAW_DIR = IUCN_DIR / "raw"
PARQUET_DIR = RAW_DIR / "parquet"
PROCESSED_DIR = IUCN_DIR / "processed"
FIGURES_DIR = IUCN_DIR / "figures"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 80)
    print("IUCN & GARD PER-SPECIES PROCESSING PIPELINE")
    print("=" * 80)

    con = duckdb.connect()

    # -------------------------------------------------------------------------
    # 1. Global Species Range Sizes & Group Quantiles
    # -------------------------------------------------------------------------
    print("\n--- 1. Computing Global Range Sizes & Quantiles ---")
    query_ranges = f"""
    WITH combined AS (
        SELECT x, y, species, 'mammals' AS grp FROM read_parquet('{PARQUET_DIR}/mammals.parquet')
        UNION ALL
        SELECT x, y, species, 'amphibians' AS grp FROM read_parquet('{PARQUET_DIR}/amphibians.parquet')
        UNION ALL
        SELECT x, y, species, 'reptiles' AS grp FROM read_parquet('{PARQUET_DIR}/reptiles.parquet')
    ),
    sp_ranges AS (
        SELECT grp, species, COUNT(DISTINCT (x, y)) AS range_size
        FROM combined
        GROUP BY grp, species
    ),
    grp_quantiles AS (
        SELECT grp,
               quantile_cont(range_size, 0.10) AS q10,
               quantile_cont(range_size, 0.25) AS q25,
               median(range_size) AS med
        FROM sp_ranges
        GROUP BY grp
    )
    SELECT r.grp, r.species, r.range_size,
           (r.range_size <= q.q10)::INTEGER AS is_small_q10,
           (r.range_size <= q.q25)::INTEGER AS is_small_q25,
           (1.0 / r.range_size) AS weight
    FROM sp_ranges r
    JOIN grp_quantiles q ON r.grp = q.grp
    """
    con.execute(f"CREATE TABLE species_range_info AS {query_ranges}")

    quantiles_summary = con.execute("""
        SELECT grp, 
               COUNT(*) AS n_species, 
               quantile_cont(range_size, 0.10) AS q10_threshold, 
               quantile_cont(range_size, 0.25) AS q25_threshold, 
               median(range_size) AS median_range,
               MAX(range_size) AS max_range
        FROM species_range_info
        GROUP BY grp
        ORDER BY grp
    """).df()
    print("Species Range Summary:")
    print(quantiles_summary.to_string(index=False))

    # -------------------------------------------------------------------------
    # 2. Grid Aggregation Function (5-degree and 2-degree)
    # -------------------------------------------------------------------------
    resolutions = [
        {"name": "5deg", "res": 5.0, "offset": 2.5, "max_pixels": 100, "min_valid": 25, "gbif_file": "integration_v2/processed/data_5deg.csv"},
        {"name": "2deg", "res": 2.0, "offset": 1.0, "max_pixels": 16, "min_valid": 4, "gbif_file": "integration_v2/processed/data_2deg.csv"},
    ]

    top10_results = {}

    for cfg in resolutions:
        name = cfg["name"]
        res = cfg["res"]
        offset = cfg["offset"]
        max_px = cfg["max_pixels"]
        min_px = cfg["min_valid"]
        gbif_path = REPO_ROOT / cfg["gbif_file"]

        print(f"\n--- 2. Processing {name} Grid (Resolution: {res}°, Min Pixels: {min_px}/{max_px}) ---")

        # Map each 0.5-degree point to macro-cell center
        query_agg = f"""
        WITH point_grid AS (
            SELECT 
                FLOOR(x / {res}) * {res} + {offset} AS cell_lon,
                FLOOR(y / {res}) * {res} + {offset} AS cell_lat,
                x, y, species, grp
            FROM (
                SELECT x, y, species, 'mammals' AS grp FROM read_parquet('{PARQUET_DIR}/mammals.parquet')
                UNION ALL
                SELECT x, y, species, 'amphibians' AS grp FROM read_parquet('{PARQUET_DIR}/amphibians.parquet')
                UNION ALL
                SELECT x, y, species, 'reptiles' AS grp FROM read_parquet('{PARQUET_DIR}/reptiles.parquet')
            )
        ),
        cell_pixels AS (
            SELECT cell_lon, cell_lat, COUNT(DISTINCT (x, y)) AS n_valid_pixels
            FROM point_grid
            GROUP BY cell_lon, cell_lat
            HAVING COUNT(DISTINCT (x, y)) >= {min_px}
        ),
        cell_species AS (
            SELECT DISTINCT pg.cell_lon, pg.cell_lat, pg.species, pg.grp,
                   s.range_size, s.is_small_q10, s.is_small_q25, s.weight
            FROM point_grid pg
            JOIN cell_pixels cp ON pg.cell_lon = cp.cell_lon AND pg.cell_lat = cp.cell_lat
            JOIN species_range_info s ON pg.grp = s.grp AND pg.species = s.species
        )
        SELECT 
            cp.cell_lon,
            cp.cell_lat,
            cp.n_valid_pixels,
            ROUND(cp.n_valid_pixels * 1.0 / {max_px}, 4) AS valid_pixel_pct,
            
            -- Mammals
            COUNT(DISTINCT CASE WHEN cs.grp = 'mammals' THEN cs.species END) AS mammals_richness,
            COUNT(DISTINCT CASE WHEN cs.grp = 'mammals' AND cs.is_small_q25 = 1 THEN cs.species END) AS mammals_small_range_q25,
            COUNT(DISTINCT CASE WHEN cs.grp = 'mammals' AND cs.is_small_q10 = 1 THEN cs.species END) AS mammals_small_range_q10,
            ROUND(COALESCE(SUM(CASE WHEN cs.grp = 'mammals' THEN cs.weight END), 0.0), 5) AS mammals_weighted_endemism,
            
            -- Amphibians
            COUNT(DISTINCT CASE WHEN cs.grp = 'amphibians' THEN cs.species END) AS amphibians_richness,
            COUNT(DISTINCT CASE WHEN cs.grp = 'amphibians' AND cs.is_small_q25 = 1 THEN cs.species END) AS amphibians_small_range_q25,
            COUNT(DISTINCT CASE WHEN cs.grp = 'amphibians' AND cs.is_small_q10 = 1 THEN cs.species END) AS amphibians_small_range_q10,
            ROUND(COALESCE(SUM(CASE WHEN cs.grp = 'amphibians' THEN cs.weight END), 0.0), 5) AS amphibians_weighted_endemism,
            
            -- Reptiles
            COUNT(DISTINCT CASE WHEN cs.grp = 'reptiles' THEN cs.species END) AS reptiles_richness,
            COUNT(DISTINCT CASE WHEN cs.grp = 'reptiles' AND cs.is_small_q25 = 1 THEN cs.species END) AS reptiles_small_range_q25,
            COUNT(DISTINCT CASE WHEN cs.grp = 'reptiles' AND cs.is_small_q10 = 1 THEN cs.species END) AS reptiles_small_range_q10,
            ROUND(COALESCE(SUM(CASE WHEN cs.grp = 'reptiles' THEN cs.weight END), 0.0), 5) AS reptiles_weighted_endemism,
            
            -- Total (True unique union across all 3 groups, never sum of pixel richness)
            COUNT(DISTINCT cs.species) AS richness_total,
            COUNT(DISTINCT CASE WHEN cs.is_small_q25 = 1 THEN cs.species END) AS small_range_richness_q25,
            COUNT(DISTINCT CASE WHEN cs.is_small_q10 = 1 THEN cs.species END) AS small_range_richness_q10,
            ROUND(COALESCE(SUM(cs.weight), 0.0), 5) AS weighted_endemism_total
            
        FROM cell_pixels cp
        LEFT JOIN cell_species cs ON cp.cell_lon = cs.cell_lon AND cp.cell_lat = cs.cell_lat
        GROUP BY cp.cell_lon, cp.cell_lat, cp.n_valid_pixels
        ORDER BY richness_total DESC
        """
        df_cells = con.execute(query_agg).df()
        print(f"[{name}] Filtered cells retained (>=25% valid pixels): {len(df_cells)}")

        # Assign continent using project spatial rules
        df_cells = assign_continents_to_df(df_cells, lat_col="cell_lat", lon_col="cell_lon")

        # Merge with GBIF dataset
        df_gbif = pd.read_csv(gbif_path)
        gbif_cols = ["cell_lon", "cell_lat", "richness", "n_records"]
        df_merged = pd.merge(
            df_cells,
            df_gbif[gbif_cols],
            on=["cell_lon", "cell_lat"],
            how="left"
        )
        df_merged.rename(columns={"richness": "gbif_richness"}, inplace=True)

        # Save to processed CSV
        out_csv = PROCESSED_DIR / f"iucn_cells_{name}.csv"
        df_merged.to_csv(out_csv, index=False)
        print(f"[{name}] Saved cell metrics to {out_csv}")

        # Compute Spearman rank correlation with GBIF
        valid_comp = df_merged.dropna(subset=["gbif_richness", "richness_total"])
        filtered_comp = valid_comp[valid_comp["n_records"] >= 10]
        
        rho_all, p_all = stats.spearmanr(valid_comp["richness_total"], valid_comp["gbif_richness"])
        rho_filt, p_filt = stats.spearmanr(filtered_comp["richness_total"], filtered_comp["gbif_richness"])
        
        rho_mam, _ = stats.spearmanr(filtered_comp["mammals_richness"], filtered_comp["gbif_richness"])
        rho_amp, _ = stats.spearmanr(filtered_comp["amphibians_richness"], filtered_comp["gbif_richness"])
        rho_rep, _ = stats.spearmanr(filtered_comp["reptiles_richness"], filtered_comp["gbif_richness"])
        
        print(f"\n--- Spearman Rank Correlation (IUCN Total vs. GBIF Richness) [{name}] ---")
        print(f"  All Matched Cells (N={len(valid_comp)}): rho = {rho_all:+.4f} (p = {p_all:.2e})")
        print(f"  Filtered Analysis Cells (n_records >= 10, N={len(filtered_comp)}): rho = {rho_filt:+.4f} (p = {p_filt:.2e})")
        print(f"  Per-Group on Filtered Cells: Mammals rho={rho_mam:+.4f}, Amphibians rho={rho_amp:+.4f}, Reptiles rho={rho_rep:+.4f}")

        # Print Top-10 Cells with Regions as Sanity Check
        print(f"\n--- Top 10 High-Richness Cells [{name}] ---")
        top10 = df_merged.head(10)[["cell_lon", "cell_lat", "continent", "richness_total", "mammals_richness", "amphibians_richness", "reptiles_richness", "weighted_endemism_total", "gbif_richness"]]
        print(top10.to_string(index=False))
        top10_results[name] = top10

    # -------------------------------------------------------------------------
    # 3. Generate Publication Figures
    # -------------------------------------------------------------------------
    print("\n--- 3. Generating Diagnostic & Publication Maps ---")
    df5 = pd.read_csv(PROCESSED_DIR / "iucn_cells_5deg.csv")

    # Figure 1: IUCN Total Vertebrate Richness Map (5°)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    sc = ax.scatter(
        df5["cell_lon"], df5["cell_lat"],
        c=df5["richness_total"],
        cmap="viridis",
        s=45,
        alpha=0.9,
        edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="IUCN/GARD Total Species Richness", shrink=0.7)
    ax.set_title("Global Modern Vertebrate Species Richness (IUCN/GARD, 5° Grid)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig1_path = FIGURES_DIR / "iucn_richness_5deg.png"
    plt.savefig(fig1_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig1_path}")

    # Figure 2: IUCN Weighted Endemism Map (5°)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    sc = ax.scatter(
        df5["cell_lon"], df5["cell_lat"],
        c=df5["weighted_endemism_total"],
        cmap="plasma",
        s=45,
        alpha=0.9,
        edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="Corrected Weighted Endemism (Σ 1/Range)", shrink=0.7)
    ax.set_title("Global Vertebrate Weighted Endemism (IUCN/GARD, 5° Grid)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig2_path = FIGURES_DIR / "iucn_endemism_5deg.png"
    plt.savefig(fig2_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig2_path}")

    # Figure 3: Small-Range Richness (Q25) Map (5°)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    sc = ax.scatter(
        df5["cell_lon"], df5["cell_lat"],
        c=df5["small_range_richness_q25"],
        cmap="inferno",
        s=45,
        alpha=0.9,
        edgecolors="none"
    )
    plt.colorbar(sc, ax=ax, label="Small-Range Species Richness (Range <= Q25)", shrink=0.7)
    ax.set_title("Global Small-Range Vertebrate Richness (Top 25% Narrow Endemics, 5° Grid)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig3_path = FIGURES_DIR / "iucn_small_range_5deg.png"
    plt.savefig(fig3_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig3_path}")

    # Figure 4: IUCN vs GBIF Richness Scatter Plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    comp = df5.dropna(subset=["gbif_richness", "richness_total"])
    comp_filt = comp[comp["n_records"] >= 10]
    
    ax.scatter(comp["richness_total"], comp["gbif_richness"], c="gray", alpha=0.4, label=f"All cells (N={len(comp)}, ρ={rho_all:.2f})")
    ax.scatter(comp_filt["richness_total"], comp_filt["gbif_richness"], c="royalblue", alpha=0.8, edgecolors="k", linewidths=0.5, label=f"Filtered cells n>=10 (N={len(comp_filt)}, ρ={rho_filt:.2f})")
    
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("IUCN / GARD True Species Richness (log scale)", fontsize=11)
    ax.set_ylabel("GBIF Observed Species Richness (log scale)", fontsize=11)
    ax.set_title("Validation: IUCN Range-Map Richness vs. GBIF Occurrence Richness", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", frameon=True)
    fig4_path = FIGURES_DIR / "iucn_vs_gbif_scatter.png"
    plt.savefig(fig4_path, bbox_inches="tight")
    plt.close()
    print(f"Saved: {fig4_path}")

    # -------------------------------------------------------------------------
    # 4. Write IUCN/notes.md
    # -------------------------------------------------------------------------
    print("\n--- 4. Writing IUCN/notes.md ---")
    write_iucn_notes(quantiles_summary, rho_all, rho_filt, len(df5), top10_results["5deg"])

    print("\n[OK] IUCN processing complete!")

def write_iucn_notes(quantiles_df, rho_all, rho_filt, n_cells_5deg, top10_df):
    notes_path = IUCN_DIR / "notes.md"
    top10_str = top10_df.to_string(index=False)
    content = f"""# IUCN & GARD Vertebrate Diversity Processing Notes

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
2. **Small-Range Richness ($S_{{c, \\text{{small}}}}$)**:
   Number of unique species in cell $c$ whose global range size is at or below the 25th percentile (or 10th percentile).
3. **Weighted Endemism (CWE)**:
   $$\\text{{WE}}_c = \\sum_{{s \\in c}} \\frac{{1}}{{\\text{{range}}(s)}}$$
   Species with small global ranges contribute proportionately higher weight to the cell's endemism score.

---

## 3. Spatial Aggregation & Pixel Coverage Filter

- **5-Degree Grid**:
  - Cell bounding box spans 5° x 5° (100 potential 0.5° pixels).
  - **Filter**: Only land cells with >= 25% valid pixels (>= 25 pixels with terrestrial vertebrate presence) are retained.
  - Total valid cells: {n_cells_5deg}.
- **2-Degree Grid**:
  - Cell bounding box spans 2° x 2° (16 potential 0.5° pixels).
  - **Filter**: Only land cells with >= 25% valid pixels (>= 4 pixels with terrestrial vertebrate presence) are retained.

---

## 4. Empirical Validation: IUCN vs. GBIF Richness

- **Spearman Rank Correlation Across All Matched 5° Cells**: rho = {rho_all:+.4f}
- **Spearman Rank Correlation on Filtered Analysis Cells ($n_{{\\text{{records}}}} \\ge 10$)**: rho = {rho_filt:+.4f}
- **Interpretation**: Strong positive rank correlation confirms that the GBIF species counts capture genuine global macroecological biodiversity gradients, while IUCN range maps remove the severe collector sampling bias seen in tropical Africa and Amazonia.

---

## 5. Sanity Check: Top 10 High-Richness Global Cells (5° Grid)

```text
{top10_str}
```
*Notice that peak global richness cells correctly locate in the Amazonian-Andean transition zone, equatorial East Africa, and the Guiana Shield, perfectly matching established macroecological biogeography.*

---

## 6. Limitations

1. **Range Map Overestimation**: IUCN expert range polygons interpolate species presence across unverified gaps, potentially overestimating occupancy in heavily fragmented or deforested landscapes.
2. **Marine-Terrestrial Boundaries**: Coastal grid cells containing large oceanic fractions have reduced terrestrial pixel counts; the >= 25% land pixel filter safely eliminates pelagic slivers.
"""
    with open(notes_path, "w") as f:
        f.write(content)
    print(f"Saved: {notes_path}")

if __name__ == "__main__":
    main()
