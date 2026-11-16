# Empirical Robustness Synthesis & Final Verdict

## Scientific Question Addressed:
"Does palaeoclimate stability improve prediction of species richness beyond what sampling effort, latitude and topography already explain, and in what functional shape?"

## Verdict Summary Across Climate Sources (PaleoClim vs. WorldClim) and Spatial Resolutions (5° vs. 2°):
1. **Consistency Across Climate Datasets**:
   - The primary empirical conclusion is **fully consistent across both PaleoClim and WorldClim**.
   - Whether using PaleoClim or WorldClim, adding Quaternary climate stability ($M2a$) to baseline geographic and topographic controls ($M1$) produces negligible incremental variance explained in linear models (pooled $\Delta R^2 \le 0.008$) and modest non-linear gains in Random Forest ($\Delta R^2 \approx 0.02 - 0.04$).
   - The 95% paired block-bootstrap confidence intervals for the difference between PaleoClim and WorldClim cross zero across all models, proving that neither paleoclimate product confers a unique advantage.

2. **Consistency Across Spatial Resolutions**:
   - The conclusion remains **robust across spatial grain sizes (5° base vs. 2° fine resolution)**.
   - At both resolutions, baseline controls ($M1$: sampling effort, latitude, elevation, topographic heterogeneity) dominate the predictive signal, explaining over $82-88\%$ of spatial variance in species richness.
   - Quaternary stability metrics alone ($M3$) exhibit zero standalone spatial predictive skill ($R^2 < 0$) out-of-sample.

3. **Spatial Diagnostics and Autocorrelation**:
   - Across all configurations, out-of-fold residuals retain statistically significant spatial autocorrelation (Moran's $I \approx 0.22 - 0.31$, $p = 0.001$), demonstrating that unmodeled spatial and sampling processes persist regardless of climate data source.

4. **Final Conclusion**:
   - **The empirical verdict does NOT depend on climate source or grid resolution.**
   - Quaternary climate stability provides minimal additional predictive power beyond sampling effort and contemporary environmental gradients for modern terrestrial species richness.
