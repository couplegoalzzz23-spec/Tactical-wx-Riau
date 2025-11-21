# ===============================================
# app.py — Tactical Weather Ops (Clean UI Edition)
# ===============================================

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    layout="wide",
)

# -----------------------------
# CSS CLEAN UI (Tactical Theme)
# -----------------------------
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
h1,h2,h3 {
    color: #a9df52;
    letter-spacing: 1px;
    text-transform: uppercase;
}
section[data-testid="stSidebar"] {
    background-color: #111;
    color: #d0d3ca;
    padding-top: 20px;
}
.stButton>button {
    background-color: #1a2a1f;
    color: #a9df52;
    border: 1px solid #3f4f3f;
    border-radius:8px;
    font-weight:bold;
}
.stButton>button:hover {
    background-color:#2b3b2b;
    border-color:#a9df52;
}
div[data-testid="stMetricValue"] {
    color: #a9df52 !important;
}
hr, .stDivider {
    border-top: 1px solid #2f3a2f;
}
.radar {
    position: relative; 
    width: 160px; 
    height: 160px; 
    border-radius: 50%; 
    background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), 
                radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%);
    background-size: 20px 20px;
    border: 2px solid #33ff55;
    overflow: hidden; 
    margin: auto; 
    box-shadow: 0 0 20px #33ff55;
}
.radar:before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width:50%; height:2px;
    background: linear-gradient(90deg,#33ff55,transparent);
    transform-origin: 100% 50%;
    animation: sweep 2.5s linear infinite;
}
@keyframes sweep {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Optional map modules
# -----------------------------
HAVE_FOLIUM = True
st_folium = None
try:
    import folium
    from folium import TileLayer, FeatureGroup, CircleMarker, Popup, PolyLine
    try:
        from streamlit_folium import st_folium
    except:
        st_folium = None
except:
    HAVE_FOLIUM = False


# -----------------------------
# Config
# -----------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384


# -----------------------------
# Utilities
# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def flatten(entry):
    rows = []
    loc = entry.get("lokasi", {})

    for group in entry.get("cuaca", []):
        for obs in group:
            r = dict(obs)
            r.update({
                "adm1": loc.get("adm1"),
                "adm2": loc.get("adm2"),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
                "local_dt": pd.to_datetime(obs.get("local_datetime")),
            })
            rows.append(r)

    df = pd.DataFrame(rows)
    for c in ["t", "hu", "ws", "wd_deg", "tcc", "tp", "vs"]:
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")

    df["ws_kt"] = df["ws"] * MS_TO_KT
    return df


# -------------------------------------
# Sidebar — Clean & Organized
# -------------------------------------
with st.sidebar:
    st.title("🛰️ Tactical Controls")

    adm1 = st.text_input("Province Code (ADM1)", value="32")

    # Radar scanning (requested to keep)
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning...</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.subheader("Parameters to Display")
    show_temp = st.checkbox("Temperature", True)
    show_humidity = st.checkbox("Humidity", True)
    show_wind = st.checkbox("Wind Speed", True)
    show_rain = st.checkbox("Rainfall", True)
    show_windrose = st.checkbox("Windrose", True)

    st.markdown("---")
    show_map = st.checkbox("Show Map", True)
    show_table = st.checkbox("Show Forecast Table", False)

    st.caption("BMKG API • Tactical Ops v2.0 Clean UI")


# -----------------------------
# Fetch Data
# -----------------------------
st.title("Tactical Weather Operations Dashboard")

try:
    raw = fetch_forecast(adm1)
except Exception as e:
    st.error(f"BMKG fetch error: {e}")
    st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No data available for this ADM1.")
    st.stop()

mapping = {}
for e in entries:
    name = e["lokasi"]["adm2"]
    mapping[name] = e

loc_choice = st.selectbox("🎯 Select Location", list(mapping.keys()))
entry = mapping[loc_choice]

df = flatten(entry)
df_sorted = df.sort_values("local_dt")

# Time selection
times = df_sorted["local_dt"].dropna().unique()
time_idx = st.slider("Time Index", 0, len(times)-1, len(times)-1)
current_time = times[time_idx]

nearest = df_sorted.iloc[(df_sorted["local_dt"] - current_time).abs().argsort()[:1]].iloc[0]


# -----------------------------
# Metrics
# -----------------------------
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Temp (°C)", f"{nearest.t}°C" if show_temp else "—")

with col2:
    st.metric("Humidity", f"{nearest.hu}%" if show_humidity else "—")

with col3:
    st.metric("Wind (KT)", f"{nearest.ws_kt:.1f}" if show_wind else "—")

with col4:
    st.metric("Rain (mm)", f"{nearest.tp}" if show_rain else "—")


# -----------------------------
# Charts (parameter-selection based)
# -----------------------------
st.markdown("---")
st.subheader("📊 Parameter Trends")

if show_temp:
    fig = px.line(df_sorted, x="local_dt", y="t", title="Temperature (°C)")
    st.plotly_chart(fig, use_container_width=True)

param_cols = st.columns(3)

with param_cols[0]:
    if show_humidity:
        fig = px.line(df_sorted, x="local_dt", y="hu", title="Humidity (%)")
        st.plotly_chart(fig, use_container_width=True)

with param_cols[1]:
    if show_wind:
        fig = px.line(df_sorted, x="local_dt", y="ws_kt", title="Wind Speed (KT)")
        st.plotly_chart(fig, use_container_width=True)

with param_cols[2]:
    if show_rain:
        fig = px.bar(df_sorted, x="local_dt", y="tp", title="Rainfall (mm)")
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Windrose (unchanged style)
# -----------------------------
if show_windrose:
    st.markdown("---")
    st.subheader("🌪️ Windrose — Direction & Speed")

    df_wr = df_sorted.dropna(subset=["wd_deg", "ws_kt"])
    if len(df_wr) > 0:
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]

        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels)
        speed_bins = [0,5,10,20,30,50,999]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels)

        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"] / freq["count"].sum() * 100

        az_map = {l:i*22.5 for i,l in enumerate(labels)}
        freq["theta"] = freq["dir_sector"].map(az_map)

        colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]

        fig = go.Figure()
        for i, sp in enumerate(speed_labels):
            sub = freq[freq["speed_class"] == sp]
            fig.add_trace(go.Barpolar(
                r=sub["percent"],
                theta=sub["theta"],
                name=sp,
                marker_color=colors[i],
                opacity=0.85,
            ))
        fig.update_layout(template="plotly_dark", title="Windrose (KT)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Windrose data unavailable.")


