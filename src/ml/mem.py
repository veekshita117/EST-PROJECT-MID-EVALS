"""
mem.py
------
Spatial Eigenvector Mapping (Moran's Eigenvector Maps - MEM).

Implements:
1. Row-standardized k=8 haversine spatial weight matrix construction.
2. Symmetrization and double-centering (H W_sym H).
3. Positive Moran eigenvector extraction filtered by Moran's I > 0.1.
4. Fold-safe SpatialEigenvectorMapper transformer with out-of-sample projection
   to prevent spatial data leakage across CV splits.
5. Model evaluation comparing residual Moran's I and delta-R² before and after MEM
   for Random Forest (RF) and HistGradientBoosting (HGB).
"""

import sys
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.neighbors import BallTree

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ml.run_residuals import calc_morans_i, build_knn_weights


def compute_mem_eigenvectors(
    coords_deg: np.ndarray,
    k: int = 8,
    moran_threshold: float = 0.1
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, csr_matrix]:
    """
    Construct spatial weight matrix and extract positive Moran eigenvectors.
    
    Parameters
    ----------
    coords_deg : np.ndarray of shape (N, 2)
        Array of [lon, lat] in degrees.
    k : int, default=8
        Number of nearest neighbors for haversine spatial weights.
    moran_threshold : float, default=0.1
        Minimum Moran's I threshold to retain eigenvectors.
        
    Returns
    -------
    selected_eigenvectors : np.ndarray of shape (N, n_selected)
        Retained Moran eigenvectors.
    selected_morans_i : np.ndarray of shape (n_selected,)
        Moran's I value of each retained eigenvector.
    selected_indices : np.ndarray
        Indices of selected eigenvectors.
    W_knn : csr_matrix of shape (N, N)
        Row-standardized k-NN spatial weight matrix.
    """
    N = len(coords_deg)
    if N <= k:
        raise ValueError(f"Sample size N={N} must be greater than k={k}")
        
    # 1. Build row-standardized k-NN weight matrix
    W_knn = build_knn_weights(coords_deg, k=k)
    
    # 2. Symmetrize W: (W + W^T) / 2
    W_dense = W_knn.toarray()
    W_sym = 0.5 * (W_dense + W_dense.T)
    
    # 3. Double-center: H = I - 1/N * 1 1^T, M = H W_sym H
    H = np.eye(N) - (1.0 / N) * np.ones((N, N))
    M = H @ W_sym @ H
    
    # 4. Eigendecomposition of symmetric matrix M
    eigenvalues, eigenvectors = np.linalg.eigh(M)
    
    # Sort eigenvalues and eigenvectors in descending order
    idx_sort = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx_sort]
    eigenvectors = eigenvectors[:, idx_sort]
    
    # Compute exact Moran's I for each eigenvector
    # For row-standardized W, sum(W) = N.
    # For centered eigenvector z: Moran's I(z) = (z^T W z) / (z^T z) = z^T W_sym z = eigenvalue
    morans_i_vals = []
    for j in range(N):
        ev = eigenvectors[:, j]
        res = calc_morans_i(ev, W_knn, n_permutations=0)
        morans_i_vals.append(res["I"])
    morans_i_vals = np.array(morans_i_vals)
    
    # 5. Filter positive Moran eigenvectors where Moran's I > moran_threshold
    mask = morans_i_vals > moran_threshold
    selected_indices = np.where(mask)[0]
    selected_eigenvectors = eigenvectors[:, selected_indices]
    selected_morans_i = morans_i_vals[selected_indices]
    
    return selected_eigenvectors, selected_morans_i, selected_indices, W_knn


class SpatialEigenvectorMapper(BaseEstimator, TransformerMixin):
    """
    Fold-safe Moran's Eigenvector Mapping (MEM) Transformer.
    
    Fits the spatial eigenvectors on training fold coordinates only.
    Projects onto out-of-sample coordinates using row-standardized k-NN interpolation:
        E_test = W_{test -> train} @ E_train
    This prevents spatial data leakage across cross-validation splits.
    """
    def __init__(self, k: int = 8, moran_threshold: float = 0.1, max_eigenvectors: Optional[int] = None):
        self.k = k
        self.moran_threshold = moran_threshold
        self.max_eigenvectors = max_eigenvectors
        self.coords_train_ = None
        self.train_tree_ = None
        self.eigenvectors_train_ = None
        self.morans_i_train_ = None
        self.selected_indices_ = None
        self.n_features_out_ = 0
        
    def fit(self, X_coords: np.ndarray, y=None):
        """
        Fit MEM on training spatial coordinates.
        
        Parameters
        ----------
        X_coords : np.ndarray of shape (N_train, 2)
            Array of [lon, lat] coordinates in degrees.
        """
        coords = np.asarray(X_coords, dtype=float)
        self.coords_train_ = coords.copy()
        
        # Compute MEM on training coordinates
        evecs, m_i, indices, _ = compute_mem_eigenvectors(
            coords, k=self.k, moran_threshold=self.moran_threshold
        )
        
        if self.max_eigenvectors is not None and evecs.shape[1] > self.max_eigenvectors:
            evecs = evecs[:, :self.max_eigenvectors]
            m_i = m_i[:self.max_eigenvectors]
            indices = indices[:self.max_eigenvectors]
            
        self.eigenvectors_train_ = evecs
        self.morans_i_train_ = m_i
        self.selected_indices_ = indices
        self.n_features_out_ = evecs.shape[1]
        
        # Build BallTree on training coordinates (in radians [lat, lon])
        lat_rad = np.radians(coords[:, 1])
        lon_rad = np.radians(coords[:, 0])
        coords_rad = np.column_stack([lat_rad, lon_rad])
        self.train_tree_ = BallTree(coords_rad, metric="haversine")
        
        return self
        
    def transform(self, X_coords: np.ndarray) -> np.ndarray:
        """
        Transform coordinates into MEM feature representations.
        
        If X_coords is identical in size and values to training coordinates,
        returns fitted eigenvectors. Otherwise, projects onto test coordinates
        using row-standardized k-NN haversine weighting.
        """
        if self.eigenvectors_train_ is None or self.n_features_out_ == 0:
            return np.empty((len(X_coords), 0), dtype=float)
            
        coords = np.asarray(X_coords, dtype=float)
        
        # Check if transforming training data exactly
        if coords.shape == self.coords_train_.shape and np.allclose(coords, self.coords_train_):
            return self.eigenvectors_train_.copy()
            
        # Out-of-sample projection
        lat_rad = np.radians(coords[:, 1])
        lon_rad = np.radians(coords[:, 0])
        query_rad = np.column_stack([lat_rad, lon_rad])
        
        # Query k nearest training points
        eff_k = min(self.k, len(self.coords_train_))
        _, indices = self.train_tree_.query(query_rad, k=eff_k)
        
        N_test = len(coords)
        N_train = len(self.coords_train_)
        
        # Build row-standardized cross-weight matrix
        W_proj = lil_matrix((N_test, N_train), dtype=float)
        for i in range(N_test):
            nbrs = indices[i]
            W_proj[i, nbrs] = 1.0 / eff_k
            
        # Project training eigenvectors
        E_test = W_proj.tocsr().dot(self.eigenvectors_train_)
        return E_test
        
    def fit_transform(self, X_coords: np.ndarray, y=None) -> np.ndarray:
        return self.fit(X_coords, y).transform(X_coords)
        
    def get_feature_names_out(self, input_features=None) -> List[str]:
        return [f"mem_{i+1}" for i in range(self.n_features_out_)]
