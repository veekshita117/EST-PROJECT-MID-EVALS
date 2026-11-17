"""
run_frontier_analysis.py
------------------------
Stage: Stochastic Frontier Analysis (SFA) of Global Species Richness.

Implements:
1. Maximum-likelihood normal-half-normal stochastic frontier model (macroecological ceiling / upper bound).
2. Models ln(richness + 1) using climate velocity, absolute latitude, and topography.
3. Treats Quaternary climate velocity as a primary constraint on the upper richness frontier.
4. Estimates frontier coefficients (beta), inefficiency variance (sigma_u^2), noise variance (sigma_v^2),
   total variance (sigma^2 = sigma_u^2 + sigma_v^2), lambda = sigma_u / sigma_v, and gamma = sigma_u^2 / sigma^2.
5. Statistically rigorous comparison with OLS via:
   - D'Agostino residual skewness test (confirming negative composite error skewness).
   - Likelihood Ratio Test (LRT) with Kodde & Palm mixed chi-square p-value.
   - AIC and BIC model selection criteria.
6. Computes 95% confidence intervals via Fisher Information / observed Hessian.
7. Computes Jondrow et al. (1982) conditional inefficiency E[u | epsilon] and technical efficiency.
8. Saves tabular results to tables/frontier_results.csv and publication figure to figures/frontier_ceiling.png.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from scipy.special import log_ndtr
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class NormalHalfNormalSFA:
    """
    Maximum Likelihood Normal-Half-Normal Stochastic Frontier Model (Ceiling / Upper Bound).
    
    Model:
        y_i = x_i' * beta + v_i - u_i
    where:
        v_i ~ N(0, sigma_v^2)  (two-sided random noise)
        u_i ~ N+(0, sigma_u^2) (one-sided non-negative inefficiency / shortfall, u_i >= 0)
        
    Composite residual:
        epsilon_i = y_i - x_i' * beta = v_i - u_i
    
    Parameter vector:
        theta = [beta_0, beta_1, ..., beta_k, ln(sigma^2), ln(lambda)]
        where sigma^2 = sigma_u^2 + sigma_v^2 and lambda = sigma_u / sigma_v.
    """
    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = feature_names
        self.params_ = {}
        self.bse_ = {}
        self.conf_int_ = {}
        self.pvalues_ = {}
        self.beta_ = None
        self.sigma_sq_ = None
        self.lambda_ = None
        self.sigma_u_sq_ = None
        self.sigma_v_sq_ = None
        self.gamma_ = None
        self.log_likelihood_ = None
        self.log_likelihood_ols_ = None
        self.lr_stat_ = None
        self.lr_pvalue_ = None
        self.ols_skew_ = None
        self.ols_skew_pvalue_ = None
        self.aic_ = None
        self.bic_ = None
        self.aic_ols_ = None
        self.bic_ols_ = None
        self.hessian_inv_ = None
        
    def _neg_log_likelihood(self, theta: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
        """Compute negative log-likelihood with numerically stable log_ndtr."""
        p = X.shape[1]
        beta = theta[:p]
        ln_sigma_sq = theta[p]
        ln_lambda = theta[p + 1]
        
        sigma_sq = np.exp(ln_sigma_sq)
        sigma = np.sqrt(sigma_sq)
        lambda_val = np.exp(ln_lambda)
        
        N = len(y)
        eps = y - X @ beta
        
        # Marginal log-likelihood of normal-half-normal composite error:
        # ln L = N * ln(sqrt(2/pi)) - (N/2)*ln(sigma^2) - (1/(2*sigma^2)) * sum(eps^2) + sum(ln(Phi(-lambda*eps/sigma)))
        term_const = N * 0.5 * np.log(2.0 / np.pi)
        term_var = -0.5 * N * ln_sigma_sq
        term_ss = -0.5 * np.sum(eps**2) / sigma_sq
        
        z_arg = - (lambda_val * eps) / sigma
        term_cdf = np.sum(log_ndtr(z_arg))
        
        ll = term_const + term_var + term_ss + term_cdf
        if not np.isfinite(ll):
            return 1e12
        return -ll

    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fit Normal-Half-Normal Stochastic Frontier Model using Maximum Likelihood."""
        N, p = X.shape
        if self.feature_names is None:
            self.feature_names = [f"x{i}" for i in range(p)]
            
        # 1. Fit OLS to obtain starting values and diagnostics
        ols_model = sm.OLS(y, X).fit()
        ols_beta = ols_model.params
        ols_resids = y - X @ ols_beta
        
        # OLS Log-Likelihood
        self.log_likelihood_ols_ = float(ols_model.llf)
        self.aic_ols_ = float(ols_model.aic)
        self.bic_ols_ = float(ols_model.bic)
        
        # Skewness diagnostic of OLS residuals (negative skewness confirms upper frontier)
        m2 = np.mean(ols_resids**2)
        m3 = np.mean(ols_resids**3)
        self.ols_skew_ = float(stats.skew(ols_resids))
        skew_res = stats.skewtest(ols_resids)
        self.ols_skew_pvalue_ = float(skew_res.pvalue)
        
        # Method of moments initialization
        denom = np.sqrt(2.0 / np.pi) * (4.0 / np.pi - 1.0)  # ~ +0.2180
        if m3 < 0:
            sigma_u_cubed = max(1e-4, -m3 / denom)
            sigma_u_init = float(sigma_u_cubed**(1.0 / 3.0))
            sigma_v_sq_init = float(np.maximum(1e-4, m2 - (1.0 - 2.0 / np.pi) * (sigma_u_init**2)))
            sigma_u_sq_init = sigma_u_init**2
            sigma_sq_init = sigma_u_sq_init + sigma_v_sq_init
            lambda_init = float(sigma_u_init / np.sqrt(sigma_v_sq_init))
            init_beta = ols_beta.copy()
            init_beta[0] += np.sqrt(2.0 / np.pi) * sigma_u_init
        else:
            sigma_sq_init = float(m2)
            lambda_init = 1.0
            init_beta = ols_beta.copy()
            init_beta[0] += 0.1
            
        theta0 = np.concatenate([init_beta, [np.log(sigma_sq_init), np.log(lambda_init)]])
        
        # 2. Maximum Likelihood Estimation via L-BFGS-B
        res = minimize(
            self._neg_log_likelihood,
            theta0,
            args=(X, y),
            method="L-BFGS-B",
            options={"maxiter": 2000, "ftol": 1e-12, "gtol": 1e-7}
        )
        
        if not res.success:
            res = minimize(
                self._neg_log_likelihood,
                res.x,
                args=(X, y),
                method="Nelder-Mead",
                options={"maxiter": 3000, "xatol": 1e-8, "fatol": 1e-8}
            )
            
        theta_hat = res.x
        self.log_likelihood_ = -float(res.fun)
        
        self.beta_ = theta_hat[:p]
        ln_sigma_sq = theta_hat[p]
        ln_lambda = theta_hat[p + 1]
        
        self.sigma_sq_ = float(np.exp(ln_sigma_sq))
        self.lambda_ = float(np.exp(ln_lambda))
        self.sigma_v_sq_ = float(self.sigma_sq_ / (1.0 + self.lambda_**2))
        self.sigma_u_sq_ = float((self.sigma_sq_ * self.lambda_**2) / (1.0 + self.lambda_**2))
        self.gamma_ = float(self.sigma_u_sq_ / self.sigma_sq_)
        
        # Information criteria
        k_sfa = p + 2
        self.aic_ = 2 * k_sfa - 2 * self.log_likelihood_
        self.bic_ = k_sfa * np.log(N) - 2 * self.log_likelihood_
        
        # Likelihood Ratio Test vs OLS
        # LR = 2 * (ll_sfa - ll_ols). Under H0: lambda=0, distribution is mixed chi-square (Kodde & Palm 1986)
        self.lr_stat_ = float(max(0.0, 2.0 * (self.log_likelihood_ - self.log_likelihood_ols_)))
        self.lr_pvalue_ = float(0.5 * (1.0 - stats.chi2.cdf(self.lr_stat_, df=1)))
        
        # 3. Standard Errors via Central Finite-Difference Hessian Inverse
        eps = 1e-4
        k_tot = len(theta_hat)
        H = np.zeros((k_tot, k_tot))
        for i in range(k_tot):
            for j in range(k_tot):
                t_pp = theta_hat.copy(); t_pp[i] += eps; t_pp[j] += eps
                t_pm = theta_hat.copy(); t_pm[i] += eps; t_pm[j] -= eps
                t_mp = theta_hat.copy(); t_mp[i] -= eps; t_mp[j] += eps
                t_mm = theta_hat.copy(); t_mm[i] -= eps; t_mm[j] -= eps
                H[i, j] = (self._neg_log_likelihood(t_pp, X, y) - self._neg_log_likelihood(t_pm, X, y) -
                           self._neg_log_likelihood(t_mp, X, y) + self._neg_log_likelihood(t_mm, X, y)) / (4.0 * eps * eps)
                
        H_inv = np.linalg.pinv(H)
        self.hessian_inv_ = H_inv
        se_theta = np.sqrt(np.maximum(1e-8, np.diag(H_inv)))
        
        # Map SEs to parameters
        for i, name in enumerate(self.feature_names):
            b = float(self.beta_[i])
            se = float(se_theta[i])
            z = b / se if se > 0 else np.nan
            p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(z)))) if se > 0 else np.nan
            self.params_[name] = b
            self.bse_[name] = se
            self.conf_int_[name] = (b - 1.96 * se, b + 1.96 * se)
            self.pvalues_[name] = p_val
            
        # Variance components SEs via delta method
        se_sigma_sq = float(se_theta[p] * self.sigma_sq_)
        se_lambda = float(se_theta[p + 1] * self.lambda_)
        
        self.params_["sigma_sq"] = self.sigma_sq_
        self.bse_["sigma_sq"] = se_sigma_sq
        self.conf_int_["sigma_sq"] = (max(1e-6, self.sigma_sq_ - 1.96 * se_sigma_sq), self.sigma_sq_ + 1.96 * se_sigma_sq)
        
        se_u_sq = float(se_sigma_sq * (self.lambda_**2 / (1.0 + self.lambda_**2)))
        self.params_["sigma_u_sq"] = self.sigma_u_sq_
        self.bse_["sigma_u_sq"] = se_u_sq
        self.conf_int_["sigma_u_sq"] = (max(1e-6, self.sigma_u_sq_ - 1.96 * se_u_sq), self.sigma_u_sq_ + 1.96 * se_u_sq)
        
        se_v_sq = float(se_sigma_sq / (1.0 + self.lambda_**2))
        self.params_["sigma_v_sq"] = self.sigma_v_sq_
        self.bse_["sigma_v_sq"] = se_v_sq
        self.conf_int_["sigma_v_sq"] = (max(1e-6, self.sigma_v_sq_ - 1.96 * se_v_sq), self.sigma_v_sq_ + 1.96 * se_v_sq)
        
        self.params_["lambda"] = self.lambda_
        self.bse_["lambda"] = se_lambda
        self.conf_int_["lambda"] = (max(1e-6, self.lambda_ - 1.96 * se_lambda), self.lambda_ + 1.96 * se_lambda)
        
        se_gamma = float((2 * self.lambda_ / (1.0 + self.lambda_**2)**2) * se_lambda)
        self.params_["gamma"] = self.gamma_
        self.bse_["gamma"] = se_gamma
        self.conf_int_["gamma"] = (np.clip(self.gamma_ - 1.96 * se_gamma, 0.0, 1.0), np.clip(self.gamma_ + 1.96 * se_gamma, 0.0, 1.0))
        
        return self
        
    def predict_frontier(self, X: np.ndarray) -> np.ndarray:
        """Predict stochastic ceiling frontier: y* = X * beta."""
        return X @ self.beta_
        
    def predict_conditional_inefficiency(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Estimate observation-specific inefficiency u_i | epsilon_i
        using the Jondrow, Lovell, Materov & Schmidt (1982) conditional mean estimator:
            E[u | epsilon] = sigma_* * [ phi(mu_* / sigma_*) / Phi(mu_* / sigma_*) + (mu_* / sigma_*) ]
        where mu_* = -epsilon * sigma_u^2 / sigma^2 and sigma_* = (sigma_u * sigma_v) / sigma.
        """
        eps = y - X @ self.beta_
        sigma_u = np.sqrt(self.sigma_u_sq_)
        sigma_v = np.sqrt(self.sigma_v_sq_)
        sigma = np.sqrt(self.sigma_sq_)
        
        sigma_star = (sigma_u * sigma_v) / sigma
        mu_star = - (eps * self.sigma_u_sq_) / self.sigma_sq_
        
        z = mu_star / sigma_star
        ratio = stats.norm.pdf(z) / np.maximum(1e-12, stats.norm.cdf(z))
        u_hat = sigma_star * (ratio + z)
        return np.maximum(0.0, u_hat)
        
    def predict_efficiency(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Estimate technical ceiling efficiency: TE = exp(-u_hat) in (0, 1]."""
        u_hat = self.predict_conditional_inefficiency(X, y)
        return np.exp(-u_hat)


def run_frontier_analysis(
    data_path: Optional[str] = None,
    resolution: str = "5deg",
    out_dir: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    print("=" * 80)
    print(f"STOCHASTIC FRONTIER ANALYSIS (SFA): MACROECOLOGICAL CEILING HYPOTHESIS")
    print(f"Resolution: {resolution}")
    print("=" * 80)
    
    if data_path is None:
        data_path = REPO_ROOT / "integration_v3" / "processed" / f"data_v3_{resolution}.csv"
    else:
        data_path = Path(data_path)
        
    df = pd.read_csv(data_path)
    print(f"Loaded master dataset: {len(df)} cells from {data_path}")
    
    tables_dir = REPO_ROOT / "tables"
    figures_dir = REPO_ROOT / "figures"
    v3_tables_dir = REPO_ROOT / "results" / "tables" / "integration_v3"
    v3_figures_dir = REPO_ROOT / "results" / "figures" / "integration_v3"
    
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    v3_tables_dir.mkdir(parents=True, exist_ok=True)
    v3_figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Define Response and Predictors
    y = np.log1p(df["richness_total"].values.astype(float))
    
    feature_cols = [
        "log10_velocity_temp",
        "abs_lat",
        "elevation_mean",
        "topographic_heterogeneity",
        "land_fraction"
    ]
    
    # Complete cases filtering
    X_raw = df[feature_cols].values.astype(float)
    valid_mask = np.isfinite(y) & np.all(np.isfinite(X_raw), axis=1)
    df_clean = df[valid_mask].copy().reset_index(drop=True)
    y_clean = y[valid_mask]
    X_clean = X_raw[valid_mask]
    
    # Standardize predictors for comparability
    X_scaled = (X_clean - np.mean(X_clean, axis=0)) / np.std(X_clean, axis=0)
    X_aug = np.column_stack([np.ones(len(y_clean)), X_scaled])
    names_aug = ["Intercept"] + feature_cols
    
    # 2. Fit OLS Reference Model
    ols_model = sm.OLS(y_clean, X_aug).fit()
    ols_beta = ols_model.params
    ols_bse = ols_model.bse
    ols_pvals = ols_model.pvalues
    ols_ci = ols_model.conf_int()
    
    # 3. Fit Stochastic Frontier Model
    sfa = NormalHalfNormalSFA(feature_names=names_aug)
    sfa.fit(X_aug, y_clean)
    
    # 4. Compile Results Table
    results_rows = []
    
    for i, name in enumerate(names_aug):
        results_rows.append({
            "parameter": name,
            "ols_coef": round(float(ols_beta[i]), 4),
            "ols_se": round(float(ols_bse[i]), 4),
            "ols_pvalue": round(float(ols_pvals[i]), 4),
            "ols_ci95_low": round(float(ols_ci[i, 0]), 4),
            "ols_ci95_high": round(float(ols_ci[i, 1]), 4),
            "sfa_frontier_coef": round(float(sfa.beta_[i]), 4),
            "sfa_frontier_se": round(float(sfa.bse_.get(name, np.nan)), 4),
            "sfa_frontier_pvalue": round(float(sfa.pvalues_.get(name, np.nan)), 4),
            "sfa_ci95_low": round(float(sfa.conf_int_.get(name, (np.nan, np.nan))[0]), 4),
            "sfa_ci95_high": round(float(sfa.conf_int_.get(name, (np.nan, np.nan))[1]), 4),
        })
        
    diagnostics = [
        ("sigma_u_sq (Inefficiency Variance)", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.sigma_u_sq_, sfa.bse_.get("sigma_u_sq", np.nan), np.nan, sfa.conf_int_["sigma_u_sq"][0], sfa.conf_int_["sigma_u_sq"][1]),
        ("sigma_v_sq (Noise Variance)", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.sigma_v_sq_, sfa.bse_.get("sigma_v_sq", np.nan), np.nan, sfa.conf_int_["sigma_v_sq"][0], sfa.conf_int_["sigma_v_sq"][1]),
        ("sigma_sq (Total Variance)", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.sigma_sq_, sfa.bse_.get("sigma_sq", np.nan), np.nan, sfa.conf_int_["sigma_sq"][0], sfa.conf_int_["sigma_sq"][1]),
        ("lambda (sigma_u / sigma_v)", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.lambda_, sfa.bse_.get("lambda", np.nan), np.nan, sfa.conf_int_["lambda"][0], sfa.conf_int_["lambda"][1]),
        ("gamma (Inefficiency Share)", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.gamma_, sfa.bse_.get("gamma", np.nan), np.nan, sfa.conf_int_["gamma"][0], sfa.conf_int_["gamma"][1]),
        ("Log-Likelihood", sfa.log_likelihood_ols_, np.nan, np.nan, np.nan, np.nan,
         sfa.log_likelihood_, np.nan, np.nan, np.nan, np.nan),
        ("AIC", sfa.aic_ols_, np.nan, np.nan, np.nan, np.nan,
         sfa.aic_, np.nan, np.nan, np.nan, np.nan),
        ("BIC", sfa.bic_ols_, np.nan, np.nan, np.nan, np.nan,
         sfa.bic_, np.nan, np.nan, np.nan, np.nan),
        ("LR Test vs OLS", np.nan, np.nan, np.nan, np.nan, np.nan,
         sfa.lr_stat_, np.nan, sfa.lr_pvalue_, np.nan, np.nan),
        ("OLS Residual Skewness", sfa.ols_skew_, np.nan, sfa.ols_skew_pvalue_, np.nan, np.nan,
         np.nan, np.nan, np.nan, np.nan, np.nan)
    ]
    
    for row in diagnostics:
        results_rows.append({
            "parameter": row[0],
            "ols_coef": round(float(row[1]), 4) if np.isfinite(row[1]) else np.nan,
            "ols_se": round(float(row[2]), 4) if np.isfinite(row[2]) else np.nan,
            "ols_pvalue": round(float(row[3]), 4) if np.isfinite(row[3]) else np.nan,
            "ols_ci95_low": round(float(row[4]), 4) if np.isfinite(row[4]) else np.nan,
            "ols_ci95_high": round(float(row[5]), 4) if np.isfinite(row[5]) else np.nan,
            "sfa_frontier_coef": round(float(row[6]), 4) if np.isfinite(row[6]) else np.nan,
            "sfa_frontier_se": round(float(row[7]), 4) if np.isfinite(row[7]) else np.nan,
            "sfa_frontier_pvalue": round(float(row[8]), 4) if np.isfinite(row[8]) else np.nan,
            "sfa_ci95_low": round(float(row[9]), 4) if np.isfinite(row[9]) else np.nan,
            "sfa_ci95_high": round(float(row[10]), 4) if np.isfinite(row[10]) else np.nan,
        })
        
    results_df = pd.DataFrame(results_rows)
    print("\nStochastic Frontier Results & OLS Comparison:")
    print(results_df.to_string(index=False))
    
    # Save CSV tables
    out_table = tables_dir / "frontier_results.csv"
    v3_out_table = v3_tables_dir / "frontier_results.csv"
    results_df.to_csv(out_table, index=False)
    results_df.to_csv(v3_out_table, index=False)
    print(f"\n[OK] Saved frontier results table to {out_table} and {v3_out_table}")
    
    # 5. Compute Predictions and Efficiency Scores
    y_frontier = sfa.predict_frontier(X_aug)
    u_hat = sfa.predict_conditional_inefficiency(X_aug, y_clean)
    efficiency = sfa.predict_efficiency(X_aug, y_clean)
    
    df_clean["y_observed"] = y_clean
    df_clean["y_frontier_ceiling"] = y_frontier
    df_clean["inefficiency_u"] = u_hat
    df_clean["ceiling_efficiency"] = efficiency
    
    # 6. Create Publication Figures (frontier_ceiling.png)
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=300)
    
    # Panel A: Upper Ceiling Frontier vs Climate Velocity
    ax_a = axes[0, 0]
    vel = df_clean["log10_velocity_temp"].values
    
    ax_a.scatter(vel, y_clean, color="#4C72B0", alpha=0.45, s=25, label="Observed Cells")
    
    # OLS fitted line vs SFA frontier line across velocity
    vel_grid = np.linspace(vel.min(), vel.max(), 200)
    vel_grid_scaled = (vel_grid - np.mean(df_clean["log10_velocity_temp"])) / np.std(df_clean["log10_velocity_temp"])
    X_grid = np.zeros((len(vel_grid), X_aug.shape[1]))
    X_grid[:, 0] = 1.0
    X_grid[:, 1] = vel_grid_scaled
    
    ols_grid = X_grid @ ols_beta
    sfa_grid = sfa.predict_frontier(X_grid)
    
    ax_a.plot(vel_grid, ols_grid, "b--", linewidth=2.0, label=f"OLS Mean Fit (β={ols_beta[1]:.3f})")
    ax_a.plot(vel_grid, sfa_grid, "r-", linewidth=2.8, label=f"SFA Ceiling Frontier (β={sfa.beta_[1]:.3f})")
    
    sigma_v = np.sqrt(sfa.sigma_v_sq_)
    ax_a.fill_between(vel_grid, sfa_grid - 1.96 * sigma_v, sfa_grid + 1.96 * sigma_v,
                     color="red", alpha=0.15, label=r"Ceiling $\pm 1.96 \sigma_v$")
    ax_a.set_xlabel(r"$\log_{10}(\text{Temperature Velocity})$ [m/yr]", fontsize=11, fontweight="bold")
    ax_a.set_ylabel(r"Species Richness: $\ln(1 + \text{richness})$", fontsize=11, fontweight="bold")
    ax_a.set_title(r"(A) Climate Velocity as a Macroecological Richness Ceiling", fontsize=12, fontweight="bold")
    ax_a.legend(frameon=True, facecolor="white", loc="lower left", fontsize=9)
    ax_a.grid(True, linestyle=":", alpha=0.5)
    
    # Panel B: Distribution of Realized Technical Efficiency
    ax_b = axes[0, 1]
    ax_b.hist(efficiency, bins=35, color="#55A868", edgecolor="#2ca02c", alpha=0.75, density=True)
    ax_b.axvline(np.mean(efficiency), color="darkgreen", linestyle="--", linewidth=2.0,
                 label=f"Mean Efficiency = {np.mean(efficiency):.3f}")
    ax_b.axvline(np.median(efficiency), color="navy", linestyle=":", linewidth=2.0,
                 label=f"Median Efficiency = {np.median(efficiency):.3f}")
    ax_b.set_xlabel(r"Technical Efficiency: $\text{TE} = \exp(-u) \in (0, 1]$", fontsize=11, fontweight="bold")
    ax_b.set_ylabel("Density", fontsize=11, fontweight="bold")
    ax_b.set_title(r"(B) Global Cell Realized Efficiency Relative to Ceiling", fontsize=12, fontweight="bold")
    ax_b.legend(frameon=True, facecolor="white", fontsize=9)
    ax_b.grid(True, linestyle=":", alpha=0.5)
    
    # Panel C: Skewness & Composite Residual Distribution
    ax_c = axes[1, 0]
    ols_resids = y_clean - X_aug @ ols_beta
    ax_c.hist(ols_resids, bins=35, density=True, color="#A1C9F4", edgecolor="#4C72B0", alpha=0.65, label="OLS Residuals")
    
    # Plot normal fit vs skewed composite density
    x_range = np.linspace(ols_resids.min(), ols_resids.max(), 300)
    norm_pdf = stats.norm.pdf(x_range, loc=0, scale=np.std(ols_resids))
    sig = np.sqrt(sfa.sigma_sq_)
    lam = sfa.lambda_
    sfa_pdf = (2.0 / sig) * stats.norm.pdf(x_range / sig) * stats.norm.cdf(-lam * x_range / sig)
    
    ax_c.plot(x_range, norm_pdf, "b--", linewidth=1.8, label=f"Symmetric Normal (Skew={stats.skew(ols_resids):.3f})")
    ax_c.plot(x_range, sfa_pdf, "r-", linewidth=2.4, label=rf"SFA Composite Density ($\lambda$={sfa.lambda_:.2f})")
    ax_c.axvline(0, color="gray", linestyle=":", linewidth=1.0)
    ax_c.set_xlabel(r"Regression Residual ($\varepsilon = v - u$)", fontsize=11, fontweight="bold")
    ax_c.set_ylabel("Density", fontsize=11, fontweight="bold")
    ax_c.set_title(f"(C) Negative Residual Skewness Diagnostic (p = {sfa.ols_skew_pvalue_:.4f})", fontsize=12, fontweight="bold")
    ax_c.legend(frameon=True, facecolor="white", fontsize=9)
    ax_c.grid(True, linestyle=":", alpha=0.5)
    
    # Panel D: Geographic Efficiency Map (Proximity to Ceiling)
    ax_d = axes[1, 1]
    scatter = ax_d.scatter(
        df_clean["cell_lon"], df_clean["cell_lat"],
        c=efficiency, cmap="viridis", s=18, alpha=0.85, vmin=0.3, vmax=1.0
    )
    cbar = plt.colorbar(scatter, ax=ax_d, orientation="horizontal", pad=0.12, fraction=0.05)
    cbar.set_label(r"Ceiling Efficiency ($\text{TE} = \exp(-u)$)", fontsize=10, fontweight="bold")
    ax_d.set_xlabel("Longitude (°)", fontsize=10, fontweight="bold")
    ax_d.set_ylabel("Latitude (°)", fontsize=10, fontweight="bold")
    ax_d.set_title(r"(D) Global Proximity to Macroecological Ceiling", fontsize=12, fontweight="bold")
    ax_d.grid(True, linestyle=":", alpha=0.4)
    
    plt.tight_layout()
    fig_path = figures_dir / "frontier_ceiling.png"
    v3_fig_path = v3_figures_dir / "frontier_ceiling.png"
    fig.savefig(fig_path, dpi=300)
    fig.savefig(v3_fig_path, dpi=300)
    plt.close(fig)
    print(f"[OK] Saved frontier ceiling figure to {fig_path} and {v3_fig_path}")
    
    return results_df, df_clean


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Stochastic Frontier Analysis")
    parser.add_argument("--resolution", type=str, default="5deg", choices=["5deg", "2deg"])
    args = parser.parse_args()
    run_frontier_analysis(resolution=args.resolution)
