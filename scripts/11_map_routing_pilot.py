from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT = Path(
    "data/processed/routing_pilot_1000_routes.gpkg"
)
OUTPUT = Path(
    "outputs/maps/toronto_bike_routes_pilot.png"
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

routes = gpd.read_file(INPUT)

fig, ax = plt.subplots(figsize=(12, 12))

routes.to_crs("EPSG:26917").plot(
    ax=ax,
    color="#16b8ca",
    linewidth=0.65,
    alpha=0.18
)

ax.set_title(
    "Toronto Bike Share — Modelled Cycling Routes\n"
    "June 2024 | GraphHopper Pilot",
    fontsize=15
)

ax.set_axis_off()
fig.tight_layout()

fig.savefig(
    OUTPUT,
    dpi=250,
    bbox_inches="tight"
)

plt.close(fig)
print(f"Saved: {OUTPUT}")
