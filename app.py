# app.py
# Tactical Weather Ops — Clean UI (BMKG)
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
# Page config + CSS (clean)
# -----------------------------
st.set_page_config(page_title="Tactical Weather Ops — Clean UI", layout="wide")
st.markdown(
    """
<style>
body { background-color: #0b0c0c; color: #d1d6c7; font-family: "Consolas","Roboto Mono",monospace; }
h1,h2,h3 { color: #a9df52; letter-spacing: 1px; }
section[data-testid="stSidebar"] { background-color: #111; }
.stButton>button { background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius:6px; font-weight:bold; }
.stButton>button:hover { background-color:#2c3b2c; border-color:#a9df52; }
div[data-testid="stMetricValue"] { color: #a9df52 !important; }
/* radar scan (preserved) */
.radar { position: relative; width: 140px; height: 140px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
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
        from streamlit_folium import st_folium
    except Exception:
        st_folium = None
except Exception:
    HAVE_FOLIUM = False
    folium = None
    TileLayer = FeatureGroup = CircleMarker = Popup = PolyLine = None
    st_folium = None

# -----------------------------
# Constants + config
# -----------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# Tile placeholders (optional)
RADAR_TMS = os.getenv("RADAR_TMS", "").strip()
MODEL_TMS = os.getenv("MODEL_TMS", "").strip()

# -----------------------------
# Utilities
# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    """Fetch BMKG admin forecast for adm1. Returns dict or {} on error."""
    try:
        resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=12)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}

def flatten_cuaca_entry(entry: dict) -> pd.DataFrame:
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
            except Exception:
                r["utc_datetime_dt"] = pd.NaT
            try:
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime")) if r.get("local_datetime") else pd.NaT
            except Exception:
                r["local_datetime_dt"] = pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # derived
    df["ws_kt"] = df.get("ws", pd.Series(dtype=float)) * MS_TO_KT
    return df

def nearest_row(df: pd.DataFrame, dt_col: str, target_dt):
    if df.empty:
        return df
    diffs = (pd.to_datetime(df[dt_col]) - pd.to_datetime(target_dt)).abs()
    idx = diffs.idxmin()
    return df.loc[[idx]]

# -----------------------------
# Sidebar (Professional grouping)
# -----------------------------
with st.sidebar:
    st.title("⚙️ Tactical Menu")
    st.markdown('<div class="radar"></div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#6f6;'>SCANNING WEATHER…</p>", unsafe_allow_html=True)
    st.markdown("---")

    adm1 = st.text_input("Province Code (ADM1)", value="32")

    st.subheader("Parameter Utama")
    show_temp = st.checkbox("Temperatur", value=True)
    show_wind = st.checkbox("Angin", value=True)
    show_rain = st.checkbox("Curah Hujan", value=True)

    st.subheader("Parameter Tambahan")
    show_hum = st.checkbox("Kelembapan", value=False)
    show_vis = st.checkbox("Visibilitas", value=False)
    show_pres = st.checkbox("Tekanan", value=False)

    st.subheader("Visualisasi")
    show_windrose = st.checkbox("Windrose", value=True)
    show_charts = st.checkbox("Grafik Tren", value=True)
    show_map = st.checkbox("Peta", value=True)
    show_table = st.checkbox("Tabel", value=False)

    st.markdown("---")
    st.caption("Data Source: BMKG API — Theme: Tactical Ops v1.0")

# -----------------------------
# Fetch data
# -----------------------------
st.title("Tactical Weather Ops — Clean UI Dashboard")
raw = fetch_forecast(adm1)
entries = raw.get("data", []) if isinstance(raw, dict) else []
if not entries:
    st.error("No data available for the given ADM1 from BMKG.")
    st.stop()

# build location map
locations = {}
for e in entries:
    lok = e.get("lokasi", {}) if isinstance(e, dict) else {}
    label = lok.get("adm2") or lok.get("kotkab") or lok.get("provinsi") or f"Location {len(locations)+1}"
    # if duplicates, append index
    if label in locations:
        label = f"{label} ({len(locations)+1})"
    locations[label] = e

col_main, col_side = st.columns([3,1])
with col_main:
    sel_loc = st.selectbox("Pilih Lokasi", options=list(locations.keys()))
with col_side:
    st.metric("Jumlah Lokasi", len(locations))

selected_entry = locations.get(sel_loc)
df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.error("No usable forecast records for selected location.")
    st.stop()

# timeline / times
times = pd.to_datetime(df["local_datetime_dt"].dropna().unique())
times = sorted([pd.to_datetime(t) for t in times])
if len(times) == 0:
    st.error("No timestamps available in dataset.")
    st.stop()

# slider index
time_index = st.slider("Time index (pakai untuk mengubah waktu)", 0, len(times)-1, value=len(times)-1)
current_time = times[time_index]

# select window (3-hour tolerance)
tol = pd.Timedelta(hours=3)
mask = (df["local_datetime_dt"] >= current_time - tol) & (df["local_datetime_dt"] <= current_time + tol)
df_sel = df.loc[mask].copy()
if df_sel.empty:
    df_sel = nearest_row(df, "local_datetime_dt", current_time)

# -----------------------------
# Metric panel
# -----------------------------
st.markdown("---")
st.subheader("📡 Kondisi Saat Ini")
now = df_sel.iloc[0] if not df_sel.empty else df.iloc[0]
c1, c2, c3, c4 = st.columns(4)
with c1:
    if show_temp:
        tval = now.get("t")
        st.metric("TEMP (°C)", f"{tval}°C" if pd.notna(tval) else "—")
    else:
        st.metric("TEMP (°C)", "—")
with c2:
    if show_wind:
        wsval = now.get("ws_kt", np.nan)
        try:
            st.metric("WIND (KT)", f"{wsval:.1f}")
        except Exception:
            st.metric("WIND (KT)", "—")
    else:
        st.metric("WIND (KT)", "—")
with c3:
    if show_rain:
        tpval = now.get("tp")
        st.metric("RAIN (mm)", f"{tpval}" if pd.notna(tpval) else "—")
    else:
        st.metric("RAIN (mm)", "—")
with c4:
    if show_hum:
        huval = now.get("hu")
        st.metric("HUMIDITY", f"{huval}%" if pd.notna(huval) else "—")
    else:
        st.metric("HUMIDITY", "—")

# -----------------------------
# Charts (compact)
# -----------------------------
st.markdown("---")
if show_charts:
    st.subheader("📈 Grafik Tren")
    cols = st.columns(2)
    # left: temp & rain
    with cols[0]:
        if show_temp and "t" in df and df["t"].notna().any():
            fig = px.line(df.sort_values("local_datetime_dt"), x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        if show_rain and "tp" in df and df["tp"].notna().any():
            fig = px.bar(df.sort_values("local_datetime_dt"), x="local_datetime_dt", y="tp", title="Rainfall (mm)")
            st.plotly_chart(fig, use_container_width=True)
    # right: wind & humidity
    with cols[1]:
        if show_wind and "ws_kt" in df and df["ws_kt"].notna().any():
            fig = px.line(df.sort_values("local_datetime_dt"), x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        if show_hum and "hu" in df and df["hu"].notna().any():
            fig = px.line(df.sort_values("local_datetime_dt"), x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Windrose (style preserved)
# -----------------------------
st.markdown("---")
if show_windrose:
    st.subheader("🌪️ Windrose — Direction & Speed")
    if {"wd_deg", "ws_kt"}.issubset(df.columns) and df[["wd_deg","ws_kt"]].dropna().shape[0] > 0:
        try:
            df_wr = df.dropna(subset=["wd_deg","ws_kt"]).copy()
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
                    subset = freq[freq["speed_class"]==sc]
                    fig_wr.add_trace(go.Barpolar(
                        r=subset["percent"], theta=subset["theta"], name=f"{sc} KT",
                        marker_color=colors[i] if i < len(colors) else None, opacity=0.85
                    ))
                fig_wr.update_layout(
                    title="Windrose (KT)",
                    polar=dict(
                        angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0,360,45))),
                        radialaxis=dict(ticksuffix="%", showline=True, gridcolor="#333")
                    ),
                    legend_title="Wind Speed Class",
                    template="plotly_dark"
                )
                st.plotly_chart(fig_wr, use_container_width=True)
            else:
                st.info("Tidak cukup data angin untuk windrose.")
        except Exception as e:
            st.info(f"Windrose generation failed: {e}")
    else:
        st.info("Data arah/kecepatan angin tidak tersedia untuk windrose.")

# -----------------------------
# Map (Folium) with graceful fallback
# -----------------------------
st.markdown("---")
if show_map:
    st.subheader("🗺️ Tactical Map")
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
            if RADAR_TMS:
                TileLayer(tiles=RADAR_TMS, name="Radar Tiles", overlay=True, control=True).add_to(m)
            if MODEL_TMS:
                TileLayer(tiles=MODEL_TMS, name="Model Tiles", overlay=True, control=True).add_to(m)
            # add observations
            if not df_sel.empty:
                fg = FeatureGroup(name="Observations", show=True)
                for _, row in df_sel.iterrows():
                    try:
                        rlat = float(row.get("lat", lat) or lat)
                        rlon = float(row.get("lon", lon) or lon)
                    except Exception:
                        rlat, rlon = lat, lon
                    popup_html = f"<b>{row.get('adm2','Station')}</b><br>Time: {row.get('local_datetime_dt')}<br>Temp: {row.get('t','—')} °C<br>Wind: {row.get('ws_kt',0):.1f} KT @ {row.get('wd_deg','—')}°<br>Rain: {row.get('tp','—')} mm"
                    Popup(popup_html, max_width=300).add_to(fg)
                    CircleMarker(location=[rlat, rlon], radius=6, color="#00ffbf", fill=True, fill_opacity=0.9).add_to(fg)
                m.add_child(fg)
            # wind vectors
            if show_wind and not df_sel.dropna(subset=["ws","wd_deg"]).empty:
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
            st.warning(f"Folium map render failed: {e}. Falling back to st.map.")
            try:
                st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
            except Exception as ee:
                st.error(f"Map fallback failed: {ee}")
    else:
        try:
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
        except Exception as e:
            st.warning(f"Map unavailable: {e}")

# -----------------------------
# Forecast table (optional) & Export
# -----------------------------
st.markdown("---")
if show_table:
    st.subheader("📋 Forecast Table")
    try:
        st.dataframe(df.sort_values("local_datetime_dt").reset_index(drop=True))
    except Exception as e:
        st.info(f"Unable to show table: {e}")

st.markdown("---")
st.subheader("💾 Export Data")
try:
    csv = df.sort_values("local_datetime_dt").to_csv(index=False)
    json_text = df.sort_values("local_datetime_dt").to_json(orient="records", force_ascii=False, date_format="iso")
    colx, coly = st.columns(2)
    with colx:
        st.download_button("⬇️ Download CSV", data=csv, file_name=f"{adm1}_{sel_loc}.csv", mime="text/csv")
    with coly:
        st.download_button("⬇️ Download JSON", data=json_text, file_name=f"{adm1}_{sel_loc}.json", mime="application/json")
except Exception as e:
    st.info(f"Export not available: {e}")

st.markdown("---")
st.caption("Tactical Weather Ops Dashboard — BMKG Data © 2025 — Clean UI. Windrose style preserved; radar scan preserved.")

