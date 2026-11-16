"""
spatial.py
----------
Spatial utilities for spatial block partitioning and continent assignment.
Implements block_id(lon, lat, size=20, offset=0) and continent assignment.
"""

import sys
from pathlib import Path
from typing import Union, Optional
import numpy as np
import pandas as pd

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.continent_rules import assign_continent


def block_id(
    lon: Union[float, np.ndarray, pd.Series],
    lat: Union[float, np.ndarray, pd.Series],
    size: float = 20.0,
    offset: float = 0.0
) -> Union[int, np.ndarray, pd.Series]:
    """
    Compute integer spatial block ID using the formula:
    floor((lon + 180 - offset) / size) and floor((lat + 90 - offset) / size)
    combined into one integer id: lat_idx * 1000 + lon_idx.
    """
    is_scalar = np.isscalar(lon)
    lon_arr = np.atleast_1d(lon).astype(float)
    lat_arr = np.atleast_1d(lat).astype(float)
    
    # Floor division by block size after offset
    lon_idx = np.floor((lon_arr + 180.0 - offset) / size).astype(int)
    lat_idx = np.floor((lat_arr + 90.0 - offset) / size).astype(int)
    
    # Deterministic integer combination
    block_ids = lat_idx * 1000 + lon_idx
    
    if is_scalar:
        return int(block_ids[0])
    if isinstance(lon, pd.Series):
        return pd.Series(block_ids, index=lon.index, name="spatial_block")
    return block_ids


def get_phase6_block_str(
    lon: Union[np.ndarray, pd.Series],
    lat: Union[np.ndarray, pd.Series]
) -> pd.Series:
    """
    Exact block formula from integration_v2/run_phase6.py:
    floor(lat / 20.0) * 20.0 and floor(lon / 20.0) * 20.0 as string.
    """
    b_lat = np.floor(np.asarray(lat) / 20.0) * 20.0
    b_lon = np.floor(np.asarray(lon) / 20.0) * 20.0
    s_block = b_lat.astype(int).astype(str) + "_" + b_lon.astype(int).astype(str)
    if isinstance(lat, pd.Series):
        return pd.Series(s_block, index=lat.index)
    return pd.Series(s_block)


def assign_continents_to_df(
    df: pd.DataFrame,
    lon_col: str = "lon",
    lat_col: str = "lat",
    repo_root: Optional[Path] = None
) -> pd.DataFrame:
    """
    Assign continent names to grid cells in df:
    1. Use existing continent column if present and complete.
    2. Try geopandas with a locally available Natural Earth file (no downloads).
    3. Fallback to documented coarse lon/lat rules in ml/src/continent_rules.py.
    
    Prints cells per continent and asserts no cell is unassigned.
    """
    df = df.copy()
    if repo_root is None:
        repo_root = REPO_ROOT
        
    if "continent" in df.columns and df["continent"].notna().all():
        print("Using existing continent column from DataFrame.")
    else:
        assigned = False
        # Try local Natural Earth via geopandas if available
        try:
            import geopandas as gpd
            # Look for locally cached naturalearth shapefile without downloading
            candidate_shapes = list((Path(sys.prefix) / "lib").glob("**/naturalearth_lowres.shp"))
            if candidate_shapes:
                world = gpd.read_file(candidate_shapes[0])
                pts_geom = gpd.points_from_xy(df[lon_col], df[lat_col], crs="EPSG:4326")
                pts_gdf = gpd.GeoDataFrame(df, geometry=pts_geom, crs="EPSG:4326")
                joined = gpd.sjoin(pts_gdf, world[["continent", "geometry"]], how="left", predicate="intersects")
                # Deduplicate if point hits border between two polygons
                joined = joined[~joined.index.duplicated(keep="first")]
                if joined["continent"].notna().sum() >= len(df) * 0.8:
                    df["continent"] = joined["continent"].values
                    # Fill any coastal / border gaps using deterministic rules
                    if df["continent"].isna().any():
                        missing_mask = df["continent"].isna()
                        df.loc[missing_mask, "continent"] = [
                            assign_continent(r[lat_col], r[lon_col]) 
                            for _, r in df[missing_mask].iterrows()
                        ]
                    assigned = True
                    print("Assigned continents using local Natural Earth vector layer (with gap filling).")
        except Exception:
            pass
            
        if not assigned:
            # Check precomputed table
            cont_table = repo_root / "tables" / "continent_assignment.csv"
            if cont_table.exists():
                lookup = pd.read_csv(cont_table)
                merged = df.merge(
                    lookup[["cell_lat", "cell_lon", "continent"]].drop_duplicates(),
                    left_on=[lat_col, lon_col],
                    right_on=["cell_lat", "cell_lon"],
                    how="left"
                )
                if merged["continent"].notna().all():
                    df["continent"] = merged["continent"].values
                    assigned = True
                    print(f"Assigned continents using {cont_table}.")

        if not assigned:
            # Deterministic rule-based fallback
            print("Assigning continents using ml/src/continent_rules.py rules.")
            df["continent"] = [assign_continent(r[lat_col], r[lon_col]) for _, r in df.iterrows()]

    # Print summary & assert no cell is unassigned
    print("\nCells per continent:")
    cont_counts = df["continent"].value_counts()
    print(cont_counts)
    
    unassigned = df["continent"].isna().sum()
    assert unassigned == 0, f"Found {unassigned} unassigned cells in continent assignment!"
    print("SUCCESS: 0 unassigned cells. Assertion passed.\n")
    
    return df


if __name__ == "__main__":
    # Test block_id
    sample_lons = np.array([-157.5, 0.0, 122.5, 177.5])
    sample_lats = np.array([-52.5, 0.0, 22.5, 72.5])
    bids = block_id(sample_lons, sample_lats, size=20, offset=0)
    print("Sample coordinates:", list(zip(sample_lons, sample_lats)))
    print("Computed Block IDs:", bids)
    
    # Test continent assignment on sample
    sample_df = pd.DataFrame({"lon": sample_lons, "lat": sample_lats})
    sample_df = assign_continents_to_df(sample_df)
    print(sample_df)
