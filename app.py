import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import math
import folium
from streamlit_folium import st_folium

# =====================================
# ⚙️ DAY/NIGHT OPS MODE
# =====================================
def get_ops_mode():
    hour = datetime.now().hour
    return "DAY MODE" if 6 <= hour < 18 else "NIGHT MODE"

# =====================================
# 🌡️ HITUNG DEW POINT
# =====================================
def calc_dew_point(temp_c, rh):
    a, b = 17.27, 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + np.log(rh/100)
    return (b * alpha) / (a - alpha)

# =====================================
# 🌡️ HITUNG HEAT INDEX
# =====================================
def calc_heat_index(temp_c, rh):
    T = temp_c
    R = rh
    HI = -8.784695 + 1.61139411*T + 2.338549*R - 0.14611605*T*R
    return HI

# =====================================
# 👁️ VISIBILITY RATING
# =====================================
def visibility_rating(km):
    if km >= 10: return "Excellent"
    if km >= 5: return "Good"
    if km >= 2: return "Moderate"
    return "Poor"

# =====================================
# 🛰️ TACTICAL WEATHER STATUS (1-hour ahead)
# =====================================
def get_tactical_status(df):
    now = datetime.now()
    target = now + timedelta(hours=1)
    row = df.iloc[0]

    status = {
        "time": target.strftime('%H:%M'),
        "temp": row['temp'],
        "humidity": row['humidity'],
        "wind": row['wind'],
        "visibility": row['visibility'],
        "dew_point": calc_dew_point(row['temp'], row['humidity']),
        "heat_index": calc_heat_index(row['temp'], row['humidity']),
        "vis_rate": visibility_rating(row['visibility'])
    }
    return status

# =====================================
# 🗺️ PREMIUM OPS MAP (FOLIUM)
# =====================================
def draw_ops_map(lat, lon, wind_dir):
    m = folium.Map(location=[lat, lon], zoom_start=11)
    folium.Marker([lat, lon], tooltip="Ops Location").add_to(m)
    folium.Circle([lat, lon], radius=5000, fill=True, color="blue", fill_opacity=0.2).add_to(m)
    return m

# =====================================
# 🚀 UI START
# =====================================
st.title("Tactical Weather Dashboard — Premium Edition")

ops_mode = get_ops_mode()
st.subheader(f"🌓 Operational Mode: **{ops_mode}**")

# ===== Dummy weather data =====
data = pd.DataFrame({
    "temp": [31],
    "humidity": [70],
    "wind": [12],
    "visibility": [8]
})

status = get_tactical_status(data)
st.markdown(f"### Tactical Weather Status — {status['time']}")

col1, col2, col3 = st.columns(3)
col1.metric("Temperature", f"{status['temp']}°C")
col1.metric("Dew Point", f"{status['dew_point']:.1f}°C")

col2.metric("Humidity", f"{status['humidity']}%")
col2.metric("Heat Index", f"{status['heat_index']:.1f}°C")

col3.metric("Visibility", f"{status['visibility']} km")
col3.metric("Rating", status['vis_rate'])

# Map
st.subheader("🗺️ Ops Map — Premium Folium View")
map_obj = draw_ops_map(-6.2, 106.8, 90)
st_folium(map_obj, width=700, height=500)
