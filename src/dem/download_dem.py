import os
import sys
import re
import time
import urllib.request
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import rasterio
from rasterio.transform import from_origin
from scipy.stats import spearmanr

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RAW_DIR = os.path.join(REPO_ROOT, "COPERNICUS_DEM", "raw")
TILES_DIR = os.path.join(RAW_DIR, "tiles")
PROCESSED_DIR = os.path.join(REPO_ROOT, "data", "dem")
FIGURES_DIR = os.path.join(REPO_ROOT, "results", "figures", "dem")
CACHE_FILE = os.path.join(RAW_DIR, "tile_stats_cache.csv")

os.makedirs(TILES_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)


def parse_tile(t):
    m = re.search(r"([NS])(\d+)_00_([EW])(\d+)_00", t)
    if not m:
        return None, None
    ns, lat_val, ew, lon_val = m.groups()
    lat = int(lat_val) if ns == "N" else -int(lat_val)
    lon = int(lon_val) if ew == "E" else -int(lon_val)
    return lat, lon


def get_tile_url(t):
    return f"https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com/{t}/{t}.tif"


def process_single_tile(tile_info, target_res=0.01, retries=3):
    t, tlat, tlon = tile_info
    out_tif = os.path.join(TILES_DIR, f"{t}.tif")
    url = get_tile_url(t)
    
    # Target resolution: 0.01 degree -> 100 x 100 pixels for 1x1 degree tile
    out_dim = int(round(1.0 / target_res))
    
    for attempt in range(retries):
        try:
            with rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                AWS_NO_SIGN_REQUEST="YES",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                VSI_CACHE="TRUE"
            ):
                with rasterio.open(url) as src:
                    # Decimated read: 100 x 100
                    arr = src.read(1, out_shape=(out_dim, out_dim)).astype(np.float32)
                    nd = src.nodata
                    if nd is not None:
                        arr[arr == nd] = np.nan
                    # Mask invalid elevation values (< -1000m or > 9000m)
                    arr[arr < -1000] = np.nan
                    arr[arr > 9000] = np.nan
                    
                    # Save reduced GeoTIFF to COPERNICUS_DEM/raw/tiles/
                    # tile coordinates: bottom-left is (tlon, tlat), top-left is (tlon, tlat + 1.0)
                    transform = from_origin(float(tlon), float(tlat + 1.0), target_res, target_res)
                    profile = {
                        "driver": "GTiff",
                        "height": out_dim,
                        "width": out_dim,
                        "count": 1,
                        "dtype": "float32",
                        "crs": "EPSG:4326",
                        "transform": transform,
                        "compress": "deflate",
                        "nodata": np.nan
                    }
                    with rasterio.open(out_tif, "w", **profile) as dst:
                        dst.write(arr, 1)
                    
                    valid = arr[~np.isnan(arr)]
                    if len(valid) == 0:
                        return {
                            "tile": t,
                            "tile_lat": tlat,
                            "tile_lon": tlon,
                            "count": 0,
                            "sum_elev": 0.0,
                            "sum_sq_elev": 0.0,
                            "min_elev": np.nan,
                            "max_elev": np.nan,
                            "status": "empty"
                        }
                    
                    return {
                        "tile": t,
                        "tile_lat": tlat,
                        "tile_lon": tlon,
                        "count": len(valid),
                        "sum_elev": float(np.sum(valid)),
                        "sum_sq_elev": float(np.sum(valid.astype(np.float64)**2)),
                        "min_elev": float(np.min(valid)),
                        "max_elev": float(np.max(valid)),
                        "status": "success"
                    }
        except Exception as e:
            if attempt == retries - 1:
                return {
                    "tile": t,
                    "tile_lat": tlat,
                    "tile_lon": tlon,
                    "count": 0,
                    "sum_elev": 0.0,
                    "sum_sq_elev": 0.0,
                    "min_elev": np.nan,
                    "max_elev": np.nan,
                    "status": f"failed: {str(e)}"
                }
            time.sleep(0.5 * (attempt + 1))


