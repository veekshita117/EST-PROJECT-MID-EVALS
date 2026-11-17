import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.common.helpers import partial_spearman


def test_reproduce_mid_eval():
    key = ["cell_lat", "cell_lon"]
    gb = pd.read_csv(os.path.join(REPO_ROOT, "data", "gbif", "gbif_richness_cells.csv"))
    pc = pd.read_csv(os.path.join(REPO_ROOT, "data", "paleoclim", "paleoclim_cell_stability.csv"))
    wc = pd.read_csv(os.path.join(REPO_ROOT, "data", "worldclim", "worldclim_cell_stability.csv"))

    df = gb.merge(pc, on=key).merge(wc, on=key)
    min_rec = 10
    df = df[df.n_records >= min_rec].copy()
    df["abs_lat"] = df.cell_lat.abs()
    df["log_n"] = np.log(df.n_records)

    # Check cell count requirement: n=188
    assert len(df) == 188, f"Expected n=188, got {len(df)}"

    expected_tab = pd.read_csv(os.path.join(REPO_ROOT, "results", "tables", "integration", "table_correlations.csv"))

    for _, row in expected_tab.iterrows():
        s = row["dataset"]
        m = row["metric"]
        expected_n = int(row["n"])
        expected_rho = float(row["rho"])
        expected_p = float(row["p"])
        expected_partial_rho = float(row["partial_rho"])
        expected_partial_p = float(row["partial_p"])

        c = f"{s}_{m}"
        rho, p = spearmanr(df[c], df["richness"])
        prho, pp = partial_spearman(df, c, "richness", ["log_n", "abs_lat"])

        assert len(df) == expected_n, f"Expected n={expected_n}, got {len(df)}"
        assert np.isclose(prho, expected_partial_rho, atol=0.002), (
            f"Mismatch in partial rho for {s}_{m}: computed {prho:.4f}, expected {expected_partial_rho:.4f}"
        )
        assert np.isclose(rho, expected_rho, atol=0.002), (
            f"Mismatch in raw rho for {s}_{m}: computed {rho:.4f}, expected {expected_rho:.4f}"
        )
        print(f"PASS: {s}_{m} (n={len(df)}, partial_rho={prho:.3f} matches expected {expected_partial_rho:.3f})")


if __name__ == "__main__":
    test_reproduce_mid_eval()
    print("All reproduction tests passed successfully.")
