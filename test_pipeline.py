"""
ClimatePrice — test suite (run: pytest test_pipeline.py -v)

3 layers:
  1. CONTRACT tests  -> joined.geojson (or synthetic twin) respects the column contract
  2. MODEL tests     -> pipeline output (risk_score, clusters, discount, verdict) is coherent
  3. SANITY tests    -> the results make real-world sense (the jury-proof checks)

Works on synthetic data TODAY and real data later — nothing to change.
If a file doesn't exist yet, its tests are SKIPPED (not failed), so you can
run this from week 1 and watch tests light up green as the project advances.

Adjust the CONFIG block below if your column names differ.
"""

import os

import pytest

gpd = pytest.importorskip("geopandas")
pd = pytest.importorskip("pandas")

# ----------------------------- CONFIG ---------------------------------
JOINED_PATH = "data/joined.geojson"  # real join (script 02)
SYNTH_PATH = "data/synthetic.geojson"  # synthetic twin (script 01)
OUTPUT_PATH = "data/climateprice_output.geojson"  # pipeline output (script 03)

CONTRACT_COLUMNS = {
    "zone_id",
    "geometry",
    "price_m2",
    "heat_score",
    "flood_score",
    "elevation",
    "dist_seine",
    "n_sales",
}

SCENARIOS = ["SSP2", "SSP5"]
HORIZONS = ["2035", "2045"]
# expected column pattern in the output, e.g. discount_SSP2_2035, verdict_SSP5_2045
DISCOUNT_COL = "discount_{s}_{h}"
VERDICT_COL = "verdict_{s}_{h}"

VERDICT_VALUES = {"Buy", "Caution", "Avoid"}
MAX_DISCOUNT = 0.15  # the 15% literature cap
BUY_THRESHOLD = 0.04
CAUTION_THRESHOLD = 0.08
# -----------------------------------------------------------------------


def _load(path):
    if not os.path.exists(path):
        pytest.skip(f"{path} not produced yet — run the matching script first")
    return gpd.read_file(path)


@pytest.fixture(scope="module")
def joined():
    """Real join if it exists, otherwise the synthetic twin."""
    path = JOINED_PATH if os.path.exists(JOINED_PATH) else SYNTH_PATH
    return _load(path)


@pytest.fixture(scope="module")
def output():
    return _load(OUTPUT_PATH)


# =========================== 1. CONTRACT ===============================


class TestContract:
    def test_exact_columns(self, joined):
        assert CONTRACT_COLUMNS.issubset(set(joined.columns)), (
            f"Missing columns: {CONTRACT_COLUMNS - set(joined.columns)}"
        )

    def test_no_missing_values(self, joined):
        cols = list(CONTRACT_COLUMNS - {"geometry"})
        nans = joined[cols].isna().sum()
        assert nans.sum() == 0, f"NaN found:\n{nans[nans > 0]}"

    def test_zone_id_unique(self, joined):
        assert joined["zone_id"].is_unique, "Duplicate zone_id — the join produced duplicates"

    def test_crs_is_wgs84(self, joined):
        assert joined.crs is not None and joined.crs.to_epsg() == 4326, (
            "Output must be saved in EPSG:4326 (computation in 2154, save in 4326)"
        )

    def test_zone_count_plausible(self, joined):
        assert 100 <= len(joined) <= 1200, (
            f"{len(joined)} zones — expected a few hundred (≈992 before filters)"
        )

    def test_value_ranges(self, joined):
        assert joined["price_m2"].between(3000, 30000).all(), "price_m2 outside 3k-30k trim"
        assert joined["flood_score"].between(0, 100).all(), "flood_score outside 0-100"
        assert joined["heat_score"].between(30, 90).all(), "heat_score outside 30-90"
        assert (joined["n_sales"] >= 20).all(), "zones with n_sales < 20 not filtered"
        assert (joined["dist_seine"] >= 0).all(), "negative dist_seine"

    def test_geometries_valid(self, joined):
        assert joined.geometry.is_valid.all(), "Invalid geometries — run .buffer(0) or make_valid"


# ============================ 2. MODEL =================================


