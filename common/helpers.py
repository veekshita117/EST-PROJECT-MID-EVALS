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


def sample_at(path, lons, lats):
    with rasterio.open(path) as src:
        v = np.array(
            [x[0] for x in src.sample(zip(lons, lats))],
            float
        )
        nd = src.nodata

    if nd is not None:
        v[v == nd] = np.nan

    v[np.abs(v) > 1e4] = np.nan

    if np.nanmax(np.abs(v)) > 100:
        v = v / 10   # °C*10 -> °C

    return v


def global_grid(path, step=2):
    lons = np.arange(-180 + step / 2, 180, step)
    lats = np.arange(90 - step / 2, -90, -step)

    LON, LAT = np.meshgrid(lons, lats)

    return sample_at(
        path,
        LON.ravel(),
        LAT.ravel()
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


def cell_climate(paths, pts, prefix):
    """paths = {'present','holocene','lgm'} -> cell-level stability metrics"""

    d = pts[["lon", "lat", "cell_lat", "cell_lon"]].copy()

    for k, p in paths.items():
        d[k] = sample_at(p, d.lon, d.lat)

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