"""02_real_data_join.py — Week 3 geospatial join.

Merges IRIS zone shapes + DVF prices + climate layers into a single file:
data/joined.geojson. This is what 03_pipeline.py will consume in place of
the synthetic twin.

Contract enforced (tests will verify):
    zone_id, geometry, price_m2, heat_score, flood_score, elevation, dist_seine, n_sales
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

IRIS_PATH = Path("data/IRIS_SHAPES.gpkg")
DVF_PATH = Path("data/dvf_by_zone.csv")
CLIMATE_PATH = Path("data/climate_layers.csv")
OUT_PATH = Path("data/joined.geojson")

METRIC_CRS = "EPSG:2154"
WGS84 = "EPSG:4326"

CONTRACT_COLUMNS = [
    "zone_id",
    "geometry",
    "price_m2",
    "heat_score",
    "flood_score",
    "elevation",
    "dist_seine",
    "n_sales",
]


def main() -> None:
    # --- 1. Load IRIS zones (already filtered to Paris by extract_iris.py) ---
    zones = gpd.read_file(IRIS_PATH)
    if "zone_id" not in zones.columns:
        # Fallback for older extracts using CODE_IRIS
        if "code_iris" in zones.columns:
            zones = zones.rename(columns={"code_iris": "zone_id"})
        else:
            raise ValueError(
                f"IRIS file has no zone_id / CODE_IRIS column. Got: {list(zones.columns)}"
            )

    zones["zone_id"] = zones["zone_id"].astype(str)
    zones = zones[["zone_id", "geometry"]]
    print(f"IRIS zones loaded: {len(zones)} (expect 992)")

    # --- 2. Load DVF prices (Data stream) ---
    dvf = pd.read_csv(DVF_PATH, dtype={"zone_id": str})
    print(f"DVF prices loaded: {len(dvf)} zones")

    # --- 3. Load climate layers (Climate stream — already on main) ---
    climate = pd.read_csv(CLIMATE_PATH, dtype={"zone_id": str})
    print(f"Climate layers loaded: {len(climate)} zones")

    # --- 4. Merge everything on zone_id ---
    # inner merge on all three: only keep zones with ALL data present
    df = zones.merge(dvf, on="zone_id", how="inner")
    df = df.merge(climate, on="zone_id", how="inner")
    print(f"After merge: {len(df)} zones with full data")

    # --- 5. Add elevation placeholder (MVP constant per schema) ---
    df["elevation"] = 40

    # --- 6. Enforce n_sales >= 20 (reliability filter — Charles-Henri already filtered, safety net) ---
    df = df[df["n_sales"] >= 20].copy()
    print(f"After n_sales filter: {len(df)} zones")

    # --- 7. Enforce column contract (exactly 8 columns) ---
    missing = set(CONTRACT_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Contract violation — missing columns: {missing}")
    df = df[CONTRACT_COLUMNS]

    # --- 8. Sanity checks ---
    assert df["zone_id"].is_unique, "duplicate zone_id after merge"
    assert df["price_m2"].between(3000, 30000).all(), "price_m2 outside trim range"
    assert df["flood_score"].between(0, 100).all(), "flood_score out of bounds"
    assert df["heat_score"].between(30, 90).all(), "heat_score out of bounds"
    assert (df["n_sales"] >= 20).all(), "unreliable zones survived filter"

    # --- 9. Save in EPSG:4326 for the app ---
    df = df.to_crs(WGS84) if df.crs and df.crs.to_epsg() != 4326 else df
    df.to_file(OUT_PATH, driver="GeoJSON")
    print(f"\n✓ saved {OUT_PATH} ({len(df)} zones)")
    print(f"  price_m2 range: {df['price_m2'].min():.0f} - {df['price_m2'].max():.0f} €/m²")
    print(f"  median price_m2: {df['price_m2'].median():.0f} €/m²")
    print(f"  zones with flood_score > 30: {(df['flood_score'] > 30).sum()}")


if __name__ == "__main__":
    main()
