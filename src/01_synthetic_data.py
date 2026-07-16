"""01_synthetic_data.py — synthetic twin of joined.geojson (same contract)."""

import os

import geopandas as gpd
import numpy as np
from shapely.geometry import box

rng = np.random.default_rng(42)
N_SIDE = 16  # 16x16 grid = 256 fake zones over the Paris bbox
lon0, lon1, lat0, lat1 = 2.25, 2.42, 48.815, 48.902

zones, seine_lat = [], 48.855  # fake Seine as a horizontal line
step_lon, step_lat = (lon1 - lon0) / N_SIDE, (lat1 - lat0) / N_SIDE

for i in range(N_SIDE):
    for j in range(N_SIDE):
        lon, lat = lon0 + i * step_lon, lat0 + j * step_lat
        centroid_lat = lat + step_lat / 2
        dist_seine = abs(centroid_lat - seine_lat) * 111  # deg -> km approx
        flood = float(np.clip(100 * np.exp(-dist_seine / 1.2) + rng.normal(0, 5), 0, 100))
        green = float(np.clip(rng.beta(2, 4), 0, 0.6))
        heat = 30 + 60 * (1 - green / 0.6)
        elevation = float(np.clip(35 + dist_seine * 8 + rng.normal(0, 3), 28, 130))
        # price: central + west = expensive, plus noise
        centrality = 1 - (abs(lon - 2.33) / 0.09 + abs(lat - 48.86) / 0.045) / 2
        price = float(np.clip(9000 + 6000 * centrality + rng.normal(0, 900), 3000, 30000))
        zones.append(
            {
                "zone_id": f"75{i:02d}{j:02d}",
                "price_m2": round(price, 0),
                "heat_score": round(heat, 1),
                "flood_score": round(flood, 1),
                "elevation": round(elevation, 1),
                "dist_seine": round(dist_seine, 2),
                "n_sales": int(rng.integers(20, 400)),
                "geometry": box(lon, lat, lon + step_lon, lat + step_lat),
            }
        )

os.makedirs("data", exist_ok=True)
gdf = gpd.GeoDataFrame(zones, crs="EPSG:4326")

gdf.to_file("data/synthetic.geojson", driver="GeoJSON")
print(f"synthetic twin: {len(gdf)} zones -> data/synthetic.geojson")
