# ClimatePrice

**Where should you buy property in Paris today to be safe in 2035/2045?**

ClimatePrice crosses real estate transaction data with climate risk (flood + urban heat) and delivers a
verdict per Paris neighborhood — **Buy / Caution / Avoid** — under two climate scenarios (SSP2, SSP5)
and two horizons (2035, 2045), on an interactive map.

Built in 4 weeks as a Le Wagon Data Science & AI bootcamp capstone.

---

## Make commands

```bash
make install         # pip install -e ".[dev]"
make download-dvf    # download DVF 75 CSVs (2021–2025) into data/
make clean-dvf       # remove the downloaded DVF CSVs
make download-green  # download Paris green spaces into data/geo_green.geojson
make clean-green     # remove data/geo_green.geojson
make download-iris   # download + extract IRIS zone polygons into data/IRIS_SHAPES.gpkg
make clean-iris      # remove the downloaded/extracted IRIS files
make synthetic-data  # generate the synthetic twin (data/synthetic.geojson)
make pipeline        # run src/03_pipeline.py
make run             # synthetic-data + pipeline + streamlit run 04_app.py
make test            # pytest
make lint            # ruff check --fix + ruff format
```

`download-dvf` only fetches files that are missing — it's safe to re-run after adding a year to
`DVF_YEARS` in the `Makefile`, it won't re-download what's already in `data/`.

`download-iris` downloads the IGN IRIS geopackage archive and runs `src/scripts/extract_iris.py`,
which extracts it, filters to Paris (`code_iris` starting with `75`), writes `data/IRIS_SHAPES.gpkg`,
and cleans up the intermediate `.7z`/tmp files.

## Features

- Interactive map of ~992 Paris IRIS neighborhoods
- Investment verdict per zone: Buy / Caution / Avoid
- Two climate risks: Seine flood exposure (PPRI) + heat island proxy (green space)
- Climate discount model anchored on academic literature (4–19% flood discounts)
- Scenario toggles: SSP2 vs SSP5 × 2035 vs 2045 — watch riverside zones flip
- Two ML models: XGBoost (risk scoring + price baseline) and K-Means (neighborhood profiles)

## Architecture

```
raw data (IGN, DVF, Géorisques, opendata.paris)
        │  src/02_real_data_join.py    ← geospatial join (EPSG:2154 math)
        ▼
data/joined.geojson                    ← THE CONTRACT (8 columns)
        │  src/03_pipeline.py          ← XGBoost + K-Means + discount + verdict
        ▼
data/climateprice_output.geojson
        │  04_app.py
        ▼
Streamlit map demo
```

The **contract**: `zone_id · geometry · price_m2 · heat_score · flood_score · elevation · dist_seine · n_sales`.
Models and app depend only on these columns — which is why the whole team can develop against the
synthetic twin (`src/01_synthetic_data.py`) before real data lands.

## Installation

```bash
git clone <repo-url> && cd ClimatePrice
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running locally

```bash
# On synthetic data (works immediately, no downloads):
python src/01_synthetic_data.py
python src/03_pipeline.py
streamlit run 04_app.py

# On real data (after downloading the sources — see "Data downloads" below):
python src/02_real_data_join.py
python src/03_pipeline.py
streamlit run 04_app.py
```

Equivalent shortcut for the synthetic path: `make run`.

## Tests

```bash
pytest                    # 20 tests: contract / models / sanity
pytest --cov              # optional coverage report
```

Tests skip (not fail) on files not yet produced — run them from day one.

## Linting

```bash
ruff check . --fix && ruff format .
```

CI (GitHub Actions) enforces both on every PR. See `docs/ENGINEERING.md` for the full workflow.

## Folder structure

```
├── src/
│   ├── 01_synthetic_data.py  # synthetic twin generator (contract-identical)
│   ├── 02_real_data_join.py  # real data cleaning + geospatial join
│   ├── 03_pipeline.py        # models + formulas + verdicts
│   └── scripts/
│       └── extract_iris.py   # unpacks the IRIS .7z, filters to Paris (used by `make download-iris`)
├── 04_app.py                 # Streamlit demo
├── tests/
│   └── test_pipeline.py      # pytest suite (contract / models / sanity)
├── data/                     # generated + downloaded data (gitignored)
├── docs/
│   ├── ROADMAP.md            # 4-week plan, owners, risks
│   └── ENGINEERING.md        # engineering practices
├── CHECKLIST.md              # weekly acceptance checklist
├── Makefile                  # install / download-* / synthetic-data / pipeline / run / test / lint
└── pyproject.toml            # deps + ruff + pytest config
```

## Team

| Stream | Owner |
|---|---|
| Geo (zones + join) | ___ |
| Data (DVF prices) | ___ |
| Climate (flood + heat) | --- |
| ML / App | ___ |

## Data downloads

All source data is public and free. Each teammate downloads locally into `data/`
(gitignored — never commit real data). The pipeline expects these exact filenames.
Where a `make download-*` target exists, prefer it over the manual steps — it fetches the file
straight to the right name.

| Source | Get it via | Save as |
|---|---|---|
| IGN Contours IRIS (zone polygons) | `make download-iris` | `data/IRIS_SHAPES.gpkg` |
| DVF geolocalized transactions (2021–2025) | `make download-dvf` | `data/dvf_75_<year>.csv.gz` |
| Paris green spaces (heat proxy) | `make download-green` | `data/geo_green.geojson` |
| Géorisques PPRI (Seine flood polygons) | manual — [georisques.gouv.fr](https://www.georisques.gouv.fr) → search Paris PPRI → export shapefile | `data/flood_zones.shp` (+ associated files) |

**Folder structure once downloaded:**

```text
data/
├── IRIS_SHAPES.gpkg
├── dvf_75_2021.csv.gz
├── dvf_75_2022.csv.gz
├── dvf_75_2023.csv.gz
├── dvf_75_2024.csv.gz
├── dvf_75_2025.csv.gz
├── geo_green.geojson
├── flood_zones.shp               # + associated files
├── synthetic.geojson             # from `make synthetic-data` / src/01_synthetic_data.py
├── joined.geojson                # from src/02_real_data_join.py — THE CONTRACT
└── climateprice_output.geojson   # from src/03_pipeline.py
```

## License

MIT — data sources remain under their respective open licenses
(IGN, DGFiP/DVF, Géorisques, Ville de Paris).
