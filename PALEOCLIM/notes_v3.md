# PALEOCLIM Notes v3: Climate Velocity & Richer Stability Metrics

This document formalizes the methodology, definitions, mathematical units, and empirical distributions for Phase 8 palaeoclimate stability metrics.

---

## 1. Predictor Hierarchy & Pre-Registration Summary

In accordance with `integration_v3/PLAN.md`:
- **PRIMARY PREDICTOR**: `log10_velocity_temp` (log10 of LGM-to-present temperature climate-change velocity).
- **SECONDARY PREDICTORS**: All other metrics (anomaly, precipitation velocity, refugial area fraction, PCA composite, seasonality changes).
- **Multiple Testing**: FDR control (Benjamini-Hochberg) is to be applied across the secondary metric family.

---

## 2. Metric Formulations & Units

| Metric Name | Formula / Definition | Raw Units | Ecological Role |
|:---|:---|:---:|:---|
| `log10_velocity_temp` | $\log_{10}\left( \text{Median}\left( \frac{|\Delta T| / 21000}{\|\nabla T\|} \right) \right)$ | $\log_{10}(\text{km/yr})$ | **Primary**: Migration distance required to track thermal niche |
| `refugial_area_fraction` | Fraction of pixels with velocity $\le Q_{25}$ (9.64 m/yr) | Dimensionless [0, 1] | Microclimatic persistence and buffering capacity |
| `temp_anomaly` | $|\text{BIO1}_{\text{pres}} - \text{BIO1}_{\text{LGM}}|$ | °C | Gross thermal magnitude change |
| `log10_velocity_precip` | $\log_{10}\left( \text{Median}\left( \frac{|\Delta \ln(P+1)| / 21000}{\|\nabla \ln(P+1)\|} \right) \right)$ | $\log_{10}(\text{km/yr})$ | Moisture shift tracking velocity |
| `precip_rel_change` | $|\ln(P_{\text{LGM}}+1) - \ln(P_{\text{pres}}+1)|$ | Dimensionless | Proportional precipitation change |
| `temp_sd` | Temporal sample SD across Present, Holocene, LGM | °C | Tri-temporal thermal instability |
| `precip_sd` | Temporal sample SD across Present, Holocene, LGM | mm | Tri-temporal moisture instability |
| `bio4_change` | $|\text{BIO4}_{\text{pres}} - \text{BIO4}_{\text{LGM}}|$ | SD * 100 | Thermal seasonality shift |
| `bio15_change` | $|\text{BIO15}_{\text{pres}} - \text{BIO15}_{\text{LGM}}|$ | CV (%) | Precipitation seasonality shift |
| `pca_composite` | PC1 of $z(\text{anomaly}), z(\log_{10} V_{\text{temp}}), z(\Delta P)$ | Dimensionless | Co-varying multidimensional macroclimatic instability |

---

## 3. Global 5° Summary Statistics (1043 Valid Land Cells)

- **Temperature Velocity ($V_{\text{temp}}$)**:
  - Global Pixel $Q_{25}$ Threshold: 0.009639 km/yr (9.64 m/yr)
  - Cell Median: 0.020614 km/yr
  - $\log_{10} V_{\text{temp}}$ Range: [-3.08, 1.06], Median = -1.69
- **Refugial Area Fraction**:
  - Median: 0.1672, Max = 0.9875
- **PCA Composite (PC1)**:
  - Explained Variance: 70.3%
  - Loadings: Anomaly = 0.619, Velocity = 0.569, Precip = 0.541
- **Scale Sensitivity**:
  - Spearman $\rho$ between 10' and 20' velocity across 5° cells: **+0.9686**

---

## 4. Cross-Source Consensus (PaleoClim vs. WorldClim)

```text
                metric                         description  spearman_rho   p_value
   log10_velocity_temp PRIMARY: Log10 Temperature Velocity        0.9661  0.00e+00
refugial_area_fraction     Refugial Area Fraction (<= Q25)        0.9466  0.00e+00
          temp_anomaly  Temperature Anomaly (|Pres - LGM|)        0.9334  0.00e+00
 log10_velocity_precip        Log10 Precipitation Velocity        0.9018 1.59e-276
     precip_rel_change       Precipitation Relative Change        0.9204 2.57e-309
               temp_sd         Tri-Temporal Temperature SD        0.9261  0.00e+00
             precip_sd       Tri-Temporal Precipitation SD        0.8706 3.77e-234
           bio4_change      Temperature Seasonality Change        0.8006 1.24e-169
          bio15_change    Precipitation Seasonality Change        0.8370 4.27e-199
         pca_composite       PCA Composite Stability (PC1)        0.9547  0.00e+00
```

---

## 5. Critical Ecological & Methodological Limitations

1. **GCM Reconstruction Uncertainty**: Paleoclimate simulations represent GCM ensemble averages (CHELSA / CCSM4); regional precipitation trends in arid regions carry high model divergence.
2. **Scale Dependence of Spatial Gradient**: Spatial slope magnitude depends on grid grain (~18.5 km at 10 arc-minutes). True microtopographic buffering (gorges, ravines, poleward slopes) occurs at sub-kilometer scales.
3. **No Continuous Temporal Trajectory**: Velocity assumes a linear monotonic trajectory over 21,000 years, neglecting millennial-scale Heinrich events and Younger Dryas climate reversals.
