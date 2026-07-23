import os
from pathlib import Path
import geopandas as gpd
import py7zr
import shutil

# files path
zip_path = Path("data/IRIS_SHAPES.7z")
extract_dir = Path("data/tmp_iris")
output_path = Path("data/IRIS_SHAPES.gpkg")

if not zip_path.exists():
    raise FileNotFoundError(f"File {zip_path} does not exist. Download it before with make download-iris")


# 1. Python native decompression
print("Décompression of .7z file in progress...")
with py7zr.SevenZipFile(zip_path, mode="r") as z:
    z.extractall(extract_dir)

# 2. Looking for gpkg files
gpkg_file = list(extract_dir.rglob("*.gpkg"))
if not gpkg_file:
    raise FileNotFoundError(f"No gpkg file found in {extract_dir}")

# 3. Loading and filtering on Paris
gpkg = gpd.read_file(gpkg_file[0])
gpkg_paris = gpkg[(gpkg["code_iris"].astype(str).str.startswith("75")) &
                  (gpkg["nom_commune"].str.contains("Paris"))].copy()
print(f"Paris shapes number found: {len(gpkg_paris)}")

# 4. Export gpkg_paris
gpkg_paris.to_file(output_path, encoding="utf-8")
print(f"File exported at: {output_path}")

# 5. Cleaning
shutil.rmtree(extract_dir)
if zip_path.exists():
    zip_path.unlink()
print("Cleaned successfuly")
