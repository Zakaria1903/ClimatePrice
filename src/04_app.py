from pathlib import Path

import geopandas as gpd
import pydeck as pdk
import streamlit as st

# ---- Page configuration ----

st.set_page_config(
    page_title="ClimatePrice",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 ClimatePrice")
st.subheader("Where should you buy property in Paris today to be safe in 2035/2045?")

# ---- Load pipeline output ----

DATA_PATH = Path("data/climateprice_output.geojson")
if not DATA_PATH.exists():
    st.error("Pipeline output not found. Run `python src/03_pipeline.py` first.")
    st.stop()

gdf = gpd.read_file(DATA_PATH)


# ---- Scenario controls ----

st.sidebar.header("Climate scenario")
scenario = st.sidebar.selectbox(
    "Scenario",
    ["SSP2", "SSP5"],
)

horizon = st.sidebar.selectbox(
    "Horizon",
    ["2035", "2045"],
)


# ---- Select scenario-specific columns ----

verdict_col = f"verdict_{scenario}_{horizon}"
discount_col = f"discount_{scenario}_{horizon}"
future_price_col = f"price_future_{scenario}_{horizon}"

# ---- Headline counters ----

st.subheader(f"Paris outlook — {scenario} / {horizon}")
counts = gdf[verdict_col].value_counts()
buy_count = counts.get("Buy", 0)
caution_count = counts.get("Caution", 0)
avoid_count = counts.get("Avoid", 0)
col1, col2, col3 = st.columns(3)

col1.metric("🟢 Buy", buy_count)
col2.metric("🟡 Caution", caution_count)
col3.metric("🔴 Avoid", avoid_count)

# ---- Interactive map ----

st.subheader("Investment map")

# Prepare map data
map_gdf = gdf.to_crs(epsg=4326).copy()
map_gdf["selected_verdict"] = map_gdf[verdict_col]
map_gdf["selected_discount"] = (map_gdf[discount_col] * 100).round(1)
map_gdf["selected_future_price"] = (map_gdf[future_price_col]).round(0)
map_gdf["risk_score_display"] = (map_gdf["risk_score"]).round(1)

# Assign map colors to each verdict
color_map = {
    "Buy": [34, 197, 94, 180],
    "Caution": [234, 179, 8, 180],
    "Avoid": [239, 68, 68, 180],
}

map_gdf["color"] = map_gdf["selected_verdict"].map(color_map)

# Create polygon layer
layer = pdk.Layer(
    "GeoJsonLayer",
    data=map_gdf.__geo_interface__,
    pickable=True,
    stroked=True,
    filled=True,
    get_fill_color="properties.color",
    get_line_color=[255, 255, 255],
    line_width_min_pixels=1,
)

# Center map on Paris
view_state = pdk.ViewState(
    latitude=48.8566,
    longitude=2.3522,
    zoom=11,
    pitch=0,
)

# Zone information shown on hover
tooltip = {
    "html": """
        <b>Zone {zone_id}</b><br/><br/>
        Verdict: <b>{selected_verdict}</b><br/>
        Current price: €{price_m2} / m²<br/>
        Climate-adjusted price: €{selected_future_price} / m²<br/>
        Climate discount: {selected_discount}%<br/>
        Risk score: {risk_score_display} / 100<br/>
        Profile: {cluster_name}
    """,
    "style": {
        "backgroundColor": "white",
        "color": "black",
    },
}

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
)

st.pydeck_chart(
    deck,
    use_container_width=True,
)

st.caption("🟢 Buy  ·  🟡 Caution  ·  🔴 Avoid")
