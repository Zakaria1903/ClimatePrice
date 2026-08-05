"""03_pipeline.py — pipeline: XGBoost risk + K-Means profiles + climate discount + verdict."""

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

df = gpd.read_file("data/joined.geojson")

# ---- Risk score (XGBoost) ----
df["risk"] = 0.6 * df["flood_score"] + 0.4 * df["heat_score"]
features = ["flood_score", "heat_score", "elevation", "dist_seine"]
X_train, X_test, y_train, y_test = train_test_split(
    df[features], df["risk"], test_size=0.2, random_state=0
)
risk_model = XGBRegressor(n_estimators=200, max_depth=4, verbosity=0).fit(X_train, y_train)
print(f"risk model R2 (test): {r2_score(y_test, risk_model.predict(X_test)):.3f}")
df["risk_score"] = np.clip(risk_model.predict(df[features]), 0, 100)

# ---- Neighborhood profiles (K-Means) ----
profile_features = ["flood_score", "heat_score", "price_m2", "elevation", "dist_seine"]
scaled = StandardScaler().fit_transform(df[profile_features])
df["cluster"] = KMeans(n_clusters=4, n_init=10, random_state=0).fit_predict(scaled)

city_avg = df[profile_features].mean()
cluster_names = {}
for cluster_id in range(4):
    avg = df.loc[df["cluster"] == cluster_id, profile_features].mean()
    tags = []
    if avg["flood_score"] > city_avg["flood_score"] * 1.2:
        tags.append("flood-exposed")
    if avg["heat_score"] > city_avg["heat_score"] * 1.05:
        tags.append("heat-exposed")
    tags.append("expensive" if avg["price_m2"] > city_avg["price_m2"] else "affordable")

    name = ", ".join(tags)
    while name in cluster_names.values():  # keep labels unique for the map legend
        name += " +"
    cluster_names[cluster_id] = name
df["cluster_name"] = df["cluster"].map(cluster_names)

# ---- Climate discount + verdict, per scenario x horizon ----
SCENARIOS = {"SSP2": 0.55, "SSP5": 1.00}
HORIZONS = {"2035": 0.60, "2045": 1.00}
for scenario, s_weight in SCENARIOS.items():
    for horizon, h_weight in HORIZONS.items():
        discount = (df["risk_score"] / 100) * 0.15 * s_weight * h_weight
        df[f"discount_{scenario}_{horizon}"] = discount
        df[f"price_future_{scenario}_{horizon}"] = df["price_m2"] * (1 - discount)
        df[f"verdict_{scenario}_{horizon}"] = pd.cut(
            discount,
            bins=[-1, 0.04, 0.08, 2],
            labels=["Buy", "Caution", "Avoid"],
            right=False,
        ).astype(str)

df.to_file("data/climateprice_output.geojson", driver="GeoJSON")
for scenario in SCENARIOS:
    for horizon in HORIZONS:
        counts = df[f"verdict_{scenario}_{horizon}"].value_counts().to_dict()
        print(f"{scenario}/{horizon}: {counts}")
print("output -> data/climateprice_output.geojson")