def download_and_accumulate_dem(max_workers=32):
    print("=== COPERNICUS DEM GLO-90 DOWNLOAD & PROCESSING PIPELINE ===")
    
    # 1. Fetch tile list
    tile_list_url = "https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com/tileList.txt"
    print(f"Reading tile catalogue from: {tile_list_url}")
    with urllib.request.urlopen(tile_list_url) as resp:
        all_tiles = [line.strip() for line in resp.read().decode("utf-8").splitlines() if line.strip()]
    print(f"Total tiles in GLO-90 catalogue: {len(all_tiles)}")
    
    # Parse tile coordinates
    parsed = []
    for t in all_tiles:
        lat, lon = parse_tile(t)
        if lat is not None:
            # 5° cell center: floor(lat/5)*5 + 2.5
            # 2° cell center: floor(lat/2)*2 + 1.0
            clat5 = np.floor(lat / 5.0) * 5.0 + 2.5
            clon5 = np.floor(lon / 5.0) * 5.0 + 2.5
            clat2 = np.floor(lat / 2.0) * 2.0 + 1.0
            clon2 = np.floor(lon / 2.0) * 2.0 + 1.0
            parsed.append((t, lat, lon, clat5, clon5, clat2, clon2))
    
    df_catalog = pd.DataFrame(parsed, columns=["tile", "tile_lat", "tile_lon", "cell_lat_5", "cell_lon_5", "cell_lat_2", "cell_lon_2"])
    
    # Target analysis cells: the 375 GBIF cells (covering all 188 mid-eval cells, Himalaya, Andes, Amazon, Siberia, Africa, etc.)
    gbif_cells = pd.read_csv(os.path.join(REPO_ROOT, "data", "gbif", "gbif_richness_cells.csv"))
    target_5deg = gbif_cells[["cell_lat", "cell_lon"]].drop_duplicates()
    
    # Filter catalog to tiles intersecting these cells
    target_tiles = df_catalog.merge(
        target_5deg,
        left_on=["cell_lat_5", "cell_lon_5"],
        right_on=["cell_lat", "cell_lon"]
    ).drop(columns=["cell_lat", "cell_lon"])
    
    print(f"Analysis grid cells (5°): {len(target_5deg)}")
    print(f"Tiles intersecting analysis cells: {len(target_tiles)}")
    
    # 2. Check cache for resumability
    cached_df = None
    cached_tiles = set()
    if os.path.exists(CACHE_FILE):
        try:
            cached_df = pd.read_csv(CACHE_FILE)
            cached_tiles = set(cached_df["tile"].tolist())
            print(f"Found cache file with {len(cached_tiles)} previously processed tiles.")
        except Exception:
            cached_df = None
    
    tiles_to_process = [
        (r.tile, r.tile_lat, r.tile_lon)
        for _, r in target_tiles.iterrows()
        if r.tile not in cached_tiles
    ]
    print(f"Tiles remaining to process: {len(tiles_to_process)}")
    
    new_results = []
    if tiles_to_process:
        print(f"Processing tiles with {max_workers} concurrent workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_tile = {executor.submit(process_single_tile, item): item[0] for item in tiles_to_process}
            with tqdm(total=len(tiles_to_process), desc="Downloading GLO-90 tiles") as pbar:
                for future in as_completed(future_to_tile):
                    res = future.result()
                    new_results.append(res)
                    pbar.update(1)
        
        new_df = pd.DataFrame(new_results)
        if cached_df is not None:
            combined_cache = pd.concat([cached_df, new_df], ignore_index=True).drop_duplicates(subset=["tile"])
        else:
            combined_cache = new_df
        combined_cache.to_csv(CACHE_FILE, index=False)
    else:
        combined_cache = cached_df
    
    # Folder size calculation
    total_size = sum(
        os.path.getsize(os.path.join(TILES_DIR, f))
        for f in os.listdir(TILES_DIR)
        if os.path.isfile(os.path.join(TILES_DIR, f))
    )
    print(f"\nTotal tiles in raw folder: {len(os.listdir(TILES_DIR))}")
    print(f"Total folder size of COPERNICUS_DEM/raw/tiles: {total_size / (1024*1024):.2f} MB")
    
    # 3. Aggregate tile pieces correctly using sums and sums of squares
    df_merged = target_tiles.merge(combined_cache, on=["tile", "tile_lat", "tile_lon"])
    valid_tiles = df_merged[df_merged["count"] > 0].copy()
    print(f"Valid land tiles accumulated: {len(valid_tiles)} / {len(df_merged)}")
    
    # Aggregate 5° cells
    print("\nAggregating 5° cell statistics...")
    agg_5 = valid_tiles.groupby(["cell_lat_5", "cell_lon_5"]).agg(
        pixel_count=("count", "sum"),
        sum_elev=("sum_elev", "sum"),
        sum_sq_elev=("sum_sq_elev", "sum"),
        elevation_min=("min_elev", "min"),
        elevation_max=("max_elev", "max")
    ).reset_index().rename(columns={"cell_lat_5": "cell_lat", "cell_lon_5": "cell_lon"})
    
    agg_5["elevation_mean"] = agg_5["sum_elev"] / agg_5["pixel_count"]
    var_5 = (agg_5["sum_sq_elev"] - (agg_5["sum_elev"]**2) / agg_5["pixel_count"]) / np.maximum(1, agg_5["pixel_count"] - 1)
    agg_5["elevation_sd"] = np.sqrt(np.maximum(0.0, var_5))
    agg_5["relief_range"] = agg_5["elevation_max"] - agg_5["elevation_min"]
    agg_5["topographic_heterogeneity"] = agg_5["relief_range"]  # Primary heterogeneity metric
    
    out_5 = agg_5[[
        "cell_lat", "cell_lon", "elevation_mean", "elevation_sd",
        "elevation_min", "elevation_max", "relief_range",
        "topographic_heterogeneity", "pixel_count"
    ]].round(2)
    out_5.to_csv(os.path.join(PROCESSED_DIR, "dem_cells_5deg.csv"), index=False)
    print(f"Saved 5° DEM statistics: {len(out_5)} cells to dem_cells_5deg.csv")
    
    # Aggregate 2° cells
    print("Aggregating 2° cell statistics...")
    agg_2 = valid_tiles.groupby(["cell_lat_2", "cell_lon_2"]).agg(
        pixel_count=("count", "sum"),
        sum_elev=("sum_elev", "sum"),
        sum_sq_elev=("sum_sq_elev", "sum"),
        elevation_min=("min_elev", "min"),
        elevation_max=("max_elev", "max")
    ).reset_index().rename(columns={"cell_lat_2": "cell_lat", "cell_lon_2": "cell_lon"})
    
    agg_2["elevation_mean"] = agg_2["sum_elev"] / agg_2["pixel_count"]
    var_2 = (agg_2["sum_sq_elev"] - (agg_2["sum_elev"]**2) / agg_2["pixel_count"]) / np.maximum(1, agg_2["pixel_count"] - 1)
    agg_2["elevation_sd"] = np.sqrt(np.maximum(0.0, var_2))
    agg_2["relief_range"] = agg_2["elevation_max"] - agg_2["elevation_min"]
    agg_2["topographic_heterogeneity"] = agg_2["relief_range"]
    
    out_2 = agg_2[[
        "cell_lat", "cell_lon", "elevation_mean", "elevation_sd",
        "elevation_min", "elevation_max", "relief_range",
        "topographic_heterogeneity", "pixel_count"
    ]].round(2)
    out_2.to_csv(os.path.join(PROCESSED_DIR, "dem_cells_2deg.csv"), index=False)
    print(f"Saved 2° DEM statistics: {len(out_2)} cells to dem_cells_2deg.csv")
    
    # 4. Correlation with Climate Stability Metrics and Latitude (on the 188 analysed cells)
    print("\n" + "=" * 60)
    print("CORRELATION ANALYSIS: ELEVATION & TOPOGRAPHIC HETEROGENEITY")
    print("=" * 60)
    int_cells = pd.read_csv(os.path.join(REPO_ROOT, "results", "tables", "integration", "table_integrated_cells.csv"))
    merged_elev = int_cells.merge(out_5, on=["cell_lat", "cell_lon"])
    print(f"Analysed cells with elevation data: {len(merged_elev)} (expected 188)")
    
    corr_rows = []
    climate_vars = ["pc_lgm_change", "pc_instability", "wc_lgm_change", "wc_instability", "abs_lat"]
    for elev_v in ["elevation_mean", "elevation_sd", "relief_range"]:
        for clim_v in climate_vars:
            r = np.corrcoef(merged_elev[elev_v], merged_elev[clim_v])[0, 1]
            rho, p = spearmanr(merged_elev[elev_v], merged_elev[clim_v])
            corr_rows.append({
                "elevation_variable": elev_v,
                "climate_variable": clim_v,
                "pearson_r": round(r, 3),
                "spearman_rho": round(rho, 3),
                "p_value": round(p, 4)
            })
    
    df_corr = pd.DataFrame(corr_rows)
    print("\nElevation & Heterogeneity Correlations:")
    print(df_corr.to_string(index=False))
    df_corr.to_csv(os.path.join(PROCESSED_DIR, "table_elevation_correlations.csv"), index=False)
    
    # 5. Acceptance Check: Top 10 Highest Relief and Bottom 10 Lowest Relief Cells
    print("\n" + "=" * 60)
    print("ACCEPTANCE CHECK: TOP 10 HIGHEST RELIEF CELLS (HIMALAYA / ANDES)")
    print("=" * 60)
    top10 = out_5.sort_values("relief_range", ascending=False).head(10).copy()
    
    # Approximate geographic region labeling
    def get_region(row):
        lat, lon = row.cell_lat, row.cell_lon
        if 25 <= lat <= 38 and 70 <= lon <= 100:
            return "Himalaya / Tibetan Plateau"
        elif -55 <= lat <= 12 and -80 <= lon <= -65:
            return "Andes"
        elif 35 <= lat <= 48 and 5 <= lon <= 18:
            return "European Alps"
        elif 30 <= lat <= 60 and -125 <= lon <= -105:
            return "North American Rockies / Cascades"
        elif -5 <= lat <= 5 and -75 <= lon <= -50:
            return "Amazon Lowlands"
        elif 55 <= lat <= 75 and 60 <= lon <= 110:
            return "Siberian Lowlands"
        elif -35 <= lat <= -20 and 15 <= lon <= 35:
            return "South Africa"
        else:
            return "Other"
    
    top10["region"] = top10.apply(get_region, axis=1)
    print(top10[["cell_lat", "cell_lon", "relief_range", "elevation_mean", "elevation_sd", "region"]].to_string(index=False))
    
    print("\n" + "=" * 60)
    print("ACCEPTANCE CHECK: BOTTOM 10 LOWEST RELIEF CELLS (AMAZON / SIBERIA / COASTAL LOWLANDS)")
    print("=" * 60)
    bottom10 = out_5.sort_values("relief_range", ascending=True).head(10).copy()
    bottom10["region"] = bottom10.apply(get_region, axis=1)
    print(bottom10[["cell_lat", "cell_lon", "relief_range", "elevation_mean", "elevation_sd", "region"]].to_string(index=False))
    
    # 6. Figures
    print("\nGenerating Figures...")
    # Fig 1: Mean elevation global map
    plt.figure(figsize=(10, 4.8))
    sc = plt.scatter(
        out_5["cell_lon"], out_5["cell_lat"],
        c=out_5["elevation_mean"], s=25, marker="s", cmap="terrain"
    )
    plt.colorbar(sc, label="Mean Elevation (m)", shrink=0.7)
    plt.title("Copernicus DEM (GLO-90): Mean Elevation per 5° Cell", fontsize=12)
    plt.xlabel("Longitude (°)")
    plt.ylabel("Latitude (°)")
    plt.xlim(-180, 180)
    plt.ylim(-90, 90)
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig(os.path.join(FIGURES_DIR, "dem_mean_elevation.png"), dpi=200, bbox_inches="tight")
    plt.close()
    
    # Fig 2: Topographic heterogeneity (relief range) global map
    plt.figure(figsize=(10, 4.8))
    sc = plt.scatter(
        out_5["cell_lon"], out_5["cell_lat"],
        c=out_5["relief_range"], s=25, marker="s", cmap="magma_r"
    )
    plt.colorbar(sc, label="Topographic Relief Range (m)", shrink=0.7)
    plt.title("Copernicus DEM (GLO-90): Topographic Heterogeneity (Max - Min Elevation)", fontsize=12)
    plt.xlabel("Longitude (°)")
    plt.ylabel("Latitude (°)")
    plt.xlim(-180, 180)
    plt.ylim(-90, 90)
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig(os.path.join(FIGURES_DIR, "dem_heterogeneity.png"), dpi=200, bbox_inches="tight")
    plt.close()
    
    # Fig 3: Histograms of mean elevation and relief range
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].hist(out_5["elevation_mean"].dropna(), bins=30, color="forestgreen", edgecolor="black", alpha=0.7)
    axes[0].set_title("Mean Elevation Distribution (5°)")
    axes[0].set_xlabel("Mean Elevation (m)")
    axes[0].set_ylabel("Cell Count")
    axes[0].grid(True, linestyle="--", alpha=0.3)
    
    axes[1].hist(out_5["relief_range"].dropna(), bins=30, color="darkorange", edgecolor="black", alpha=0.7)
    axes[1].set_title("Topographic Relief Range Distribution (5°)")
    axes[1].set_xlabel("Relief Range (m)")
    axes[1].set_ylabel("Cell Count")
    axes[1].grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "dem_histograms.png"), dpi=200, bbox_inches="tight")
    plt.close()
    
    # Fig 4: Scatter of Topographic Heterogeneity vs LGM Temperature Change
    plt.figure(figsize=(6, 5))
    plt.scatter(merged_elev["relief_range"], merged_elev["pc_lgm_change"], s=20, alpha=0.6, color="purple")
    r_val = np.corrcoef(merged_elev["relief_range"], merged_elev["pc_lgm_change"])[0, 1]
    rho_val, _ = spearmanr(merged_elev["relief_range"], merged_elev["pc_lgm_change"])
    plt.title(f"Heterogeneity vs LGM Temp Change (r={r_val:.2f}, rho={rho_val:.2f})")
    plt.xlabel("Topographic Relief Range (m)")
    plt.ylabel("PaleoClim |Present - LGM| (°C)")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.savefig(os.path.join(FIGURES_DIR, "dem_vs_lgm_change.png"), dpi=200, bbox_inches="tight")
    plt.close()
    
    print("Pipeline completed successfully.")


