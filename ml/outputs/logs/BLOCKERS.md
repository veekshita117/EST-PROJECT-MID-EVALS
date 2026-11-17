# Blockers and Dependency Issues Log

## Active Blockers

*None. All previously identified blockers have been resolved.*

---

## Resolved Issues

1. **`pyyaml` package missing in default python environment (`notebook_env`)**:
   - Status: **RESOLVED**. Installed `pyyaml` (version 6.0.3) into `notebook_env`.

2. **`shap` package missing in default python environment (`notebook_env`)**:
   - Status: **RESOLVED**. Installed `shap` (version 0.54.1) into `notebook_env`. TreeExplainer verified operational on Random Forest and HistGradientBoosting.

3. **`continent` column mapping**:
   - Status: **RESOLVED**. Assigned via Natural Earth spatial join with deterministic gap filling in `ml/src/spatial.py`.

4. **`KeyError: pc_composite_instability` on WorldClim configs in `run_hotspots.py`**:
   - Status: **RESOLVED**. Dynamically parameterised prefix based on climate data source (`wc_` vs `pc_`). Historical traceback archived in `BLOCKERS_ARCHIVE.md`.

5. **`LinAlgError: Singular matrix` in `run_hotspots.py` logistic regression**:
   - Status: **RESOLVED**. Removed duplicate `lat` (using `abs_lat` only) and replaced unstable clustered logit with robust unadjusted odds ratios and documented effort caveat. Historical traceback archived in `BLOCKERS_ARCHIVE.md`.

6. **Collinear VIF Singularity ($10^{15}$) in `compute_vif_and_correlations`**:
   - Status: **RESOLVED**. Removed duplicate latitude (`abs_lat` used exclusively) and excluded composite metric when individual components are present in the design matrix. VIF calculations now complete with finite, stable values.

### [FAILURE] Config: paleoclim (base) - Stage: core_cv
```
Traceback (most recent call last):
  File "ml/src/run_all.py", line 65, in run_pipeline_for_config
    stage_fn()
  File "ml/src/run_all.py", line 54, in <lambda>
    ("core_cv", lambda: run_core_cv(source=source, resolution=resolution, fast=fast, n_repeats=repeats)),
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "ml/src/run_core_cv.py", line 451, in run_core_cv
    folds_rep0 = [folds_dict[(0, f)] for f in range(1, k_outer + 1)]
                  ^^^^^^^^^^
NameError: name 'folds_dict' is not defined

```

### [FAILURE] Config: paleoclim (base) - Stage: interpret
```
Traceback (most recent call last):
  File "notebook_env/lib/python3.12/site-packages/sklearn/utils/_indexing.py", line 411, in _get_column_indices
    return [column_names.index(col) for col in selected_columns]
            ^^^^^^^^^^^^^^^^^^^^^^^
ValueError: 'cell_lat' is not in list

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "ml/src/run_all.py", line 65, in run_pipeline_for_config
    stage_fn()
  File "ml/src/run_all.py", line 57, in <lambda>
    ("interpret", lambda: run_interpretation(source=source, resolution=resolution, fast=fast)),
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "ml/src/run_interpret.py", line 364, in run_interpretation
    pdp_fold = partial_dependence(
               ^^^^^^^^^^^^^^^^^^^
  File "notebook_env/lib/python3.12/site-packages/sklearn/utils/_param_validation.py", line 218, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "notebook_env/lib/python3.12/site-packages/sklearn/inspection/_partial_dependence.py", line 669, in partial_dependence
    _get_column_indices(X, features), dtype=np.intp, order="C"
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "notebook_env/lib/python3.12/site-packages/sklearn/utils/_indexing.py", line 415, in _get_column_indices
    raise ValueError(msg) from e
ValueError: Some column names are not columns of the dataframe: {'cell_lat'}

```
