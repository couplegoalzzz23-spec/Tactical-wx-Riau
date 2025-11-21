# tactical_wx_ventusky_meteoblue_streamlit.py
# Enhanced Streamlit weather dashboard inspired by Ventusky & Meteoblue
# Features:
# - Interactive Folium map with multiple base layers
# - Time slider + simple animation controls
# - Layer toggles (stations, rainfall, wind markers)
# - Trend charts (temperature, humidity, wind, precipitation)
# - Windrose, CSV/JSON export
# - Plug-and-play tile overlay placeholder for radar/forecast tiles
#
# Requirements:
# pip install streamlit requests pandas numpy plotly folium streamlit_folium branca

import streamlit as st
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium import TileLayer, FeatureGroup, LayerControl, CircleMarker, Popup
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta
import json

# -----------------------------
# Configuration / Constants
# -----------------------------
st.set_page_config(page_title="Tactical Weather — Ventusky/Meteoblue Style", layout="wide")
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"  # BMKG admin forecast endpoint
MS_TO_KT = 1.94384

# Tile overlay placeholders
DEFAULT_BASE_TILES = {
    "OpenStreetMap": "OpenStreetMap",
    "Stamen Terrain": "Stamen Terrain",
    "CartoDB Positron": "CartoDB positron",
}

# If you have a radar / forecast TMS/WMS URL (from a provider), put it here
# Example TMS template (placeholder):
RADAR_TMS = ""  # e.g. "https://tileserver.example.com/radar/{z}/{x}/{y}.png"
FORECAST_TMS = ""  # e.g. ensemble / model tiles

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
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "provinsi": lokasi.get("provinsi"),
                "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"),
                "lat": lokasi.get("lat"),
            })
            try:
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
            except Exception:
                r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# -----------------------------
# Sidebar Controls
# -----------------------------
with st.sidebar:
    st.title("Tactical Controls — Ventusky Mode")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    st.markdown("---")
    st.subheader("Map Layers")
    base_tile = st.selectbox("Base Map", options=list(DEFAULT_BASE_TILES.keys()), index=0)
    show_radarlayer = st.checkbox("Show Radar/Forecast Tile Layer (TMS)", value=False)
    show_stations = st.checkbox("Show Stations / Observations", value=True)
    show_choropleth = st.checkbox("Show Choropleth (Rainfall)", value=False)
    st.markdown("---")
    st.subheader("Variable & Time")
    var_choice = st.selectbox("Primary Variable", options=["t","hu","tp","ws","wd_deg"], index=0)
    animate = st.checkbox("Enable Animation (auto-play)", value=False)
    st.markdown("---")
    st.caption("Data source: BMKG forecast API — customize tile URLs for radar/forecast overlays")

# -----------------------------
# Fetch data
# -----------------------------
st.title("Tactical Weather — Ventusky / Meteoblue Inspired Dashboard")
with st.spinner("Fetching BMKG forecast..."):
    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"Failed to fetch BMKG data: {e}")
        st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data found for the given ADM1.")
    st.stop()

# Build mapping label -> entry
mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = e

col_main, col_side = st.columns([3,1])
with col_side:
    st.metric("Locations", len(mapping))
with col_main:
    loc_choice = st.selectbox("Select Location", options=list(mapping.keys()))

selected_entry = mapping[loc_choice]
df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.warning("No usable observations in selected location.")
    st.stop()

# convert wind speed to knots and compute simple u/v
df["ws_kt"] = df["ws"] * MS_TO_KT
# wind components (approx) for simple map arrows (not accounting for vertical)
df["u"] = -df["ws"] * np.sin(np.deg2rad(df.get("wd_deg", 0)))
df["v"] = -df["ws"] * np.cos(np.deg2rad(df.get("wd_deg", 0)))

# timeline handling
if df["local_datetime_dt"].isna().all():
    st.error("No valid datetimes in dataset.")
    st.stop()

min_dt = df["local_datetime_dt"].min()
max_dt = df["local_datetime_dt"].max()
# produce list of datetimes for slider
times = pd.to_datetime(df["local_datetime_dt"]).sort_values().unique()

