"""
run_all.py
----------
Orchestrator for the multi-resolution ML pipeline.
Runs PaleoClim only (WorldClim is used solely for the PaleoClim vs WorldClim
agreement check, not for ML runs), over resolution in [base (5 deg, primary), 2deg (sensitivity)].
For each configuration, executes sequentially:
  1. run_core_cv
  2. run_loco
  3. run_residuals_diagnostics
  4. run_interpretation
Writes all outputs strictly into ml/outputs/{source}_{resolution}/.
Logs any unexpected error to BLOCKERS.md without stopping subsequent configurations.
"""

import sys
from pathlib import Path
import argparse
import traceback

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ml.run_core_cv import run_core_cv
from src.ml.run_loco import run_loco
from src.ml.run_residuals import run_residuals_diagnostics
from src.ml.run_interpret import run_interpretation


def log_blocker(source: str, resolution: str, stage: str, error_msg: str):
    """
    Append failure details to BLOCKERS.md per project rules.
    """
    blockers_path = REPO_ROOT / "results" / "ml" / "logs" / "BLOCKERS.md"
    blockers_path.parent.mkdir(parents=True, exist_ok=True)
    with open(blockers_path, "a") as f:
        f.write(f"\n### [FAILURE] Config: {source} ({resolution}) - Stage: {stage}\n")
        f.write(f"```\n{error_msg}\n```\n")
    print(f"[BLOCKER LOGGED]: Error in {source} {resolution} during {stage} logged to {blockers_path}")


def run_pipeline_for_config(source: str, resolution: str, fast: bool = False, repeats: int = 3):
    print(f"\n================================================================================")
    print(f"  STARTING PIPELINE FOR CONFIGURATION: source={source}, resolution={resolution}")
    print(f"  Fast Mode: {fast} | Repeats: {repeats}")
    print(f"================================================================================\n")
    
    stages = [
        ("core_cv", lambda: run_core_cv(source=source, resolution=resolution, fast=fast, n_repeats=repeats)),
        ("loco", lambda: run_loco(source=source, resolution=resolution, fast=fast)),
        ("residuals", lambda: run_residuals_diagnostics(source=source, resolution=resolution, fast=fast)),
        ("interpret", lambda: run_interpretation(source=source, resolution=resolution, fast=fast)),
    ]
    
    for stage_name, stage_fn in stages:
        print(f"\n>>> Executing Stage: [{stage_name}] for {source} {resolution} <<<")
        try:
            stage_fn()
            print(f"[STAGE COMPLETE]: {stage_name} ({source} {resolution}) finished successfully.")
        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"[ERROR]: Failed in stage {stage_name} for {source} {resolution}: {e}")
            log_blocker(source, resolution, stage_name, err_trace)
            return False
            
    print(f"\n[CONFIGURATION SUCCESS]: Completed all {len(stages)} stages for {source} {resolution}.\n")
    return True


def run_all(only_source: str = None, only_resolution: str = None, fast: bool = False, repeats: int = 3):
    sources = [only_source] if only_source else ["paleoclim"]
    resolutions = [only_resolution] if only_resolution else ["base", "2deg"]
    
    print("\n=======================================================")
    print("  RUN ALL CONFIGURATIONS (STAGE 8 ROBUSTNESS PIPELINE)")
    print(f"  Sources: {sources}")
    print(f"  Resolutions: {resolutions}")
    print(f"  Fast Mode: {fast} | Repeats: {repeats}")
    print("=======================================================\n")
    
    status_summary = {}
    
    for src in sources:
        for res in resolutions:
            cfg_key = f"{src}_{res}"
            success = run_pipeline_for_config(src, res, fast=fast, repeats=repeats)
            status_summary[cfg_key] = "SUCCESS" if success else "FAILED"
            
    print("\n=======================================================")
    print("  PIPELINE EXECUTION SUMMARY ACROSS CONFIGURATIONS")
    print("=======================================================")
    for cfg_key, status in status_summary.items():
        print(f"  {cfg_key:20s}: {status}")
    print("=======================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 8: Run Complete Pipeline Across Configurations")
    parser.add_argument("--source", type=str, default=None, choices=["paleoclim"])
    parser.add_argument("--resolution", type=str, default=None, choices=["base", "2deg"])
    parser.add_argument("--only-source", type=str, default=None, choices=["paleoclim"])
    parser.add_argument("--only-resolution", type=str, default=None, choices=["base", "2deg"])
    parser.add_argument("--fast", action="store_true", help="Fast execution mode")
    parser.add_argument("--repeats", type=int, default=3, help="Number of block-shift repeats for core CV")
    args = parser.parse_args()
    
    src = args.only_source or args.source
    res = args.only_resolution or args.resolution
    
    run_all(only_source=src, only_resolution=res, fast=args.fast, repeats=args.repeats)
