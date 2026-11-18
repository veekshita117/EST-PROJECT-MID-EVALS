# Cleanup Notes

Branch: `cleanup` (created from `main` at commit `245b138`; the working tree was clean, so no separate "backup" commit was needed — `main` is the backup).

Scope: remove analyses that are not needed to answer Problem 24 ("Are present biodiversity-rich regions disproportionately associated with long-term climatic stability?"), without changing the analysis logic of what remains.

---

## 1. Housekeeping (Prompt 1)

- **`__pycache__` / `*.pyc`**: none were tracked or present before the cleanup. (Caches created by test runs during the cleanup were deleted.)
- **Top-level `common/`, `integration_v3/`, `ml/`**: these folders do not exist at the repository root; the only copies are under `src/`, which contain real code. Nothing deleted.
- **`.gitignore`**: added `*.pyc` and `.ipynb_checkpoints/` (`__pycache__/` and `.DS_Store` were already present).
- **README vs `reports/` mismatch**: no mismatch found. `reports/` is **not** empty; it contains `final_research_report.md` and `supplementary_material.pdf`, as README states. No files were created.

---

## 2. Files removed

### Stochastic Frontier Analysis and Joint Multi-Taxa MixedLM (Prompt 2)
- `results/figures/fig5_stochastic_frontier.png`
- `results/figures/fig6_joint_taxa_effects.png`
- `results/figures/integration_v3/frontier_ceiling.png`
- `results/figures/integration_v3/joint_taxa_effects.png`
- `results/tables/integration_v3/frontier_results.csv`
- `results/tables/integration_v3/joint_taxa_model.csv`
- `results/tables/integration_v3/taxa_contrasts.csv`
- `results/tables/table5_stochastic_frontier.csv`
- `results/tables/table6_joint_taxa_model.csv`
- `results/tables/tableS4_taxa_contrasts.csv`
- `src/integration_v3/run_frontier_analysis.py`
- `src/integration_v3/run_joint_taxa_model.py`
- `tests/test_frontier_analysis.py`
- `tests/test_joint_taxa.py`

Kept (separate analyses): hotspot enrichment (`hotspot_enrichment*.csv`, `hotspot_spatial_null.png`), quantile regression, `taxa_comparison.*`.

### Unsupervised regimes (KMeans/GMM) and hotspot classifiers (Prompt 3)
- `results/ml/paleoclim_2deg/figures/hotspot_classification_map.png`
- `results/ml/paleoclim_2deg/figures/hotspot_confusion_matrix.png`
- `results/ml/paleoclim_2deg/figures/hotspot_decile_rate.png`
- `results/ml/paleoclim_2deg/figures/hotspot_roc_curves.png`
- `results/ml/paleoclim_2deg/figures/regime_k_selection.png`
- `results/ml/paleoclim_2deg/figures/regime_residual_boxplots.png`
- `results/ml/paleoclim_2deg/figures/regime_spatial_map.png`
- `results/ml/paleoclim_2deg/tables/hotspot_by_decile.csv`
- `results/ml/paleoclim_2deg/tables/hotspot_delta_auc.csv`
- `results/ml/paleoclim_2deg/tables/hotspot_metrics.csv`
- `results/ml/paleoclim_2deg/tables/regime_centroids.csv`
- `results/ml/paleoclim_2deg/tables/regime_delta_r2.csv`
- `results/ml/paleoclim_2deg/tables/regime_k_selection.csv`
- `results/ml/paleoclim_2deg/tables/regime_kruskal_pairwise.csv`
- `results/ml/paleoclim_2deg/tables/regime_regression_coefficients.csv`
- `results/ml/paleoclim_base/figures/hotspot_classification_map.png`
- `results/ml/paleoclim_base/figures/hotspot_confusion_matrix.png`
- `results/ml/paleoclim_base/figures/hotspot_decile_rate.png`
- `results/ml/paleoclim_base/figures/hotspot_roc_curves.png`
- `results/ml/paleoclim_base/figures/regime_k_selection.png`
- `results/ml/paleoclim_base/figures/regime_residual_boxplots.png`
- `results/ml/paleoclim_base/figures/regime_spatial_map.png`
- `results/ml/paleoclim_base/tables/hotspot_by_decile.csv`
- `results/ml/paleoclim_base/tables/hotspot_delta_auc.csv`
- `results/ml/paleoclim_base/tables/hotspot_metrics.csv`
- `results/ml/paleoclim_base/tables/regime_centroids.csv`
- `results/ml/paleoclim_base/tables/regime_delta_r2.csv`
- `results/ml/paleoclim_base/tables/regime_k_selection.csv`
- `results/ml/paleoclim_base/tables/regime_kruskal_pairwise.csv`
- `results/ml/paleoclim_base/tables/regime_regression_coefficients.csv`
- `src/ml/run_hotspots.py`
- `src/ml/run_regimes.py`

