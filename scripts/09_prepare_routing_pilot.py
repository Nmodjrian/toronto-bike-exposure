from pathlib import Path
import pandas as pd
import geopandas as gpd

DATA = Path("data/processed")

trips = pd.read_parquet(
    DATA / "bikeshare_june_2024_validated.parquet"
)

stations = gpd.read_file(
    DATA / "bikeshare_station_reference_provisional.gpkg"
)

# For the first pilot, use stations appearing in both
# snapshots with coordinates differing by at most 30 m.
stable = stations[
    stations["coordinate_difference_m"].notna()
    & (stations["coordinate_difference_m"] <= 30)
    & ~stations["location_review_required"]
].copy()

print("Pilot-eligible stations:", len(stable))

origins = stable[
    ["station_id", "lat", "lon"]
].rename(columns={
    "station_id": "Start_Station_Id",
    "lat": "start_lat",
    "lon": "start_lon"
})

destinations = stable[
    ["station_id", "lat", "lon"]
].rename(columns={
    "station_id": "End_Station_Id",
    "lat": "end_lat",
    "lon": "end_lon"
})

df = trips.merge(
    origins, on="Start_Station_Id", how="inner"
).merge(
    destinations, on="End_Station_Id", how="inner"
)

df["Trip_Duration"] = pd.to_numeric(
    df["Trip_Duration"], errors="coerce"
)

df = df[
    (df["Start_Station_Id"] != df["End_Station_Id"])
    & df["Trip_Duration"].between(60, 7200)
].copy()

# Reproducible sample of 1,000 trips.
pilot = df.sample(
    n=min(1000, len(df)),
    random_state=42
)

if pilot.empty:
    raise RuntimeError("No pilot trips passed the filters")

output = DATA / "routing_pilot_1000.parquet"
pilot.to_parquet(output, index=False)

print("\n=== ROUTING PILOT ===")
print("Trips meeting pilot criteria:", f"{len(df):,}")
print("Trips selected:", len(pilot))
print(
    "Unique origin-destination pairs:",
    pilot.groupby([
        "Start_Station_Id", "End_Station_Id"
    ]).ngroups
)
print("Saved:", output)
