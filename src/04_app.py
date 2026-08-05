from pathlib import Path

import geopandas as gpd
import pydeck as pdk
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="ClimatePrice",
    page_icon="🏠",
    layout="wide",
)
st.title("🏠 ClimatePrice")
st.subheader("Where should you buy property in Paris today to be safe in 2035/2045?")

st.caption(
    "Each Paris IRIS neighborhood gets a verdict Buy / Caution / Avoid based on "
    "flood and heat exposure. Pick a climate scenario and horizon in the sidebar; "
    "hover any zone for details."
)

# Load pipeline output
DATA_PATH = Path("data/climateprice_output.geojson")
if not DATA_PATH.exists():
    st.error("Pipeline output not found. Run `python src/03_pipeline.py` first.")
    st.stop()
gdf = gpd.read_file(DATA_PATH)

# Scenario controls
st.sidebar.header("Climate scenario")
scenario_label = st.sidebar.selectbox(
    "Scenario",
    ["SSP2-4.5 (moderate)", "SSP5-8.5 (worst case)"],
)
scenario = "SSP2" if "SSP2" in scenario_label else "SSP5"
horizon = st.sidebar.selectbox(
    "Horizon",
    ["2035", "2045"],
)

verdict_col = f"verdict_{scenario}_{horizon}"
discount_col = f"discount_{scenario}_{horizon}"
future_price_col = f"price_future_{scenario}_{horizon}"

# Headline counters
st.subheader(f"Paris outlook {scenario_label} / {horizon}")
counts = gdf[verdict_col].value_counts()
col1, col2, col3 = st.columns(3)
col1.metric("🟢 Buy", counts.get("Buy", 0))
col2.metric("🟡 Caution", counts.get("Caution", 0))
col3.metric("🔴 Avoid", counts.get("Avoid", 0))

# Interactive map
st.subheader("Investment map")
map_gdf = gdf.to_crs(epsg=4326).copy()
map_gdf["selected_verdict"] = map_gdf[verdict_col]
map_gdf["selected_discount"] = (map_gdf[discount_col] * 100).round(1)
map_gdf["selected_future_price"] = map_gdf[future_price_col].round(0).astype(int)
map_gdf["price_display"] = map_gdf["price_m2"].round(0).astype(int)
map_gdf["risk_score_display"] = map_gdf["risk_score"].round(1)
map_gdf["arrondissement"] = (
    map_gdf["zone_id"].astype(str).str[3:5].astype(int).astype(str) + "e arr."
)

color_map = {
    "Buy": [34, 197, 94, 180],
    "Caution": [234, 179, 8, 180],
    "Avoid": [239, 68, 68, 180],
}
map_gdf["color"] = map_gdf["selected_verdict"].map(color_map)

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

view_state = pdk.ViewState(latitude=48.8566, longitude=2.3522, zoom=11, pitch=0)

tooltip = {
    "html": """
        <b>Zone {zone_id} — {arrondissement}</b><br/><br/>
        Verdict: <b>{selected_verdict}</b><br/>
        Current price: €{price_display} / m²<br/>
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

deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
st.pydeck_chart(deck, use_container_width=True)
st.caption("🟢 Buy  ·  🟡 Caution  ·  🔴 Avoid")
