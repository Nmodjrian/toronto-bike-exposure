from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd

DATA = Path("data/processed")

trips = pd.read_parquet(
    DATA / "bikeshare_june_2024_validated.parquet"
)

current = gpd.read_file(
    DATA / "bikeshare_stations_snapshot.gpkg"
)

with open("data/raw/stations_2023_snapshot.json") as f:
    historical = pd.DataFrame(
        json.load(f)["data"]["stations"]
    )

def prepare(df, suffix):
    result = df[["station_id", "name", "lat", "lon"]].copy()
    result["station_id"] = (
        result["station_id"].astype("string").str.strip()
    )
    for col in ["lat", "lon"]:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result = result.dropna(
        subset=["station_id", "lat", "lon"]
    )
    return result.drop_duplicates("station_id").rename(
        columns={
            "name": f"name_{suffix}",
            "lat": f"lat_{suffix}",
            "lon": f"lon_{suffix}",
        }
    )

old = prepare(historical, "2023")
new = prepare(current, "2026")

stations = old.merge(new, on="station_id", how="outer")

# Prefer the older snapshot, but retain source information.
stations["lat"] = stations["lat_2023"].combine_first(
    stations["lat_2026"]
)
stations["lon"] = stations["lon_2023"].combine_first(
    stations["lon_2026"]
)

stations["coordinate_source"] = np.where(
    stations["lat_2023"].notna(),
    "2023_snapshot",
    "2026_snapshot"
)

# Calculate differences where both snapshots are available.
lat1 = np.radians(stations["lat_2023"])
lon1 = np.radians(stations["lon_2023"])
lat2 = np.radians(stations["lat_2026"])
lon2 = np.radians(stations["lon_2026"])

a = (
    np.sin((lat2 - lat1) / 2) ** 2
    + np.cos(lat1) * np.cos(lat2)
    * np.sin((lon2 - lon1) / 2) ** 2
)

stations["coordinate_difference_m"] = (
    2 * 6371000 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
)

stations["location_review_required"] = (
    (stations["coordinate_difference_m"] > 50)
    | (
        stations["name_2023"].notna()
        & stations["name_2026"].notna()
        & (
            stations["name_2023"].str.strip().str.casefold()
            != stations["name_2026"].str.strip().str.casefold()
        )
    )
)

stations["location_review_required"] = (
    stations["location_review_required"].fillna(False)
)

stations["coordinate_verified_for_june_2024"] = False

gdf = gpd.GeoDataFrame(
    stations,
    geometry=gpd.points_from_xy(
        stations["lon"], stations["lat"]
    ),
    crs="EPSG:4326"
)

output = DATA / "bikeshare_station_reference_provisional.gpkg"
gdf.to_file(output, driver="GPKG")

known = set(gdf["station_id"])

matched = (
    trips["Start_Station_Id"].isin(known)
    & trips["End_Station_Id"].isin(known)
)

same = (
    trips["Start_Station_Id"].eq(
        trips["End_Station_Id"]
    ).fillna(False)
)

duration = pd.to_numeric(
    trips["Trip_Duration"], errors="coerce"
)

pilot_eligible = (
    matched
    & ~same
    & duration.gt(0)
)

print("\n=== CONSOLIDATED STATIONS ===")
print("Total stations:", len(gdf))
print("From 2023 snapshot:",
      (gdf["coordinate_source"] == "2023_snapshot").sum())
print("From 2026 snapshot:",
      (gdf["coordinate_source"] == "2026_snapshot").sum())
print("Require location review:",
      gdf["location_review_required"].sum())

print("\n=== ROUTING COVERAGE ===")
print("June trips:", len(trips))
print("Both station IDs matched:", matched.sum())
print("Preliminary routing candidates:", pilot_eligible.sum())
print("Still unmatched:", (~matched).sum())
print("\nSaved:", output)
