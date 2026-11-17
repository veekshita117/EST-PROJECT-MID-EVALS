"""
verify_foundation.py
--------------------
Verification script for Stage 2 Foundation layer.
Prints:
- Filtered row counts
- Number of 20° spatial blocks
- Cells per continent
- Features per group and nested feature sets
- Spatial outer fold sizes and LOCO fold sizes
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.src.data import load_dataset
from ml.src.cv import spatial_outer_folds, loco_folds


def run_foundation_verification():
    print("=" * 80)
    print("STAGE 2 FOUNDATION VERIFICATION REPORT")
    print("=" * 80)
    
    for source in ["paleoclim", "worldclim"]:
        for res in ["base", "2deg"]:
            res_label = "5-degree (base)" if res == "base" else "2-degree"
            print(f"\n>>> Source: {source.upper()} | Resolution: {res_label} <<<")
            
            df, feature_groups, feature_sets = load_dataset(source=source, resolution=res)
            
            # 1. Row counts
            print(f"\n1. ROWS:")
            print(f"   Clean, filtered rows: {len(df)} (target y: min={df['y'].min():.3f}, max={df['y'].max():.3f})")
            
            # 2. Number of blocks
            folds, groups = spatial_outer_folds(df, k=5, seed=42, offset=0.0, reuse_phase6=(res == "base"))
            n_blocks = len(groups.unique())
            print(f"\n2. NUMBER OF 20° BLOCKS:")
            print(f"   Occupied 20° spatial blocks: {n_blocks}")
            
            # 3. Cells per continent
            print(f"\n3. CELLS PER CONTINENT:")
            for cont, cnt in df["continent"].value_counts().items():
                print(f"   - {cont}: {cnt} cells")
                
            # 4. Features per group & sets
            print(f"\n4. FEATURES PER GROUP:")
            for grp_name, f_list in feature_groups.items():
                print(f"   - {grp_name} ({len(f_list)} features): {f_list}")
                
            print(f"\n   FEATURE SETS (M0..M3):")
            for fs_name in ["M0", "M1", "M2a", "M2b", "M3a", "M3b"]:
                print(f"   - {fs_name} ({len(feature_sets[fs_name])} features): {feature_sets[fs_name]}")
                
            # 5. Fold sizes
            print(f"\n5. FOLD SIZES (5-Fold Spatial CV):")
            for f_idx, (tr, te) in enumerate(folds):
                print(f"   - Fold {f_idx + 1}: Train={len(tr)} cells, Test={len(te)} cells")
                
            print(f"\n   LOCO FOLD SIZES (min_cells=15):")
            loco_splits = loco_folds(df, min_cells=15)
            for tr, te, cname in loco_splits:
                print(f"   - Test {cname}: {len(te)} cells (Train: {len(tr)} cells)")
                
    print("\n" + "=" * 80)
    print("ALL FOUNDATION VERIFICATIONS COMPLETED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    run_foundation_verification()
