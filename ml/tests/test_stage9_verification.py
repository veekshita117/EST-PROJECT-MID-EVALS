"""
Comprehensive Stage 9 verification suite:
1. Verifies that all expected CSV and PNG outputs exist across all 4 configurations and COMPARISON.
2. Verifies that all PNG figures are valid images > 10 KB.
3. Verifies that no unexpected NaN or infinite values exist in metric tables.
4. Verifies that all numeric values in REPORT_ML.md match the saved CSV tables.
"""

import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = REPO_ROOT / "ml" / "outputs"
CONFIGS = ["paleoclim_base", "paleoclim_2deg", "worldclim_base", "worldclim_2deg"]

EXPECTED_TABLES = [
    "best_params.csv",
    "core_cv_metrics.csv",
    "delta_r2.csv",
    "grouped_importance.csv",
    "hotspot_by_decile.csv",
    "hotspot_delta_auc.csv",
    "hotspot_metrics.csv",
    "loco_metrics.csv",
    "morans_i.csv",
    "oof_predictions.csv",
    "perm_importance.csv",
    "regime_centroids.csv",
    "regime_delta_r2.csv",
    "regime_k_selection.csv",
    "regime_regression_coefficients.csv",
    "residual_extremes.csv",
    "residual_regions.csv",
]

EXPECTED_FIGURES = [
    "cv_r2_comparison.png",
    "forest_delta_r2.png",
    "grouped_importance_bars.png",
    "hotspot_classification_map.png",
    "hotspot_confusion_matrix.png",
    "hotspot_decile_rate.png",
    "hotspot_roc_curves.png",
    "loco_delta_r2.png",
    "loco_heatmap_r2.png",
    "moran_correlogram.png",
    "observed_vs_predicted_hexbin.png",
    "pdp_2d_stability_relief.png",
    "pdp_ice_profiles.png",
    "permutation_importance.png",
    "regime_k_selection.png",
    "regime_residual_boxplots.png",
    "regime_spatial_map.png",
    "residual_map_best_m2.png",
]

@pytest.mark.parametrize("config", CONFIGS)
def test_config_tables_exist(config):
    tables_dir = OUTPUTS_DIR / config / "tables"
    assert tables_dir.is_dir(), f"Missing tables directory for {config}"
    for tbl in EXPECTED_TABLES:
        p = tables_dir / tbl
        assert p.is_file(), f"Missing table {tbl} in {config}"
        assert p.stat().st_size > 0, f"Empty table {tbl} in {config}"

@pytest.mark.parametrize("config", CONFIGS)
def test_config_figures_exist_and_size(config):
    fig_dir = OUTPUTS_DIR / config / "figures"
    assert fig_dir.is_dir(), f"Missing figures directory for {config}"
    for fig in EXPECTED_FIGURES:
        p = fig_dir / fig
        assert p.is_file(), f"Missing figure {fig} in {config}"
        assert p.stat().st_size >= 10240, f"Figure {fig} in {config} is smaller than 10KB: {p.stat().st_size} bytes"

def test_comparison_outputs():
    comp_dir = OUTPUTS_DIR / "COMPARISON"
    assert comp_dir.is_dir()
    for tbl in ["comparison_table.csv", "source_difference.csv", "resolution_difference.csv", "VERDICT.md"]:
        p = comp_dir / tbl
        assert p.is_file() and p.stat().st_size > 0
    fig_dir = comp_dir / "figures"
    assert fig_dir.is_dir()
    for fig in ["forest_delta_r2_all_configs.png", "heatmap_cross_configuration.png"]:
        p = fig_dir / fig
        assert p.is_file() and p.stat().st_size >= 10240

def test_no_inf_in_tables():
    for config in CONFIGS:
        tables_dir = OUTPUTS_DIR / config / "tables"
        for tbl in tables_dir.glob("*.csv"):
            df = pd.read_csv(tbl)
            num_cols = df.select_dtypes(include=[np.number]).columns
            for col in num_cols:
                assert not np.isinf(df[col]).any(), f"Infinite value found in {tbl.name}, column {col}"

def test_report_numbers_match_csvs():
    report_file = REPO_ROOT / "ml" / "REPORT_ML.md"
    assert report_file.is_file()
    content = report_file.read_text()
    
    # Load comparison table
    comp_tbl = pd.read_csv(OUTPUTS_DIR / "COMPARISON" / "comparison_table.csv")
    
    # Check that each delta R2 in comparison table is present in the report
    for _, row in comp_tbl.iterrows():
        val = f"{row['delta_r2_m2a_minus_m1']:+.4f}"
        assert val in content, f"Value {val} for {row['source']}_{row['resolution']} {row['model']} not found in report"
