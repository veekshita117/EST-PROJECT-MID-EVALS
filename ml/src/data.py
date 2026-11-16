"""
data.py
-------
Data loading, cleaning, standardization, and feature set definitions.
Implements standardized columns, common row masking, and saves correlation/VIF tables.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

from ml.src.config import get_repo_root, get_validated_config


def compute_vif_and_correlations(
    df: pd.DataFrame,
    stability_cols: List[str],
    source: str,
    resolution: str,
    repo_root: Path
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute Pearson/Spearman correlation matrix and Variance Inflation Factors (VIF)
    for palaeoclimate stability columns. Saves outputs to tables/ and ml/outputs/.
    """
    # 1. Correlation Matrix
    corr_matrix = df[stability_cols].corr(method="pearson")
    
    # 2. VIF Table
    X = sm.add_constant(df[stability_cols].dropna())
    vif_rows = []
    for i, col in enumerate(X.columns):
        if col == "const":
            continue
        try:
            val = float(variance_inflation_factor(X.values, i))
        except Exception:
            val = np.nan
        vif_rows.append({"feature": col, "VIF": val})
    vif_df = pd.DataFrame(vif_rows)
    
    # Save destinations
    tables_dir = repo_root / "tables"
    ml_tables_dir = repo_root / "ml" / "outputs" / f"{source}_{resolution}" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    
    corr_filename = f"stability_correlations_{source}_{resolution}.csv"
    vif_filename = f"stability_vif_{source}_{resolution}.csv"
    
    corr_matrix.to_csv(tables_dir / corr_filename)
    corr_matrix.to_csv(ml_tables_dir / corr_filename)
    vif_df.to_csv(tables_dir / vif_filename, index=False)
    vif_df.to_csv(ml_tables_dir / vif_filename, index=False)
    
    print(f"[{source}_{resolution}] Saved correlation matrix and VIF table to tables/ and {ml_tables_dir}")
    return corr_matrix, vif_df


