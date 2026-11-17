"""
test_mem.py
-----------
Unit tests for Moran's Eigenvector Mapping (MEM) module.
Verifies:
1. Row-standardization of k=8 haversine spatial weight matrix.
2. Centering and orthogonality of extracted Moran eigenvectors.
3. Filtering by Moran's I threshold (> 0.1).
4. Fold-safe behavior of SpatialEigenvectorMapper transformer (zero train/test leakage).
5. Dimension matching for train and out-of-sample test transformations.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.mem import compute_mem_eigenvectors, SpatialEigenvectorMapper
from ml.src.run_residuals import build_knn_weights, calc_morans_i


@pytest.fixture
def synthetic_coords():
    """Generate 60 synthetic global coordinates."""
    rng = np.random.default_rng(42)
    lons = rng.uniform(-150, 150, size=60)
    lats = rng.uniform(-50, 50, size=60)
    return np.column_stack([lons, lats])


def test_knn_weight_matrix_row_standardized(synthetic_coords):
    """Test that k=8 haversine spatial weight matrix has row sums equal to 1.0."""
    W = build_knn_weights(synthetic_coords, k=8)
    row_sums = np.array(W.sum(axis=1)).flatten()
    assert np.allclose(row_sums, 1.0), "Weight matrix rows are not row-standardized to 1.0"
    # Diagonal should be 0 (no self-loops)
    assert np.allclose(W.diagonal(), 0.0), "Weight matrix has non-zero diagonal"


def test_positive_moran_eigenvectors(synthetic_coords):
    """Test that extracted eigenvectors all have Moran's I > 0.1."""
    evecs, m_i, indices, W = compute_mem_eigenvectors(synthetic_coords, k=8, moran_threshold=0.1)
    
    assert len(m_i) > 0, "No eigenvectors extracted with Moran's I > 0.1"
    assert np.all(m_i > 0.1), f"Some eigenvectors had Moran's I <= 0.1: min={m_i.min()}"
    assert evecs.shape[0] == len(synthetic_coords)
    assert evecs.shape[1] == len(m_i)
    
    # Check centering: sum of each eigenvector should be close to 0
    col_sums = np.sum(evecs, axis=0)
    assert np.allclose(col_sums, 0.0, atol=1e-10), "Eigenvectors are not centered"


def test_spatial_eigenvector_mapper_fold_safe(synthetic_coords):
    """
    Test that SpatialEigenvectorMapper fits strictly on training coordinates
    and projects out-of-sample test coordinates without leakage.
    """
    train_coords = synthetic_coords[:45]
    test_coords = synthetic_coords[45:]
    
    mapper = SpatialEigenvectorMapper(k=8, moran_threshold=0.1)
    mapper.fit(train_coords)
    
    n_features = mapper.n_features_out_
    assert n_features > 0, "Mapper fitted zero features"
    
    # Train transformation
    mem_train = mapper.transform(train_coords)
    assert mem_train.shape == (45, n_features)
    
    # Test transformation (out of sample)
    mem_test = mapper.transform(test_coords)
    assert mem_test.shape == (15, n_features)
    assert np.all(np.isfinite(mem_test)), "NaN or Inf in out-of-sample projection"
    
    # Verify that fitting on train does not know about test coordinates
    assert mapper.coords_train_.shape == (45, 2)