# -----------------------------
# Map (clean)
# -----------------------------
if show_map:
    st.markdown("---")
    st.subheader("🗺️ Tactical Map")

    lat = float(entry["lokasi"]["lat"])
    lon = float(entry["lokasi"]["lon"])

    if HAVE_FOLIUM and st_folium:
        try:
            m = folium.Map(location=[lat, lon], zoom_start=7, tiles="OpenStreetMap")

            CircleMarker([lat, lon], radius=8, color="#00ffbf", fill=True).add_to(m)

            st_folium(m, width=1000, height=550)
        except Exception as e:
            st.warning(f"Map error: {e}")
            st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))
    else:
        st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))


# -----------------------------
# Table
# -----------------------------
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table")
    st.dataframe(df_sorted)


# -----------------------------
# Export
# -----------------------------
st.markdown("---")
st.subheader("💾 Export Data")

csv = df_sorted.to_csv(index=False)
json_data = df_sorted.to_json(orient="records", date_format="iso")

colA, colB = st.columns(2)
with colA:
    st.download_button("Download CSV", csv, file_name=f"{adm1}_{loc_choice}.csv")
with colB:
    st.download_button("Download JSON", json_data, file_name=f"{adm1}_{loc_choice}.json")

st.caption("Tactical Ops Dashboard — Clean UI Version © BMKG 2025")