Code also removed: `get_classifier()` and the Logistic/RF/HGB classifier imports in `src/ml/models.py`, and the `logistic` branch of `get_param_grid()` (used only by the classifiers). `metrics.py` had no classifier-only functions, so it is unchanged. The hotspot **enrichment** analysis (odds ratios vs the spherical-rotation null) in `src/integration_v3` is untouched.

### Spatial Eigenvector Mapping (MEM) and ridge orthogonalisation (Prompt 4)
- `results/figures/fig2_orthogonalized_stability.png`
- `results/figures/fig3_spatial_mem.png`
- `results/ml/paleoclim_base/figures/mem_comparison.png`
- `results/ml/paleoclim_base/figures/orthogonalized_stability_comparison.png`
- `results/ml/paleoclim_base/tables/mem_comparison.csv`
- `results/ml/paleoclim_base/tables/orthogonalized_stability_correlations.csv`
- `results/ml/paleoclim_base/tables/orthogonalized_stability_evaluation.csv`
- `results/ml/paleoclim_base/tables/orthogonalized_stability_vif.csv`
- `results/tables/table4_orthogonalized_stability.csv`
- `results/tables/tableS3_mem_diagnostics.csv`
- `src/ml/mem.py`
- `src/ml/run_mem_analysis.py`
- `src/ml/run_orthogonalized_stability.py`
- `tests/ml/test_mem.py`
- `tests/ml/test_orthogonalize.py`

Code also removed: `StabilityOrthogonalizer` and `orthogonalize_stability_features()` from `src/ml/data.py` (used only by the deleted script/test). Buffered spatial CV, 20° GroupKFold CV and LOCO code are unchanged.

### WorldClim ML runs (Prompt 6)
- `results/ml/worldclim_base/` (40 files: tables + figures)
- `results/ml/worldclim_2deg/` (40 files: tables + figures)

Total: 141 tracked files removed.

---

## 3. Files edited

