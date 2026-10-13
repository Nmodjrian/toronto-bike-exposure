from pathlib import Path
import os
import json
import sqlite3
import time

import pandas as pd
import requests
from tqdm.auto import tqdm

DATA = Path("data/processed")
DB = DATA / "full_june_routes.sqlite"
INPUT = DATA / "full_june_od_pairs.parquet"

API = "http://127.0.0.1:8989/route"

# Default: process 10,000 NEW pairs per execution.
# Set MAX_NEW=0 to attempt all remaining pairs.
MAX_NEW = int(os.getenv("MAX_NEW", "10000"))

pairs = pd.read_parquet(INPUT)

conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS routes (
    start_id TEXT NOT NULL,
    end_id TEXT NOT NULL,
    distance_m REAL,
    time_min REAL,
    geometry_json TEXT,
    error TEXT,
    PRIMARY KEY (start_id, end_id)
)
""")
conn.commit()

# Skip successful routes from previous executions.
completed = set(conn.execute("""
SELECT start_id, end_id FROM routes
WHERE geometry_json IS NOT NULL
""").fetchall())

print(f"Total unique OD pairs: {len(pairs):,}")
print(f"Previously completed: {len(completed):,}")

session = requests.Session()

health = session.get(
    "http://127.0.0.1:8989/health",
    timeout=15
)
health.raise_for_status()

processed = 0
succeeded = 0
failed = 0

try:
    for row in tqdm(
        pairs.itertuples(index=False),
        total=len(pairs),
        desc="Full-month routing"
    ):
        start_id = str(row.Start_Station_Id)
        end_id = str(row.End_Station_Id)

        if (start_id, end_id) in completed:
            continue

        if MAX_NEW and processed >= MAX_NEW:
            break

        record = (
            start_id, end_id, None, None, None, None
        )

        try:
            response = session.get(
                API,
                params=[
                    ("point", f"{row.start_lat},{row.start_lon}"),
                    ("point", f"{row.end_lat},{row.end_lon}"),
                    ("profile", "bike"),
                    ("points_encoded", "false"),
                    ("instructions", "false")
                ],
                timeout=45
            )

            # A stopped server should terminate the run
            # rather than generate thousands of failures.
            response.raise_for_status()
            payload = response.json()

            if not payload.get("paths"):
                raise ValueError(
                    str(payload.get("message", "No path"))
                )

            path = payload["paths"][0]

            record = (
                start_id,
                end_id,
                float(path["distance"]),
                float(path["time"]) / 60000,
                json.dumps(
                    path["points"],
                    separators=(",", ":")
                ),
                None
            )

            succeeded += 1

        except requests.ConnectionError:
            print("\nGraphHopper connection lost; stopping.")
            break

        except (requests.RequestException,
                ValueError, KeyError, TypeError) as exc:
            record = (
                start_id, end_id,
                None, None, None, str(exc)[:1000]
            )
            failed += 1

        conn.execute("""
        INSERT OR REPLACE INTO routes
        (start_id, end_id, distance_m, time_min,
         geometry_json, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """, record)

        processed += 1

        if processed % 100 == 0:
            conn.commit()

finally:
    conn.commit()

    done = conn.execute("""
    SELECT COUNT(*) FROM routes
    WHERE geometry_json IS NOT NULL
    """).fetchone()[0]

    print("\n=== FULL ROUTING PROGRESS ===")
    print(f"Pairs attempted this run: {processed:,}")
    print(f"Successful this run: {succeeded:,}")
    print(f"Failed this run: {failed:,}")
    print(f"Total successful OD routes: {done:,}")
    print(f"Total OD pairs: {len(pairs):,}")
    print(f"Database: {DB}")

    conn.close()
    session.close()
