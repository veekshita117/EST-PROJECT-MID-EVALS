import numpy as np, pandas as pd, rasterio, glob, os, re
import matplotlib.pyplot as plt
from scipy.stats import spearmanr, rankdata


CELL = 5  # grid size in degrees (use 5 if cells have too few records)


def load_gbif(path):
    df = pd.read_csv(path, sep=None, engine="python", on_bad_lines="skip")
    df = df.rename(columns={
        "decimalLatitude": "lat",
        "decimalLongitude": "lon"
    })
    df["species"] = df["speciesKey"]
    df = df[["species", "lat", "lon"]].dropna().drop_duplicates()
    df = df[df.lat.between(-90, 90) & df.lon.between(-180, 180)]

    return df[~((df.lat == 0) & (df.lon == 0))]


def add_cell(df, cell=CELL):
    df["cell_lat"] = np.floor(df.lat / cell) * cell + cell / 2
    df["cell_lon"] = np.floor(df.lon / cell) * cell + cell / 2

    return df


def find_bio1(folder):
    pat = re.compile(r"(bio_?1|bi1)(?!\d)", re.I)

    hits = [
        f for f in glob.glob(f"{folder}/**/*", recursive=True)
        if pat.search(os.path.basename(f))
        and (f.lower().endswith(".tif") or os.path.isdir(f))
    ]

    if not hits:
        raise FileNotFoundError(f"No BIO1 in {folder}")

    return hits[0]


def sample_at(path, lons, lats, scale=None, nodata_threshold=1e4):
    with rasterio.open(path) as src:
        v = np.array(
            [x[0] for x in src.sample(zip(lons, lats))],
            float
        )
        nd = src.nodata

    if nd is not None:
        v[v == nd] = np.nan

    if nodata_threshold is not None:
        v[np.abs(v) > nodata_threshold] = np.nan

    valid_v = v[~np.isnan(v)]
    if scale is None:
        if len(valid_v) > 0 and np.nanmax(np.abs(valid_v)) > 100:
            v = v / 10   # °C*10 -> °C
    elif scale == 1:
        pass
    elif callable(scale):
        v = scale(v)
    else:
        v = v * scale

    return v


