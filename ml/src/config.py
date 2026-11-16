"""
config.py
---------
Configuration management for the machine learning layer.
Loads and validates ml/config.yaml against repository datasets.
"""

from pathlib import Path
from typing import Dict, Any, Union
import yaml
import pandas as pd


def get_repo_root() -> Path:
    """Return the absolute path of the repository root."""
    # Assuming this file lives in ml/src/config.py
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: Union[str, Path] = "ml/config.yaml") -> Dict[str, Any]:
    """
    Load ml/config.yaml from the repository root.
    """
    repo_root = get_repo_root()
    full_path = repo_root / config_path if not Path(config_path).is_absolute() else Path(config_path)
    
    if not full_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {full_path}")
        
    with open(full_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    return config


def validate_config(config: Dict[str, Any], repo_root: Path = None) -> bool:
    """
    Validate that:
    1. Dataset files defined in config paths exist relative to repo root.
    2. All mapped columns exist in their corresponding dataset files.
    Fails with a descriptive ValueError / FileNotFoundError if anything is missing.
    """
    if repo_root is None:
        repo_root = get_repo_root()
        
    # 1. Validate data paths
    paths = config.get("paths", {})
    for source in ["paleoclim", "worldclim"]:
        if source not in paths:
            raise ValueError(f"Config validation error: missing '{source}' in paths.")
        for res_key in ["base", "2deg"]:
            if res_key not in paths[source]:
                raise ValueError(f"Config validation error: missing resolution '{res_key}' under paths['{source}'].")
            rel_file = paths[source][res_key]
            full_file = repo_root / rel_file
            if not full_file.exists():
                raise FileNotFoundError(
                    f"Config validation error: Data file does not exist: {full_file} (from paths.{source}.{res_key})"
                )

    # 2. Validate mapped columns against actual data files
    cmap = config.get("column_map", {})
    required_cols_to_check = [
        ("coord_lon", cmap.get("coord_lon")),
        ("coord_lat", cmap.get("coord_lat")),
        ("target_raw", cmap.get("target_raw")),
        ("effort_raw", cmap.get("effort_raw")),
        ("effort_feature", cmap.get("effort_feature")),
        ("elevation_feature", cmap.get("elevation_feature")),
        ("relief_feature", cmap.get("relief_feature")),
    ]
    
    # Check on 5deg and 2deg tables
    for res_name, rel_path in [("base", paths["paleoclim"]["base"]), ("2deg", paths["paleoclim"]["2deg"])]:
        df = pd.read_csv(repo_root / rel_path, nrows=5)
        for label, col_name in required_cols_to_check:
            if col_name not in df.columns:
                raise ValueError(
                    f"Config validation error: Mapped column '{col_name}' ({label}) is missing from {rel_path} ({res_name})!"
                )
                
        # Check stability columns for both paleoclim and worldclim
        stab_dict = config.get("stability_columns", {})
        for src in ["paleoclim", "worldclim"]:
            for col in stab_dict.get(src, []):
                if col not in df.columns:
                    raise ValueError(
                        f"Config validation error: Stability column '{col}' for source '{src}' is missing from {rel_path}!"
                    )
                    
    return True


def get_validated_config(config_path: Union[str, Path] = "ml/config.yaml") -> Dict[str, Any]:
    """Convenience function: loads and validates configuration in one call."""
    config = load_config(config_path)
    validate_config(config)
    return config


if __name__ == "__main__":
    cfg = get_validated_config()
    print("SUCCESS: Configuration loaded and validated successfully.")
    print(f"Base path: {cfg['paths']['paleoclim']['base']}")
    print(f"2deg path: {cfg['paths']['paleoclim']['2deg']}")
    print(f"Min records filter: {cfg['min_records']}")