def download_global_dem(max_workers=64):
    print("=== COPERNICUS DEM GLO-90 GLOBAL LAND CELLS PIPELINE ===")
    
    # 1. Fetch tile list
    tile_list_url = "https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com/tileList.txt"
    print(f"Reading tile catalogue from: {tile_list_url}")
    with urllib.request.urlopen(tile_list_url) as resp:
        all_tiles = [line.strip() for line in resp.read().decode("utf-8").splitlines() if line.strip()]
    print(f"Total tiles in GLO-90 catalogue: {len(all_tiles)}")
    
    # Parse tile coordinates
    parsed = []
    for t in all_tiles:
        lat, lon = parse_tile(t)
        if lat is not None:
            clat5 = np.floor(lat / 5.0) * 5.0 + 2.5
            clon5 = np.floor(lon / 5.0) * 5.0 + 2.5
            clat2 = np.floor(lat / 2.0) * 2.0 + 1.0
            clon2 = np.floor(lon / 2.0) * 2.0 + 1.0
            parsed.append((t, lat, lon, clat5, clon5, clat2, clon2))
    
    df_catalog = pd.DataFrame(parsed, columns=["tile", "tile_lat", "tile_lon", "cell_lat_5", "cell_lon_5", "cell_lat_2", "cell_lon_2"])
    
    # Load all land cells from PaleoClim zonal tables (5° and 2°)
    pc5 = pd.read_csv(os.path.join(REPO_ROOT, "data", "paleoclim", "paleoclim_zonal_5deg.csv"))[["cell_lat", "cell_lon"]].drop_duplicates()
    pc2 = pd.read_csv(os.path.join(REPO_ROOT, "data", "paleoclim", "paleoclim_zonal_2deg.csv"))[["cell_lat", "cell_lon"]].drop_duplicates()
    
    tiles_5 = df_catalog.merge(pc5, left_on=["cell_lat_5", "cell_lon_5"], right_on=["cell_lat", "cell_lon"]).drop(columns=["cell_lat", "cell_lon"])
    tiles_2 = df_catalog.merge(pc2, left_on=["cell_lat_2", "cell_lon_2"], right_on=["cell_lat", "cell_lon"]).drop(columns=["cell_lat", "cell_lon"])
    target_tiles = pd.concat([tiles_5, tiles_2]).drop_duplicates(subset=["tile"])
    
    print(f"PaleoClim 5° land cells: {len(pc5)}, 2° land cells: {len(pc2)}")
    print(f"Tiles intersecting 5° land cells: {len(tiles_5)}")
    print(f"Tiles intersecting 2° land cells: {len(tiles_2)}")
    print(f"Total unique 1° tiles intersecting land cells: {len(target_tiles)}")
    
    # 2. Check existing cache
    cached_df = None
    cached_tiles = set()
    if os.path.exists(CACHE_FILE):
        try:
            cached_df = pd.read_csv(CACHE_FILE)
            cached_tiles = set(cached_df["tile"].tolist())
            print(f"Found cache file with {len(cached_tiles)} previously processed tiles.")
        except Exception as e:
            print(f"Error reading cache: {e}")
            cached_df = None
    
    tiles_to_process = [
        (r.tile, r.tile_lat, r.tile_lon)
        for _, r in target_tiles.iterrows()
        if r.tile not in cached_tiles
    ]
    new_tiles_needed = len(tiles_to_process)
    estimated_size_mb = new_tiles_needed * 0.0286
    estimated_size_gb = estimated_size_mb / 1024.0
    print(f"\nTiles remaining to process: {new_tiles_needed}")
    print(f"Estimated size of new tiles: {estimated_size_mb:.2f} MB ({estimated_size_gb:.3f} GB)")
    
    if estimated_size_gb > 5.0:
        print(f"STOPPING: Estimated size ({estimated_size_gb:.3f} GB) exceeds 5 GB threshold.")
        return
    
    # 3. Process missing tiles with resumability
    if tiles_to_process:
        print(f"Processing {new_tiles_needed} tiles with {max_workers} concurrent workers...")
        new_results = []
        batch_size = 200
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_tile = {executor.submit(process_single_tile, item): item[0] for item in tiles_to_process}
            with tqdm(total=len(tiles_to_process), desc="Downloading GLO-90 tiles") as pbar:
                for future in as_completed(future_to_tile):
                    res = future.result()
                    new_results.append(res)
                    pbar.update(1)
                    
                    # Flush periodically to cache
                    if len(new_results) % batch_size == 0:
                        batch_df = pd.DataFrame(new_results)
                        if cached_df is not None:
                            combined = pd.concat([cached_df, batch_df], ignore_index=True).drop_duplicates(subset=["tile"])
                        else:
                            combined = batch_df
                        combined.to_csv(CACHE_FILE, index=False)
        
        new_df = pd.DataFrame(new_results)
        if cached_df is not None:
            combined_cache = pd.concat([cached_df, new_df], ignore_index=True).drop_duplicates(subset=["tile"])
        else:
            combined_cache = new_df
        combined_cache.to_csv(CACHE_FILE, index=False)
        print(f"Cache updated: total {len(combined_cache)} tiles in {CACHE_FILE}")
    else:
        combined_cache = cached_df
        print("All target tiles already cached.")
    
    # 4. Aggregate tile pieces into 5° and 2° cells
    df_merged = target_tiles.merge(combined_cache, on=["tile", "tile_lat", "tile_lon"])
    valid_tiles = df_merged[df_merged["count"] > 0].copy()
    print(f"\nValid land tiles accumulated: {len(valid_tiles)} / {len(df_merged)}")
    
    # 5° aggregation
    print("Aggregating global 5° cell statistics...")
    agg_5 = valid_tiles.groupby(["cell_lat_5", "cell_lon_5"]).agg(
        pixel_count=("count", "sum"),
        sum_elev=("sum_elev", "sum"),
        sum_sq_elev=("sum_sq_elev", "sum"),
        elevation_min=("min_elev", "min"),
        elevation_max=("max_elev", "max")
    ).reset_index().rename(columns={"cell_lat_5": "cell_lat", "cell_lon_5": "cell_lon"})
    
    agg_5["elevation_mean"] = agg_5["sum_elev"] / agg_5["pixel_count"]
    var_5 = (agg_5["sum_sq_elev"] - (agg_5["sum_elev"]**2) / agg_5["pixel_count"]) / np.maximum(1, agg_5["pixel_count"] - 1)
    agg_5["elevation_sd"] = np.sqrt(np.maximum(0.0, var_5))
    agg_5["relief_range"] = agg_5["elevation_max"] - agg_5["elevation_min"]
    agg_5["topographic_heterogeneity"] = agg_5["relief_range"]
    
    out_global_5 = agg_5[[
        "cell_lat", "cell_lon", "elevation_mean", "elevation_sd",
        "elevation_min", "elevation_max", "relief_range",
        "topographic_heterogeneity", "pixel_count"
    ]].round(2)
    
    global_5_path = os.path.join(PROCESSED_DIR, "dem_cells_global_5deg.csv")
    out_global_5.to_csv(global_5_path, index=False)
    print(f"Saved global 5° DEM statistics: {len(out_global_5)} cells to {global_5_path}")
    
    # 2° aggregation
    print("Aggregating global 2° cell statistics...")
    agg_2 = valid_tiles.groupby(["cell_lat_2", "cell_lon_2"]).agg(
        pixel_count=("count", "sum"),
        sum_elev=("sum_elev", "sum"),
        sum_sq_elev=("sum_sq_elev", "sum"),
        elevation_min=("min_elev", "min"),
        elevation_max=("max_elev", "max")
    ).reset_index().rename(columns={"cell_lat_2": "cell_lat", "cell_lon_2": "cell_lon"})
    
    agg_2["elevation_mean"] = agg_2["sum_elev"] / agg_2["pixel_count"]
    var_2 = (agg_2["sum_sq_elev"] - (agg_2["sum_elev"]**2) / agg_2["pixel_count"]) / np.maximum(1, agg_2["pixel_count"] - 1)
    agg_2["elevation_sd"] = np.sqrt(np.maximum(0.0, var_2))
    agg_2["relief_range"] = agg_2["elevation_max"] - agg_2["elevation_min"]
    agg_2["topographic_heterogeneity"] = agg_2["relief_range"]
    
    out_global_2 = agg_2[[
        "cell_lat", "cell_lon", "elevation_mean", "elevation_sd",
        "elevation_min", "elevation_max", "relief_range",
        "topographic_heterogeneity", "pixel_count"
    ]].round(2)
    
    global_2_path = os.path.join(PROCESSED_DIR, "dem_cells_global_2deg.csv")
    out_global_2.to_csv(global_2_path, index=False)
    print(f"Saved global 2° DEM statistics: {len(out_global_2)} cells to {global_2_path}")
    
    # 5. Verification against old tables (375 GBIF cells)
    old_5_path = os.path.join(PROCESSED_DIR, "dem_cells_5deg.csv")
    if os.path.exists(old_5_path):
        old_5 = pd.read_csv(old_5_path)
        comp_5 = old_5.merge(out_global_5, on=["cell_lat", "cell_lon"], suffixes=("_old", "_new"))
        print(f"\nVerification against existing 375-cell table ({old_5_path}):")
        print(f"Overlapping cells: {len(comp_5)} / {len(old_5)}")
        mean_diff = (comp_5["elevation_mean_old"] - comp_5["elevation_mean_new"]).abs().max()
        sd_diff = (comp_5["elevation_sd_old"] - comp_5["elevation_sd_new"]).abs().max()
        relief_diff = (comp_5["relief_range_old"] - comp_5["relief_range_new"]).abs().max()
        print(f"Max absolute diff - Mean elevation: {mean_diff:.4f}")
        print(f"Max absolute diff - Elevation SD:   {sd_diff:.4f}")
        print(f"Max absolute diff - Relief range:   {relief_diff:.4f}")
        assert mean_diff < 0.05, f"Mean elevation mismatch: {mean_diff}"
        assert sd_diff < 0.05, f"Elevation SD mismatch: {sd_diff}"
        assert relief_diff < 0.05, f"Relief range mismatch: {relief_diff}"
        print("MATCH VERIFIED: All GBIF cells in global table match old table within tolerance!")
    
    print("\nGlobal DEM pipeline completed successfully.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--global":
        download_global_dem(max_workers=64)
    else:
        download_and_accumulate_dem(max_workers=36)
