IGN_URL := "https://data.geopf.fr/telechargement/download/CONTOURS-IRIS/CONTOURS-IRIS_3-0__GPKG_WGS84G_FRA_2026-01-01/CONTOURS-IRIS_3-0__GPKG_WGS84G_FRA_2026-01-01.7z"
DVF_YEARS := 2021 2022 2023 2024 2025
DVF_BASE := https://files.data.gouv.fr/geo-dvf/latest/csv
DVF_FILES := $(patsubst %, data/dvf_75_%.csv.gz, $(DVF_YEARS))

install:
	pip install -e ".[dev]"

.PHONY: download-dvf
download-dvf: $(DVF_FILES)

.PHONY: clean-dvf
clean-dvf:
	rm -f $(DVF_FILES)

data/:
	mkdir -p $@

data/dvf_75_%.csv.gz: | data/
	curl -Lf -o $@ $(DVF_BASE)/$*/departements/75.csv.gz

pipeline:
	python 03_pipeline.py

run: data pipeline
	streamlit run 04_app.py

test:
	pytest

lint:
	ruff check . --fix && ruff format