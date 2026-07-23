DVF_YEARS := 2021 2022 2023 2024 2025
DVF_BASE := https://files.data.gouv.fr/geo-dvf/latest/csv
DVF_FILES := $(patsubst %, data/dvf_75_%.csv.gz, $(DVF_YEARS))
GREEN_SPACES_URL := https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/espaces_verts/exports/geojson?lang=fr&timezone=Europe%2FParis
IRIS_URL := https://data.geopf.fr/telechargement/download/CONTOURS-IRIS/CONTOURS-IRIS_3-0__GPKG_WGS84G_FRA_2026-01-01/CONTOURS-IRIS_3-0__GPKG_WGS84G_FRA_2026-01-01.7z

.PHONY: install download-dvf clean-dvf download-green clean-green download-iris clean-iris \
	synthetic-data pipeline run test lint

install:
	pip install -e ".[dev]"

download-dvf: $(DVF_FILES)

clean-dvf:
	rm -f $(DVF_FILES)

data/dvf_75_%.csv.gz: | data/
	curl -Lf -o $@ $(DVF_BASE)/$*/departements/75.csv.gz

download-green: data/geo_green.geojson

data/geo_green.geojson: | data/
	curl -Lf -o $@ $(GREEN_SPACES_URL)

clean-green:
	rm -f data/geo_green.geojson

download-iris: data/IRIS_SHAPES.7z
data/IRIS_SHAPES.7z: | data/
	curl -Lf -o $@ $(IRIS_URL)
	uv run python src/scripts/extract_iris.py

clean-iris:
	rm -f data/IRIS_SHAPES.*

data/:
	mkdir -p $@

synthetic-data: | data/
	python src/01_synthetic_data.py

pipeline:
	python src/03_pipeline.py

run: synthetic-data pipeline
	streamlit run 04_app.py

test:
	pytest

lint:
	ruff check . --fix && ruff format .