def cell_zonal_stats(raster_path, cell=CELL, stats=("mean", "std", "min", "max", "count"), scale=None, nodata_threshold=1e4):
    """
    Computes statistics over all valid raster pixels inside each grid cell,
    using the cell definition: floor(lat/cell)*cell + cell/2.
    Returns a DataFrame with cell coordinates, requested stats, and valid_fraction.
    """
    with rasterio.open(raster_path) as src:
        width = src.width
        height = src.height
        transform = src.transform
        nd = src.nodata
        dx = abs(transform.a)
        dy = abs(transform.e)
        expected_per_cell = (cell / dx) * (cell / dy)

        arr = src.read(1).astype(float)

    if nd is not None:
        arr[arr == nd] = np.nan
    if nodata_threshold is not None:
        arr[np.abs(arr) > nodata_threshold] = np.nan

    valid_all = arr[~np.isnan(arr)]
    if scale is None:
        if len(valid_all) > 0 and np.nanmax(np.abs(valid_all)) > 100:
            arr = arr / 10
    elif scale == 1:
        pass
    elif callable(scale):
        arr = scale(arr)
    else:
        arr = arr * scale

    if transform.b == 0 and transform.d == 0:
        lons = transform.c + (np.arange(width) + 0.5) * transform.a
        lats = transform.f + (np.arange(height) + 0.5) * transform.e

        cell_lons = np.floor(lons / cell) * cell + cell / 2
        cell_lats = np.floor(lats / cell) * cell + cell / 2

        def get_slices(vals):
            uvals, sidx = np.unique(vals, return_index=True)
            order = np.argsort(sidx)
            uvals = uvals[order]
            sidx = sidx[order]
            eidx = np.append(sidx[1:], len(vals))
            return list(zip(uvals, sidx, eidx))

        lat_slices = get_slices(cell_lats)
        lon_slices = get_slices(cell_lons)

        records = []
        for clat, r0, r1 in lat_slices:
            sub_lat = arr[r0:r1]
            for clon, c0, c1 in lon_slices:
                blk = sub_lat[:, c0:c1].ravel()
                valid = blk[~np.isnan(blk)]
                cnt = len(valid)
                vfrac = min(1.0, cnt / expected_per_cell) if expected_per_cell > 0 else 0.0

                row = {"cell_lat": clat, "cell_lon": clon}
                if cnt > 0:
                    if "mean" in stats: row["mean"] = float(np.mean(valid))
                    if "std" in stats: row["std"] = float(np.std(valid))
                    if "min" in stats: row["min"] = float(np.min(valid))
                    if "max" in stats: row["max"] = float(np.max(valid))
                    if "count" in stats: row["count"] = cnt
                else:
                    if "mean" in stats: row["mean"] = np.nan
                    if "std" in stats: row["std"] = np.nan
                    if "min" in stats: row["min"] = np.nan
                    if "max" in stats: row["max"] = np.nan
                    if "count" in stats: row["count"] = 0
                row["valid_fraction"] = vfrac
                records.append(row)

        return pd.DataFrame(records)
    else:
        cols, rows = np.meshgrid(np.arange(width), np.arange(height))
        xs, ys = rasterio.transform.xy(transform, rows, cols)
        xs = np.array(xs)
        ys = np.array(ys)
        clon = np.floor(xs / cell) * cell + cell / 2
        clat = np.floor(ys / cell) * cell + cell / 2

        df_grid = pd.DataFrame({
            "cell_lat": clat.ravel(),
            "cell_lon": clon.ravel(),
            "val": arr.ravel()
        })

        grouped = df_grid.groupby(["cell_lat", "cell_lon"])
        res_df = grouped["val"].agg(
            count="count",
            mean="mean",
            std="std",
            min="min",
            max="max"
        ).reset_index()
        res_df["valid_fraction"] = (res_df["count"] / expected_per_cell).clip(upper=1.0)
        cols_to_keep = ["cell_lat", "cell_lon"] + [s for s in stats if s in res_df.columns] + ["valid_fraction"]
        return res_df[cols_to_keep]


def global_grid(path, step=2, **kwargs):
    lons = np.arange(-180 + step / 2, 180, step)
    lats = np.arange(90 - step / 2, -90, -step)

    LON, LAT = np.meshgrid(lons, lats)

    return sample_at(
        path,
        LON.ravel(),
        LAT.ravel(),
        **kwargs
    ).reshape(LON.shape)


def plot_map(arr, title, label, out, cmap="viridis"):
    plt.figure(figsize=(9, 4.5))

    plt.imshow(
        arr,
        extent=[-180, 180, -90, 90],
        cmap=cmap
    )

    plt.colorbar(label=label, shrink=.7)
    plt.title(title)
    plt.axis("off")

    plt.savefig(
        out,
        dpi=200,
        bbox_inches="tight"
    )

    plt.show()


def cell_climate(paths, pts, prefix, **kwargs):
    """paths = {'present','holocene','lgm'} -> cell-level stability metrics"""

    d = pts[["lon", "lat", "cell_lat", "cell_lon"]].copy()

    for k, p in paths.items():
        d[k] = sample_at(p, d.lon, d.lat, **kwargs)

    d = d.dropna()

    d["lgm_change"] = (d.present - d.lgm).abs()
    d["holo_change"] = (d.present - d.holocene).abs()
    d["instability"] = d[["present", "holocene", "lgm"]].std(axis=1)

    out = (
        d.drop(columns=["lon", "lat"])
        .groupby(["cell_lat", "cell_lon"])
        .mean()
        .reset_index()
    )

    return out.rename(
        columns=lambda c: c if c.startswith("cell_") else f"{prefix}_{c}"
    )


def partial_spearman(df, x, y, covs):
    R = df[[x, y] + covs].apply(rankdata)

    Z = np.column_stack(
        [np.ones(len(R))] + [R[c] for c in covs]
    )

    res = lambda v: v - Z @ np.linalg.lstsq(
        Z,
        v,
        rcond=None
    )[0]

    return spearmanr(
        res(R[x]),
        res(R[y])
    )
