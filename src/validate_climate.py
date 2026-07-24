"""validate_climate.py — runs the climate layers on REAL data and produces the
Week-2 acceptance evidence: stats, domain checks, and the two maps.

Best practice: validation is a script, not a manual ritual. Run it after every
data refresh; attach its outputs (PNG + printed report) to the PR.

Usage:
    python validate_climate.py \
        --zones data/CONTOURS-IRIS.shp \
        --flood data/flood_zones.shp \
        --green data/espaces_verts.geojson

Outputs:
    data/climate_layers.csv   (zone_id, flood_score, dist_seine, heat_score)
    reports/flood_map.png     (the riverside band — THE visual checkpoint)
    reports/heat_map.png
    + a printed PASS/FAIL domain-check report
"""

import argparse
import logging
import sys
from pathlib import Path

import geopandas as gpd

from climate_layers import compute_flood_layer, compute_heat_layer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Official domain fact (PPRI de Paris, DRIEAT): these arrondissements are entirely
# OUTSIDE the Seine flood zone. Used as an independent sanity check.
DRY_ARRONDISSEMENTS = {"14", "17", "18", "19", "20"}


def load_paris_zones(path: Path) -> gpd.GeoDataFrame:
    zones = gpd.read_file(path)
    zones = zones[zones["INSEE_COM"].astype(str).str.startswith("75")].copy()
    zones = zones.rename(columns={"CODE_IRIS": "zone_id"})
    log.info("zones loaded: %d (expect ~992)", len(zones))
    # arrondissement = last 2 digits of INSEE_COM (75101 -> 01 ... 75120 -> 20)
    zones["arrondissement"] = zones["INSEE_COM"].astype(str).str[-2:]
    return zones


def check(name: str, condition: bool, detail: str) -> bool:
    status = "PASS" if condition else "FAIL"
    log.info("[%s] %s — %s", status, name, detail)
    return condition


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zones", type=Path, default=Path("data/CONTOURS-IRIS.shp"))
    p.add_argument("--flood", type=Path, default=Path("data/flood_zones.shp"))
    p.add_argument("--green", type=Path, default=Path("data/espaces_verts.geojson"))
    p.add_argument("--out", type=Path, default=Path("data/climate_layers.csv"))
    args = p.parse_args()

    zones = load_paris_zones(args.zones)

    flood_gdf = gpd.read_file(args.flood)
    log.info("flood polygons: %d", len(flood_gdf))
    flood = compute_flood_layer(zones, flood_gdf)

    try:
        green_gdf = gpd.read_file(args.green)
        log.info("green polygons: %d", len(green_gdf))
    except Exception as exc:  # noqa: BLE001
        log.warning("green file unreadable (%s) -> flat UHI fallback", exc)
        green_gdf = None
    heat = compute_heat_layer(zones, green_gdf)

    df = flood.merge(heat, on="zone_id")
    df = df.merge(zones[["zone_id", "arrondissement"]], on="zone_id")

    args.out.parent.mkdir(exist_ok=True)
    df.drop(columns="arrondissement").to_csv(args.out, index=False)
    log.info("saved %s (%d zones)", args.out, len(df))

    # ---------------- domain checks ----------------
    log.info("---- DOMAIN CHECKS ----")
    results = []

    share_zero = (df["flood_score"] == 0).mean()
    results.append(
        check("most zones dry", 0.4 <= share_zero <= 0.95, f"{share_zero:.0%} at flood_score=0")
    )

    riverside = df[df["flood_score"] > 30]
    results.append(
        check("riverside band exists", len(riverside) >= 20, f"{len(riverside)} zones > 30")
    )

    dry = df[df["arrondissement"].isin(DRY_ARRONDISSEMENTS)]
    dry_max = dry["flood_score"].max()
    results.append(
        check(
            "official dry arrondissements (14/17/18/19/20)",
            dry_max < 5,
            f"max flood_score there = {dry_max:.1f} (PPRI says ~0)",
        )
    )

    corr = df["flood_score"].corr(df["dist_seine"])
    results.append(check("flood decreases with distance", corr < -0.3, f"corr = {corr:.2f}"))

    heat_spread = df["heat_score"].std()
    results.append(check("heat varies across zones", heat_spread > 5, f"std = {heat_spread:.1f}"))
    results.append(
        check(
            "heat within bounds",
            df["heat_score"].between(30, 90).all(),
            f"range {df['heat_score'].min():.0f}-{df['heat_score'].max():.0f}",
        )
    )

    # ---------------- maps ----------------
    try:
        import matplotlib.pyplot as plt

        reports = Path("reports")
        reports.mkdir(exist_ok=True)
        gdf = zones.merge(df, on="zone_id")
        for col, cmap, fname in [
            ("flood_score", "Blues", "flood_map.png"),
            ("heat_score", "OrRd", "heat_map.png"),
        ]:
            ax = gdf.plot(column=col, cmap=cmap, legend=True, figsize=(10, 8))
            ax.set_axis_off()
            ax.set_title(f"Paris — {col}")
            plt.savefig(reports / fname, dpi=130, bbox_inches="tight")
            plt.close()
            log.info("saved reports/%s", fname)
    except ImportError:
        log.warning("matplotlib not installed -> skipping maps (pip install matplotlib)")

    log.info("---- SUMMARY: %d/%d checks passed ----", sum(results), len(results))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
