"""
continent_rules.py
------------------
Deterministic, rule-based geographic classifier assigning grid cells to continents
based on latitude and longitude coordinates. Deliberately handles islands (Canary Islands,
Madagascar, Taiwan, Hawaii, Caribbean, Indonesian/Melanesian archipelagos).

Generates:
- tables/continent_assignment.csv (and ml/outputs/tables/continent_assignment.csv)
- tables/continent_boundary_cells.csv
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np

# Rule boundaries for checking cells within 5 degrees
BOUNDARIES = [
    # (name, lat_min, lat_max, lon_min, lon_max, description)
    ("Panama_NA_SA", 7.0, 9.5, -83.0, -77.0, "Panama Isthmus dividing North and South America"),
    ("Suez_Sinai_AF_AS", 27.0, 32.5, 31.0, 35.5, "Sinai / Suez dividing Africa and Asia"),
    ("Gibraltar_AF_EU", 34.0, 37.0, -7.0, -4.0, "Strait of Gibraltar dividing Africa and Europe"),
    ("Bosphorus_EU_AS", 39.5, 42.5, 26.0, 30.0, "Turkish Straits dividing Europe and Asia"),
    ("Urals_EU_AS", 50.0, 70.0, 58.0, 62.0, "Ural Mountains dividing Europe and Asia"),
    ("Wallace_AS_OC", -11.0, 6.0, 128.0, 134.0, "Lydekker / New Guinea line dividing Asia and Oceania"),
]

def assign_continent(lat: float, lon: float) -> str:
    """
    Assign a continent to a latitude/longitude coordinate pair.
    
    Continents: Africa, Europe, Asia, North America, South America, Oceania, Antarctica
    """
    # 1. Antarctica
    if lat < -60.0:
        return "Antarctica"
    
    # 2. Deliberate Island Assignments
    # Hawaii / Polynesian outliers
    if 18.0 <= lat <= 29.0 and -179.0 <= lon <= -150.0:
        return "Oceania"
    # Canary Islands & Madeira
    if 27.0 <= lat <= 33.5 and -19.0 <= lon <= -12.5:
        return "Africa"
    # Madagascar, Comoros, Mascarenes
    if -26.5 <= lat <= -11.0 and 42.5 <= lon <= 58.0:
        return "Africa"
    # Taiwan
    if 21.0 <= lat <= 26.0 and 119.0 <= lon <= 123.0:
        return "Asia"
    # Iceland
    if 63.0 <= lat <= 67.5 and -25.0 <= lon <= -13.0:
        return "Europe"
    # Greenland
    if lat >= 59.5 and -75.0 <= lon <= -10.0:
        return "North America"
    # Caribbean Islands
    if 10.0 <= lat <= 27.0 and -86.0 <= lon <= -59.0:
        return "North America"
    # Falkland Islands
    if -53.5 <= lat <= -51.0 and -62.0 <= lon <= -57.0:
        return "South America"

    # 3. Americas (West of ~ -30° lon, excluding islands handled above)
    if lon < -30.0:
        # North America vs South America boundary at Panama (~7.5°N - 9.0°N, -77.5°W)
        if lat >= 8.5:
            return "North America"
        elif lat < 7.0:
            return "South America"
        else:
            # Transition zone in Panama: lon < -79 is NA, lon >= -79 is SA
            return "North America" if lon < -79.0 else "South America"

    # 4. Oceania (Australia, New Zealand, New Guinea, Melanesia/Micronesia)
    if (lat <= -10.0 and lon >= 110.0) or (lat <= 0.0 and lon >= 130.0) or (-50.0 <= lat <= -30.0 and lon >= 160.0):
        return "Oceania"
    # Pacific Island domain
    if -25.0 <= lat <= 20.0 and lon >= 150.0:
        return "Oceania"

    # 5. Africa
    # Continental Africa: lat down to -35°, up to ~36°N; lon from -18° to 52°E (excluding Sinai/Asia)
    if -36.0 <= lat <= 37.5 and -20.0 <= lon <= 55.0:
        # Exclude Europe (north of Mediterranean ~36°N, or Gibraltar)
        if lat >= 36.0 and lon > -6.0:
            return "Europe"
        # Exclude Middle East (Asia): Sinai/Arabia (lat >= 12.0 and lon >= 34.5)
        if lat >= 12.0 and lon >= 34.5:
            # Gulf of Suez / Red Sea boundary
            if lat >= 29.5 and lon >= 32.5:
                return "Asia"
            if lat < 29.5 and lon >= 35.0:
                return "Asia"
        return "Africa"

    # 6. Europe vs Asia
    if lat >= 35.0 and -15.0 <= lon <= 180.0:
        # Southern boundary of Europe in Mediterranean
        if lat < 36.0 and lon < 35.0:
            return "Africa"
        # Eastern boundary of Europe: Ural Mountains (~60°E) and Turkish Straits / Caucasus
        if lon < 60.0:
            # Asia Minor / Middle East is Asia: south of Black Sea (~41.5°N) and east of Aegean (~26°E)
            if lat < 42.0 and lon >= 27.5:
                return "Asia"
            # Caucasus boundary around 40°N
            if lat < 43.0 and lon >= 40.0:
                return "Asia"
            return "Europe"
        else:
            # East of Urals (60°E) is Asia
            return "Asia"

    # 7. Rest of Asia (South Asia, SE Asia, East Asia)
    if lat >= -11.0 and 60.0 <= lon <= 180.0:
        return "Asia"

    # Default fallback
    return "Asia" if lon >= 60.0 else "Europe"


def check_boundary_proximity(lat: float, lon: float, buffer_deg: float = 5.0):
    """Check if a coordinate is within buffer_deg of a continental transition zone."""
    for name, lat_min, lat_max, lon_min, lon_max, desc in BOUNDARIES:
        if (lat_min - buffer_deg <= lat <= lat_max + buffer_deg) and \
           (lon_min - buffer_deg <= lon <= lon_max + buffer_deg):
            return True, name, desc
    return False, None, None


def classify_filtered_cells(repo_root: Path):
    """Classify all filtered cells (n_records >= 10) at 5deg and 2deg resolutions."""
    df5 = pd.read_csv(repo_root / "integration_v2" / "processed" / "data_5deg.csv")
    df2 = pd.read_csv(repo_root / "integration_v2" / "processed" / "data_2deg.csv")
    
    sub5 = df5[df5.n_records >= 10][["cell_lat", "cell_lon"]].drop_duplicates().copy()
    sub5["resolution"] = "5deg"
    
    sub2 = df2[df2.n_records >= 10][["cell_lat", "cell_lon"]].drop_duplicates().copy()
    sub2["resolution"] = "2deg"
    
    all_cells = pd.concat([sub5, sub2], ignore_index=True)
    all_cells["continent"] = [assign_continent(r.cell_lat, r.cell_lon) for _, r in all_cells.iterrows()]
    
    near_boundary = []
    boundary_name = []
    boundary_desc = []
    for _, r in all_cells.iterrows():
        is_near, b_name, b_desc = check_boundary_proximity(r.cell_lat, r.cell_lon, buffer_deg=5.0)
        near_boundary.append(is_near)
        boundary_name.append(b_name if is_near else "")
        boundary_desc.append(b_desc if is_near else "")
        
    all_cells["near_boundary_5deg"] = near_boundary
    all_cells["boundary_name"] = boundary_name
    all_cells["boundary_description"] = boundary_desc
    
    # Target directories
    tables_dir = repo_root / "tables"
    ml_tables_dir = repo_root / "ml" / "outputs" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    ml_tables_dir.mkdir(parents=True, exist_ok=True)
    
    out_csv = tables_dir / "continent_assignment.csv"
    all_cells.to_csv(out_csv, index=False)
    all_cells.to_csv(ml_tables_dir / "continent_assignment.csv", index=False)
    
    boundary_cells = all_cells[all_cells.near_boundary_5deg].copy()
    b_csv = tables_dir / "continent_boundary_cells.csv"
    boundary_cells.to_csv(b_csv, index=False)
    boundary_cells.to_csv(ml_tables_dir / "continent_boundary_cells.csv", index=False)
    
    print(f"Assigned continents to {len(all_cells)} total filtered cell entries ({len(sub5)} at 5deg, {len(sub2)} at 2deg).")
    print(f"Summary by resolution:")
    print(all_cells.groupby(["resolution", "continent"]).size())
    print(f"\nSaved full assignment to: {out_csv}")
    print(f"Saved boundary review table ({len(boundary_cells)} entries) to: {b_csv}")
    
    return all_cells, boundary_cells

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent.parent
    classify_filtered_cells(repo_root)
