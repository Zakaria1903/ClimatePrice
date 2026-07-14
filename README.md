# ClimatePrice Project

**Where should you buy property in Paris today to be safe in 2035/2045?**

ClimatePrice crosses real estate transaction data with climate risk (flood + urban heat) and delivers a
verdict per Paris neighborhood — **Buy / Caution / Avoid** — under two climate scenarios (SSP2, SSP5)
and two horizons (2035, 2045), on an interactive map.

Built in 4 weeks as a Le Wagon Data Science & AI bootcamp capstone.

---

## Features

- Interactive map of ~992 Paris IRIS neighborhoods
- Investment verdict per zone: Buy / Caution / Avoid
- Two climate risks: Seine flood exposure (PPRI) + heat island proxy (green space)
- Climate discount model anchored on academic literature (4-19% flood discounts)
- Scenario toggles: SSP2 vs SSP5 × 2035 vs 2045 -> watch riverside zones flip
- Two ML models: XGBoost (risk scoring + price baseline) and K-Means (neighborhood profiles)

## Architecture

```
raw data (IGN, DVF, Géorisques, opendata.paris)
        │  02_real_data_join.py        ← geospatial join (EPSG:2154 math)
        ▼
data/joined.geojson                    ← THE CONTRACT (8 columns)
        │  03_pipeline.py              ← XGBoost + K-Means + discount + verdict
        ▼
data/climateprice_output.geojson
        │  04_app.py
        ▼
Streamlit map demo
```

The **contract**: `zone_id - geometry - price_m2 - heat_score - flood_score - elevation - dist_seine - n_sales`.
Models and app depend only on these columns which is why the whole team can develop against the
synthetic twin (`01_synthetic_data.py`) before real data lands.

## Installation

```bash
git clone <repo-url> && cd climateprice
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running locally

```bash
# On synthetic data (works immediately, no downloads):
python 01_synthetic_data.py
python 03_pipeline.py
streamlit run 04_app.py

# On real data (after downloading the sources — see ENGINEERING.md):
python 02_real_data_join.py
python 03_pipeline.py
streamlit run 04_app.py
```

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

CI (GitHub Actions) enforces both on every PR. See `ENGINEERING.md` for the full workflow.

## Folder structure

```
├── 01_synthetic_data.py      # synthetic twin generator (contract-identical)
├── 02_real_data_join.py      # real data cleaning + geospatial join
├── 03_pipeline.py            # models + formulas + verdicts
├── 04_app.py                 # Streamlit demo
├── test_pipeline.py          # pytest suite (contract / models / sanity)
├── data/                     # generated + downloaded data (gitignored)
├── ROADMAP.md                # 4-week plan, owners, risks
├── CHECKLIST.md              # weekly acceptance checklist
├── ENGINEERING.md            # engineering practices
└── pyproject.toml            # deps + ruff + pytest config
```

## Team

| Stream | Owner |
|---|---|
| Geo (zones + join) | ___ |
| Data (DVF prices) | ___ |
| Climate (flood + heat) | --- |
| ML / App | ___ |

## License

MIT - data sources remain under their respective open licenses
(IGN, DGFiP/DVF, Géorisques, Ville de Paris).