# time slider (main)
time_idx = st.slider("Time", 0, len(times)-1, value=len(times)-1)
current_time = pd.to_datetime(times[time_idx])

# animation auto-play: rudimentary by re-running with st.experimental_rerun on timer
if animate:
    # simple autoplay: loop a small number of frames to avoid runaway reruns
    for i in range(time_idx, min(time_idx+20, len(times))):
        st.experimental_rerun()

# filter df for the selected time +/- tolerance
tolerance = pd.Timedelta(hours=1)
mask = (df["local_datetime_dt"] >= current_time - tolerance) & (df["local_datetime_dt"] <= current_time + tolerance)
df_sel = df.loc[mask].copy()
if df_sel.empty:
    st.info("No observations for selected time slice — showing nearest available.")
    # pick nearest
    nearest_idx = (np.abs(pd.to_datetime(df["local_datetime_dt"]) - current_time)).argmin()
    df_sel = df.iloc[[nearest_idx]].copy()

# -----------------------------
# Map: Folium with layers
# -----------------------------
st.subheader("Interactive Map")
lat = float(selected_entry.get("lokasi", {}).get("lat", 0) or 0)
lon = float(selected_entry.get("lokasi", {}).get("lon", 0) or 0)

m = folium.Map(location=[lat, lon], zoom_start=7, tiles=None)
# base tiles
TileLayer(DEFAULT_BASE_TILES[base_tile], name=base_tile, control=True).add_to(m)
TileLayer('Stamen Toner', name='Toner', control=True).add_to(m)
TileLayer('CartoDB Dark_Matter', name='Dark', control=True).add_to(m)

# optional radar / forecast TMS
if show_radarlayer and RADAR_TMS:
    TileLayer(tiles=RADAR_TMS, name='Radar / Forecast Tiles', attr='Provider', overlay=True, control=True).add_to(m)
else:
    if show_radarlayer:
        folium.map.LayerControl().add_to(m)
        st.warning("Radar/forecast tile layer selected but no TMS URL configured. Set RADAR_TMS/FORECAST_TMS in the script.")

# station markers
fg_obs = FeatureGroup(name='Observations', show=show_stations)
for _, row in df_sel.iterrows():
    try:
        rlat = float(row.get('lat', lat))
        rlon = float(row.get('lon', lon))
    except Exception:
        rlat, rlon = lat, lon
    popup_html = f"<b>{row.get('adm2','Station')}</b><br>Time: {row.get('local_datetime')}<br>Temp: {row.get('t','—')} °C<br>RH: {row.get('hu','—')}%<br>Wind: {row.get('ws_kt',0):.1f} KT @ {row.get('wd_deg','—')}°<br>Rain: {row.get('tp','—')} mm"
    popup = Popup(popup_html, max_width=300)
    CircleMarker(location=[rlat, rlon], radius=6, color='#00ffbf', fill=True, fill_opacity=0.9, popup=popup).add_to(fg_obs)

m.add_child(fg_obs)

# choropleth (simple tile-less approach using circle markers sized by rainfall)
if show_choropleth:
    fg_chor = FeatureGroup(name='Rainfall (proxy)', show=True)
    for _, row in df_sel.iterrows():
        rlat = float(row.get('lat', lat))
        rlon = float(row.get('lon', lon))
        rain = float(row.get('tp', 0) or 0)
        CircleMarker(location=[rlat, rlon], radius=3 + rain*0.6, color=None, fill=True, fill_color='#ffb300', fill_opacity=0.6, popup=f"Rain: {rain} mm").add_to(fg_chor)
    m.add_child(fg_chor)

# wind arrows (simplified as small lines via PolyLine)
fg_wind = FeatureGroup(name='Wind Vectors', show=True)
for _, row in df_sel.dropna(subset=['ws','wd_deg']).iterrows():
    rlat = float(row.get('lat', lat))
    rlon = float(row.get('lon', lon))
    spd = float(row.get('ws', 0))
    wd = float(row.get('wd_deg', 0))
    # small displacement for arrow visualization
    dlat = -0.02 * spd * np.cos(np.deg2rad(wd))
    dlon = 0.02 * spd * np.sin(np.deg2rad(wd))
    folium.PolyLine(locations=[[rlat, rlon], [rlat+dlat, rlon+dlon]], color='#a9df52', weight=2).add_to(fg_wind)

