import json
import pandas as pd
import geopandas as gpd

DATA = "data/processed/"

trips = pd.read_parquet(
    DATA + "bikeshare_june_2024_validated.parquet"
)

current = gpd.read_file(
    DATA + "bikeshare_stations_snapshot.gpkg"
)

with open("data/raw/stations_2023_snapshot.json") as f:
    payload = json.load(f)

historical = pd.DataFrame(payload["data"]["stations"])

for df in (current, historical):
    df["station_id"] = df["station_id"].astype("string")

current_ids = set(current["station_id"])
historical_ids = set(historical["station_id"])

june_ids = (
    set(trips["Start_Station_Id"].dropna())
    | set(trips["End_Station_Id"].dropna())
)

missing_2026 = june_ids - current_ids
recovered = missing_2026 & historical_ids

print("=== HISTORICAL STATION RECOVERY ===")
print("Unmatched June station IDs:", len(missing_2026))
print("IDs found in 2023 snapshot:", len(recovered))
print("IDs still unresolved:", len(missing_2026 - recovered))

# Estimate potential coverage with combined station IDs.
combined_ids = current_ids | historical_ids

matched = (
    trips["Start_Station_Id"].isin(combined_ids)
    & trips["End_Station_Id"].isin(combined_ids)
)

print("Potential matched trips:", f"{matched.sum():,}")
print("Potential matching rate:", f"{matched.mean():.2%}")

details = historical[
    historical["station_id"].isin(recovered)
][["station_id", "name", "lat", "lon"]].copy()

details = details.rename(
    columns={"name": "historical_name"}
)

june_names = pd.concat([
    trips[["Start_Station_Id", "Start_Station_Name"]]
        .rename(columns={
            "Start_Station_Id": "station_id",
            "Start_Station_Name": "june_name"
        }),
    trips[["End_Station_Id", "End_Station_Name"]]
        .rename(columns={
            "End_Station_Id": "station_id",
            "End_Station_Name": "june_name"
        })
]).dropna(subset=["station_id", "june_name"])

june_names = (
    june_names.groupby("station_id")["june_name"]
    .agg(lambda x: x.mode().iloc[0])
    .reset_index()
)

details = details.merge(
    june_names, on="station_id", how="left"
)

details["name_matches"] = (
    details["historical_name"].str.casefold().str.strip()
    == details["june_name"].str.casefold().str.strip()
)

details.to_csv(
    DATA + "historical_station_candidates.csv",
    index=False
)

print("\n=== RECOVERED STATION CANDIDATES ===")
print(details.to_string(index=False))
print("\nSaved historical_station_candidates.csv")
