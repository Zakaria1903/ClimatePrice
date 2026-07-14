"""03_pipeline.py — minimal pipeline: XGBoost risk + K-Means + discount + verdict."""

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

df = gpd.read_file("data/synthetic.geojson")

# ---- Model 1: XGBoost risk scorer ----
df["risk"] = 0.6 * df["flood_score"] + 0.4 * df["heat_score"]
X = df[["flood_score", "heat_score", "elevation", "dist_seine"]]
y = df["risk"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=0)
m1 = XGBRegressor(n_estimators=200, max_depth=4, verbosity=0).fit(Xtr, ytr)
print(f"risk model R2 (test): {r2_score(yte, m1.predict(Xte)):.3f}")
df["risk_score"] = np.clip(m1.predict(X), 0, 100)

# ---- Model 2: K-Means profiles ----
feats = df[["flood_score", "heat_score", "price_m2", "elevation", "dist_seine"]]
km = KMeans(n_clusters=4, n_init=10, random_state=0)
df["cluster"] = km.fit_predict(StandardScaler().fit_transform(feats))
city = feats.mean()
names = {}
for c in range(4):
    avg = feats[df["cluster"] == c].mean()
    tags = []
    if avg["flood_score"] > city["flood_score"] * 1.2:
        tags.append("flood-exposed")
    if avg["heat_score"] > city["heat_score"] * 1.05:
        tags.append("heat-exposed")
    tags.append("expensive" if avg["price_m2"] > city["price_m2"] else "affordable")
    name = ", ".join(tags)
    while name in names.values():  # guarantee unique labels on the map legend
        name += " +"
    names[c] = name
df["cluster_name"] = df["cluster"].map(names)

# ---- Baseline price (flood deliberately excluded) ----
mb = XGBRegressor(n_estimators=200, max_depth=4, verbosity=0)
mb.fit(df[["elevation", "dist_seine", "heat_score"]], df["price_m2"])
df["price_baseline"] = mb.predict(df[["elevation", "dist_seine", "heat_score"]])

# ---- Discount + verdict for the 4 combos ----
S = {"SSP2": 0.55, "SSP5": 1.00}
H = {"2035": 0.60, "2045": 1.00}
for s, sv in S.items():
    for h, hv in H.items():
        d = (df["risk_score"] / 100) * 0.15 * sv * hv
        df[f"discount_{s}_{h}"] = d
        df[f"price_future_{s}_{h}"] = df["price_baseline"] * (1 - d)
        df[f"verdict_{s}_{h}"] = pd.cut(
            d, bins=[-1, 0.04, 0.08, 2], labels=["Buy", "Caution", "Avoid"], right=False
        ).astype(str)

df.to_file("data/climateprice_output.geojson", driver="GeoJSON")
for s in S:
    for h in H:
        vc = df[f"verdict_{s}_{h}"].value_counts().to_dict()
        print(f"{s}/{h}: {vc}")
print("output -> data/climateprice_output.geojson")
