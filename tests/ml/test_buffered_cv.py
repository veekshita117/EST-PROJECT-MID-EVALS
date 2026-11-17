"""
test_buffered_cv.py
-------------------
Unit tests for BufferedSpatialCV in ml/src/cv.py:
1. Generates expected number of spatial folds (e.g. 5 folds).
2. Guarantees zero spatial proximity leakage: min distance between test and train is >= buffer_km.
3. Accounting identity: n_candidate_train == n_effective_train + n_discarded.
4. Fold diagnostics: reports fold number, effective sample size, discarded counts, and discard rate.
5. Invariance: test sets across folds partition the input dataset without duplicate tests.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.cv import BufferedSpatialCV, EARTH_RADIUS_KM


@pytest.fixture
def synthetic_spatial_df():
    """Create synthetic dataset distributed across known geographical coordinates."""
    rng = np.random.default_rng(42)
    n = 100
    # Cluster points in 5 distinct geographical regions
    centers = [
        (-100.0, 40.0), # North America
        (-60.0, -15.0), # South America
        (20.0, 10.0),   # Africa
        (80.0, 30.0),   # Asia
        (135.0, -25.0)  # Australia
    ]
    lons = []
    lats = []
    for c_lon, c_lat in centers:
        lons.extend(c_lon + rng.normal(0, 3, size=20))
        lats.extend(c_lat + rng.normal(0, 3, size=20))
        
    df = pd.DataFrame({
        "lon": lons,
        "lat": lats,
        "y": rng.normal(3.0, 1.0, size=n)
    })
    return df


def test_buffered_spatial_cv_distance_exclusion(synthetic_spatial_df):
    """Verify that every training point is at least buffer_km away from test points."""
    df = synthetic_spatial_df
    buffer_km = 800.0
    cv = BufferedSpatialCV(n_splits=5, buffer_km=buffer_km, seed=42)
    
    folds = list(cv.split(df))
    assert len(folds) == 5, f"Expected 5 folds, got {len(folds)}"
    
    all_test_indices = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(folds):
        assert len(train_idx) > 0, f"Fold {fold_idx} has empty training set"
        assert len(test_idx) > 0, f"Fold {fold_idx} has empty test set"
        assert set(train_idx).isdisjoint(set(test_idx)), f"Fold {fold_idx} has overlapping train and test!"
        all_test_indices.extend(test_idx)
        
        # Verify haversine distances between train and test
        tr_lats = np.radians(df.iloc[train_idx]["lat"].values)
        tr_lons = np.radians(df.iloc[train_idx]["lon"].values)
        te_lats = np.radians(df.iloc[test_idx]["lat"].values)
        te_lons = np.radians(df.iloc[test_idx]["lon"].values)
        
        # Check minimum pairwise distance between train and test
        for i in range(len(train_idx)):
            dlat = te_lats - tr_lats[i]
            dlon = te_lons - tr_lons[i]
            a = np.sin(dlat / 2.0)**2 + np.cos(tr_lats[i]) * np.cos(te_lats) * np.sin(dlon / 2.0)**2
            c = 2.0 * np.arcsin(np.clip(np.sqrt(a), 0, 1))
            min_dist = np.min(c) * EARTH_RADIUS_KM
            assert min_dist >= buffer_km - 1.0, (
                f"Fold {fold_idx}: Train sample {train_idx[i]} is within buffer ({min_dist:.1f} km < {buffer_km} km)"
            )
            
    # Check that each test point was evaluated
    assert len(np.unique(all_test_indices)) == len(df)


def test_buffered_spatial_cv_diagnostics(synthetic_spatial_df):
    """Verify that diagnostics reporting captures effective train size and discarded counts."""
    df = synthetic_spatial_df
    cv = BufferedSpatialCV(n_splits=5, buffer_km=500.0, seed=42)
    _ = list(cv.split(df))
    
    diag_df = cv.get_diagnostics_df()
    assert len(diag_df) == 5
    assert "n_effective_train" in diag_df.columns
    assert "n_discarded" in diag_df.columns
    assert "discard_rate_pct" in diag_df.columns
    
    for _, row in diag_df.iterrows():
        assert row["n_candidate_train"] == row["n_effective_train"] + row["n_discarded"]
        assert row["n_effective_train"] > 0