m.add_child(fg_wind)

# layer control
LayerControl().add_to(m)

# render map
st_data = st_folium(m, width=900, height=600)

# -----------------------------
# Right column: charts & details
# -----------------------------
st.markdown("---")
col_a, col_b = st.columns([2,1])
with col_a:
    st.subheader("Parameter Trends — Nearby Timeline")
    # show a window of timeline around current_time
    window_hours = 24
    t0 = current_time - pd.Timedelta(hours=window_hours)
    t1 = current_time + pd.Timedelta(hours=window_hours)
    df_window = df[(df['local_datetime_dt'] >= t0) & (df['local_datetime_dt'] <= t1)].copy()
    if not df_window.empty:
        fig_t = px.line(df_window, x='local_datetime_dt', y='t', title='Temperature (°C)', markers=True)
        st.plotly_chart(fig_t, use_container_width=True)
        fig_h = px.line(df_window, x='local_datetime_dt', y='hu', title='Humidity (%)', markers=True)
        st.plotly_chart(fig_h, use_container_width=True)
        fig_w = px.line(df_window, x='local_datetime_dt', y='ws_kt', title='Wind Speed (KT)', markers=True)
        st.plotly_chart(fig_w, use_container_width=True)
        fig_r = px.bar(df_window, x='local_datetime_dt', y='tp', title='Rainfall (mm)')
        st.plotly_chart(fig_r, use_container_width=True)
    else:
        st.info('No timeline data in the display window')

with col_b:
    st.subheader('Windrose & Diagnostics')
    if 'wd_deg' in df.columns and 'ws_kt' in df.columns:
        df_wr = df.dropna(subset=['wd_deg','ws_kt'])
        if not df_wr.empty:
            # simple windrose using plotly
            bins_dir = np.arange(-11.25, 360, 22.5)
            labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            df_wr['dir_sector'] = pd.cut(df_wr['wd_deg'] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
            speed_bins = [0,5,10,20,30,50,100]
            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
            df_wr['speed_class'] = pd.cut(df_wr['ws_kt'], bins=speed_bins, labels=speed_labels, include_lowest=True)
            freq = df_wr.groupby(['dir_sector','speed_class']).size().reset_index(name='count')
            freq['percent'] = freq['count']/freq['count'].sum()*100
            az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
                      "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
            freq['theta'] = freq['dir_sector'].map(az_map)
            colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
            fig_wr = go.Figure()
            for i, sc in enumerate(speed_labels):
                subset = freq[freq['speed_class']==sc]
                fig_wr.add_trace(go.Barpolar(r=subset['percent'], theta=subset['theta'], name=f"{sc} KT", marker_color=colors[i]))
            fig_wr.update_layout(template='plotly_dark', title='Windrose (KT)')
            st.plotly_chart(fig_wr, use_container_width=True)
    else:
        st.info('No wind data available for windrose')

# -----------------------------
# Export & Download
# -----------------------------
st.markdown('---')
st.subheader('Export Data & Share')
csv = df.to_csv(index=False)
json_text = df.to_json(orient='records', force_ascii=False, date_format='iso')
st.download_button('Download full CSV', data=csv, file_name=f'bmkg_forecast_{adm1}.csv', mime='text/csv')
st.download_button('Download full JSON', data=json_text, file_name=f'bmkg_forecast_{adm1}.json', mime='application/json')

st.markdown('\n---\n')
st.caption('Notes: To replicate Ventusky/Meteoblue-style visualization you will likely need tiled forecast/radar layers (TMS/WMS) from a tile provider. Add TMS URLs to RADAR_TMS or FORECAST_TMS variables in this script and enable `Show Radar/Forecast Tile Layer`.')

# End of script
