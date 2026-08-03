"""Merge IRIS zones, DVF prices and climate layers into joined.geojson."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

IRIS_PATH = Path("data/IRIS_SHAPES.gpkg")
DVF_PATH = Path("data/dvf_by_zone.csv")
CLIMATE_PATH = Path("data/climate_layers.csv")
OUT_PATH = Path("data/joined.geojson")

CONTRACT = [
    "zone_id",
    "geometry",
    "price_m2",
    "heat_score",
    "flood_score",
    "elevation",
    "dist_seine",
    "n_sales",
]


def load_iris(path: Path) -> gpd.GeoDataFrame:
    zones = gpd.read_file(path)
    if "zone_id" not in zones.columns and "code_iris" in zones.columns:
        zones = zones.rename(columns={"code_iris": "zone_id"})
    zones["zone_id"] = zones["zone_id"].astype(str)
    return zones[["zone_id", "geometry"]]


def main() -> None:
    zones = load_iris(IRIS_PATH)
    dvf = pd.read_csv(DVF_PATH, dtype={"zone_id": str})
    climate = pd.read_csv(CLIMATE_PATH, dtype={"zone_id": str})

    df = zones.merge(dvf, on="zone_id").merge(climate, on="zone_id")
    df["elevation"] = 40
    df = df[df["n_sales"] >= 20][CONTRACT]

    df.to_crs("EPSG:4326").to_file(OUT_PATH, driver="GeoJSON")
    print(f"saved {len(df)} zones, median {df['price_m2'].median():.0f} €/m²")


if __name__ == "__main__":
    main()
