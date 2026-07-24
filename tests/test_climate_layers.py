"""Tests for climate_layers.py — synthetic geometry, no real data needed.

Setup: a 3-zone toy city in EPSG:2154 meters.
  zone A: fully inside the flood envelope, no green
  zone B: half inside the flood envelope, half green
  zone C: dry, fully green
"""

import geopandas as gpd
import pytest
from shapely.geometry import box

from climate_layers import compute_flood_layer, compute_heat_layer

M = "EPSG:2154"


@pytest.fixture
def zones():
    return gpd.GeoDataFrame(
        {
            "zone_id": ["A", "B", "C"],
            "geometry": [
                box(0, 0, 1000, 1000),  # A
                box(1000, 0, 2000, 1000),  # B
                box(5000, 0, 6000, 1000),  # C (far away)
            ],
        },
        crs=M,
    )


@pytest.fixture
def flood():
    # covers all of A and the left half of B
    return gpd.GeoDataFrame({"geometry": [box(0, 0, 1500, 1000)]}, crs=M)


@pytest.fixture
def green():
    # right half of B + all of C
    return gpd.GeoDataFrame(
        {"geometry": [box(1500, 0, 2000, 1000), box(5000, 0, 6000, 1000)]}, crs=M
    )


class TestFlood:
    def test_scores(self, zones, flood):
        out = compute_flood_layer(zones, flood).set_index("zone_id")
        assert out.loc["A", "flood_score"] == pytest.approx(100, abs=0.1)
        assert out.loc["B", "flood_score"] == pytest.approx(50, abs=0.1)
        assert out.loc["C", "flood_score"] == pytest.approx(0, abs=0.1)

    def test_distance(self, zones, flood):
        out = compute_flood_layer(zones, flood).set_index("zone_id")
        assert out.loc["A", "dist_seine"] == 0.0  # centroid inside envelope
        assert out.loc["B", "dist_seine"] == 0.0  # centroid at x=1500, on edge
        assert out.loc["C", "dist_seine"] == pytest.approx(4.0, abs=0.1)  # 5500-1500 m

    def test_crs_reprojection(self, zones, flood):
        """Inputs in WGS84 must be handled identically."""
        out_metric = compute_flood_layer(zones, flood)
        out_wgs = compute_flood_layer(zones.to_crs("EPSG:4326"), flood.to_crs("EPSG:4326"))
        assert out_metric["flood_score"].tolist() == pytest.approx(
            out_wgs["flood_score"].tolist(), abs=0.5
        )

    def test_missing_crs_raises(self, zones, flood):
        naked = gpd.GeoDataFrame(
            {"zone_id": zones["zone_id"], "geometry": zones.geometry.to_numpy()}
        )
        with pytest.raises(ValueError, match="no CRS"):
            compute_flood_layer(naked, flood)


class TestHeat:
    def test_scores(self, zones, green):
        out = compute_heat_layer(zones, green).set_index("zone_id")
        assert out.loc["A", "heat_score"] == pytest.approx(90, abs=0.1)  # no green -> max
        assert out.loc["C", "heat_score"] == pytest.approx(30, abs=0.1)  # all green -> min
        # B is 50% green, above the 0.6 saturation? 0.5/0.6 = 0.833 -> UHI 0.167 -> 40
        assert out.loc["B", "heat_score"] == pytest.approx(40, abs=0.5)

    def test_fallback_when_file_missing(self, zones):
        out = compute_heat_layer(zones, None)
        # flat UHI 0.6 -> heat = 30 + 60*0.6 = 66 everywhere
        assert out["heat_score"].tolist() == pytest.approx([66.0, 66.0, 66.0], abs=0.1)

    def test_bounds(self, zones, green):
        out = compute_heat_layer(zones, green)
        assert out["heat_score"].between(30, 90).all()
