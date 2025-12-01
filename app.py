############################################################
#  TACTICAL WEATHER OPS - ORIGINAL SCRIPT (PRESERVED)
#  + NATO FIGHTER PILOT PANEL (ADD-ON)
############################################################

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Tactical Weather Ops", layout="wide")

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
body {
    background-color: #0b0f19;
    color: #f0f0f0;
}
.metric-box {
    background: rgba(255,255,255,0.06);
    padding: 12px 18px;
    border-radius: 12px;
    margin-bottom: 10px;
    border: 1px solid rgba(255,255,255,0.1);
}
.metric-label {
    font-size: 18px;
    opacity: 0.8;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
}
.detail-value {
    font-size: 20px;
    font-weight: 600;
}
.section-title {
    font-size: 24px;
    font-weight: bold;
    margin-top: 25px;
}
.small {
    opacity: 0.7;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# DATA LOADER (PRESERVED)
# =========================================================
@st.cache_data(ttl=300)
def load_data(url):
    try:
        res = requests.get(url, timeout=5)
        data = pd.DataFrame(res.json())
        data['time'] = pd.to_datetime(data['time'])
        data = data.set_index('time')
        return data, False
    except:
        # Fallback dummy data
        now = datetime.utcnow()
        idx = [now - timedelta(minutes=i*10) for i in range(24)]
        df = pd.DataFrame({
            "time": idx,
            "t": np.random.uniform(24, 33, len(idx)),
            "rh": np.random.uniform(55, 95, len(idx)),
            "ws": np.random.uniform(2, 20, len(idx)),
            "wd": np.random.uniform(0, 360, len(idx)),
            "vis": np.random.uniform(3, 10, len(idx)),
            "pres": np.random.uniform(1005, 1014, len(idx)),
            "rain": np.random.uniform(0, 8, len(idx)),
            "cloud_base": np.random.uniform(800, 3500, len(idx)),
        })

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

        return df, True


# =========================================================
# UTILITY FUNCTIONS (PRESERVED)
# =========================================================
def compute_wind_components(ws, wd, rwy_heading):
    try:
        angle_diff = math.radians(wd - rwy_heading)
        hw = ws * math.cos(angle_diff)
        xw = ws * math.sin(angle_diff)
        return hw, xw
    except:
        return None, None


def flight_category(vis, ceiling):
    if vis >= 8 and ceiling >= 3000:
        return "VFR", "green"
    if vis >= 5 and ceiling >= 1500:
        return "MVFR", "yellow"
    if vis >= 3 and ceiling >= 800:
        return "IFR", "orange"
    return "LIFR", "red"


# =========================================================
# SIDEBAR (ORIGINAL PRESERVED)
# =========================================================
st.sidebar.title("Settings")

api_url = st.sidebar.text_input(
    "API URL",
    "https://invalid-url-for-fallback.com/data"
)

runway = st.sidebar.selectbox("Runway Heading", [4, 13, 22, 31], index=1)

hours = st.sidebar.slider("Data Range (hours)", 3, 48, 12)


# =========================================================
# LOAD DATA
# =========================================================
df, dummy = load_data(api_url)

if dummy:
    st.sidebar.warning("⚠ API tidak dapat diakses — menggunakan dummy data.")
else:
    st.sidebar.success("✔ Data dari API berhasil dimuat")

df_sel = df[df.index >= df.index.max() - timedelta(hours=hours)]
last = df_sel.iloc[-1]


# =========================================================
# MAIN TITLE
# =========================================================
st.title("🛩️ Tactical Weather Ops Dashboard")


# =========================================================
# PILOT SNAPSHOT (ORIGINAL PRESERVED)
# =========================================================
col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"""
<div class='metric-box'>
    <div class='metric-label'>Temperature</div>
    <div class='metric-value'>{last['t']:.1f} °C</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class='metric-box'>
    <div class='metric-label'>Humidity</div>
    <div class='metric-value'>{last['rh']:.0f} %</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class='metric-box'>
    <div class='metric-label'>Visibility</div>
    <div class='metric-value'>{last['vis']:.1f} km</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div class='metric-box'>
    <div class='metric-label'>Pressure</div>
    <div class='metric-value'>{last['pres']:.0f} hPa</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# METEOROLOGICAL DETAILS (ORIGINAL PRESERVED)
# =========================================================
st.markdown("## 🌦️ Meteorological Details")

dewpt = last['t'] - (100 - last['rh'])/5
dewpt_disp = f"{dewpt:.1f} °C"

col_t, col_rh, col_dp = st.columns(3)

col_t.metric("Temperature", f"{last['t']:.1f} °C")
col_rh.metric("Humidity", f"{last['rh']:.0f} %")
col_dp.metric("Dew Point (Est.)", dewpt_disp)


# =========================================================
# RUNWAY WIND COMPONENT (ORIGINAL PRESERVED)
# =========================================================
hw, xw = compute_wind_components(last["ws"], last["wd"], runway)

st.markdown("## 🛫 Runway Wind Component")

st.markdown(f"""
<div class='metric-box'>
    <div class='metric-label'>Wind</div>
    <div class='metric-value'>{last['ws']:.1f} KT @ {last['wd']:.0f}°</div>
    <div class='small'>Runway {runway}: HW {hw:.1f} KT — XW {abs(xw):.1f} KT</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# FLIGHT CATEGORY (ORIGINAL PRESERVED)
# =========================================================
cat, color = flight_category(last['vis'], last['cloud_base'])

st.markdown(f"""
## 🟢 Flight Category
<div class='metric-box' style="border-left: 6px solid {color};">
    <div class='metric-value'>{cat}</div>
    <div class='small'>Visibility {last['vis']:.1f} km — Ceiling {last['cloud_base']:.0f} ft</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# ALERT SYSTEM (ORIGINAL PRESERVED)
# =========================================================
st.markdown("## 🚨 Alerts")

alerts = []
if last["ws"] >= 25: alerts.append("💨 Strong Wind ≥ 25 KT")
if last["vis"] <= 3: alerts.append("🌫 Low Visibility ≤ 3 km")
if last["rain"] >= 10: alerts.append("🌧 Heavy Rain ≥ 10 mm")
if last["pres"] <= 1005: alerts.append("📉 Low Pressure ≤ 1005 hPa")

if alerts:
    for a in alerts:
        st.error(a)
else:
    st.success("No active alerts.")


# =========================================================
# TRENDS (ORIGINAL PRESERVED)
# =========================================================
st.markdown("## 📈 Trends")

c1, c2 = st.columns(2)
c1.plotly_chart(px.line(df_sel, y="t", title="Temperature"), use_container_width=True)
c2.plotly_chart(px.line(df_sel, y="ws", title="Wind Speed"), use_container_width=True)


# =========================================================
# QAM REPORT (ORIGINAL PRESERVED)
# =========================================================
st.markdown("## 📘 QAM Report")

st.code(f"""
Time: {last.name}
Temp       : {last['t']:.1f} °C
Humidity   : {last['rh']:.0f} %
Wind       : {last['ws']:.1f} KT ({last['wd']:.0f}°)
Visibility : {last['vis']:.1f} km
Pressure   : {last['pres']:.0f} hPa
Rainfall   : {last['rain']:.1f} mm
Ceiling    : {last['cloud_base']:.0f} ft
""")

# =========================================================
# TACTICAL MAP (ORIGINAL PRESERVED)
# =========================================================
st.markdown("## 🗺 Tactical Map")

df_map = df_sel.copy()
df_map["lat"] = -6.25
df_map["lon"] = 106.85

fig = px.scatter_mapbox(
    df_map.iloc[-1:],
    lat="lat",
    lon="lon",
    size="ws",
    color="ws",
    zoom=6,
    color_continuous_scale="Turbo",
    height=400
)

fig.update_layout(mapbox_style="carto-darkmatter")
st.plotly_chart(fig, use_container_width=True)


# =========================================================
# 🔵 NATO FIGHTER PILOT WEATHER BLOCK (ADD-ON)
# =========================================================
def nato_fighter_block(df):
    last = df.iloc[-1]

    temp = last["t"]
    rh = last["rh"]
    vis = last["vis"]
    ws = last["ws"]
    wd = last["wd"]
    pres = last["pres"]
    rain = last["rain"]
    ceiling = last["cloud_base"]

    # Dew point
    dewpt = temp - (100 - rh)/5

    # Gust / windshear indicator
    gust_factor = ws * 0.15
    windshear_risk = "HIGH" if gust_factor >= 10 else ("MOD" if gust_factor >= 5 else "LOW")

    # Convective indicator
    cb_risk = "POSSIBLE" if rain >= 5 else "LOW"

    # Visibility class
    if vis >= 8: vis_class = "VFR (Green)"
    elif vis >= 5: vis_class = "MVFR (Amber)"
    elif vis >= 3: vis_class = "IFR (Red)"
    else: vis_class = "LIFR (Red/Black)"

    # GO / NO-GO logic
    nogo = []
    if vis < 5: nogo.append("Visibility")
    if ceiling < 1200: nogo.append("Ceiling")
    if ws >= 25: nogo.append("Strong Wind")
    if cb_risk == "POSSIBLE": nogo.append("Convective Activity")
    if windshear_risk == "HIGH": nogo.append("Windshear")

    mission_status = "NO-GO" if len(nogo) >= 2 else ("MARGINAL" if len(nogo) >= 1 else "GO")
    status_color = "red" if mission_status == "NO-GO" else ("orange" if mission_status == "MARGINAL" else "lightgreen")

    # Render block
    st.markdown("## 🔵 NATO Fighter Pilot Block")
    st.markdown(f"""
    <div style="
        background:#0d1117;
        padding:20px;
        border-radius:14px;
        border:1px solid #334155;
    ">
    <h3 style="margin-top:0;">Mission Status: 
        <span style="color:{status_color};">{mission_status}</span>
    </h3>

    <b>● Visibility:</b> {vis:.1f} km — <i>{vis_class}</i><br>
    <b>● Ceiling:</b> {ceiling:.0f} ft<br>
    <b>● Wind:</b> {ws:.1f} KT @ {wd:.0f}°<br>
    <b>● Pressure:</b> {pres:.0f} hPa<br>
    <b>● Temp / DP:</b> {temp:.1f}°C / {dewpt:.1f}°C<br>

    <hr style="opacity:0.25;">

    <b>Threat Indicators:</b><br>
    - Windshear Risk: <b>{windshear_risk}</b><br>
    - Gust Factor: {gust_factor:.1f} KT<br>
    - CB / Convective Index: <b>{cb_risk}</b><br>
    - Rainfall: {rain:.1f} mm<br>

    <hr style="opacity:0.25;">

    <b>No-Go Factors:</b><br>
    {"None" if len(nogo)==0 else ", ".join(nogo)}
    </div>
    """, unsafe_allow_html=True)


# RENDER NATO PANEL
nato_fighter_block(df_sel)

