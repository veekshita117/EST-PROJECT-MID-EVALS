# Machine Learning Evaluation Framework: Palaeoclimate Stability & Modern Biodiversity

This directory contains the complete, self-contained machine learning extension for evaluating whether Quaternary palaeoclimate stability metrics improve global predictions of modern vertebrate species richness beyond sampling effort, geographic latitude, and contemporary topography.

---

## 1. Quick Reproduction Guide

All scripts run from the project root directory (`.`) using Python 3.12+.

### Fast Verification Run (~3 minutes)
Runs both PaleoClim configurations (5° base, 2° sensitivity) with 1 repeat of spatial CV and accelerated tuning:
```bash
python3 src/ml/run_all.py --fast
python3 src/ml/compare_configs.py
python3 src/ml/make_report.py
```

### Full Production Run (~15–20 minutes)
Runs both PaleoClim configurations with full 3-repeat shifted spatial block CV and complete permutation importance:
```bash
python3 src/ml/run_all.py
python3 src/ml/compare_configs.py
python3 src/ml/make_report.py
```

### Running Individual Stages / Configurations
You can execute individual pipeline stages for the `paleoclim` source and a resolution (`base` [5°] or `2deg` [2°]). WorldClim is no longer used for ML runs; it is kept only for the PaleoClim vs WorldClim agreement check on the stability metrics:

```bash
# 1. Core spatial block cross-validation (nested tuning, M0..M3 feature sets)
python3 src/ml/run_core_cv.py --source paleoclim --resolution base --fast

# 2. Leave-One-Continent-Out (LOCO) generalization & spatial Moran's I diagnostics
python3 src/ml/run_loco.py --source paleoclim --resolution base --fast
python3 src/ml/run_residuals.py --source paleoclim --resolution base --fast

# 3. Model interpretation (permutation importance, grouped importance, PDP/ICE)
python3 src/ml/run_interpret.py --source paleoclim --resolution base --fast

# 4. Buffered spatial CV (1,000 km exclusion buffer) vs 20° GroupKFold
python3 src/ml/run_buffered_cv_comparison.py --source paleoclim --fast
```

---

## 2. Directory Structure

```text
ml/
├── config.yaml                    # Master experiment configuration & feature group mappings
├── requirements_ml.txt            # Pinned environment requirements
├── README_ML.md                   # This reproduction & architecture guide
├── REPORT_ML.md                   # Programmatically generated final scientific synthesis
├── VERDICT.md                     # Definitive answers to core scientific questions
├── ML_AUDIT.md                    # Initial data audit & baseline regression replication
├── src/
│   ├── config.py                  # YAML loader and configuration schema validator
│   ├── data.py                    # Dataset loading, filtering (n >= 10), feature sets M0..M3
│   ├── spatial.py                 # Spatial 20-degree block grid generator & coordinate utilities
│   ├── cv.py                      # Spatial GroupKFold and LOCO cross-validation iterators
│   ├── models.py                  # Estimator factories & hyperparameter tuning spaces
│   ├── metrics.py                 # Evaluation metrics (R2, RMSE, Spearman rho, Moran's I)
│   ├── run_core_cv.py             # Stage 3: Spatial CV across models & feature sets
│   ├── run_loco.py                # Stage 4 Part A: Leave-One-Continent-Out transfer
│   ├── run_residuals.py           # Stage 4 Part B: Out-of-fold spatial autocorrelation & maps
│   ├── run_interpret.py           # Stage 5: Permutation importance, grouped drops, PDP/ICE
│   ├── run_buffered_cv_comparison.py # Buffered spatial CV (1,000 km) vs 20° GroupKFold
│   ├── run_all.py                 # Stage 8: Pipeline orchestrator (PaleoClim 5° and 2°)
│   ├── compare_configs.py         # Stage 8: Cross-resolution synthesis
│   └── make_report.py             # Stage 9: Programmatic report generator from CSV outputs
├── tests/
│   └── test_foundation.py         # Pytest verification suite (8 foundation tests)
└── outputs/
    ├── paleoclim_base/            # PaleoClim 5-degree grid outputs (results/tables/ & results/figures/)
    ├── paleoclim_2deg/            # PaleoClim 2-degree grid outputs (results/tables/ & results/figures/)
    ├── COMPARISON/                # Cross-configuration forest plots & comparison tables
    └── logs/
        └── RESULTS_LOG.md         # Chronological stage execution log
```

---

## 3. Environment & Package Versions

Developed and validated under Linux (x86_64) using Python 3.12.3:
- `numpy==2.4.1`
- `scipy==1.18.0`
- `pandas==3.0.0`
- `scikit-learn==1.9.1`
- `matplotlib==3.10.8`
- `pyyaml==6.0.3`
- `statsmodels==0.15.0`
- `joblib==1.6.0`
- `esda==2.10.0`
- `libpysal==4.15.1`
- `pytest==9.2.0`

---

## 4. Runtime Estimates

| Configuration | Fast Mode (`--fast`) | Full Mode (3 repeats) | Cell Count ($N$) |
|:---|:---:|:---:|:---:|
| `paleoclim_base` (5°) | ~30s | ~3.5 min | 188 |
| `paleoclim_2deg` (2°) | ~50s | ~5.5 min | 264 |
| **Complete Pipeline (`run_all.py`)** | **~3 min** | **~18 min** | **—** |

---

## 5. Methodological Summary

1. **Nested Feature Sets**:
   - `M0`: Sampling effort only (`log_effort` = $\ln[1 + \text{records}]$).
   - `M1`: Effort + Geography (`cell_lat`, `abs_lat`) + Topography (`elevation_m`, `topo_relief_m`).
   - `M2a`: `M1` + primary composite stability index (`pc_composite_instability`).
   - `M2b`: `M1` + all 11 individual Quaternary stability metrics.
   - `M3a` / `M3b`: Stability metrics alone (without baseline controls).
2. **Spatial Validation**:
   - 20° $\times$ 20° spatial block partitioning (`SpatialBlockCV`) to eliminate geographic autocorrelation leakage.
   - 3-repeat origin-shifted grids (offsets $0^\circ, 7^\circ, 13^\circ$).
   - Nested hyperparameter tuning: inner 3-fold spatial GroupKFold inside training blocks only.
3. **Leave-One-Continent-Out (LOCO)**:
   - Evaluates intercontinental transferability across 6 continents (Africa, Eurasia, North America, South America, Oceania, Australia).
4. **Residual Spatial Diagnostics**:
   - Out-of-fold spatial Moran's $I$ computed on $k=8$ nearest-neighbor haversine distance weights with 999 permutations (dual verified via `esda`).
5. **Buffered Spatial Cross-Validation**:
   - 5 spatial folds with a 1,000 km haversine exclusion buffer around test cells, compared against the 20° GroupKFold CV.

> [!NOTE]
> **GBIF-Effort Caveat & IUCN Extension**: Original GBIF-based evaluations are heavily dominated by collector sampling effort (`log_effort`, explaining $>80\%$ of variance). The IUCN extension (`results/ml/iucn_*`) drops sampling effort completely and directly tests expert-verified vertebrate richness, small-range richness, and weighted endemism against Quaternary climate velocity and refugia across 5° and 2° grids.
