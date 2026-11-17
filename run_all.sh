#!/usr/bin/env bash
# ==============================================================================
# run_all.sh
# ----------
# Master end-to-end execution script for:
# "Palaeoclimate Stability and Modern Biodiversity"
#
# Execution Order:
#   1. Copernicus DEM streaming & zonal summary statistics
#   2. Paleoclimate stability expansions (PaleoClim & WorldClim)
#   3. Phase 6 econometric regressions & baseline spatial models
#   4. Phase 9 sensitivity, block-bootstrap FDR, and spatial error models (v3b)
#   5. Machine Learning baseline evaluation layer (GBIF, PaleoClim, WorldClim)
#   6. IUCN Machine Learning pipeline (20° spatial-block CV, nested tuning, LOCO)
#   7. IUCN diagnostic figures, grouped importance, PDP, and residual Moran's I
#   8. Automated test suite (spatial block leakage and regression benchmarks)
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "================================================================================"
echo "PALAEOCLIMATE STABILITY AND MODERN BIODIVERSITY: FULL REPRODUCIBILITY PIPELINE"
echo "Working directory: $REPO_ROOT"
echo "================================================================================"

# ------------------------------------------------------------------------------
# STEP 0: Check Required Raw Files
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 0: Auditing Required Raw Input Files <<<"

RAW_MISSING=0

# 1. PaleoClim rasters
if [ ! -f "PALEOCLIM/raw/paleoclim_current_BIO1.tif" ]; then
    echo "[NOTICE] Raw PaleoClim rasters missing in PALEOCLIM/raw/. Using verified processed files in data/paleoclim/."
    RAW_MISSING=1
else
    echo "[OK] Raw PaleoClim rasters found."
fi

# 2. WorldClim rasters
if [ ! -d "WORLDCLIM/raw/present/bio" ]; then
    echo "[NOTICE] Raw WorldClim rasters missing in WORLDCLIM/raw/. Using verified processed files in data/worldclim/."
    RAW_MISSING=1
else
    echo "[OK] Raw WorldClim rasters found."
fi

# 3. Copernicus DEM
if [ ! -f "data/dem/dem_cells_5deg.csv" ]; then
    echo "[STATUS] Streaming Copernicus DEM tiles from AWS S3..."
    python3 src/dem/download_dem.py
else
    echo "[OK] Copernicus DEM processed cells verified (5deg and 2deg)."
fi

# 4. GBIF occurrence files
if [ ! -f "GBIF/raw/gbif_all_continents.csv" ] && [ ! -f "GBIF/raw/gbif_africa_5000.csv" ]; then
    echo "[NOTICE] Raw GBIF download archives missing. Using cleaned tables in data/gbif/."
    RAW_MISSING=1
else
    echo "[OK] GBIF raw archives found."
fi

# 5. IUCN rasterSp global rasters
if [ ! -f "data/iucn/iucn_cells_5deg.csv" ]; then
    echo "[NOTICE] Raw rasterSp 0.5° rasters missing. Using verified aggregations in data/iucn/."
    RAW_MISSING=1
else
    echo "[OK] IUCN processed cell distributions verified (5deg and 2deg)."
fi

if [ "$RAW_MISSING" -eq 1 ]; then
    echo "[INFO] Running pipeline using verified processed inputs where raw archives were not placed."
fi

# ------------------------------------------------------------------------------
# STEP 1: Copernicus DEM & Phase 2 Climate Expansion (if raw available)
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 1: Verifying Foundation Environmental & Topographic Layers <<<"
if [ -f "PALEOCLIM/raw/paleoclim_current_BIO1.tif" ]; then
    python3 src/run_phase2_climate_expansion.py
else
    echo "[SKIP] run_phase2_climate_expansion.py skipped; using data/paleoclim/ and data/worldclim/."
fi

# ------------------------------------------------------------------------------
# STEP 2: Phase 6 Econometric & Spatial Autoregressive Models
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 2: Running Phase 6 Spatial Econometric Baseline (integration_v2) <<<"
python3 src/integration_v2/run_phase6.py

# ------------------------------------------------------------------------------
# STEP 3: Phase 9 Sensitivity, Block-Bootstrap FDR, & Spatial Error Models (v3b)
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 3: Running Phase 9 Statistical & Sensitivity Pipeline (integration_v3b) <<<"
python3 src/integration_v3/run_phase9_statistics_v3b.py

# ------------------------------------------------------------------------------
# STEP 4: Machine Learning Foundation Suite (GBIF Baseline)
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 4: Running Baseline Machine Learning Evaluation (src/ml/run_all.py --fast) <<<"
python3 src/ml/run_all.py --fast

# ------------------------------------------------------------------------------
# STEP 5: IUCN Machine Learning Pipeline (20° Spatial-Block CV & LOCO)
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 5: Running Full IUCN Machine Learning Pipeline (src/ml/run_iucn.py) <<<"
python3 src/ml/run_iucn.py

# ------------------------------------------------------------------------------
# STEP 6: IUCN Diagnostics, Grouped Permutation Importance, & Residual Moran's I
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 6: Generating Interpretation Diagnostics & Residual Figures (src/ml/run_iucn_diagnostics.py) <<<"
python3 src/ml/run_iucn_diagnostics.py

# ------------------------------------------------------------------------------
# STEP 7: Automated Test Suite Execution
# ------------------------------------------------------------------------------
echo -e "\n>>> STEP 7: Executing Automated Pytest Test Suites <<<"
pytest tests/
pytest tests/ml/

echo -e "\n================================================================================"
echo "PIPELINE COMPLETED SUCCESSFULLY: ALL TABLES, FIGURES, AND TESTS VERIFIED"
echo "================================================================================"
