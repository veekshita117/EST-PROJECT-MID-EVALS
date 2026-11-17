"""
test_block_leakage.py
---------------------
Unit tests verifying zero spatial block leakage and invariant integrity for IUCN ML pipeline:
1. Outer spatial folds have zero block overlap between train and test splits (5deg and 2deg).
2. Block offset shifts maintain zero spatial leakage.
3. Inner nested tuning folds have zero block overlap.
4. Leave-One-Continent-Out (LOCO) splits have zero continent leakage.
5. Effort features (log_n, n_records) are completely dropped from M1 and M2 for IUCN targets.
6. M1 (7 features) is a strict subset of M2 (11 features).
7. Targets are finite with zero NaNs across all complete cases.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ml.spatial import block_id
from src.ml.cv import spatial_outer_folds, assert_no_group_overlap, loco_folds
from src.ml.data import load_dataset


@pytest.fixture(scope="module")
def iucn_5deg_data():
    df, fg, fs = load_dataset(resolution="base", target="iucn_log_richness")
    return df, fg, fs


@pytest.fixture(scope="module")
def iucn_2deg_data():
    df, fg, fs = load_dataset(resolution="2deg", target="iucn_endemism")
    return df, fg, fs


def test_iucn_effort_dropped(iucn_5deg_data, iucn_2deg_data):
    """Verify that log_n and GBIF effort are completely dropped from IUCN feature sets."""
    for df, fg, fs in [iucn_5deg_data, iucn_2deg_data]:
        assert "log_n" not in fs["M1"], "log_n found in M1!"
        assert "log_effort" not in fs["M1"], "log_effort found in M1!"
        assert "n_records" not in fs["M1"], "n_records found in M1!"
        assert "log_n" not in fs["M2"], "log_n found in M2!"
        assert "log_effort" not in fs["M2"], "log_effort found in M2!"
        assert "n_records" not in fs["M2"], "n_records found in M2!"
        assert len(fg["effort"]) == 0, f"Effort group not empty: {fg['effort']}"


def test_iucn_feature_sets_exact_sizes(iucn_5deg_data, iucn_2deg_data):
    """Verify that M1 has exactly 7 features and M2 has exactly 11 features."""
    expected_m1 = {
        "abs_lat", "elevation_mean", "topographic_heterogeneity",
        "pc_temp_present", "pc_precip_present", "pc_bio4_present", "pc_bio15_present"
    }
    expected_m2_add = {
        "log10_velocity_temp", "refugial_area_fraction", "temp_anomaly", "precip_rel_change"
    }
    expected_m2 = expected_m1.union(expected_m2_add)

    for df, fg, fs in [iucn_5deg_data, iucn_2deg_data]:
        assert set(fs["M1"]) == expected_m1, f"M1 mismatch: {set(fs['M1']) ^ expected_m1}"
        assert set(fs["M2"]) == expected_m2, f"M2 mismatch: {set(fs['M2']) ^ expected_m2}"
        assert len(fs["M1"]) == 7
        assert len(fs["M2"]) == 11
        assert set(fs["M1"]).issubset(set(fs["M2"]))


def test_no_outer_block_leakage_5deg(iucn_5deg_data):
    """Verify zero spatial group overlap in outer 5-fold CV on 5deg IUCN data across offsets."""
    df, _, _ = iucn_5deg_data
    for offset in [0.0, 4.0, 7.0, 11.0, 13.0]:
        folds, groups = spatial_outer_folds(df, k=5, seed=42, offset=offset)
        for tr, te in folds:
            tr_grps = groups.iloc[tr]
            te_grps = groups.iloc[te]
            assert_no_group_overlap(tr_grps, te_grps)


def test_no_outer_block_leakage_2deg(iucn_2deg_data):
    """Verify zero spatial group overlap in outer 5-fold CV on 2deg IUCN data."""
    df, _, _ = iucn_2deg_data
    folds, groups = spatial_outer_folds(df, k=5, seed=42, offset=0.0)
    for tr, te in folds:
        tr_grps = groups.iloc[tr]
        te_grps = groups.iloc[te]
        assert_no_group_overlap(tr_grps, te_grps)


def test_no_inner_block_leakage_nested_tuning(iucn_5deg_data):
    """Verify that inner GroupKFold splits strictly partition blocks without leakage."""
    df, _, _ = iucn_5deg_data
    blocks = block_id(df["lon"].values, df["lat"].values, size=20.0, offset=0.0)
    blocks = pd.Series(blocks, index=df.index)
    
    outer_gkf = GroupKFold(n_splits=5)
    inner_gkf = GroupKFold(n_splits=3)
    
    for tr_outer, te_outer in outer_gkf.split(df, groups=blocks):
        df_tr = df.iloc[tr_outer]
        blocks_tr = blocks.iloc[tr_outer]
        
        for tr_inner, val_inner in inner_gkf.split(df_tr, groups=blocks_tr):
            inner_tr_grps = blocks_tr.iloc[tr_inner]
            inner_val_grps = blocks_tr.iloc[val_inner]
            assert_no_group_overlap(inner_tr_grps, inner_val_grps)


def test_loco_zero_continent_leakage(iucn_5deg_data, iucn_2deg_data):
    """Verify that Leave-One-Continent-Out splits strictly isolate each continent."""
    for df, _, _ in [iucn_5deg_data, iucn_2deg_data]:
        splits = loco_folds(df, continent_col="continent", min_cells=15)
        assert len(splits) == 6, f"Expected 6 evaluated continents, found {len(splits)}"
        
        all_evaluated = set()
        for tr, te, cont_name in splits:
            tr_continents = set(df.iloc[tr]["continent"].unique())
            te_continents = set(df.iloc[te]["continent"].unique())
            
            assert te_continents == {cont_name}
            assert cont_name not in tr_continents
            assert tr_continents.isdisjoint(te_continents)
            all_evaluated.add(cont_name)
            
        assert len(all_evaluated) == 6


def test_target_finite_and_clean_sample_counts(iucn_5deg_data, iucn_2deg_data):
    """Verify sample size and absence of NaNs/Infs in target."""
    df5, _, _ = iucn_5deg_data
    df2, _, _ = iucn_2deg_data
    
    assert len(df5) == 755
    assert len(df2) == 4395
    assert df5["y"].notna().all()
    assert np.isfinite(df5["y"]).all()
    assert df2["y"].notna().all()
    assert np.isfinite(df2["y"]).all()
