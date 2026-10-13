from pathlib import Path
import zipfile
import pandas as pd

ZIP_PATH = Path("data/raw/bikeshare-ridership-2024.zip")
OUTPUT = Path("data/processed/bikeshare_june_2024.parquet")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

june_chunks = []
total_rows = 0

with zipfile.ZipFile(ZIP_PATH) as archive:
    with archive.open("bikeshare-ridership-2024.csv") as file:

        reader = pd.read_csv(
            file,
            chunksize=100_000,
            dtype={
                "Start_Station_Id": "string",
                "End_Station_Id": "string",
            },
            low_memory=False,
        )

        for chunk in reader:
            total_rows += len(chunk)

            # Select trips starting in June 2024
            mask = (
                chunk["Start_Time"]
                .astype("string")
                .str.startswith("2024-06-", na=False)
            )

            june = chunk.loc[mask].copy()

            if not june.empty:
                june_chunks.append(june)

            print(
                f"Processed {total_rows:,} rows | "
                f"June trips found: "
                f"{sum(len(x) for x in june_chunks):,}"
            )

if not june_chunks:
    raise RuntimeError("No June 2024 trips were found")

df = pd.concat(june_chunks, ignore_index=True)

df["Start_Time"] = pd.to_datetime(
    df["Start_Time"], errors="coerce"
)
df["End_Time"] = pd.to_datetime(
    df["End_Time"], errors="coerce"
)

df["Trip_Duration"] = pd.to_numeric(
    df["Trip_Duration"], errors="coerce"
)

df.to_parquet(OUTPUT, index=False)

print("\n=== JUNE 2024 SUMMARY ===")
print(f"Total annual rows scanned: {total_rows:,}")
print(f"June 2024 trips: {len(df):,}")
print(f"Unique trip IDs: {df['Trip_Id'].nunique():,}")
print(
    "Unique start stations:",
    df["Start_Station_Id"].nunique()
)
print(
    "Unique end stations:",
    df["End_Station_Id"].nunique()
)
print(
    "Missing start station IDs:",
    df["Start_Station_Id"].isna().sum()
)
print(
    "Missing end station IDs:",
    df["End_Station_Id"].isna().sum()
)

same_station = (
    df["Start_Station_Id"].notna()
    & df["End_Station_Id"].notna()
    & (
        df["Start_Station_Id"]
        == df["End_Station_Id"]
    )
)
print(f"Same-station trips: {same_station.sum():,}")

print("\nTrip duration (seconds):")
print(df["Trip_Duration"].describe())

print(f"\nSaved: {OUTPUT}")
