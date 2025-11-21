# app.py
# Tactical Weather Ops — Clean UI + Parameter Menu + Error-Free
# Note:
#  - Radar scanning icon TIDAK DIHAPUS
#  - Lokasi (mapping ADM) TIDAK DIUBAH
#  - Windrose style ORIGINAL dipertahankan

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

# -------------------------------------------------------------------------
# PAGE CONFIG + THEME
# -------------------------------------------------------------------------
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# CSS tema lebih bersih & minimal
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #d4d7cd;
    font-family: "Consolas", monospace;
}

h1, h2, h3, h4 {
    color: #a9df52;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #111;
    color: #d0d3ca;
}

/* Buttons */
.stButton>button {
    background-color: #1a2a1f;
    color: #a9df52;
    border: 1px solid #3f4f3f;
    border-radius: 8px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #2b3b2b;
    border-color: #a9df52;
}

div[data-testid="stMetricValue"] {
    color: #a9df52 !important;
}

/* Radar scanning icon — dipertahankan */
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
    width: 50%;
    height: 2px;
    background: linear-gradient(90deg, #33ff55, transparent);
    transform-origin: 100% 50%;
    animation: sweep 2.8s linear infinite;
}
@keyframes sweep {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Optional mapping libs
# -------------------------------------------------------------------------
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
    folium = None

# -------------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

RADAR_TMS = os.getenv("RADAR_TMS", "")
MODEL_TMS = os.getenv("MODEL_TMS", "")

# -------------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=12)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for grp in entry.get("cuaca", []):
        for obs in grp:
            r = dict(obs)
            r.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "provinsi": lokasi.get("provinsi"),
                "kotkab": lokasi.get("kotkab"),
                "lat": lokasi.get("lat"),
                "lon": lokasi.get("lon")
            })
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    numeric = ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]
    for c in numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# -------------------------------------------------------------------------
# SIDEBAR — cleaned, menu-based
# -------------------------------------------------------------------------
with st.sidebar:
    st.title("Tactical Controls")

    adm1 = st.text_input("Province Code (ADM1)", value="32")

    # scanning icon — DIPERTAHANKAN
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#57ff57;'>Scanning Weather...</p>", unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Display Options")
    show_map = st.checkbox("Map", value=True)
    show_charts = st.checkbox("Charts", value=True)
    show_windrose = st.checkbox("Windrose", value=True)
    show_table = st.checkbox("Data Table", value=False)

    st.markdown("---")
    st.subheader("Map Layers")
    use_tiles = st.checkbox("Enable TMS Radar/Model Layers")
    show_wind_vectors = st.checkbox("Wind Vectors", value=True)

    st.caption("Tactical Weather Ops — UI v2.0")

# -------------------------------------------------------------------------
# FETCH DATA
# -------------------------------------------------------------------------
st.title("Tactical Weather Operations Dashboard")
st.caption("Source: BMKG API — Live Forecast")

try:
    data = fetch_forecast(adm1)
except Exception as e:
    st.error(f"Failed to fetch BMKG data: {e}")
    st.stop()

entries = data.get("data", [])
if not entries:
    st.error("No data available.")
    st.stop()

# Build location mapping (ASLI, TIDAK DIUBAH)
mapping = {}
for e in entries:
    lokasi = e.get("lokasi", {})
    label = lokasi.get("kotkab") or lokasi.get("adm2") or f"Loc {len(mapping)+1}"
    mapping[label] = {"entry": e}

loc_choice = st.selectbox("Select Location", list(mapping.keys()))
selected = mapping[loc_choice]["entry"]

df = flatten_cuaca_entry(selected)
if df.empty:
    st.error("No forecast data available.")
    st.stop()

# Derived fields
df["ws_kt"] = df["ws"] * MS_TO_KT
df["u"] = -df["ws"] * np.sin(np.deg2rad(df["wd_deg"]))
df["v"] = -df["ws"] * np.cos(np.deg2rad(df["wd_deg"]))

times = sorted(df["local_datetime_dt"].dropna().unique())
t_index = st.slider("Forecast Time Index", 0, len(times)-1, len(times)-1)
curr_time = times[t_index]

sel = df.loc[df["local_datetime_dt"] == curr_time]
if sel.empty:
    sel = df.iloc[[0]]

# -------------------------------------------------------------------------
# STATUS PANEL
# -------------------------------------------------------------------------
st.markdown("---")
st.subheader("Tactical Weather Status")