def load_dataset(
    source: str = "paleoclim",
    resolution: str = "base",
    config_path: str = "ml/config.yaml"
) -> Tuple[pd.DataFrame, Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Load dataset for given source and resolution, apply standardized column names,
    apply common row mask, attach continent assignments, and return:
    - Cleaned DataFrame (df)
    - FEATURE_GROUPS dict
    - FEATURE_SETS dict (M0, M1, M2, M3, M2a, M2b, M3a, M3b)
    """
    repo_root = get_repo_root()
    cfg = get_validated_config(config_path)
    
    source = source.lower()
    resolution = resolution.lower()
    
    if source not in ["paleoclim", "worldclim"]:
        raise ValueError(f"Unknown source '{source}', must be 'paleoclim' or 'worldclim'")
    if resolution not in ["base", "2deg"]:
        raise ValueError(f"Unknown resolution '{resolution}', must be 'base' or '2deg'")
        
    rel_path = cfg["paths"][source][resolution]
    raw_df = pd.read_csv(repo_root / rel_path)
    n_initial = len(raw_df)
    
    cmap = cfg["column_map"]
    min_records = cfg.get("min_records", 10)
    
    # 1. Apply Filtering (Effort threshold >= min_records)
    effort_col = cmap["effort_raw"]
    effort_mask = raw_df[effort_col] >= min_records
    n_dropped_effort = int((~effort_mask).sum())
    df = raw_df[effort_mask].copy().reset_index(drop=True)
    
    print(f"[{source}_{resolution}] Initial rows: {n_initial}. Dropped {n_dropped_effort} rows with {effort_col} < {min_records}.")
    print(f"[{source}_{resolution}] Filtered rows retained: {len(df)}")
    
    # 2. Standardize Column Names
    # lon, lat, richness, y (= log1p(richness)), effort, log_effort, elevation, relief, continent
    stability_cols = cfg["stability_columns"][source]
    
    standard_df = pd.DataFrame()
    standard_df["lon"] = df[cmap["coord_lon"]].astype(float)
    standard_df["lat"] = df[cmap["coord_lat"]].astype(float)
    standard_df["abs_lat"] = standard_df["lat"].abs()
    standard_df["richness"] = df[cmap["target_raw"]].astype(int)
    standard_df["y"] = np.log1p(standard_df["richness"].values)
    standard_df["effort"] = df[cmap["effort_raw"]].astype(int)
    standard_df["log_effort"] = np.log1p(standard_df["effort"].values)
    standard_df["log_n"] = np.log(standard_df["effort"].values)
    standard_df["elevation"] = df[cmap["elevation_feature"]].astype(float)
    standard_df["relief"] = df[cmap["relief_feature"]].astype(float)
    
    # Copy stability columns
    for sc in stability_cols:
        standard_df[sc] = df[sc].astype(float)
        
    # Copy spatial_block_20deg if present in raw
    if "spatial_block_20deg" in df.columns:
        standard_df["spatial_block_20deg"] = df["spatial_block_20deg"].astype(str)
        
    # 3. Continent Assignment
    continent_table_path = repo_root / "tables" / "continent_assignment.csv"
    if continent_table_path.exists():
        cont_lookup = pd.read_csv(continent_table_path)
        # Merge on lat/lon
        m = standard_df.merge(
            cont_lookup[["cell_lat", "cell_lon", "continent"]].drop_duplicates(),
            left_on=["lat", "lon"],
            right_on=["cell_lat", "cell_lon"],
            how="left"
        )
        standard_df["continent"] = m["continent"].values
    else:
        from ml.src.continent_rules import assign_continent
        standard_df["continent"] = [assign_continent(r.lat, r.lon) for _, r in standard_df.iterrows()]
        
    # Check for unassigned continents
    n_unassigned_cont = standard_df["continent"].isna().sum()
    if n_unassigned_cont > 0:
        raise ValueError(f"[{source}_{resolution}] Found {n_unassigned_cont} unassigned continent cells!")
        
    # 4. Define Feature Groups
    feature_groups = {
        "effort": ["log_effort"],
        "geography": ["lat", "abs_lat"],
        "topography": ["elevation", "relief"],
        "palaeoclimate": stability_cols,
    }
    
    # Composite column name for this source
    comp_col = f"{'pc' if source == 'paleoclim' else 'wc'}_composite_instability"
    
    # 5. Define Nested Feature Sets
    m0_features = ["log_effort"]
    m1_features = m0_features + feature_groups["geography"] + feature_groups["topography"]
    m2a_features = m1_features + [comp_col]
    m2b_features = m1_features + stability_cols
    m3a_features = [comp_col]
    m3b_features = list(stability_cols)
    
    # Specific feature sets for exact OLS mid-eval benchmark replication
    m0_ols = ["log_n"]
    m1_ols = ["log_n", "abs_lat", "elevation", "relief"]
    m2a_ols = m1_ols + [comp_col]
    m2b_ols = m1_ols + stability_cols
    m3a_ols = [comp_col]
    m3b_ols = list(stability_cols)
    
    feature_sets = {
        "M0": m0_features,
        "M1": m1_features,
        "M2a": m2a_features,
        "M2b": m2b_features,
        "M2": m2a_features,  # Default M2 is primary M2a
        "M3a": m3a_features,
        "M3b": m3b_features,
        "M3": m3a_features,  # Default M3 is primary M3a
        "M0_ols": m0_ols,
        "M1_ols": m1_ols,
        "M2a_ols": m2a_ols,
        "M2b_ols": m2b_ols,
        "M3a_ols": m3a_ols,
        "M3b_ols": m3b_ols,
    }
    
    # 6. Apply Common Row Mask across all feature sets
    all_needed_cols = list(set(["y", "lat", "lon", "continent"] + m2b_features))
    valid_mask = standard_df[all_needed_cols].notna().all(axis=1)
    n_dropped_missing = int((~valid_mask).sum())
    if n_dropped_missing > 0:
        print(f"[{source}_{resolution}] Dropped {n_dropped_missing} rows due to missing values across features/target.")
        standard_df = standard_df[valid_mask].copy().reset_index(drop=True)
    else:
        print(f"[{source}_{resolution}] Zero rows dropped due to missingness. Clean sample size: {len(standard_df)}")
        
    # Assert identical row indices across all feature sets
    for fs_name, fs_cols in feature_sets.items():
        assert len(standard_df[fs_cols]) == len(standard_df), f"Row count mismatch in feature set {fs_name}"
        assert standard_df[fs_cols].index.equals(standard_df.index), f"Index mismatch in feature set {fs_name}"
        
    # 7. Compute & Save Correlation Matrix and VIF Table
    compute_vif_and_correlations(standard_df, stability_cols, source, resolution, repo_root)
    
    return standard_df, feature_groups, feature_sets


if __name__ == "__main__":
    df, fg, fs = load_dataset(source="paleoclim", resolution="base")
    print("\nSUCCESS: Dataset loaded successfully.")
    print("Columns:", list(df.columns))
    print(f"M0 ({len(fs['M0'])} cols): {fs['M0']}")
    print(f"M1 ({len(fs['M1'])} cols): {fs['M1']}")
    print(f"M2a ({len(fs['M2a'])} cols): {fs['M2a']}")
    print(f"M2b ({len(fs['M2b'])} cols): {fs['M2b']}")
    print(f"M3a ({len(fs['M3a'])} cols): {fs['M3a']}")
    print(f"M3b ({len(fs['M3b'])} cols): {fs['M3b']}")
    print(f"Continent breakdown:\n{df['continent'].value_counts()}")
