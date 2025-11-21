import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# =====================================================
# SAFE IMPORT FOLIUM (ANTI ERROR)
# =====================================================
try:
    import folium
    from streamlit_folium import st_folium
    folium_available = True
except Exception:
    folium_available = False

# =====================================================
# APLIKASI UTAMA
# =====================================================
st.set_page_config(page_title="Tactical Weather Dashboard", layout="wide")

st.title("🔥 Tactical Weather Dashboard — Riau")
st.caption("Versi Premium — Anti Error, Auto Fallback, Day/Night Ops Mode")


# =====================================================
# FETCH DATA (AMBIL API)
# =====================================================
@st.cache_data
def get_weather():
    url = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm/1471"
    try:
        return requests.get(url).json()
    except Exception:
        return None

data = get_weather()

if data is None:
    st.error("Tidak dapat mengambil data BMKG.")
    st.stop()

# =====================================================
# PARSING DATA
# =====================================================
forecast = data["data"]['forecast'][0]
location = data["data"]['lokasi']

city = location["kota"]
lat = float(location["lat"])
lon = float(location["lon"])

# Ambil time index pertama
ti = forecast["timeIndex"][0]
local_dt = datetime.fromtimestamp(ti["local_datetime"])
hour = local_dt.hour

# Tentukan Day/Night Mode otomatis
mode = "Day Ops" if 6 <= hour < 18 else "Night Ops"

# Ambil parameter cuaca
wx = ti["weather_desc"]
t = ti["t"]
humid = ti["hu"]
wind = ti["ws"]


# =====================================================
# PANEL TACTICAL WEATHER STATUS
# =====================================================
st.subheader("🎯 Tactical Weather Status")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Mode", mode)
col2.metric("Temperature", f"{t}°C")
col3.metric("Humidity", f"{humid}%")
col4.metric("Wind Speed", f"{wind} m/s")


# =====================================================
# OPS MAP (ANTI ERROR)
# =====================================================
st.subheader("🗺️ Tactical Ops Map")

if folium_available:
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles="CartoDB Positron")

    folium.Marker(
        [lat, lon],
        tooltip=f"{city}",
        popup=f"Lokasi: {city}",
        icon=folium.Icon(color="green" if mode=="Day Ops" else "darkgreen")
    ).add_to(m)

    st_data = st_folium(m, width=900, height=500)

else:
    st.warning("⚠ Folium tidak tersedia di server. Aktifkan dengan menambahkannya ke `requirements.txt`:\n\n`folium\nbranca\nstreamlit_folium`")
    st.info(f"Lokasi: {city}\nLat: {lat}\nLon: {lon}")
    st.code("Map disabled — Folium not installed.", language="text")


# =====================================================
# RIWAYAT / RAW OUTPUT
# =====================================================
with st.expander("Raw Data BMKG"):
    st.json(data)