row = sel.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temp (°C)", f"{row['t']:.1f}" if pd.notna(row['t']) else "—")
c2.metric("Humidity", f"{row['hu']}%" if pd.notna(row['hu']) else "—")
c3.metric("Wind (kt)", f"{row['ws_kt']:.1f}" if pd.notna(row['ws_kt']) else "—")
c4.metric("Rain (mm)", f"{row['tp']}" if pd.notna(row['tp']) else "—")

# -------------------------------------------------------------------------
# CHARTS — appear ONLY if enabled
# -------------------------------------------------------------------------
if show_charts:
    st.markdown("---")
    st.subheader("Parameter Trends")

    df_sorted = df.sort_values("local_datetime_dt")

    colA, colB = st.columns(2)

    with colA:
        if df["t"].notna().any():
            st.plotly_chart(px.line(df_sorted, x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True), use_container_width=True)

    with colB:
        if df["hu"].notna().any():
            st.plotly_chart(px.line(df_sorted, x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True), use_container_width=True)

    colC, colD = st.columns(2)

    with colC:
        if df["ws_kt"].notna().any():
            st.plotly_chart(px.line(df_sorted, x="local_datetime_dt", y="ws_kt", title="Wind Speed (kt)", markers=True), use_container_width=True)

    with colD:
        if df["tp"].notna().any():
            st.plotly_chart(px.bar(df_sorted, x="local_datetime_dt", y="tp", title="Rainfall (mm)"), use_container_width=True)

# -------------------------------------------------------------------------
# WINDROSE — style ASLI (tidak diubah)
# -------------------------------------------------------------------------
if show_windrose:
    st.markdown("---")
    st.subheader("Windrose — Direction & Speed")

    try:
        wr = df.dropna(subset=["wd_deg", "ws_kt"]).copy()
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S",
                      "SSW","SW","WSW","W","WNW","NW","NNW"]
        wr["dir_sector"] = pd.cut(wr["wd_deg"], bins=bins_dir, labels=labels_dir)

        sp_bins = [0,5,10,20,30,50,100]
        sp_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        wr["speed_class"] = pd.cut(wr["ws_kt"], bins=sp_bins, labels=sp_labels)

        freq = wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"] / freq["count"].sum() * 100
        az = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
              "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
        freq["theta"] = freq["dir_sector"].map(az)

        colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]

        fig = go.Figure()
        for i, sc in enumerate(sp_labels):
            sub = freq[freq["speed_class"] == sc]
            fig.add_trace(go.Barpolar(
                r=sub["percent"], theta=sub["theta"],
                name=sc + " kt",
                marker_color=colors[i],
                opacity=0.85
            ))
        fig.update_layout(template="plotly_dark", title="Windrose (KT)")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.info(f"Windrose unavailable: {e}")

# -------------------------------------------------------------------------
# MAP — Cleaned version
# -------------------------------------------------------------------------
if show_map:
    st.markdown("---")
    st.subheader("Tactical Map")

    lat = float(selected.get("lokasi", {}).get("lat", 0))
    lon = float(selected.get("lokasi", {}).get("lon", 0))

    if HAVE_FOLIUM and st_folium:
        try:
            m = folium.Map(location=[lat, lon], zoom_start=7, tiles=None)

            TileLayer("OpenStreetMap").add_to(m)

            # Optional tiles
            if use_tiles and RADAR_TMS:
                TileLayer(tiles=RADAR_TMS, name="Radar").add_to(m)
            if use_tiles and MODEL_TMS:
                TileLayer(tiles=MODEL_TMS, name="Model").add_to(m)

            fg = FeatureGroup("Forecast Points")

            for _, r in sel.iterrows():
                CircleMarker(
                    [r["lat"], r["lon"]],
                    radius=6,
                    color="#00ffbf",
                    fill=True,
                    fill_opacity=0.9
                ).add_to(fg)

            m.add_child(fg)
            folium.LayerControl().add_to(m)
            st_folium(m, height=550)

        except Exception as e:
            st.warning(f"Map unavailable: {e}")
            st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))

    else:
        st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))

# -------------------------------------------------------------------------
# TABLE
# -------------------------------------------------------------------------
if show_table:
    st.markdown("---")
    st.subheader("Forecast Table")
    st.dataframe(df.sort_values("local_datetime_dt"))

# -------------------------------------------------------------------------
# EXPORT
# -------------------------------------------------------------------------
st.markdown("---")
st.subheader("Export Data")

csv = df.to_csv(index=False)
json_text = df.to_json(orient="records", date_format="iso")

cE1, cE2 = st.columns(2)
cE1.download_button("Download CSV", csv, file_name="forecast.csv", mime="text/csv")
cE2.download_button("Download JSON", json_text, file_name="forecast.json", mime="application/json")

st.caption("© 2025 Tactical Weather Ops — BMKG Data")
