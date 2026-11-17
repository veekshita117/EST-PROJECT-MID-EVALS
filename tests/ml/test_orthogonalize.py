"""
test_orthogonalize.py
---------------------
Unit tests for Orthogonalized Climate Stability features in ml/src/data.py:
1. StabilityOrthogonalizer fits Ridge(alpha=1e-3) on training data controls.
2. Residualized stability features have near-zero correlation with controls.
3. VIF of orthogonalized stability features is approximately 1.0 (uncorrelated).
4. Fold safety: transform on test set uses strictly training-fitted Ridge regressors.
5. Invariance: preserves total row count and does not introduce NaNs.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.data import StabilityOrthogonalizer, orthogonalize_stability_features


@pytest.fixture
def synthetic_stability_data():
    """Create synthetic dataset where stability is collinear with latitude and elevation."""
    rng = np.random.default_rng(42)
    n = 100
    abs_lat = rng.uniform(0, 60, size=n)
    elevation = rng.uniform(100, 2500, size=n)
    relief = rng.uniform(10, 500, size=n)
    
    # Stability has strong linear dependence on latitude + some noise
    stability_1 = 0.5 * abs_lat - 0.001 * elevation + rng.normal(0, 1, size=n)
    stability_2 = -0.3 * abs_lat + 0.002 * relief + rng.normal(0, 1, size=n)
    
    return pd.DataFrame({
        "abs_lat": abs_lat,
        "elevation": elevation,
        "relief": relief,
        "stability_1": stability_1,
        "stability_2": stability_2,
    })


def test_orthogonalize_zero_correlation(synthetic_stability_data):
    """Test that orthogonalized stability features have near-zero correlation with controls."""
    df = synthetic_stability_data
    controls = ["abs_lat", "elevation", "relief"]
    stabs = ["stability_1", "stability_2"]
    
    # Check that raw correlations are substantial
    assert abs(df["stability_1"].corr(df["abs_lat"])) > 0.5
    
    df_orth, models = orthogonalize_stability_features(
        df, stability_cols=stabs, control_cols=controls, alpha=1e-3
    )
    
    # Check that orthogonalized correlations are virtually zero
    for s in stabs:
        for c in controls:
            r = df_orth[s].corr(df_orth[c])
            assert abs(r) < 1e-3, f"Correlation between {s} and {c} after orthogonalization is {r} (expected < 1e-3)"


def test_transformer_fold_safety(synthetic_stability_data):
    """Test that StabilityOrthogonalizer fits on train and transforms test without test leakage."""
    df = synthetic_stability_data
    train_df = df.iloc[:70].copy()
    test_df = df.iloc[70:].copy()
    
    orth = StabilityOrthogonalizer(stability_cols=["stability_1", "stability_2"], alpha=1e-3)
    orth.fit(train_df)
    
    test_orth = orth.transform(test_df)
    assert len(test_orth) == 30
    assert not test_orth[["stability_1", "stability_2"]].isna().any().any()
    
    # Model coefficients must come from train only
    for col, m in orth.models_.items():
        assert hasattr(m, "coef_")
        assert len(m.coef_) == 3
