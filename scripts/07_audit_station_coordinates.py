import json
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

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

for df in (current, historical):
    df["station_id"] = (
        df["station_id"].astype("string").str.strip()
    )

current_ids = set(current["station_id"])
historical_ids = set(historical["station_id"])

# Count trip endpoints by station.
starts = trips[
    ["Start_Station_Id", "Start_Station_Name"]
].rename(columns={
    "Start_Station_Id": "station_id",
    "Start_Station_Name": "station_name"
})

ends = trips[
    ["End_Station_Id", "End_Station_Name"]
].rename(columns={
    "End_Station_Id": "station_id",
    "End_Station_Name": "station_name"
})

endpoints = pd.concat([starts, ends])

unresolved_ids = (
    set(endpoints["station_id"].dropna())
    - current_ids
    - historical_ids
)

unresolved = (
    endpoints[endpoints["station_id"].isin(unresolved_ids)]
    .groupby(["station_id", "station_name"], dropna=False)
    .size()
    .reset_index(name="trip_endpoints")
    .sort_values("trip_endpoints", ascending=False)
)

print("=== 14 UNRESOLVED STATIONS ===")
print(unresolved.to_string(index=False))

unresolved.to_csv(
    DATA / "unresolved_stations.csv", index=False
)

# Compare stations existing in both snapshots.
common = current[
    ["station_id", "name", "lat", "lon"]
].merge(
    historical[
        ["station_id", "name", "lat", "lon"]
    ],
    on="station_id",
    suffixes=("_2026", "_2023")
)

# Haversine distance in metres.
lat1 = np.radians(common["lat_2023"].astype(float))
lon1 = np.radians(common["lon_2023"].astype(float))
lat2 = np.radians(common["lat_2026"].astype(float))
lon2 = np.radians(common["lon_2026"].astype(float))

a = (
    np.sin((lat2 - lat1) / 2) ** 2
    + np.cos(lat1) * np.cos(lat2)
    * np.sin((lon2 - lon1) / 2) ** 2
)

common["distance_m"] = (
    2 * 6371000 * np.arcsin(
        np.sqrt(np.clip(a, 0, 1))
    )
)

common = common.sort_values(
    "distance_m", ascending=False
)

print("\n=== COORDINATE COMPARISON ===")
print("Stations in both snapshots:", len(common))
print("Moved more than 50m:",
      (common["distance_m"] > 50).sum())
print("Moved more than 100m:",
      (common["distance_m"] > 100).sum())

print("\n=== LARGEST COORDINATE DIFFERENCES ===")
print(common[
    ["station_id", "name_2023",
     "name_2026", "distance_m"]
].head(20).to_string(index=False))

common.to_csv(
    DATA / "station_coordinate_audit.csv",
    index=False
)

print("\nAudit files saved.")
