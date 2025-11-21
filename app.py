import streamlit as st
import requests
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, BeautifyIcon
from streamlit_folium import st_folium

# ==========================
# CONFIGURASI STREAMLIT
# ==========================
st.set_page_config(page_title="Tactical Weather Riau", layout="wide")


# ==========================
# FUNGSI AMAN AMBIL DATA BMKG
# ==========================
@st.cache_data(ttl=900)
def load_bmkg(adm="Riau"):
    url = f"https://cuaca.bmkg.go.id/api/df/v1/forecast/adm?adm={adm}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data["data"])
        return df
    except:
        return pd.DataFrame()


# ==========================
# VALIDASI DATA
# ==========================
df = load_bmkg("Riau")

if df.empty:
    st.error("Data BMKG tidak tersedia.")
    st.stop()

# Convert ke numeric jika ada
for col in ["t", "hu", "ws", "wd", "tp"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Drop baris tidak valid
df = df.dropna(subset=["lat", "lon"])


# ==========================
# FUNGSI LAYER WIND ARROWS
# ==========================
def add_wind_arrows(m, df):
    for _, row in df.iterrows():
        if pd.isna(row["ws"]) or pd.isna(row["wd"]):
            continue

        u = -row["ws"] * np.sin(np.radians(row["wd"]))
        v = -row["ws"] * np.cos(np.radians(row["wd"]))

        folium.RegularPolygonMarker(
            location=[row["lat"], row["lon"]],
            number_of_sides=3,
            radius=6,
            rotation=row["wd"],
            color="blue",
            fill=True,
            fill_color="blue"
        ).add_to(m)


# ==========================
# FUNGSI LAYER HEATMAP SUHU
# ==========================
def add_temperature_heatmap(m, df):
    if "t" not in df.columns:
        return

    heat_data = df[["lat", "lon", "t"]].dropna().values.tolist()
    if len(heat_data) > 5:
        HeatMap(heat_data, radius=25, blur=15, max_zoom=8).add_to(m)


# ==========================
# FUNGSI LAYER CURAH HUJAN (CHOROPLETH)
# ==========================
def add_rain_choropleth(m, df):
    for _, row in df.iterrows():
        if pd.isna(row["tp"]):
            continue

        val = float(row["tp"])

        if val == 0:
            color = "#d0f0ff"
        elif val < 5:
            color = "#80d0ff"
        elif val < 20:
            color = "#4090ff"
        else:
            color = "#0040ff"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
        ).add_to(m)


# ==========================
# FUNGSI CLOUD SHADING
# ==========================
def add_cloud_shading(m, df):
    if "tcc" not in df.columns:
        return

    for _, row in df.iterrows():
        if pd.isna(row["tcc"]):
            continue

        alpha = min(max(row["tcc"] / 100, 0.1), 0.8)

        folium.Circle(
            radius=20000,
            location=[row["lat"], row["lon"]],
            color=None,
            fill=True,
            fill_opacity=alpha,
            fill_color="gray"
        ).add_to(m)


# ==========================
# FUNGSI STATION MARKERS
# ==========================
def add_station_markers(m, df):
    for _, row in df.iterrows():
        popup = f"""
        <b>{row.get('lokasi','')}</b><br>
        Suhu: {row.get('t','-')}°C <br>
        Angin: {row.get('ws','-')} m/s <br>
        Arah: {row.get('wd','-')}° <br>
        Hujan: {row.get('tp','-')} mm
        """

        folium.Marker(
            [row["lat"], row["lon"]],
            popup=popup,
            icon=BeautifyIcon(
                icon="cloud",
                border_color="blue",
                text_color="white",
                background_color="blue"
            )
        ).add_to(m)



# ==========================
# MENU LAYER
# ==========================
layer_options = [
    "Wind Arrows",
    "Temperature Heatmap",
    "Rainfall Choropleth",
    "Cloud Shading",
    "Weather Stations"
]

selected_layers = st.sidebar.multiselect(
    "Pilih Map Layers:",
    layer_options,
    default=["Weather Stations"]
)

# ==========================
# BANGUN PETA
# ==========================
center = [df["lat"].mean(), df["lon"].mean()]
m = folium.Map(location=center, zoom_start=7)

# Tambahkan layer sesuai pilihan user
if "Wind Arrows" in selected_layers:
    add_wind_arrows(m, df)

if "Temperature Heatmap" in selected_layers:
    add_temperature_heatmap(m, df)

if "Rainfall Choropleth" in selected_layers:
    add_rain_choropleth(m, df)

if "Cloud Shading" in selected_layers:
    add_cloud_shading(m, df)

if "Weather Stations" in selected_layers:
    add_station_markers(m, df)

# Tampilkan peta
st_folium(m, width=1250, height=600)

