"""download_climate_data.py — automated acquisition of the Climate stream's raw data.

Best practice: data acquisition is CODE, not clicks. Anyone on the team can rebuild
the data/ folder by running this script — reproducible, documented, versionable.

Usage:
    python download_climate_data.py            # downloads everything missing
    python download_climate_data.py --force    # re-downloads even if present

What it fetches:
  1. Paris green spaces (opendata.paris.fr)  -> data/espaces_verts.geojson  [automated]
  2. Flood zones dept 75 (Géorisques TRI)    -> data/flood_raw/             [tries known
     URLs; if all fail, prints exact manual instructions]

The flood shapefile then needs one manual step (choosing the 'moyen' scenario file),
guided by the script's final message.
"""

import argparse
import logging
import sys
import urllib.request
import zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path("data")

# Stable Opendatasoft export API — reliable URL pattern
GREEN_URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/espaces_verts/exports/geojson"
)
GREEN_OUT = DATA_DIR / "espaces_verts.geojson"

# Géorisques TRI 2020 departmental archives — URL patterns observed in the wild.
# Portals move; we try candidates in order and fall back to manual instructions.
FLOOD_CANDIDATES = [
    "https://files.georisques.fr/di_2020/tri_2020_sig_di_075.zip",
    "https://files.georisques.fr/di_2020/TRI_2020_SIG_DI_075.zip",
]
FLOOD_RAW_DIR = DATA_DIR / "flood_raw"
FLOOD_PAGE = (
    "https://www.georisques.gouv.fr/donnees/bases-de-donnees/zonages-inondation-rapportage-2020"
)

MANUAL_FLOOD_HELP = f"""
--------------------------------------------------------------------------
MANUAL STEP REQUIRED for the flood data:
  1. Open {FLOOD_PAGE}
  2. Section 'Echelle départementale' -> select 75 (Paris) -> download the zip
  3. Unzip into {FLOOD_RAW_DIR}/
  4. Then run:  python download_climate_data.py  again to finish the setup check
--------------------------------------------------------------------------"""


def download(url: str, dest: Path, timeout: int = 120) -> bool:
    """Download url to dest. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        log.info("downloading %s", url)
        req = urllib.request.Request(url, headers={"User-Agent": "climateprice-bootcamp/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            f.write(resp.read())
        tmp.rename(dest)
        log.info("saved %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
        return True
    except Exception as exc:  # noqa: BLE001 — we want to fall through to the next candidate
        log.warning("failed: %s (%s)", url, exc)
        tmp.unlink(missing_ok=True)
        return False


def fetch_green(force: bool) -> bool:
    if GREEN_OUT.exists() and not force:
        log.info("green spaces already present: %s", GREEN_OUT)
        return True
    return download(GREEN_URL, GREEN_OUT)


def fetch_flood(force: bool) -> bool:
    shp_present = list(FLOOD_RAW_DIR.glob("**/*.shp")) if FLOOD_RAW_DIR.exists() else []
    if shp_present and not force:
        log.info(
            "flood shapefiles already present: %d found in %s", len(shp_present), FLOOD_RAW_DIR
        )
        return True

    zip_path = DATA_DIR / "flood_75.zip"
    for url in FLOOD_CANDIDATES:
        if download(url, zip_path):
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(FLOOD_RAW_DIR)
            log.info("extracted to %s", FLOOD_RAW_DIR)
            return True
    return False


def report_flood_scenarios() -> None:
    """List candidate shapefiles so the user can pick the 'moyen' scenario."""
    shps = sorted(FLOOD_RAW_DIR.glob("**/*.shp"))
    if not shps:
        return
    log.info("Available flood shapefiles (pick the MOYEN scenario = centennial flood):")
    for p in shps:
        marker = "  <-- likely this one" if "moy" in p.name.lower() else ""
        log.info("   %s%s", p.relative_to(DATA_DIR), marker)
    log.info(
        "Next: point climate_layers/validate_climate to it, or copy it to "
        "data/flood_zones.shp (with its .dbf/.shx/.prj siblings)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    ok_green = fetch_green(args.force)
    ok_flood = fetch_flood(args.force)

    if not ok_green:
        log.error("green spaces download failed — check your connection and retry")
    if not ok_flood:
        log.error("automatic flood download failed — do the manual step:%s", MANUAL_FLOOD_HELP)
    else:
        report_flood_scenarios()

    return 0 if (ok_green and ok_flood) else 1


if __name__ == "__main__":
    sys.exit(main())
