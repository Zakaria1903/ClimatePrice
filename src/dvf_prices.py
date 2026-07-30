"""dvf_prices.py — median price/m2 + n_sales per Paris IRIS zone, from DVF data."""

import geopandas as gpd
import pandas as pd

DVF_FILES = [
    "data/dvf_75_2021.csv.gz",
    "data/dvf_75_2022.csv.gz",
    "data/dvf_75_2023.csv.gz",
    "data/dvf_75_2024.csv.gz",
    "data/dvf_75_2025.csv.gz",
]
IRIS_PATH = "data/IRIS_SHAPES.gpkg"

MIN_SURFACE = 8  # m2, filters out garbage rows
MIN_VALUE = 1000  # euros, filters out garbage rows
MIN_PRICE_M2 = 500
MAX_PRICE_M2 = 50000


def load_dvf() -> pd.DataFrame:
    frames = [pd.read_csv(f, compression="gzip", low_memory=False) for f in DVF_FILES]
    sales = pd.concat(frames, ignore_index=True)
    print(f"raw DVF rows loaded: {len(sales)}")
    return sales


def clean_dvf(sales: pd.DataFrame) -> pd.DataFrame:
    sales = sales[sales["nature_mutation"] == "Vente"]
    sales = sales[sales["type_local"].isin(["Appartement", "Maison"])]
    sales = sales.dropna(subset=["valeur_fonciere", "surface_reelle_bati", "longitude", "latitude"])
    sales = sales[sales["surface_reelle_bati"] > MIN_SURFACE]
    sales = sales[sales["valeur_fonciere"] > MIN_VALUE]
    sales = sales.drop_duplicates(subset=["id_mutation"])

    sales["price_m2"] = sales["valeur_fonciere"] / sales["surface_reelle_bati"]
    sales = sales[(sales["price_m2"] >= MIN_PRICE_M2) & (sales["price_m2"] <= MAX_PRICE_M2)]

    print(f"rows after cleaning: {len(sales)}")
    return sales


def join_to_zones(sales: pd.DataFrame, iris: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = gpd.GeoDataFrame(
        sales,
        geometry=gpd.points_from_xy(sales["longitude"], sales["latitude"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(points, iris[["code_iris", "geometry"]], predicate="within", how="inner")
    return joined


def aggregate_by_zone(joined: gpd.GeoDataFrame) -> pd.DataFrame:
    agg = (
        joined.groupby("code_iris")
        .agg(
            price_m2=("price_m2", "median"),
            n_sales=("price_m2", "count"),
        )
        .reset_index()
    )
    agg = agg.rename(columns={"code_iris": "zone_id"})
    return agg


def main():
    sales = load_dvf()
    sales = clean_dvf(sales)

    iris = gpd.read_file(IRIS_PATH)
    joined = join_to_zones(sales, iris)
    result = aggregate_by_zone(joined)

    zones_ok = (result["n_sales"] >= 20).sum()
    print(f"zones with >=20 sales: {zones_ok} / {len(result)} (out of 992 total IRIS zones)")

    result.to_csv("data/dvf_by_zone.csv", index=False)
    print(f"output -> data/dvf_by_zone.csv ({len(result)} zones)")


if __name__ == "__main__":
    main()
