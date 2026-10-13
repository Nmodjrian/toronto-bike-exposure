from pathlib import Path
import pandas as pd

INPUT = Path(
    "data/processed/bikeshare_june_2024.parquet"
)
OUTPUT = Path(
    "data/processed/bikeshare_june_2024_validated.parquet"
)

df = pd.read_parquet(INPUT)

print("=== BEFORE NORMALISATION ===")
print(df[[
    "Start_Station_Id", "End_Station_Id"
]].head(10).to_string(index=False))

# Normalise station IDs while retaining missing values.
for col in ["Start_Station_Id", "End_Station_Id"]:
    df[col] = (
        df[col]
        .astype("string")
        .str.strip()
        .str.replace(r"\.0+$", "", regex=True)
    )
    df.loc[df[col] == "", col] = pd.NA

# Compare normalised station identifiers.
valid_ids = (
    df["Start_Station_Id"].notna()
    & df["End_Station_Id"].notna()
)

same_station = (
    valid_ids
    & df["Start_Station_Id"].eq(
        df["End_Station_Id"]
    ).fillna(False)
)

duration = pd.to_numeric(
    df["Trip_Duration"], errors="coerce"
)

short_same_station = (
    same_station
    & (duration <= 60)
)

print("\n=== VALIDATION SUMMARY ===")
print(f"Total June trips: {len(df):,}")
print(f"Unique trip IDs: {df['Trip_Id'].nunique():,}")
print(f"Same-station trips: {same_station.sum():,}")
print(
    f"Same-station trips <= 60 seconds: "
    f"{short_same_station.sum():,}"
)
print(
    f"Missing start station IDs: "
    f"{df['Start_Station_Id'].isna().sum():,}"
)
print(
    f"Missing end station IDs: "
    f"{df['End_Station_Id'].isna().sum():,}"
)
print(
    f"Unique start stations: "
    f"{df['Start_Station_Id'].nunique():,}"
)
print(
    f"Unique end stations: "
    f"{df['End_Station_Id'].nunique():,}"
)
print(
    f"Trips with zero or negative duration: "
    f"{(duration <= 0).sum():,}"
)
print(
    f"Trips longer than 24 hours: "
    f"{(duration > 86400).sum():,}"
)

print("\n=== AFTER NORMALISATION ===")
print(df[[
    "Start_Station_Id", "End_Station_Id"
]].head(10).to_string(index=False))

df.to_parquet(OUTPUT, index=False)
print(f"\nSaved: {OUTPUT}")
