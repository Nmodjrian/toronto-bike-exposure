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

origins = stations[
    ["station_id", "lat", "lon"]
].rename(columns={
    "station_id": "Start_Station_Id",
    "lat": "start_lat",
    "lon": "start_lon"
})

destinations = stations[
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

duration = pd.to_numeric(df["Trip_Duration"], errors="coerce")

df = df[
    (df["Start_Station_Id"] != df["End_Station_Id"])
    & (duration > 0)
].copy()

pairs = (
    df.groupby(
        [
            "Start_Station_Id",
            "End_Station_Id",
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lon"
        ],
        dropna=False
    )
    .size()
    .reset_index(name="trip_count")
    .sort_values("trip_count", ascending=False)
    .reset_index(drop=True)
)

output = DATA / "full_june_od_pairs.parquet"
pairs.to_parquet(output, index=False)

print("\n=== FULL JUNE ROUTING ===")
print(f"Trips eligible for routing: {len(df):,}")
print(f"Unique directed OD pairs: {len(pairs):,}")
print(f"Most popular OD pair: {pairs['trip_count'].max():,} trips")
print(f"Median trips per OD pair: {pairs['trip_count'].median():.0f}")
print(f"Saved: {output}")
