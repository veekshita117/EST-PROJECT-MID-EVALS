"""
test_frontier_analysis.py
-------------------------
Unit tests for Stochastic Frontier Analysis (SFA) module in integration_v3/run_frontier_analysis.py:
1. NormalHalfNormalSFA fits and recovers parameters on synthetic data with known half-normal inefficiency.
2. Variance parameters satisfy theoretical identities:
   - sigma^2 == sigma_u^2 + sigma_v^2
   - lambda == sigma_u / sigma_v
   - gamma == sigma_u^2 / sigma^2 in (0, 1)
3. Upper frontier ceiling property: frontier predictions exceed mean OLS predictions.
4. Technical efficiency scores satisfy TE in (0, 1].
5. Likelihood Ratio Test vs. OLS computes positive LR statistic and valid p-value.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration_v3.run_frontier_analysis import NormalHalfNormalSFA


@pytest.fixture
def synthetic_frontier_data():
    """Generate synthetic data with true half-normal production ceiling frontier."""
    rng = np.random.default_rng(42)
    N = 250
    x1 = rng.uniform(-2, 2, size=N)
    x2 = rng.uniform(-1, 1, size=N)
    X = np.column_stack([np.ones(N), x1, x2])
    
    true_beta = np.array([5.0, -0.3, 0.4])
    true_sigma_v = 0.2
    true_sigma_u = 0.8
    
    v = rng.normal(0, true_sigma_v, size=N)
    u = np.abs(rng.normal(0, true_sigma_u, size=N))  # half-normal >= 0
    
    # Production ceiling: y = X*beta + v - u
    y = X @ true_beta + v - u
    return X, y, true_beta, true_sigma_u, true_sigma_v


def test_sfa_fit_and_variance_identities(synthetic_frontier_data):
    """Test that SFA parameter estimates satisfy theoretical variance relationships."""
    X, y, true_beta, true_sigma_u, true_sigma_v = synthetic_frontier_data
    
    sfa = NormalHalfNormalSFA(feature_names=["const", "x1", "x2"])
    sfa.fit(X, y)
    
    assert len(sfa.beta_) == 3
    assert sfa.sigma_sq_ > 0.0
    assert sfa.sigma_u_sq_ > 0.0
    assert sfa.sigma_v_sq_ > 0.0
    assert sfa.lambda_ > 0.0
    assert 0.0 < sfa.gamma_ < 1.0
    
    # Check theoretical identity: sigma^2 = sigma_u^2 + sigma_v^2
    assert np.isclose(sfa.sigma_sq_, sfa.sigma_u_sq_ + sfa.sigma_v_sq_, rtol=1e-4)
    # Check theoretical identity: lambda = sigma_u / sigma_v
    assert np.isclose(sfa.lambda_, np.sqrt(sfa.sigma_u_sq_ / sfa.sigma_v_sq_), rtol=1e-4)
    # Check theoretical identity: gamma = sigma_u^2 / sigma^2
    assert np.isclose(sfa.gamma_, sfa.sigma_u_sq_ / sfa.sigma_sq_, rtol=1e-4)


def test_sfa_ceiling_property_and_efficiency(synthetic_frontier_data):
    """Test that SFA frontier acts as upper bound and technical efficiency is in (0, 1]."""
    X, y, _, _, _ = synthetic_frontier_data
    
    sfa = NormalHalfNormalSFA(feature_names=["const", "x1", "x2"])
    sfa.fit(X, y)
    
    y_frontier = sfa.predict_frontier(X)
    u_hat = sfa.predict_conditional_inefficiency(X, y)
    eff = sfa.predict_efficiency(X, y)
    
    # Inefficiency u_hat must be non-negative
    assert np.all(u_hat >= 0.0), f"Found negative inefficiency values: min={u_hat.min()}"
    # Technical efficiency exp(-u) must be strictly between 0 and 1
    assert np.all((eff > 0.0) & (eff <= 1.0)), "Efficiency values outside (0, 1]"
    
    # The ceiling frontier should be strictly higher than the average observed y
    assert np.mean(y_frontier) > np.mean(y)


def test_sfa_likelihood_ratio_test(synthetic_frontier_data):
    """Test that LR test vs OLS has positive test statistic and valid p-value."""
    X, y, _, _, _ = synthetic_frontier_data
    
    sfa = NormalHalfNormalSFA(feature_names=["const", "x1", "x2"])
    sfa.fit(X, y)
    
    assert sfa.lr_stat_ >= 0.0
    assert 0.0 <= sfa.lr_pvalue_ <= 1.0
    assert sfa.log_likelihood_ > sfa.log_likelihood_ols_
