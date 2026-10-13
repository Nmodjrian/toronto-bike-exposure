from pathlib import Path
import json
import requests
import pandas as pd
import geopandas as gpd

DATA = Path("data/processed")
RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)

TRIPS = DATA / "bikeshare_june_2024_validated.parquet"

URL = (
    "https://tor.publicbikesystem.net/"
    "ube/gbfs/v1/en/station_information"
)

response = requests.get(URL, timeout=60)
response.raise_for_status()
payload = response.json()

# Save the original response for reproducibility.
(RAW / "station_information_snapshot.json").write_text(
    json.dumps(payload, indent=2)
)

stations = pd.DataFrame(payload["data"]["stations"])

print("Available station columns:")
print(stations.columns.tolist())

required = {"station_id", "name", "lat", "lon"}
missing = required - set(stations.columns)
if missing:
    raise ValueError(f"Missing station fields: {missing}")

stations["station_id"] = (
    stations["station_id"]
    .astype("string")
    .str.strip()
    .str.replace(r"\.0+$", "", regex=True)
)

stations["lat"] = pd.to_numeric(
    stations["lat"], errors="coerce"
)
stations["lon"] = pd.to_numeric(
    stations["lon"], errors="coerce"
)

stations = stations.dropna(
    subset=["station_id", "lat", "lon"]
)

stations = stations.drop_duplicates(
    subset=["station_id"]
)

gdf = gpd.GeoDataFrame(
    stations,
    geometry=gpd.points_from_xy(
        stations["lon"], stations["lat"]
    ),
    crs="EPSG:4326",
)

gdf.to_file(
    DATA / "bikeshare_stations_snapshot.gpkg",
    driver="GPKG"
)

trips = pd.read_parquet(TRIPS)

known_ids = set(stations["station_id"])

origin_match = trips["Start_Station_Id"].isin(known_ids)
destination_match = trips["End_Station_Id"].isin(known_ids)
both_match = origin_match & destination_match

print("\n=== STATION MATCHING SUMMARY ===")
print(f"Stations with coordinates: {len(stations):,}")
print(f"June trips: {len(trips):,}")
print(f"Matched origins: {origin_match.sum():,}")
print(f"Matched destinations: {destination_match.sum():,}")
print(f"Trips with both stations matched: {both_match.sum():,}")
print(f"Trips without both matches: {(~both_match).sum():,}")
print(f"Matching rate: {both_match.mean():.2%}")

historical_ids = (
    set(trips["Start_Station_Id"].dropna())
    | set(trips["End_Station_Id"].dropna())
)

unmatched = sorted(historical_ids - known_ids)

pd.DataFrame({
    "station_id": unmatched
}).to_csv(
    DATA / "unmatched_june_2024_stations.csv",
    index=False
)

print(f"Unmatched historical station IDs: {len(unmatched):,}")
print("Saved station GeoPackage and unmatched ID list.")
