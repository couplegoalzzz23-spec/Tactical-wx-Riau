# app.py
# Tactical Weather Ops — Clean UI (BMKG)
# (Full script inserted as requested, location selector unchanged)

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------
st.set_page_config(page_title="Tactical Weather Ops — Clean UI", layout="wide")
st.markdown("""
<style>	body { background-color: #0b0c0c; color: #d1d6c7; font-family: 'Consolas','Roboto Mono',monospace; }
	h1,h2,h3 { color: #a9df52; letter-spacing: 1px; }
	section[data-testid="stSidebar"] { background-color: #111; }
	.stButton>button { background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius:6px; font-weight:bold; }
	.stButton>button:hover { background-color:#2c3b2c; border-color:#a9df52; }
	div[data-testid="stMetricValue"] { color: #a9df52 !important; }
	.radar { position: relative; width: 140px; height: 140px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
	.radar:before { content: ''; position: absolute; top: 0; left: 0; width:50%; height:2px; background: linear-gradient(90deg,#33ff55,transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
	@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
	hr, .stDivider { border-top: 1px solid #2f3a2f; }
</style>
""", unsafe_allow_html=True)

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
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384
RADAR_TMS = os.getenv("RADAR_TMS", "").strip()
MODEL_TMS = os.getenv("MODEL_TMS", "").strip()

# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
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
            try: r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
            except: r["utc_datetime_dt"] = pd.NaT
            try: r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
            except: r["local_datetime_dt"] = pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df.get("ws", pd.Series(dtype=float)) * MS_TO_KT
    return df

# -----------------------------
with st.sidebar:
    st.title("⚙️ Tactical Menu")
    st.markdown('<div class="radar"></div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#6f6;'>SCANNING WEATHER…</p>", unsafe_allow_html=True)
    st.markdown("---")

    adm1 = st.text_input("Province Code (ADM1)", value="32")

    st.subheader("Parameter Utama")
    show_temp = st.checkbox("Temperatur", True)
    show_wind = st.checkbox("Angin", True)
    show_rain = st.checkbox("Curah Hujan", True)

    st.subheader("Parameter Tambahan")
    show_hum = st.checkbox("Kelembapan", False)
    show_vis = st.checkbox("Visibilitas", False)
    show_pres = st.checkbox("Tekanan", False)

    st.subheader("Visualisasi")
    show_windrose = st.checkbox("Windrose", True)
    show_charts = st.checkbox("Grafik Tren", True)
    show_map = st.checkbox("Peta", True)
    show_table = st.checkbox("Tabel", False)

    st.markdown("---")
    st.caption("BMKG Tactical Ops Theme v1.0")

# -----------------------------
st.title("Tactical Weather Ops — Clean UI Dashboard")
raw = fetch_forecast(adm1)
entries = raw.get("data", []) if isinstance(raw, dict) else []
if not entries:
    st.error("No data available for the given ADM1.")
    st.stop()

locations = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("adm2") or lok.get("kotkab") or lok.get("provinsi") or f"Location {len(locations)+1}"
    if label in locations:
        label = f"{label} ({len(locations)+1})"
    locations[label] = e

col_main, col_side = st.columns([3,1])
with col_main:
    sel_loc = st.selectbox("Pilih Lokasi", list(locations.keys()))
with col_side:
    st.metric("Jumlah Lokasi", len(locations))

selected_entry = locations[sel_loc]
df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.error("No usable forecast data.")
    st.stop()

times = sorted([t for t in pd.to_datetime(df["local_datetime_dt"].dropna()).unique()])
if not times:
    st.error("No timestamps available.")
    st.stop()

time_index = st.slider("Time index", 0, len(times)-1, len(times)-1)
current_time = times[time_index]

tol = pd.Timedelta(hours=3)
df_sel = df[(df["local_datetime_dt"] >= current_time - tol) & (df["local_datetime_dt"] <= current_time + tol)]
if df_sel.empty:
    df_sel = df.iloc[[ (pd.to_datetime(df["local_datetime_dt"]) - current_time).abs().idxmin() ]]

# -----------------------------
st.markdown("---")
st.subheader("📡 Kondisi Saat Ini")
now = df_sel.iloc[0]

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric("TEMP (°C)", f"{now.get('t','—')}°C" if show_temp else "—")
with c2:
    st.metric("WIND (KT)", f"{now.get('ws_kt',0):.1f}" if show_wind else "—")
with c3:
    st.metric("RAIN (mm)", f"{now.get('tp','—')}" if show_rain else "—")
