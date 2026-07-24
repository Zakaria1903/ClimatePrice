# ClimatePrice — Acceptance checklist (PM)

The manual companion to `tests/test_pipeline.py`. Pytest checks what a machine can check;
this list checks what only a human can judge. Review together at the end of each week.

**Rule: a stream is "done" when its boxes are ticked AND its pytest layer is green.**

---

## Week 1 — Everyone starts, nobody waits
- [ ] Every teammate has cloned the repo and installed the environment
- [ ] Every teammate has run `make run` (or `src/01_synthetic_data.py → src/03_pipeline.py → streamlit run 04_app.py`) and SEEN the map
- [ ] `pytest` runs green on the synthetic data
- [ ] All 4 raw datasets downloaded (IRIS, DVF x5 years, Géorisques, espaces verts)
- [ ] Roadmap shared and every stream owner confirmed their scope

## Week 2 — Clean layers delivered
### Geo
- [ ] ~992 Paris zones, EPSG:2154, `zone_id` column present
### Data
- [ ] 100k+ DVF rows survive cleaning
- [ ] Median price per zone looks sane: 6e/7e/16e among the most expensive
- [ ] Most zones survive the n_sales ≥ 20 filter (spot-check the count)
### Climate
- [ ] flood_score map shows a clear riverside band (visual check on a quick plot)
- [ ] heat_score higher in dense mineral areas, lower near parks (spot-check 3 zones you know)
### ML / App
- [ ] App fully working on synthetic: toggles, zone click-card, headline counters

## Week 3 — The join + the switch to real data
- [ ] `joined.geojson` exists and pytest CONTRACT layer is green on it
- [ ] Pipeline re-run on real data with zero code changes outside script 02
- [ ] pytest MODEL + SANITY layers green on real output
- [ ] Visual review as a team: SSP2/2035 mostly Buy, SSP5/2045 flips riverside zones to Avoid
- [ ] Click 5 zones you know personally — do the verdicts feel defensible?

## Week 4 — Freeze + pitch
- [ ] Feature freeze declared (anything unfinished moves to V2, no exceptions)
- [ ] Full pytest suite green on final data — screenshot it for the deck (juries love it)
- [ ] Demo rehearsed twice, under 3 minutes
- [ ] Jury Q&A prepared: no future-price prediction claim / no double counting / why ML on our own label
- [ ] Backup plan tested: demo runs on synthetic data if something breaks on stage

---

## Standing rules
1. Nobody is ever blocked: until `joined.geojson` lands, everything runs on the synthetic twin.
2. Week 4 is sacred: no new features after the freeze.
3. A failing test blocks a merge. A red checklist box blocks the weekly milestone.
