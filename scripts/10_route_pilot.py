from pathlib import Path
import time

import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import shape
from tqdm.auto import tqdm

DATA = Path("data/processed")
OUTPUT = DATA / "routing_pilot_1000_routes.gpkg"
FAILURES = DATA / "routing_pilot_failures.csv"

URL = "http://127.0.0.1:8989/route"

trips = pd.read_parquet(
    DATA / "routing_pilot_1000.parquet"
)

# Each station pair needs routing only once.
pairs = trips.drop_duplicates(
    ["Start_Station_Id", "End_Station_Id"]
).copy()

session = requests.Session()

# Verify that the local GraphHopper server is available.
health = session.get(
    "http://127.0.0.1:8989/health",
    timeout=15
)
health.raise_for_status()

routes = []
failures = []

for row in tqdm(
    pairs.itertuples(index=False),
    total=len(pairs),
    desc="Routing station pairs"
):
    try:
        response = session.get(
            URL,
            params=[
                ("point", f"{row.start_lat},{row.start_lon}"),
                ("point", f"{row.end_lat},{row.end_lon}"),
                ("profile", "bike"),
                ("points_encoded", "false"),
            ],
            timeout=60
        )
        response.raise_for_status()

        result = response.json()

        if not result.get("paths"):
            raise ValueError(str(result.get("message", result)))

        path = result["paths"][0]

        routes.append({
            "Start_Station_Id": row.Start_Station_Id,
            "End_Station_Id": row.End_Station_Id,
            "route_distance_m": path["distance"],
            "route_time_min": path["time"] / 60000,
            "geometry": shape(path["points"]),
        })

    except (requests.RequestException, ValueError, KeyError) as exc:
        failures.append({
            "Start_Station_Id": row.Start_Station_Id,
            "End_Station_Id": row.End_Station_Id,
            "error": str(exc),
        })

if not routes:
    raise RuntimeError("No routes were successfully reconstructed")

route_gdf = gpd.GeoDataFrame(
    routes,
    geometry="geometry",
    crs="EPSG:4326"
)

# Join routes back to individual trips.
result = trips.merge(
    route_gdf,
    on=["Start_Station_Id", "End_Station_Id"],
    how="inner"
)

result = gpd.GeoDataFrame(
    result,
    geometry="geometry",
    crs="EPSG:4326"
)

result["actual_time_min"] = (
    result["Trip_Duration"] / 60
)

# Descriptive duration difference only:
# not yet a validated measure of avoidable exposure.
result["duration_difference_min"] = (
    result["actual_time_min"] - result["route_time_min"]
)

result.to_file(
    OUTPUT,
    layer="bike_routes",
    driver="GPKG"
)

pd.DataFrame(
    failures,
    columns=["Start_Station_Id", "End_Station_Id", "error"]
).to_csv(FAILURES, index=False)

print("\n=== GRAPHOPPER ROUTING RESULTS ===")
print(f"Pilot trips: {len(trips):,}")
print(f"Unique OD pairs: {len(pairs):,}")
print(f"Successfully routed OD pairs: {len(routes):,}")
print(f"Failed OD pairs: {len(failures):,}")
print(f"Trips with reconstructed routes: {len(result):,}")
print(f"Mean route distance: {result['route_distance_m'].mean()/1000:.2f} km")
print(f"Median route time: {result['route_time_min'].median():.2f} min")
print(f"Median observed duration: {result['actual_time_min'].median():.2f} min")
print(f"\nSaved: {OUTPUT}")
print(f"Failures saved: {FAILURES}")
