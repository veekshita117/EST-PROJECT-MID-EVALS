"""
metrics.py
----------
Evaluation metrics and spatial block-bootstrap confidence intervals for paired model differences.
"""

from typing import Tuple, Union, Optional
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def calc_r2(y_true: Union[np.ndarray, pd.Series], y_pred: Union[np.ndarray, pd.Series]) -> float:
    """Calculate coefficient of determination R2."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    if ss_tot == 0.0:
        return 0.0
    return float(1.0 - (ss_res / ss_tot))


def calc_rmse(y_true: Union[np.ndarray, pd.Series], y_pred: Union[np.ndarray, pd.Series]) -> float:
    """Calculate Root Mean Squared Error (RMSE)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_t - y_p) ** 2)))


def calc_mae(y_true: Union[np.ndarray, pd.Series], y_pred: Union[np.ndarray, pd.Series]) -> float:
    """Calculate Mean Absolute Error (MAE)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_t - y_p)))


def calc_spearman(y_true: Union[np.ndarray, pd.Series], y_pred: Union[np.ndarray, pd.Series]) -> Tuple[float, float]:
    """Calculate Spearman rank correlation rho and p-value."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    res = spearmanr(y_t, y_p)
    return float(res.statistic), float(res.pvalue)


def pooled_out_of_fold_r2(y_true: Union[np.ndarray, pd.Series], y_pred: Union[np.ndarray, pd.Series]) -> float:
    """
    Calculate pooled out-of-fold R2 across concatenated test predictions:
    1 - sum((y - y_hat)^2) / sum((y - y_bar)^2)
    """
    return calc_r2(y_true, y_pred)


def block_bootstrap_ci(
    y_true: Union[np.ndarray, pd.Series],
    y_pred_a: Union[np.ndarray, pd.Series],
    y_pred_b: Union[np.ndarray, pd.Series],
    groups: Union[np.ndarray, pd.Series],
    metric: str = "r2",
    n: int = 1000,
    seed: int = 42,
    alpha: float = 0.05
) -> Tuple[float, float, float]:
    """
    Cluster bootstrap confidence interval for the DIFFERENCE in a metric
    between two models (Model B minus Model A): Delta = Metric(B) - Metric(A).
    
    Resamples whole blocks (groups) with replacement, never individual cells.
    Returns (point_estimate, ci_low, ci_high).
    """
    rng = np.random.RandomState(seed)
    
    y_t = np.asarray(y_true, dtype=float)
    y_a = np.asarray(y_pred_a, dtype=float)
    y_b = np.asarray(y_pred_b, dtype=float)
    grps = np.asarray(groups)
    
    # Point estimate on full sample
    if metric == "r2":
        metric_fn = calc_r2
    elif metric == "rmse":
        metric_fn = calc_rmse
    elif metric == "spearman":
        metric_fn = lambda yt, yp: calc_spearman(yt, yp)[0]
    else:
        raise ValueError(f"Unsupported metric '{metric}'. Use 'r2', 'rmse', or 'spearman'.")
        
    point_delta = float(metric_fn(y_t, y_b) - metric_fn(y_t, y_a))
    
    unique_blocks = np.unique(grps)
    n_blocks = len(unique_blocks)
    
    # Precompute indices for each block to speed up bootstrap
    block_indices = {b: np.where(grps == b)[0] for b in unique_blocks}
    
    boot_deltas = []
    for _ in range(n):
        sampled_blocks = rng.choice(unique_blocks, size=n_blocks, replace=True)
        sample_idx = np.concatenate([block_indices[b] for b in sampled_blocks])
        
        y_t_samp = y_t[sample_idx]
        y_a_samp = y_a[sample_idx]
        y_b_samp = y_b[sample_idx]
        
        # Check variance in resampled target
        if np.std(y_t_samp) == 0:
            continue
            
        m_a = metric_fn(y_t_samp, y_a_samp)
        m_b = metric_fn(y_t_samp, y_b_samp)
        boot_deltas.append(m_b - m_a)
        
    if len(boot_deltas) < n * 0.5:
        return point_delta, np.nan, np.nan
        
    ci_low = float(np.percentile(boot_deltas, 100 * (alpha / 2.0)))
    ci_high = float(np.percentile(boot_deltas, 100 * (1.0 - alpha / 2.0)))
    
    return point_delta, ci_low, ci_high


if __name__ == "__main__":
    np.random.seed(42)
    y_t = np.random.normal(3.0, 1.0, 100)
    y_a = y_t + np.random.normal(0, 0.4, 100)
    y_b = y_t + np.random.normal(0, 0.35, 100) # Slightly better
    grps = np.repeat(np.arange(10), 10)
    
    pt, lo, hi = block_bootstrap_ci(y_t, y_a, y_b, grps, metric="r2", n=500, seed=42)
    print(f"Sample R2 Delta: {pt:.4f}, 95% Block Bootstrap CI: [{lo:.4f}, {hi:.4f}]")
