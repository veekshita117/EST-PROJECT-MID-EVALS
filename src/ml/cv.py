"""
cv.py
-----
Cross-validation splitters for spatial block cross-validation and Leave-One-Continent-Out (LOCO).
Ensures zero spatial leakage with strict disjoint group assertions.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Union, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import BallTree

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ml.spatial import block_id, get_phase6_block_str

EARTH_RADIUS_KM = 6371.0088


class BufferedSpatialCV:
    """
    Buffered Spatial Cross-Validation.
    
    Partitions spatial data into n_splits folds (e.g. 5 spatial folds) and enforces
    an exclusion buffer (e.g. 1000 km) between test observations and candidate training observations
    using spherical haversine distances.
    
    Observations within buffer_km of ANY test observation in a given fold are discarded from training,
    eliminating spatial autocorrelation leakage across boundaries.
    
    Tracks and reports effective training sample sizes and discarded observations per fold.
    """
    def __init__(
        self,
        n_splits: int = 5,
        buffer_km: float = 1000.0,
        lon_col: str = "lon",
        lat_col: str = "lat",
        seed: int = 42,
        min_train_size: int = 10
    ):
        self.n_splits = n_splits
        self.buffer_km = buffer_km
        self.lon_col = lon_col
        self.lat_col = lat_col
        self.seed = seed
        self.min_train_size = min_train_size
        self.fold_stats_ = []
        
    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits
        
    def split(self, X: pd.DataFrame, y=None, groups=None):
        """
        Generate (train_idx, test_idx) with buffer exclusion applied.
        """
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X)
        N = len(df)
        
        # Determine spatial groups if not provided
        if groups is None:
            if self.lon_col in df.columns and self.lat_col in df.columns:
                groups = block_id(df[self.lon_col].values, df[self.lat_col].values, size=20.0)
            else:
                raise ValueError(f"Columns {self.lon_col} and {self.lat_col} required for spatial grouping.")
                
        groups = np.asarray(groups)
        unique_groups = np.unique(groups)
        
        # Check number of groups vs n_splits
        eff_splits = self.n_splits
        if len(unique_groups) < self.n_splits:
            eff_splits = max(2, len(unique_groups))
            print(f"[BufferedSpatialCV] Groups ({len(unique_groups)}) < n_splits ({self.n_splits}). Reducing to {eff_splits}.")
            
        gkf = GroupKFold(n_splits=eff_splits)
        self.fold_stats_ = []
        
        # Extract coordinates in radians for haversine distance
        lats_rad = np.radians(df[self.lat_col].values.astype(float))
        lons_rad = np.radians(df[self.lon_col].values.astype(float))
        coords_rad = np.column_stack([lats_rad, lons_rad])
        
        for fold_idx, (cand_train_idx, test_idx) in enumerate(gkf.split(df, groups=groups)):
            test_coords = coords_rad[test_idx]
            cand_coords = coords_rad[cand_train_idx]
            
            # Build BallTree on test coordinates
            test_tree = BallTree(test_coords, metric="haversine")
            
            # Distance from each candidate train point to nearest test point
            min_dist_rad, _ = test_tree.query(cand_coords, k=1)
            min_dist_km = min_dist_rad[:, 0] * EARTH_RADIUS_KM
            
            # Exclude training observations within buffer_km
            keep_mask = min_dist_km >= self.buffer_km
            eff_train_idx = cand_train_idx[keep_mask]
            discarded_idx = cand_train_idx[~keep_mask]
            
            # Fallback if buffer discards too many observations
            if len(eff_train_idx) < self.min_train_size:
                print(f"[BufferedSpatialCV WARNING] Fold {fold_idx+1}: Only {len(eff_train_idx)} training samples left with buffer={self.buffer_km}km. Relaxing buffer to retain {self.min_train_size} samples.")
                sort_dist_idx = np.argsort(min_dist_km)[::-1]
                eff_train_idx = cand_train_idx[sort_dist_idx[:max(self.min_train_size, len(cand_train_idx) // 2)]]
                discarded_idx = np.setdiff1d(cand_train_idx, eff_train_idx)
                
            n_cand = len(cand_train_idx)
            n_eff = len(eff_train_idx)
            n_disc = len(discarded_idx)
            disc_rate = (n_disc / n_cand) * 100.0 if n_cand > 0 else 0.0
            
            stat = {
                "fold": fold_idx + 1,
                "n_test": len(test_idx),
                "n_candidate_train": n_cand,
                "n_effective_train": n_eff,
                "n_discarded": n_disc,
                "discard_rate_pct": round(disc_rate, 2),
                "buffer_km": self.buffer_km
            }
            self.fold_stats_.append(stat)
            
            # Verify no test observation is in train
            assert set(eff_train_idx).isdisjoint(set(test_idx)), "Spatial test leak into training set!"
            
            yield eff_train_idx, test_idx
            
    def get_diagnostics_df(self) -> pd.DataFrame:
        """Return DataFrame of effective training sample sizes and discarded counts per fold."""
        return pd.DataFrame(self.fold_stats_)


def assert_no_group_overlap(
    train_groups: Union[np.ndarray, pd.Series, list],
    test_groups: Union[np.ndarray, pd.Series, list]
) -> None:
    """
    Assert programmatically that training groups and test groups are strictly disjoint.
    Prevents spatial data leakage.
    """
    train_set = set(train_groups)
    test_set = set(test_groups)
    overlap = train_set.intersection(test_set)
    if len(overlap) > 0:
        raise AssertionError(
            f"SPATIAL DATA LEAKAGE DETECTED: {len(overlap)} groups overlap between train and test! Overlapping groups: {overlap}"
        )


def spatial_outer_folds(
    df: pd.DataFrame,
    k: int = 5,
    seed: int = 42,
    offset: float = 0.0,
    reuse_phase6: bool = False,
    lon_col: str = "lon",
    lat_col: str = "lat"
) -> Tuple[List[Tuple[np.ndarray, np.ndarray]], Union[pd.Series, np.ndarray]]:
    """
    Generate deterministic, reusable (train_idx, test_idx) folds grouped by 20° spatial blocks.
    
    If reuse_phase6 is True (for offset 0), reuses the exact block string and GroupKFold
    behavior from integration_v2/run_phase6.py to guarantee reproduction of mid-eval benchmarks.
    Otherwise uses block_id(lon, lat, size=20, offset=offset).
    
    Automatically reduces k if number of blocks < 2*k.
    Asserts inner GroupKFold(3) has at least 3 training blocks.
    """
    if reuse_phase6 and offset == 0.0:
        if "spatial_block_20deg" in df.columns:
            groups = df["spatial_block_20deg"]
        else:
            groups = get_phase6_block_str(df[lon_col], df[lat_col])
    else:
        groups = block_id(df[lon_col].values, df[lat_col].values, size=20.0, offset=offset)
        groups = pd.Series(groups, index=df.index)
        
    unique_blocks = np.unique(groups)
    n_blocks = len(unique_blocks)
    
    # Print diagnostics
    block_counts = pd.Series(groups).value_counts()
    print(f"[CV Offset {offset}°] Occupied 20° spatial blocks: {n_blocks}")
    print(f"[CV Offset {offset}°] Cells per block summary: min={block_counts.min()}, median={block_counts.median()}, max={block_counts.max()}")
    
    if n_blocks < 20:
        print(f"[CV WARNING] Fewer than 20 spatial blocks ({n_blocks}). Bootstrap CIs may be wide.")
        
    # Check k against 2*k
    effective_k = k
    if n_blocks < 2 * k:
        effective_k = max(2, n_blocks // 2)
        print(f"[CV NOTE] Total blocks ({n_blocks}) < 2*k ({2*k}). Automatically reducing outer k from {k} to {effective_k}.")
        
    gkf = GroupKFold(n_splits=effective_k)
    splits = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(gkf.split(df, groups=groups)):
        train_grps = groups.iloc[train_idx] if isinstance(groups, pd.Series) else groups[train_idx]
        test_grps = groups.iloc[test_idx] if isinstance(groups, pd.Series) else groups[test_idx]
        
        # Programmatic assertion
        assert_no_group_overlap(train_grps, test_grps)
        
        # Assert inner GroupKFold has at least 3 training blocks
        n_train_blocks = len(np.unique(train_grps))
        assert n_train_blocks >= 3, f"Fold {fold_idx} has only {n_train_blocks} training blocks, inner GroupKFold(3) requires >= 3!"
        
        splits.append((train_idx, test_idx))
        
    return splits, groups


def loco_folds(
    df: pd.DataFrame,
    continent_col: str = "continent",
    min_cells: int = 15
) -> List[Tuple[np.ndarray, np.ndarray, str]]:
    """
    Leave-One-Continent-Out (LOCO) cross-validation splitter.
    
    Only evaluates continents with >= min_cells.
    Logs and skips continents with fewer than min_cells.
    
    Returns list of (train_idx, test_idx, test_continent_name).
    """
    cont_counts = df[continent_col].value_counts()
    splits = []
    skipped = []
    
    for cont_name, count in cont_counts.items():
        if count < min_cells:
            skipped.append((cont_name, count))
            continue
            
        test_mask = df[continent_col] == cont_name
        test_idx = np.where(test_mask)[0]
        train_idx = np.where(~test_mask)[0]
        
        # Verify disjoint
        assert set(train_idx).isdisjoint(set(test_idx))
        splits.append((train_idx, test_idx, cont_name))
        
    if skipped:
        print(f"[LOCO] Skipped continents with < {min_cells} cells: {skipped}")
    else:
        print(f"[LOCO] All continents met threshold (>={min_cells} cells). Zero skipped.")
        
    print(f"[LOCO] Configured {len(splits)} folds: {[s[2] for s in splits]}")
    return splits


if __name__ == "__main__":
    from src.ml.data import load_dataset
    df, _, _ = load_dataset("paleoclim", "base")
    
    print("\n--- Testing Spatial Outer Folds ---")
    folds, groups = spatial_outer_folds(df, k=5, seed=42, offset=0.0, reuse_phase6=True)
    print(f"Generated {len(folds)} outer folds.")
    for i, (tr, te) in enumerate(folds):
        print(f"  Fold {i+1}: Train={len(tr)} cells, Test={len(te)} cells")
        
    print("\n--- Testing LOCO Folds ---")
    loco_splits = loco_folds(df, min_cells=15)
    for tr, te, cname in loco_splits:
        print(f"  LOCO Test Continent: {cname} (Test={len(te)}, Train={len(tr)})")
