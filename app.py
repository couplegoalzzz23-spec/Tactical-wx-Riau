# tactical_wx_ventusky_meteoblue_streamlit.py
# Enhanced Streamlit weather dashboard inspired by Ventusky & Meteoblue
# Robustified for graceful degradation (no errors if optional libs missing)
# Requirements (recommended):
# pip install streamlit requests pandas numpy plotly folium streamlit_folium branca

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Optional imports (fall back if not available)
HAVE_FOLIUM = True
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
# Configuration / Constants
# -----------------------------
st.set_page_config(page_title="Tactical Weather — Ventusky/Meteoblue Style", layout="wide")
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# Placeholder for external tiles (set your provider URLs here if you have them)
RADAR_TMS = ""
FORECAST_TMS = ""

# -----------------------------
# Utilities
# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    """
    Fetch BMKG forecast for a given ADM1. Raises HTTPError if request fails.
    """
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()


def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
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
            # parse datetimes if present
            try:
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime")) if r.get("utc_datetime") is not None else pd.NaT
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime")) if r.get("local_datetime") is not None else pd.NaT
            except Exception:
                r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    # normalize numeric columns
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
    base_tile = st.selectbox("Base Map", options=["OpenStreetMap", "Stamen Terrain", "CartoDB Positron"], index=0)
    show_radarlayer = st.checkbox("Show Radar/Forecast Tile Layer (TMS)", value=False)
    show_stations = st.checkbox("Show Stations / Observations", value=True)
    show_choropleth = st.checkbox("Show Rain Proxy (circles)", value=False)
    st.markdown("---")
    st.subheader("Variable & Time")
    var_choice = st.selectbox("Primary Variable", options=["t","hu","tp","ws","wd_deg"], index=0)
    animate = st.checkbox("Enable simple animation (loop slider)", value=False)
    st.markdown("---")
    st.caption("Data source: BMKG forecast API — set RADAR_TMS/FORECAST_TMS in script for tile overlays")

# -----------------------------
# Fetch data
# -----------------------------
st.title("Tactical Weather — Ventusky / Meteoblue Inspired Dashboard")
with st.spinner("Fetching BMKG forecast..."):
    try:
        raw = fetch_forecast(adm1)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch BMKG data: {e}")
        st.stop()

entries = raw.get("data", []) if isinstance(raw, dict) else []
if not entries:
    st.warning("No forecast data found for the given ADM1.")
    st.stop()

# Build mapping label -> entry
mapping = {}
for e in entries:
    lok = e.get("lokasi", {}) if isinstance(e, dict) else {}
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = e

col_main, col_side = st.columns([3,1])
with col_side:
    st.metric("Locations", len(mapping))
with col_main:
    loc_choice = st.selectbox("Select Location", options=list(mapping.keys()))

selected_entry = mapping.get(loc_choice)
if not selected_entry:
    st.error("Selected location data missing.")
    st.stop()

# prepare dataframe
df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.warning("No usable observations in selected location.")
    st.stop()

# wind conversions and components (safe handling)
df["ws_kt"] = df.get("ws", pd.Series(dtype=float)) * MS_TO_KT
wd = df.get("wd_deg", pd.Series(dtype=float)).fillna(0)
ws = df.get("ws", pd.Series(dtype=float)).fillna(0)
df["u"] = -ws * np.sin(np.deg2rad(wd))
df["v"] = -ws * np.cos(np.deg2rad(wd))

# timeline handling
if df["local_datetime_dt"].isna().all():
    st.error("No valid datetimes in dataset.")
    st.stop()

times = pd.to_datetime(df["local_datetime_dt"]).sort_values().unique()
if len(times) == 0:
    st.error("No timestamps available to build timeline.")
    st.stop()

# slider index
time_idx = st.slider("Time index", 0, max(0, len(times)-1), value=len(times)-1)
current_time = pd.to_datetime(times[time_idx])

# simple animation: if requested, advance slider using session state (non-blocking)
if animate:
    if "animate_idx" not in st.session_state:
        st.session_state.animate_idx = time_idx
    else:
        # increment but wrap around
        st.session_state.animate_idx = (st.session_state.animate_idx + 1) % len(times)
    # override current_time with animated index so map/charts move
    current_time = pd.to_datetime(times[st.session_state.animate_idx])

# filter df for the selected time +/- tolerance
tolerance = pd.Timedelta(hours=1)
mask = (df["local_datetime_dt"] >= current_time - tolerance) & (df["local_datetime_dt"] <= current_time + tolerance)
df_sel = df.loc[mask].copy()
if df_sel.empty:
    # choose nearest single row to show
    diffs = np.abs(pd.to_datetime(df["local_datetime_dt"]) - current_time)
    nearest_idx = int(diffs.idxmin())
    df_sel = df.iloc[[nearest_idx]].copy()

# -----------------------------
# Metric panel
# -----------------------------
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")
now = df_sel.iloc[0]
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("TEMP (°C)", f"{now.get('t', '—')}°C")
with c2:
    st.metric("HUMIDITY", f"{now.get('hu', '—')}%")
with c3:
    ws_kt_val = now.get('ws_kt') if pd.notna(now.get('ws_kt')) else 0
    st.metric("WIND (KT)", f"{ws_kt_val:.1f}")
with c4:
    st.metric("RAIN (mm)", f"{now.get('tp', '—')}")

# -----------------------------
# Charts: trends
# -----------------------------
st.markdown("---")
st.subheader("📊 Parameter Trends")
col1, col2 = st.columns(2)
with col1:
    try:
        fig_t = px.line(df.sort_values('local_datetime_dt'), x='local_datetime_dt', y='t', title='Temperature (°C)', markers=True)
        st.plotly_chart(fig_t, use_container_width=True)
    except Exception:
        st.info('Temperature chart unavailable')
    try:
        fig_h = px.line(df.sort_values('local_datetime_dt'), x='local_datetime_dt', y='hu', title='Humidity (%)', markers=True)
        st.plotly_chart(fig_h, use_container_width=True)
    except Exception:
        st.info('Humidity chart unavailable')
with col2:
    try:
        fig_w = px.line(df.sort_values('local_datetime_dt'), x='local_datetime_dt', y='ws_kt', title='Wind Speed (KT)', markers=True)
        st.plotly_chart(fig_w, use_container_width=True)
    except Exception:
        st.info('Wind chart unavailable')
    try:
        fig_r = px.bar(df.sort_values('local_datetime_dt'), x='local_datetime_dt', y='tp', title='Rainfall (mm)')
        st.plotly_chart(fig_r, use_container_width=True)
    except Exception:
        st.info('Rain chart unavailable')

# -----------------------------
# Windrose
# -----------------------------
st.markdown("---")
st.subheader("🌪️ Windrose — Direction & Speed")
if 'wd_deg' in df.columns and 'ws_kt' in df.columns:
    df_wr = df.dropna(subset=['wd_deg', 'ws_kt']).copy()
    if not df_wr.empty:
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
            fig_wr.add_trace(go.Barpolar(r=subset['percent'], theta=subset['theta'], name=f"{sc} KT", marker_color=colors[i] if i < len(colors) else None))
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
        st.info('No wind data for windrose')
else:
    st.info('Wind data columns missing')

# -----------------------------
# Map display (folium if available, else fallback to Streamlit map)
# -----------------------------
show_map = True
if HAVE_FOLIUM and st_folium is not None:
    st.markdown("---")
    st.subheader("🗺️ Tactical Map — Interactive")
    lat = float(selected_entry.get("lokasi", {}).get("lat", 0) or 0)
    lon = float(selected_entry.get("lokasi", {}).get("lon", 0) or 0)
    try:
        m = folium.Map(location=[lat, lon], zoom_start=7, tiles=None)
        # base tiles
        TileLayer('OpenStreetMap', name='OpenStreetMap', control=True).add_to(m)
        TileLayer('Stamen Terrain', name='Stamen Terrain', control=True).add_to(m)
        TileLayer('CartoDB Positron', name='CartoDB Positron', control=True).add_to(m)
        # optional radar
        if show_radarlayer and RADAR_TMS:
            TileLayer(tiles=RADAR_TMS, name='Radar Tiles', attr='Provider', overlay=True, control=True).add_to(m)
        # add observation markers
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
        # wind vectors
        fg_wind = FeatureGroup(name='Wind Vectors', show=True)
        for _, row in df_sel.dropna(subset=['ws','wd_deg']).iterrows():
            try:
                rlat = float(row.get('lat', lat))
                rlon = float(row.get('lon', lon))
                spd = float(row.get('ws', 0))
                wd = float(row.get('wd_deg', 0))
            except Exception:
                continue
            dlat = -0.02 * spd * np.cos(np.deg2rad(wd))
            dlon = 0.02 * spd * np.sin(np.deg2rad(wd))
            PolyLine(locations=[[rlat, rlon], [rlat+dlat, rlon+dlon]], color='#a9df52', weight=2).add_to(fg_wind)
        m.add_child(fg_wind)
        folium.LayerControl().add_to(m)
        st_folium(m, width=900, height=500)
    except Exception as e:
        st.warning(f"Folium map failed: {e}")
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
else:
    # fallback simple map
    st.markdown("---")
    st.subheader("🗺️ Tactical Map — Simple (folium unavailable)")
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", 0) or 0)
        lon = float(selected_entry.get("lokasi", {}).get("lon", 0) or 0)
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
    except Exception as e:
        st.warning(f"Map unavailable: {e}")

# -----------------------------
# Forecast table (collapsible)
# -----------------------------
with st.expander("Show forecast table"):
    st.dataframe(df.sort_values('local_datetime_dt'))

# -----------------------------
# Export
# -----------------------------
st.markdown("---")
st.subheader("💾 Export Data")
csv = df.to_csv(index=False)
json_text = df.to_json(orient='records', force_ascii=False, date_format='iso')
colx, coly = st.columns(2)
with colx:
    st.download_button("⬇️ Download CSV", data=csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
with coly:
    st.download_button("⬇️ Download JSON", data=json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")

# Footer
st.markdown("---")
st.caption('Tactical Weather Ops Dashboard — BMKG Data © 2025 — Designed for robust execution')
