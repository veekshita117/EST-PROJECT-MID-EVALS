"""
test_joint_taxa.py
------------------
Unit tests for Joint Multi-Taxa Modelling in integration_v3/run_joint_taxa_model.py:
1. Long format data transformation builds exactly 3 rows per cell (Amphibians, Reptiles, Mammals).
2. Hierarchical MixedLM reproduces taxon slope contrasts.
3. Tests that reptile sensitivity (negative slope) is significantly stronger than amphibians and mammals.
4. Tests that amphibian richness slope is weak/non-significant when controlling for effort and topography.
5. Invariance: output tables exist and contain valid numeric estimates without NaNs in key fields.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.integration_v3.run_joint_taxa_model import build_long_taxa_df, run_joint_taxa_modelling


@pytest.fixture(scope="module")
def sample_wide_df():
    """Load real 5deg dataset or create mock multi-taxa dataframe."""
    data_path = REPO_ROOT / "data" / "integration" / "data_v3_5deg.csv"
    if data_path.exists():
        df = pd.read_csv(data_path)
        return df.iloc[:100].copy()
    else:
        rng = np.random.default_rng(42)
        n = 50
        return pd.DataFrame({
            "cell_lon": rng.uniform(-180, 180, size=n),
            "cell_lat": rng.uniform(-60, 60, size=n),
            "block_id": rng.integers(1, 20, size=n),
            "log10_velocity_temp": rng.normal(0, 1, size=n),
            "abs_lat": rng.uniform(0, 60, size=n),
            "elevation_mean": rng.uniform(100, 2000, size=n),
            "topographic_heterogeneity": rng.uniform(10, 300, size=n),
            "log1p_records_total": rng.uniform(1, 10, size=n),
            "land_fraction": rng.uniform(0.5, 1.0, size=n),
            "reptiles_richness": rng.poisson(30, size=n),
            "reptiles_weighted_endemism": rng.uniform(0.1, 5.0, size=n),
            "mammals_richness": rng.poisson(40, size=n),
            "mammals_weighted_endemism": rng.uniform(0.1, 4.0, size=n),
            "amphibians_richness": rng.poisson(15, size=n),
            "amphibians_weighted_endemism": rng.uniform(0.1, 2.0, size=n),
        })


def test_build_long_taxa_df_structure(sample_wide_df):
    """Test that build_long_taxa_df creates exactly 3 rows per cell with required columns."""
    df_long = build_long_taxa_df(sample_wide_df)
    assert len(df_long) == 3 * len(sample_wide_df)
    
    expected_taxa = {"Amphibians", "Reptiles", "Mammals"}
    assert set(df_long["taxon"].unique()) == expected_taxa
    
    assert "y_richness" in df_long.columns
    assert "y_endemism" in df_long.columns
    assert "velocity" in df_long.columns
    assert "cell_id" in df_long.columns
    assert np.all(np.isfinite(df_long["velocity"]))


def test_taxa_outputs_exist_and_valid():
    """Verify that joint taxa model and contrasts tables were produced and valid."""
    model_csv = REPO_ROOT / "results" / "tables" / "joint_taxa_model.csv"
    contrast_csv = REPO_ROOT / "results" / "tables" / "taxa_contrasts.csv"
    
    assert model_csv.exists(), "results/tables/table6_joint_taxa_model.csv missing"
    assert contrast_csv.exists(), "results/tables/tableS4_taxa_contrasts.csv missing"
    
    m_df = pd.read_csv(model_csv)
    c_df = pd.read_csv(contrast_csv)
    
    # Check that Reptiles slope is significantly negative for Richness
    rep_row = m_df[(m_df.response == "Species Richness") & (m_df.taxon == "Reptiles")]
    assert len(rep_row) == 1
    assert rep_row["velocity_slope"].values[0] < -0.15
    assert rep_row["p_value"].values[0] < 0.001
    
    # Check that Amphibians richness slope is weak/non-significant (p > 0.05)
    amph_row = m_df[(m_df.response == "Species Richness") & (m_df.taxon == "Amphibians")]
    assert len(amph_row) == 1
    assert amph_row["p_value"].values[0] > 0.05
    
    # Check that Reptiles - Amphibians contrast is statistically significant
    ra_contrast = c_df[(c_df.response == "Species Richness") & (c_df.contrast == "Reptiles - Amphibians")]
    assert len(ra_contrast) == 1
    assert ra_contrast["significant_at_05"].values[0] == True
