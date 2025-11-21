# app.py
# Tactical Weather Ops — Robust Streamlit dashboard (Ventusky-like inspiration)
# Usage:
#   pip install streamlit requests pandas numpy plotly
# Optional for interactive map:
#   pip install folium streamlit_folium branca
# Run:
#   streamlit run app.py

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------
# CSS: Military theme + radar
# -----------------------------
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")
st.markdown(
    """
<style>
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
h1,h2,h3,h4 { color: #a9df52; text-transform: uppercase; letter-spacing: 1px; }
section[data-testid="stSidebar"] { background-color: #111; color: #d0d3ca; }
.stButton>button { background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius:8px; font-weight:bold; }
.stButton>button:hover { background-color:#2b3b2b; border-color:#a9df52; }
div[data-testid="stMetricValue"] { color: #a9df52 !important; }
.radar { position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width:50%; height:2px; background: linear-gradient(90deg,#33ff55,transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
hr, .stDivider { border-top: 1px solid #2f3a2f; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Optional mapping libs (safe import)
# -----------------------------
HAVE_FOLIUM = True
st_folium = None
try:
    import folium
    from folium import TileLayer, FeatureGroup, CircleMarker, Popup, PolyLine
    try:
        from streamlit_folium import st_folium  # may not be installed
    except Exception:
        st_folium = None
except Exception:
    HAVE_FOLIUM = False
    folium = None
    TileLayer = FeatureGroup = CircleMarker = Popup = PolyLine = None
    st_folium = None

# -----------------------------
# Config & placeholders
# -----------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# If you have TMS/WMS tile URLs for model/radar overlays, set env vars or hardcode here:
RADAR_TMS = os.getenv("RADAR_TMS", "").strip()   # e.g. "https://tileserver/.../{z}/{x}/{y}.png"
MODEL_TMS = os.getenv("MODEL_TMS", "").strip()   # e.g. model wind tiles
# Mapbox token (optional, not required)
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "").strip()

# -----------------------------
# Utilities
# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {}) if isinstance(entry, dict) else {}
    for group in entry.get("cuaca", []) or []:
        for obs in group or []:
            r = dict(obs) if isinstance(obs, dict) else {}
            r.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "provinsi": lokasi.get("provinsi"),
                "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"),
                "lat": lokasi.get("lat"),
            })
            try:
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime")) if r.get("utc_datetime") else pd.NaT
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime")) if r.get("local_datetime") else pd.NaT
            except Exception:
                r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def nearest_row(df, dt_col, target_dt):
    if df.empty:
        return df
    diffs = (pd.to_datetime(df[dt_col]) - pd.to_datetime(target_dt)).abs()
    idx = diffs.idxmin()
    return df.loc[[idx]]

# -----------------------------
# Sidebar (controls)
# -----------------------------
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table", value=False)
    use_tiles = st.checkbox("Enable model/radar tiles (TMS) if configured", value=False)
    show_wind_vectors = st.checkbox("Show Wind Vectors on Map", value=True)
    st.markdown("---")
    st.caption("Data Source: BMKG API — Theme: Tactical Ops v1.0")

# -----------------------------
# Fetch data
# -----------------------------
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Source: BMKG Forecast API — Live Data*")

with st.spinner("🛰️ Acquiring weather intelligence..."):
    try:
        raw = fetch_forecast(adm1)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch data from BMKG: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error fetching data: {e}")
        st.stop()

entries = raw.get("data", []) if isinstance(raw, dict) else []
if not entries:
    st.warning("No forecast data available for the chosen ADM1.")
    st.stop()

mapping = {}
for e in entries:
    lok = e.get("lokasi", {}) if isinstance(e, dict) else {}
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping) + 1}"
    mapping[label] = {"entry": e}

col1, col2 = st.columns([2, 1])
with col1:
    loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
with col2:
    st.metric("📍 Locations", len(mapping))

selected_entry = mapping.get(loc_choice, {}).get("entry")
if not selected_entry:
    st.error("Selected location data missing.")
    st.stop()

df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.warning("No valid weather data found for the selected location.")
    st.stop()

# Derived columns
df["ws_kt"] = df.get("ws", pd.Series(dtype=float)) * MS_TO_KT
wd_series = df.get("wd_deg", pd.Series(dtype=float)).fillna(0)
ws_series = df.get("ws", pd.Series(dtype=float)).fillna(0)
df["u"] = -ws_series * np.sin(np.deg2rad(wd_series))
df["v"] = -ws_series * np.cos(np.deg2rad(wd_series))

# Ensure datetimes available
if df["local_datetime_dt"].isna().all():
    st.error("No valid datetime available in dataset.")
    st.stop()

# Timeline controls (use index-based slider to avoid datetime slider issues)
times = pd.to_datetime(df["local_datetime_dt"]).sort_values().unique()
times = [pd.to_datetime(t) for t in times]
if len(times) == 0:
    st.error("No timestamps available.")
    st.stop()

time_index = st.slider("Time index (move to change time slice)", 0, max(0, len(times) - 1), value=len(times) - 1)
current_time = times[time_index]

# Select a time window (tolerance)
tolerance = pd.Timedelta(hours=3)
mask = (df["local_datetime_dt"] >= current_time - tolerance) & (df["local_datetime_dt"] <= current_time + tolerance)
df_sel = df.loc[mask].copy()
if df_sel.empty:
    df_sel = nearest_row(df, "local_datetime_dt", current_time)

# -----------------------------
# Metric panel
# -----------------------------
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")
now = df_sel.iloc[0] if not df_sel.empty else df.iloc[0]
c1, c2, c3, c4 = st.columns(4)
with c1:
    tval = now.get("t", "—")
    st.metric("TEMP (°C)", f"{tval}°C" if pd.notna(tval) else "—")
with c2:
    huval = now.get("hu", "—")
    st.metric("HUMIDITY", f"{huval}%" if pd.notna(huval) else "—")
with c3:
    wsval = now.get("ws_kt", np.nan)
    try:
        st.metric("WIND (KT)", f"{wsval:.1f}")
    except Exception:
        st.metric("WIND (KT)", "—")
with c4:
    tpval = now.get("tp", "—")
    st.metric("RAIN (mm)", f"{tpval}" if pd.notna(tpval) else "—")

# -----------------------------
# Parameter charts
# -----------------------------
st.markdown("---")
st.subheader("📊 Parameter Trends")
df_sorted = df.sort_values("local_datetime_dt")

# Temperature
if "t" in df.columns and df["t"].notna().any():
    try:
        fig = px.line(df_sorted, x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Temperature chart unavailable.")
else:
    st.info("Temperature data not available.")

# Humidity, Wind, Rain (compact)
cols = st.columns(3)
with cols[0]:
    if "hu" in df.columns and df["hu"].notna().any():
        try:
            fig = px.line(df_sorted, x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Humidity chart unavailable.")
    else:
        st.info("Humidity data not available.")
with cols[1]:
    if "ws_kt" in df.columns and df["ws_kt"].notna().any():
        try:
            fig = px.line(df_sorted, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Wind chart unavailable.")
    else:
        st.info("Wind data not available.")
with cols[2]:
    if "tp" in df.columns and df["tp"].notna().any():
        try:
            fig = px.bar(df_sorted, x="local_datetime_dt", y="tp", title="Rainfall (mm)")
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Rain chart unavailable.")
    else:
        st.info("Rainfall data not available.")

# -----------------------------
# Windrose
# -----------------------------
st.markdown("---")
st.subheader("🌪️ Windrose — Direction & Speed")
if {"wd_deg", "ws_kt"}.issubset(df.columns) and df[["wd_deg", "ws_kt"]].dropna().shape[0] > 0:
    try:
        df_wr = df.dropna(subset=["wd_deg", "ws_kt"]).copy()
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        if freq["count"].sum() > 0:
            freq["percent"] = freq["count"]/freq["count"].sum()*100
            az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
                      "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
            freq["theta"] = freq["dir_sector"].map(az_map)
            colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
            fig_wr = go.Figure()
            for i, sc in enumerate(speed_labels):
                subset = freq[freq["speed_class"] == sc]
                fig_wr.add_trace(go.Barpolar(
                    r=subset["percent"], theta=subset["theta"], name=f"{sc} KT",
                    marker_color=colors[i] if i < len(colors) else None, opacity=0.85
                ))
            fig_wr.update_layout(template="plotly_dark", title="Windrose (KT)")
            st.plotly_chart(fig_wr, use_container_width=True)
        else:
            st.info("Not enough wind records for windrose.")
    except Exception as e:
        st.info(f"Windrose generation failed: {e}")
else:
    st.info("Wind direction/speed data not present.")

# -----------------------------
# Map: Folium interactive (fallback to st.map)
# -----------------------------
st.markdown("---")
if show_map:
    st.subheader("🗺️ Tactical Map")
    lat = 0.0
    lon = 0.0
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", 0) or 0)
        lon = float(selected_entry.get("lokasi", {}).get("lon", 0) or 0)
    except Exception:
        lat, lon = 0.0, 0.0

    if HAVE_FOLIUM and st_folium is not None:
        try:
            m = folium.Map(location=[lat, lon], zoom_start=7, tiles=None)
            TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
            TileLayer("Stamen Terrain", name="Terrain").add_to(m)
            TileLayer("CartoDB Positron", name="Positron").add_to(m)
            if use_tiles and RADAR_TMS:
                TileLayer(tiles=RADAR_TMS, name="Radar Tiles", overlay=True, control=True).add_to(m)
            if use_tiles and MODEL_TMS:
                TileLayer(tiles=MODEL_TMS, name="Model Tiles", overlay=True, control=True).add_to(m)
            # add observation markers
            if not df_sel.empty:
                fg = FeatureGroup(name="Observations", show=True)
                for _, row in df_sel.iterrows():
                    try:
                        rlat = float(row.get("lat", lat) or lat)
                        rlon = float(row.get("lon", lon) or lon)
                    except Exception:
                        rlat, rlon = lat, lon
                    popup_html = f"<b>{row.get('adm2','Station')}</b><br>Time: {row.get('local_datetime')}<br>Temp: {row.get('t','—')} °C<br>RH: {row.get('hu','—')}%<br>Wind: {row.get('ws_kt',0):.1f} KT @ {row.get('wd_deg','—')}°<br>Rain: {row.get('tp','—')} mm"
                    Popup(popup_html, max_width=300).add_to(fg)
                    CircleMarker(location=[rlat, rlon], radius=6, color="#00ffbf", fill=True, fill_opacity=0.9).add_to(fg)
                m.add_child(fg)
            # wind vectors
            if show_wind_vectors and not df_sel.dropna(subset=["ws","wd_deg"]).empty:
                fg2 = FeatureGroup(name="Wind Vectors", show=True)
                for _, row in df_sel.dropna(subset=["ws","wd_deg"]).iterrows():
                    try:
                        rlat = float(row.get("lat", lat) or lat)
                        rlon = float(row.get("lon", lon) or lon)
                        spd = float(row.get("ws", 0))
                        wd = float(row.get("wd_deg", 0))
                    except Exception:
                        continue
                    dlat = -0.02 * spd * np.cos(np.deg2rad(wd))
                    dlon = 0.02 * spd * np.sin(np.deg2rad(wd))
                    PolyLine(locations=[[rlat, rlon], [rlat + dlat, rlon + dlon]], color="#a9df52", weight=2).add_to(fg2)
                m.add_child(fg2)
            folium.LayerControl().add_to(m)
            st_folium(m, width=1000, height=600)
        except Exception as e:
            st.warning(f"Folium map render failed: {e}. Falling back to simple st.map.")
            try:
                st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
            except Exception as ee:
                st.error(f"Map fallback failed: {ee}")
    else:
        # simple fallback: st.map
        try:
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
        except Exception as e:
            st.warning(f"Map unavailable: {e}")

# -----------------------------
# Forecast table and export
# -----------------------------
st.markdown("---")
if show_table:
    st.subheader("📋 Forecast Table")
    try:
        st.dataframe(df_sorted.reset_index(drop=True))
    except Exception as e:
        st.info(f"Unable to show table: {e}")

st.markdown("---")
st.subheader("💾 Export Data")
try:
    csv = df_sorted.to_csv(index=False)
    json_text = df_sorted.to_json(orient="records", force_ascii=False, date_format="iso")
    colx, coly = st.columns(2)
    with colx:
        st.download_button("⬇️ Download CSV", data=csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
    with coly:
        st.download_button("⬇️ Download JSON", data=json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")
except Exception as e:
    st.info(f"Export not available: {e}")

st.markdown("---")
st.caption("Tactical Weather Ops Dashboard — BMKG Data © 2025. For Ventusky-like animated wind fields add model/radar tile URLs to RADAR_TMS/MODEL_TMS environment variables.")
