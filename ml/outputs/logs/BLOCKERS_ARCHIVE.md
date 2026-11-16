# Blockers Archive (Historical Failures)

This document archives historical tracebacks and resolved errors encountered during previous pipeline runs.

---

### [RESOLVED] Config: worldclim (base) - Stage: hotspots
```
Traceback (most recent call last):
  File "pandas/_libs/index.pyx", line 197, in pandas._libs.index.IndexEngine.get_loc
KeyError: 'pc_composite_instability'
During handling of the above exception, another exception occurred:
KeyError: 'pc_composite_instability'
```
*Resolution*: Corrected dynamic selection of stability column in `ml/src/run_hotspots.py`: uses `wc_composite_instability` for WorldClim and `pc_composite_instability` for PaleoClim.

---

### [RESOLVED] Config: worldclim (2deg) - Stage: hotspots
```
Traceback (most recent call last):
  File "pandas/_libs/index.pyx", line 197, in pandas._libs.index.IndexEngine.get_loc
KeyError: 'pc_composite_instability'
During handling of the above exception, another exception occurred:
KeyError: 'pc_composite_instability'
```
*Resolution*: Resolved alongside `worldclim (base)` by dynamically prefixing `wc_` / `pc_`.

---

### [RESOLVED] Config: worldclim (base) - Stage: hotspots (Singular Matrix in Clustered Logit)
```
Traceback (most recent call last):
  File "statsmodels/base/model.py", line 631, in fit
  File "numpy/linalg/_linalg.py", line 145, in _raise_linalgerror_singular
numpy.linalg.LinAlgError: Singular matrix
```
*Resolution*: Removed duplicate collinear latitude (`lat` alongside `abs_lat`) from formula; replaced unstable clustered logistic regression with robust unadjusted odds ratio with Wilson score confidence intervals and documented note on observer effort.
