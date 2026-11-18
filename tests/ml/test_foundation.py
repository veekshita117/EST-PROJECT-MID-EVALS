"""
test_foundation.py
------------------
Pytest suite verifying the core invariants of the ML foundation layer:
1. Feature sets are nested (M0 subset of M1 subset of M2).
2. M3 is disjoint from M1.
3. y equals log1p(richness).
4. No NaN or Inf in y.
5. All feature sets share identical row indices.
6. Train and test blocks never overlap in any fold (zero spatial leakage).
7. Fold construction is deterministic for the same seed.
8. block_id is consistent for known coordinates.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ml.config import get_validated_config
from src.ml.data import load_dataset
from src.ml.spatial import block_id, assign_continents_to_df
from src.ml.cv import spatial_outer_folds, loco_folds, assert_no_group_overlap
from src.ml.models import get_regressor, get_param_grid
from src.ml.metrics import calc_r2, calc_rmse, calc_spearman, block_bootstrap_ci


@pytest.fixture(scope="module")
def paleoclim_base_data():
    """Load and cache paleoclim base dataset."""
    df, fg, fs = load_dataset(source="paleoclim", resolution="base")
    return df, fg, fs


@pytest.fixture(scope="module")
def paleoclim_2deg_data():
    """Load and cache paleoclim 2deg dataset (WorldClim ML runs were removed)."""
    df, fg, fs = load_dataset(source="paleoclim", resolution="2deg")
    return df, fg, fs


def test_feature_sets_nested(paleoclim_base_data):
    """Verify that feature sets are nested: M0 subset of M1 subset of M2 (both M2a and M2b)."""
    _, _, fs = paleoclim_base_data
    
    m0_set = set(fs["M0"])
    m1_set = set(fs["M1"])
    m2a_set = set(fs["M2a"])
    m2b_set = set(fs["M2b"])
    
    # M0 is subset of M1
    assert m0_set.issubset(m1_set), f"M0 is not a subset of M1: {m0_set - m1_set}"
    assert len(m1_set) > len(m0_set)
    
    # M1 is subset of M2a and M2b
    assert m1_set.issubset(m2a_set), f"M1 is not a subset of M2a: {m1_set - m2a_set}"
    assert m1_set.issubset(m2b_set), f"M1 is not a subset of M2b: {m1_set - m2b_set}"
    assert len(m2a_set) > len(m1_set)
    assert len(m2b_set) > len(m2a_set)


def test_m3_disjoint_from_m1(paleoclim_base_data, paleoclim_2deg_data):
    """Verify that M3 (stability alone) is disjoint from M1 (effort + geography + topography)."""
    for df, _, fs in [paleoclim_base_data, paleoclim_2deg_data]:
        m1_set = set(fs["M1"])
        m3a_set = set(fs["M3a"])
        m3b_set = set(fs["M3b"])
        
        assert m3a_set.isdisjoint(m1_set), f"M3a shares features with M1: {m3a_set.intersection(m1_set)}"
        assert m3b_set.isdisjoint(m1_set), f"M3b shares features with M1: {m3b_set.intersection(m1_set)}"


def test_y_equals_log1p_richness(paleoclim_base_data, paleoclim_2deg_data):
    """Verify that y strictly equals np.log1p(richness)."""
    for df, _, _ in [paleoclim_base_data, paleoclim_2deg_data]:
        expected_y = np.log1p(df["richness"].values)
        np.testing.assert_allclose(df["y"].values, expected_y, rtol=1e-12, atol=1e-12)


def test_no_nan_in_y(paleoclim_base_data, paleoclim_2deg_data):
    """Verify that target y contains zero NaNs and zero infinite values."""
    for df, _, _ in [paleoclim_base_data, paleoclim_2deg_data]:
        assert df["y"].notna().all(), "Found NaN in target y!"
        assert np.isfinite(df["y"]).all(), "Found Inf in target y!"


def test_identical_row_indices_across_feature_sets(paleoclim_base_data):
    """Verify that all feature sets share identical row indices with zero row mismatch."""
    df, _, fs = paleoclim_base_data
    base_idx = df.index
    
    for fs_name in ["M0", "M1", "M2a", "M2b", "M2", "M3a", "M3b", "M3"]:
        sub_X = df[fs[fs_name]]
        assert len(sub_X) == len(df), f"Row count mismatch in {fs_name}"
        assert sub_X.index.equals(base_idx), f"Index mismatch in {fs_name}"
        assert sub_X.notna().all().all(), f"Found NaNs in feature set {fs_name}"


def test_no_train_test_group_overlap(paleoclim_base_data):
    """Verify zero spatial group overlap between training and test sets across all folds."""
    df, _, _ = paleoclim_base_data
    
    # Test for offset 0 (phase 6 benchmark)
    folds_0, grps_0 = spatial_outer_folds(df, k=5, seed=42, offset=0.0, reuse_phase6=True)
    for i, (tr, te) in enumerate(folds_0):
        assert_no_group_overlap(grps_0.iloc[tr], grps_0.iloc[te])
        
    # Test for non-zero offset
    folds_7, grps_7 = spatial_outer_folds(df, k=5, seed=42, offset=7.0, reuse_phase6=False)
    for i, (tr, te) in enumerate(folds_7):
        assert_no_group_overlap(grps_7.iloc[tr], grps_7.iloc[te])


def test_deterministic_fold_construction(paleoclim_base_data):
    """Verify that fold construction is completely deterministic for the same random seed."""
    df, _, _ = paleoclim_base_data
    
    folds_a, _ = spatial_outer_folds(df, k=5, seed=42, offset=4.0)
    folds_b, _ = spatial_outer_folds(df, k=5, seed=42, offset=4.0)
    
    assert len(folds_a) == len(folds_b)
    for (tr_a, te_a), (tr_b, te_b) in zip(folds_a, folds_b):
        np.testing.assert_array_equal(tr_a, tr_b)
        np.testing.assert_array_equal(te_a, te_b)


def test_block_id_consistent_known_coordinates():
    """Verify that block_id produces exact deterministic integers for known coordinate landmarks."""
    # (0, 0), size=20, offset=0: lon_idx=floor(180/20)=9, lat_idx=floor(90/20)=4 -> 4009
    assert block_id(0.0, 0.0, size=20.0, offset=0.0) == 4009
    
    # (10.0, 10.0), size=20, offset=0: lon_idx=floor(190/20)=9, lat_idx=floor(100/20)=5 -> 5009
    assert block_id(10.0, 10.0, size=20.0, offset=0.0) == 5009
    
    # Points inside same 20x20 box [0, 20) x [0, 20)
    # lat in [0, 20) -> lat+90 in [90, 110) -> lat_idx = 4 or 5
    # (5, 5) -> lon_idx=floor(185/20)=9, lat_idx=floor(95/20)=4 -> 4009
    # (15, 5) -> lon_idx=floor(195/20)=9, lat_idx=floor(95/20)=4 -> 4009
    assert block_id(5.0, 5.0, size=20.0, offset=0.0) == 4009
    assert block_id(15.0, 5.0, size=20.0, offset=0.0) == 4009
    
    # Across border (21.0, 5.0) -> lon_idx=floor(201/20)=10, lat_idx=4 -> 4010
    assert block_id(21.0, 5.0, size=20.0, offset=0.0) == 4010
    assert block_id(5.0, 5.0, size=20.0, offset=0.0) != block_id(21.0, 5.0, size=20.0, offset=0.0)
