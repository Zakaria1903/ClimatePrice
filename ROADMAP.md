# ClimatePrice — Roadmap MVP1 (4 weeks)

One page, one source of truth. PM updates it 5 min/week.
Dates assume pitch in the week of Aug 3 — shift everything if the real demo date differs.

## Streams & owners

| Stream | Owner | Scope |
|---|---|---|
| Geo | ___ | IRIS zones + the final geospatial join |
| Data | ___ | DVF → median price + n_sales per zone |
| Climate | ---- | flood_score, dist_seine, heat_score per zone |
| ML / App | ___ | XGBoost, K-Means, discount formula, Streamlit demo |

## Timeline

| Week | Focus | Milestone (definition of done) |
|---|---|---|
| W1 · Jul 13-19 | Downloads + everyone runs the synthetic pipeline | Every teammate has seen the app run locally; pytest green on synthetic |
| W2 · Jul 20-26 | Each stream delivers its clean layer | Geo: ~992 zones · Data: price/zone, 100k+ rows · Climate: flood + heat scores · ML: app done on synthetic |
| W3 · Jul 27 - Aug 2 | **The join (critical path)** then switch to real data | `joined.geojson` passes contract tests; full pipeline green on real data; checkpoints validated as a team |
| W4 · Aug 3-9 | Freeze + pitch | Demo < 3 min, rehearsed twice; jury Q&A ready; tests screenshot in the deck |

## Dependencies

- Streams Geo / Data / Climate feed the W3 join — the only hard dependency.
- ML/App never waits: it develops against the synthetic twin (same column contract).

## Risks

| Risk | Impact | Plan B |
|---|---|---|
| The join slips past W3 | Demo has no real data | Demo runs on the synthetic twin — the product still works end to end |
| Géorisques export is messy | flood_score unreliable | Fallback: distance-to-Seine as sole flood proxy, documented as a V1 limit |
| A teammate drops a week | Stream stalls | Streams documented well enough for any teammate to pick up (this repo) |

## Done means done

A milestone counts only when: pytest layer green + checklist boxes ticked (see CHECKLIST.md).
