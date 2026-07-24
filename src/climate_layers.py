import geopandas as gpd
import numpy as np
import pandas as pd

METRIC_CRS = "EPSG:2154"


def _to_metric(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to meters; repair invalid geometries on the way."""
    if gdf.crs is None:
        raise ValueError("Input has no CRS — read the file with geopandas, don't strip .prj")
    out = gdf.to_crs(METRIC_CRS).copy()
    invalid = ~out.geometry.is_valid
    if invalid.any():
        out.loc[invalid, "geometry"] = out.loc[invalid, "geometry"].buffer(0)
    return out


def compute_flood_layer(zones: gpd.GeoDataFrame, flood_zones: gpd.GeoDataFrame) -> pd.DataFrame:
    """flood_score = % of zone area inside PPRI flood polygons (0-100).

    dist_seine = distance (km) from zone centroid to the flood envelope.
    Zones inside the envelope get dist_seine = 0.

    Args:
        zones: IRIS zones with columns zone_id, geometry.
        flood_zones: PPRI polygons (any columns, only geometry is used).

    Returns:
        DataFrame with zone_id, flood_score, dist_seine.
    """
    zones_m = _to_metric(zones)
    flood_m = _to_metric(flood_zones)

    flood_union = flood_m.union_all()  # one (multi)polygon for the whole envelope

    zone_area = zones_m.geometry.area
    flooded_area = zones_m.geometry.intersection(flood_union).area
    flood_score = (100 * flooded_area / zone_area).clip(0, 100)

    dist_seine = zones_m.geometry.centroid.distance(flood_union) / 1000  # m -> km

    return pd.DataFrame(
        {
            "zone_id": zones_m["zone_id"].to_numpy(),
            "flood_score": flood_score.round(1).to_numpy(),
            "dist_seine": dist_seine.round(2).to_numpy(),
        }
    )


def compute_heat_layer(
    zones: gpd.GeoDataFrame,
    green_spaces: gpd.GeoDataFrame | None,
    fallback_uhi: float = 0.6,
) -> pd.DataFrame:
    """heat_score in 30-90: the less green a zone, the hotter.

    green_share = green area within the zone / zone area
    UHI = 1 - clip(green_share, 0, 0.6) / 0.6      (0 = very green, 1 = mineral)
    heat_score = 30 + 60 * UHI

    Args:
        zones: IRIS zones with zone_id, geometry.
        green_spaces: green-space polygons, or None if the file is missing
            (then a flat fallback UHI is applied, per the MVP contract).
        fallback_uhi: UHI used when green_spaces is None.

    Returns:
        DataFrame with zone_id, heat_score.
    """
    zones_m = _to_metric(zones)

    if green_spaces is None or len(green_spaces) == 0:
        uhi = np.full(len(zones_m), fallback_uhi)
    else:
        green_m = _to_metric(green_spaces)
        green_union = green_m.union_all()
        green_area = zones_m.geometry.intersection(green_union).area
        green_share = (green_area / zones_m.geometry.area).clip(0, 1)
        uhi = 1 - np.clip(green_share, 0, 0.6) / 0.6

    heat_score = 30 + 60 * uhi

    return pd.DataFrame(
        {
            "zone_id": zones_m["zone_id"].to_numpy(),
            "heat_score": np.round(heat_score, 1),
        }
    )


if __name__ == "__main__":
    # Manual run on real files once downloaded (adjust filenames if needed):
    zones = gpd.read_file("data/CONTOURS-IRIS.shp")
    zones = zones[zones["INSEE_COM"].astype(str).str.startswith("75")].copy()
    zones = zones.rename(columns={"CODE_IRIS": "zone_id"})
    print(f"zones: {len(zones)} (expect ~992)")

    flood = gpd.read_file("data/flood_zones.shp")
    flood_df = compute_flood_layer(zones, flood)
    print(flood_df.describe())

    try:
        green = gpd.read_file("data/espaces_verts.geojson")
    except Exception:
        print("green-space file missing -> flat UHI fallback")
        green = None
    heat_df = compute_heat_layer(zones, green)
    print(heat_df.describe())

    out = flood_df.merge(heat_df, on="zone_id")
    out.to_csv("data/climate_layers.csv", index=False)
    print(f"saved data/climate_layers.csv ({len(out)} zones)")