| File | Change |
| :--- | :--- |
| `src/ml/run_all.py` | PaleoClim only; stages are core CV, LOCO, residuals, interpretation (hotspot and regime stages removed). |
| `src/ml/compare_configs.py` | PaleoClim 5°/2° only; hotspot/regime columns and the PaleoClim-vs-WorldClim ML source-difference computation removed; verdict text updated; creates `results/ml/logs/` before appending. |
| `src/ml/make_report.py` | Hotspot, regime and source-difference sections removed; cross-resolution table added in their place (reads the existing `resolution_difference.csv`). |
| `src/ml/config.yaml` | Added `ml_runs` block documenting the grid (PaleoClim; 5° primary, 2° sensitivity; OLS/Ridge/RF/HGB); removed `hotspots` and `regimes` settings. WorldClim data paths kept (needed by the data loader and the agreement check). |
| `src/ml/models.py`, `src/ml/data.py` | Removed classifier and orthogonaliser code (see above). |
| `src/compile_experiment_results.py`, `data/experiment_results.csv` | Removed MEM, orthogonalised-stability, SFA and joint-taxa sections/rows (21 → 8 rows). |
| `results/ml/COMPARISON/comparison_table.csv` | Dropped WorldClim rows and hotspot/regime columns (rows/columns removed only; no values recomputed). |
| `results/ml/COMPARISON/resolution_difference.csv` | Dropped WorldClim rows (no values recomputed). |
| `tests/ml/test_stage9_verification.py` | Expects PaleoClim configs only and no hotspot/regime outputs. |
| `tests/ml/test_foundation.py` | Removed the unused `get_classifier` import; the 2° fixture now loads PaleoClim instead of WorldClim (WorldClim ML runs removed). |
| `README.md`, `run_all.sh`, `results/figures_and_tables.md`, `docs/readme_ml.md`, `docs/methods_justification.md`, `docs/audit_final.md`, `docs/report_ml_gbif_v1.md` | References to the removed analyses, files and test counts removed or updated. |
| `reports/final_research_report.md` | Sections, table rows, findings and artifact links for MEM, orthogonalisation, SFA and joint taxa removed. The endemism finding previously cited MixedLM slopes; it now cites the retained `correlations_5deg.csv` and `taxa_comparison.csv` values (amphibian endemism is **not** significant there, p = 0.10, so the "across all taxa" wording was dropped). |
| `src/reports/*.py` (manuscript generator) | Title/abstract/keywords/objectives, method §3.6–3.10, result §4.2–4.6, discussion, limitations and conclusions trimmed; Tables 4–6, S3, S4 and Figures 2, 3, 5, 6 removed; remaining figures renumbered (fig4 → Figure 2, fig7 → Figure 3; Table S5 → S3). Captions of Figures S2/S3 corrected (the images never showed MEM). Two references cited only by the SFA text removed (D'Agostino 1990, Kodde & Palm 1986). `calibrate_sections.py` re-synced to an identical copy. The generator was test-built successfully. |

---

## 4. Known issues / items for the authors

1. **Tests**: `pytest tests/` → **25 tests, 23 passed, 2 failed** (was 39 tests, 36 passed, 3 failed before cleanup). Both remaining failures existed before the cleanup and are unrelated to the deletions:
   - `test_comparison_outputs`: `results/ml/COMPARISON/VERDICT.md` was never committed.
   - `test_report_numbers_match_csvs`: looks for `ml/REPORT_ML.md`, a path that no longer exists after the repository restructure.
2. **Stale committed outputs**: re-running `compare_configs.py` on the committed `oof_predictions.csv` gives different R²/ΔR² values from the committed `comparison_table.csv`, so the table was not regenerated. Consequently the two COMPARISON figures (`forest_delta_r2_all_configs.png`, `heatmap_cross_configuration.png`) still show the old WorldClim rows; regenerate them once the outputs are re-run.
3. **`results/ml/COMPARISON/source_difference.csv`** (PaleoClim vs WorldClim ML ΔR²) is kept as a frozen record but can no longer be regenerated. The PaleoClim vs WorldClim **agreement check** on the stability metrics is kept at data level (`results/tables/integration_v2/table_dataset_agreement.csv`, `results/tables/integration/table_metric_agreement.csv`, `data/integration/source_concordance_v3.csv`, `results/figures/integration/agreement_*.png`).
4. **Test side-effects**: `tests/ml/test_foundation.py` writes VIF/correlation CSVs into `results/` each run (and overwrites the tracked `results/ml/paleoclim_2deg/tables/stability_vif_paleoclim_2deg.csv` with different values). This behaviour pre-dates the cleanup (it previously did the same for `worldclim_2deg`). Restore with `git checkout -- results/` after running tests.
5. **Not edited (binary or historical)**: `reports/supplementary_material.pdf` and `presentations/est_midpresentation.pptx` still contain the removed analyses; `docs/ml_logs/blockers*.md` and `docs/audit_interim.md` are historical logs and still mention `run_hotspots.py` / `worldclim_base`.
6. **Manuscript prose**: the manuscript generator text was trimmed, not rewritten; the authors should re-read the abstract, introduction (the "mean-regression / taxonomic fragmentation" motivation paragraph is still present) and discussion for flow. Some references were already uncited before the cleanup (Anselin 1988, Dray 2006, Griffith 2006, Jondrow 1982, Karger, Meyer 2018).

---

## 5. Superseded versions (Prompt 5) — awaiting approval, nothing deleted yet

| Item | Status | Reason |
| :--- | :--- | :--- |
| `src/integration_v2/run_phase6.py` | **Still needed** | Run by `run_all.sh` step 2 and README; produces `results/tables/integration_v2/` including the PaleoClim vs WorldClim agreement table. |
| `data/integration_v2/data_5deg.csv`, `data_2deg.csv` | **Still needed** | GBIF 188/264-cell baseline: ML inputs in `src/ml/config.yaml`; written by `src/gbif/process_gbif.py`; read by `src/iucn/process_iucn.py`. |
| `results/tables/integration_v2/*` (11 files) | **Still needed** | Outputs of `run_phase6.py` (kept in pipeline); `table_dataset_agreement.csv` is the agreement check. |
| `results/tables/integration/table_correlations.csv` | **Still needed** | Read by `tests/test_reproduce_mid_eval.py`. |
| `results/tables/integration/table_integrated_cells.csv` | **Still needed** | Read by `src/dem/download_dem.py` (188-cell GBIF baseline). |
| `results/tables/integration/table_metric_agreement.csv` | **Still needed** | PaleoClim vs WorldClim agreement statistics. |
| `results/tables/integration/table_quartiles.csv` | Safe to delete | Only read by `notebooks/integration.ipynb` (mid-eval). |
| `results/figures/integration/agreement_composite_index.png`, `agreement_precip_change.png`, `int_dataset_agreement.png` | **Still needed** | Agreement-check figures. |
| `results/figures/integration/int_scatter.png`, `int_quartiles.png`, `int_hotspots.png` | Safe to delete | Mid-eval notebook outputs; not read by any script/test. |
| `docs/notes/gbif_v1.md`, `gbif_v2.md`, `paleoclim_v1.md`, `paleoclim_v2.md`, `worldclim_v1.md`, `worldclim_v2.md` | Safe to delete | Not referenced by any script, test or README. |
| `docs/integration/plan_v2.md`, `plan_v3.md`, `results_v1.md`, `results_v2.md` | Safe to delete | Not referenced by any script, test or README. |
