# Blockers and Dependency Issues Log

## Active Blockers

1. **`pyyaml` package missing in default python environment (`notebook_env`)**:
   - Status: Active / Awaiting confirmation.
   - Impact: Cannot `import yaml` in scripts unless `pyyaml` is installed via `pip install pyyaml` in `notebook_env` (or using `label_env` which has pyyaml, or using standard library JSON/fallback parser).
   - Binding Rule 4 reminder: *"Do not upgrade or reinstall existing packages. If you must pip install a required package, tell me first."*
   - Question to User: May we install `pyyaml` into the current environment (`/home/mokshitha/notebook_env`), or should we use a standard-library parser for YAML/JSON?

2. **`continent` column missing from processed tables (`data_5deg.csv` and `data_2deg.csv`)**:
   - Status: Identified in Stage 1 Audit.
   - Impact: Continent-level stratification/analysis will require deriving continent tags from the raw regional GBIF occurrence CSV files in `GBIF/raw/` or spatial polygon mapping before continent-stratified cross-validation.

### [FAILURE] Config: worldclim (base) - Stage: hotspots
```
Traceback (most recent call last):
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 3641, in get_loc
    return self._engine.get_loc(casted_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "pandas/_libs/index.pyx", line 168, in pandas._libs.index.IndexEngine.get_loc
  File "pandas/_libs/index.pyx", line 197, in pandas._libs.index.IndexEngine.get_loc
  File "pandas/_libs/hashtable_class_helper.pxi", line 7668, in pandas._libs.hashtable.PyObjectHashTable.get_item
  File "pandas/_libs/hashtable_class_helper.pxi", line 7676, in pandas._libs.hashtable.PyObjectHashTable.get_item
KeyError: 'pc_composite_instability'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 65, in run_pipeline_for_config
    stage_fn()
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 58, in <lambda>
    ("hotspots", lambda: run_hotspots(source=source, resolution=resolution, fast=fast)),
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_hotspots.py", line 312, in run_hotspots
    df["stab_decile"] = pd.qcut(df[primary_stab_col], q=10, labels=False, duplicates="drop")
                                ~~^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/frame.py", line 4378, in __getitem__
    indexer = self.columns.get_loc(key)
              ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 3648, in get_loc
    raise KeyError(key) from err
KeyError: 'pc_composite_instability'

```

### [FAILURE] Config: worldclim (2deg) - Stage: hotspots
```
Traceback (most recent call last):
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 3641, in get_loc
    return self._engine.get_loc(casted_key)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "pandas/_libs/index.pyx", line 168, in pandas._libs.index.IndexEngine.get_loc
  File "pandas/_libs/index.pyx", line 197, in pandas._libs.index.IndexEngine.get_loc
  File "pandas/_libs/hashtable_class_helper.pxi", line 7668, in pandas._libs.hashtable.PyObjectHashTable.get_item
  File "pandas/_libs/hashtable_class_helper.pxi", line 7676, in pandas._libs.hashtable.PyObjectHashTable.get_item
KeyError: 'pc_composite_instability'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 65, in run_pipeline_for_config
    stage_fn()
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 58, in <lambda>
    ("hotspots", lambda: run_hotspots(source=source, resolution=resolution, fast=fast)),
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_hotspots.py", line 312, in run_hotspots
    df["stab_decile"] = pd.qcut(df[primary_stab_col], q=10, labels=False, duplicates="drop")
                                ~~^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/frame.py", line 4378, in __getitem__
    indexer = self.columns.get_loc(key)
              ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/pandas/core/indexes/base.py", line 3648, in get_loc
    raise KeyError(key) from err
KeyError: 'pc_composite_instability'

```

### [FAILURE] Config: worldclim (base) - Stage: hotspots
```
Traceback (most recent call last):
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 65, in run_pipeline_for_config
    stage_fn()
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_all.py", line 58, in <lambda>
    ("hotspots", lambda: run_hotspots(source=source, resolution=resolution, fast=fast)),
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/EST-PROJECT-MID-EVALS/ml/src/run_hotspots.py", line 379, in run_hotspots
    logit_res = logit_mod.fit(cov_type="cluster", cov_kwds={"groups": sub_q["spatial_block_20deg"]}, disp=False)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/statsmodels/discrete/discrete_model.py", line 2845, in fit
    bnryfit = super().fit(
              ^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/statsmodels/discrete/discrete_model.py", line 268, in fit
    mlefit = super().fit(
             ^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/statsmodels/base/model.py", line 631, in fit
    Hinv = np.linalg.inv(retvals["Hessian"]) / nobs
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/numpy/linalg/_linalg.py", line 648, in inv
    ainv = _umath_linalg.inv(a, signature=signature)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/mokshitha/notebook_env/lib/python3.12/site-packages/numpy/linalg/_linalg.py", line 145, in _raise_linalgerror_singular
    raise LinAlgError("Singular matrix")
numpy.linalg.LinAlgError: Singular matrix

```
