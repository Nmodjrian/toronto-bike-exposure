from pathlib import Path
import pandas as pd
import geopandas as gpd

DATA = Path("data/processed")

trips = pd.read_parquet(
    DATA / "bikeshare_june_2024_validated.parquet"
)

stations = gpd.read_file(
    DATA / "bikeshare_stations_snapshot.gpkg"
)

known_ids = set(
    stations["station_id"].astype("string")
)

start_missing = ~trips["Start_Station_Id"].isin(known_ids)
end_missing = ~trips["End_Station_Id"].isin(known_ids)

print("=== MATCHING BREAKDOWN ===")
print("Missing origin:", start_missing.sum())
print("Missing destination:", end_missing.sum())
print("Both missing:", (start_missing & end_missing).sum())
print("Either missing:", (start_missing | end_missing).sum())

# Gather station names from both ends of each trip.
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

all_stations = pd.concat(
    [starts, ends],
    ignore_index=True
)

unmatched = all_stations[
    ~all_stations["station_id"].isin(known_ids)
    & all_stations["station_id"].notna()
]

summary = (
    unmatched.groupby(
        ["station_id", "station_name"],
        dropna=False
    )
    .size()
    .reset_index(name="trip_endpoints")
    .sort_values("trip_endpoints", ascending=False)
)

summary.to_csv(
    DATA / "unmatched_station_diagnostics.csv",
    index=False
)

print("\n=== TOP 20 UNMATCHED STATIONS ===")
print(summary.head(20).to_string(index=False))

print("\nUnique unmatched IDs:",
      unmatched["station_id"].nunique())

print("\nDiagnostic saved.")
