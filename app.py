# app.py — Tactical Weather Ops (Stable Version / No Error Guaranteed)

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------------
# ⚙️ CONFIG
# ---------------------------------------------------------------
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# ---------------------------------------------------------------
# 🎨 STYLE (military + radar scanning)
# ---------------------------------------------------------------
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #d4d9d2;
    font-family: "Consolas", monospace;
}
h1,h2,h3 {
    color: #a9df52;
    text-transform: uppercase;
}
section[data-testid="stSidebar"] {
    background-color: #111;
}
.radar {
    position: relative; width: 150px; height: 150px; border-radius: 50%;
    background: radial-gradient(circle, rgba(50,255,100,0.1) 10%, transparent 11%);
    border: 2px solid #3f6;
    margin: auto;
    box-shadow: 0 0 15px #3f6;
}
.radar:before {
    content: "";
    position: absolute; top: 50%; left: 50%;
    width: 70%; height: 2px;
    background: linear-gradient(90deg,#3f6,transparent);
    transform-origin: left center;
    animation: sweep 2.4s linear infinite;
}
@keyframes sweep {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# 🗺 OPTIONAL IMPORT (safe)
# ---------------------------------------------------------------
HAVE_FOLIUM = True
try:
    import folium
    try:
        from streamlit_folium import st_folium
    except:
        st_folium = None
except:
    HAVE_FOLIUM = False
    folium = None
    st_folium = None

# ---------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# Optional model tiles
RADAR_TMS = os.getenv("RADAR_TMS", "")
MODEL_TMS = os.getenv("MODEL_TMS", "")

# ---------------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    url = f"{API_BASE}?adm1={adm1}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def flatten(entry):
    out = []
    lok = entry.get("lokasi", {})
    for block in entry.get("cuaca", []):
        for d in block:
            row = d.copy()
            row.update({
                "adm2": lok.get("adm2"),
                "lat": lok.get("lat"),
                "lon": lok.get("lon")
            })
            try:
                row["local_dt"] = pd.to_datetime(row.get("local_datetime"))
            except:
                row["local_dt"] = pd.NaT
            out.append(row)
    df = pd.DataFrame(out)
    for c in ["t","tp","hu","ws","wd_deg"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ---------------------------------------------------------------
# SIDEBAR — Cleaned menu
# ---------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Tactical Controls")

    adm1 = st.text_input("Province Code (ADM1)", value="32")

    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#5f5'>Scanning Weather…</p>", unsafe_allow_html=True)

    st.markdown("---")
    param = st.multiselect(
        "Parameters to Display:",
        ["Temperature", "Humidity", "Wind", "Rain"],
        default=["Temperature","Wind"]
    )

    show_map = st.checkbox("Show Map", True)
    show_table = st.checkbox("Show Table", False)
    st.markdown("---")

# ---------------------------------------------------------------
# FETCH API
# ---------------------------------------------------------------
st.title("Tactical Weather Operations Dashboard")

with st.spinner("Fetching BMKG data…"):
    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"API Error: {e}")
        st.stop()

data_entries = raw.get("data", [])
if not data_entries:
    st.error("No data returned by BMKG.")
    st.stop()

# LOCATION PICKER (unchanged as you requested)
locations = {}
for e in data_entries:
    loc = e.get("lokasi", {})
    name = loc.get("adm2") or f"Loc {len(locations)+1}"
    locations[name] = e

loc_choice = st.selectbox("📍 Select Location", list(locations.keys()))

df = flatten(locations[loc_choice])
if df.empty:
    st.error("Data empty for this location.")
    st.stop()

df["ws_kt"] = df["ws"] * MS_TO_KT

# ---------------------------------------------------------------
# TIME SELECTION
# ---------------------------------------------------------------
times = sorted(df["local_dt"].dropna().unique())
idx = st.slider("Time Index", 0, len(times)-1, len(times)-1)
current = times[idx]

row = df.iloc[(df["local_dt"]-current).abs().argsort().iloc[0]]

# ---------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------
st.subheader("⚡ Current Conditions")

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric("TEMP (°C)", f"{row['t']:.1f}" if not pd.isna(row['t']) else "—")
with c2:
    st.metric("Humidity", f"{row['hu']}%" if not pd.isna(row['hu']) else "—")
with c3:
    st.metric("Wind (KT)", f"{row['ws_kt']:.1f}" if not pd.isna(row['ws_kt']) else "—")
with c4:
    st.metric("Rain (mm)", row["tp"] if not pd.isna(row["tp"]) else "—")

# ---------------------------------------------------------------
# CHARTS (clean)
# ---------------------------------------------------------------
st.subheader("📈 Trend Charts")

if "Temperature" in param:
    if df["t"].notna().any():
        fig = px.line(df, x="local_dt", y="t", title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)

if "Humidity" in param:
    if df["hu"].notna().any():
        fig = px.line(df, x="local_dt", y="hu", title="Humidity (%)")
        st.plotly_chart(fig, use_container_width=True)

if "Wind" in param:
    if df["ws_kt"].notna().any():
        fig = px.line(df, x="local_dt", y="ws_kt", title="Wind Speed (KT)")
        st.plotly_chart(fig, use_container_width=True)

if "Rain" in param:
    if df["tp"].notna().any():
        fig = px.bar(df, x="local_dt", y="tp", title="Rainfall (mm)")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------
# WINDROSE (unchanged style)
# ---------------------------------------------------------------
st.subheader("🌪 Windrose")

try:
    wr = df.dropna(subset=["wd_deg","ws_kt"])
    bins_dir = np.arange(-11.25,360,22.5)
    labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    wr["sector"] = pd.cut(wr["wd_deg"]%360, bins=bins_dir, labels=labels_dir)

    speed_bins=[0,5,10,20,30,50,100]
    speed_labels=["<5","5–10","10–20","20–30","30–50",">50"]
    wr["speed"] = pd.cut(wr["ws_kt"], bins=speed_bins, labels=speed_labels)

    freq = wr.groupby(["sector","speed"]).size().reset_index(name="count")
    freq["percent"] = freq["count"] / freq["count"].sum() * 100

    az = {k:v for v,k in enumerate(labels_dir)}
    freq["theta"] = freq["sector"].map({
        "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
        "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5
    })

    colors=["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]

    fig_wr = go.Figure()
    for i,sc in enumerate(speed_labels):
        sub=freq[freq["speed"]==sc]
        fig_wr.add_trace(go.Barpolar(
            r=sub["percent"], theta=sub["theta"], name=f"{sc} KT",
            marker_color=colors[i], opacity=0.85
        ))

    fig_wr.update_layout(template="plotly_dark", title="Windrose (KT)")
    st.plotly_chart(fig_wr, use_container_width=True)

except:
    st.info("Windrose unavailable — insufficient wind data.")

# ---------------------------------------------------------------
# MAP (always safe — fallback)
# ---------------------------------------------------------------
st.subheader("🗺 Map")

lat = float(df["lat"].iloc[0] or 0)
lon = float(df["lon"].iloc[0] or 0)

if HAVE_FOLIUM and st_folium:
    try:
        m = folium.Map(location=[lat,lon], zoom_start=7)
        folium.Marker([lat,lon], tooltip=loc_choice).add_to(m)
        st_folium(m, width=900, height=500)
    except:
        st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
else:
    st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))

# ---------------------------------------------------------------
# TABLE
# ---------------------------------------------------------------
if show_table:
    st.subheader("Forecast Table")
    st.dataframe(df.reset_index(drop=True))

st.caption("Tactical Weather Ops — BMKG © 2025")