class TestModels:
    def test_risk_score_bounds(self, output):
        assert output["risk_score"].between(0, 100).all(), "risk_score not clipped to 0-100"

    def test_clusters_k4(self, output):
        assert output["cluster"].nunique() == 4, (
            f"{output['cluster'].nunique()} clusters — expected k=4"
        )

    def test_cluster_names_exist(self, output):
        assert output["cluster_name"].notna().all()
        assert output["cluster_name"].nunique() == 4

    def test_all_four_combos_exist(self, output):
        for s in SCENARIOS:
            for h in HORIZONS:
                col = DISCOUNT_COL.format(s=s, h=h)
                assert col in output.columns, f"Missing combo column: {col}"

    def test_discount_bounds(self, output):
        for s in SCENARIOS:
            for h in HORIZONS:
                d = output[DISCOUNT_COL.format(s=s, h=h)]
                assert (d >= 0).all() and (d <= MAX_DISCOUNT + 1e-9).all(), (
                    f"discount {s}/{h} outside [0, 15%]"
                )

    def test_verdict_values(self, output):
        for s in SCENARIOS:
            for h in HORIZONS:
                v = set(output[VERDICT_COL.format(s=s, h=h)].unique())
                assert v.issubset(VERDICT_VALUES), f"Unknown verdict values: {v - VERDICT_VALUES}"

    def test_verdict_matches_thresholds(self, output):
        """Verdict must be derivable from the discount — no drift between the two."""
        for s in SCENARIOS:
            for h in HORIZONS:
                d = output[DISCOUNT_COL.format(s=s, h=h)]
                v = output[VERDICT_COL.format(s=s, h=h)]
                expected = pd.cut(
                    d,
                    bins=[-1, BUY_THRESHOLD, CAUTION_THRESHOLD, 2],
                    labels=["Buy", "Caution", "Avoid"],
                    right=False,
                ).astype(str)
                mismatch = (expected != v.astype(str)).sum()
                assert mismatch == 0, f"{mismatch} verdicts inconsistent with thresholds ({s}/{h})"

    def test_scenario_monotonicity(self, output):
        """SSP5 must discount at least as much as SSP2, 2045 at least as much as 2035."""
        for h in HORIZONS:
            d2 = output[DISCOUNT_COL.format(s="SSP2", h=h)]
            d5 = output[DISCOUNT_COL.format(s="SSP5", h=h)]
            assert (d5 >= d2 - 1e-9).all(), f"SSP5 < SSP2 for some zones ({h})"
        for s in SCENARIOS:
            d35 = output[DISCOUNT_COL.format(s=s, h="2035")]
            d45 = output[DISCOUNT_COL.format(s=s, h="2045")]
            assert (d45 >= d35 - 1e-9).all(), f"2045 < 2035 for some zones ({s})"

    def test_discount_follows_risk(self, output):
        """Higher risk_score => higher discount (same scenario/horizon)."""
        d = output[DISCOUNT_COL.format(s="SSP5", h="2045")]
        corr = output["risk_score"].corr(d)
        assert corr > 0.95, f"discount/risk correlation only {corr:.2f} — formula bug?"


# ============================ 3. SANITY ================================


class TestSanity:
    def test_flood_decreases_with_distance(self, joined):
        """Zones nearer the flood envelope should score higher — the riverside band."""
        corr = joined["flood_score"].corr(joined["dist_seine"])
        assert corr < 0, f"flood_score/dist_seine correlation = {corr:.2f} — should be negative"

    def test_ssp2_2035_mostly_buy(self, output):
        v = output[VERDICT_COL.format(s="SSP2", h="2035")]
        share_buy = (v == "Buy").mean()
        assert share_buy > 0.5, (
            f"Only {share_buy:.0%} Buy under SSP2/2035 — expected the mild scenario to be mostly Buy"
        )

    def test_ssp5_2045_has_avoid(self, output):
        v = output[VERDICT_COL.format(s="SSP5", h="2045")]
        assert (v == "Avoid").any(), (
            "No Avoid zone even under SSP5/2045 — the pessimistic scenario should flip riverside zones"
        )

    def test_price_variance_exists(self, joined):
        """Paris prices vary a lot by zone; near-constant prices mean the DVF aggregation broke."""
        cv = joined["price_m2"].std() / joined["price_m2"].mean()
        assert cv > 0.05, "price_m2 nearly constant across zones — check the DVF aggregation"
