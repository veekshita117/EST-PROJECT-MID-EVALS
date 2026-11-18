"""
models.py
---------
Model factories returning scikit-learn Pipelines for regression.
Ensures zero data leakage: imputers and scalers are strictly part of the Pipeline.
Provides get_param_grid for fast and full tuning.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Union
import numpy as np

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor


def get_regressor(model_name: str = "ridge", random_state: int = 42) -> Pipeline:
    """
    Factory returning an sklearn Pipeline for regression.
    
    Supported:
    - 'ridge': SimpleImputer(median) + StandardScaler + Ridge
    - 'rf': SimpleImputer(median) + RandomForestRegressor(n_estimators=300, n_jobs=-1)
    - 'hgb': HistGradientBoostingRegressor(early_stopping=False)
    """
    model_name = model_name.lower()
    
    if model_name == "ridge":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(random_state=random_state))
        ])
    elif model_name == "rf":
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=300,
                n_jobs=-1,
                random_state=random_state
            ))
        ])
    elif model_name == "hgb":
        # HGB handles NaNs natively; early_stopping must be False to prevent spatial leakage
        return Pipeline([
            ("model", HistGradientBoostingRegressor(
                early_stopping=False,
                random_state=random_state
            ))
        ])
    else:
        raise ValueError(f"Unknown regressor model_name '{model_name}'. Choose 'ridge', 'rf', or 'hgb'.")


def get_param_grid(model_name: str, fast: bool = False) -> Dict[str, Any]:
    """
    Return parameter tuning grid for inner cross-validation.
    
    If fast is True, returns compact grids with fewer iterations / trees.
    """
    model_name = model_name.lower()
    
    if model_name == "ridge":
        if fast:
            return {"model__alpha": np.logspace(-3, 3, 7)}
        return {"model__alpha": np.logspace(-3, 3, 13)}
        
    elif model_name == "rf":
        if fast:
            return {
                "model__n_estimators": [100],
                "model__max_depth": [4, 8],
                "model__min_samples_leaf": [1, 5],
                "model__max_features": [0.6, 1.0]
            }
        return {
            "model__n_estimators": [300],
            "model__max_depth": [6, 12, None],
            "model__min_samples_leaf": [1, 5, 20],
            "model__max_features": [0.33, 0.6, 1.0]
        }
        
    elif model_name == "hgb":
        if fast:
            return {
                "model__learning_rate": [0.03, 0.1],
                "model__max_depth": [3, 5],
                "model__max_iter": [100]
            }
        return {
            "model__learning_rate": [0.03, 0.06, 0.1],
            "model__max_depth": [3, 5, None],
            "model__max_leaf_nodes": [15, 31, 63],
            "model__min_samples_leaf": [20, 50],
            "model__l2_regularization": [0.0, 1.0],
            "model__max_iter": [200, 400]
        }
    else:
        raise ValueError(f"Unknown model_name '{model_name}'.")


if __name__ == "__main__":
    for m in ["ridge", "rf", "hgb"]:
        reg = get_regressor(m)
        pg_fast = get_param_grid(m, fast=True)
        pg_full = get_param_grid(m, fast=False)
        print(f"[{m.upper()}] Regressor: {reg.named_steps.keys()}, Grid keys: {list(pg_full.keys())}")
