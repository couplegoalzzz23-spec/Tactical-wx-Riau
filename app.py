############################################################
#  PILOT-GRADE TACTICAL WEATHER OPS — FINAL v3 (NO ERROR)  #
#  ✔ Fix runway 04 leading zero                             #
#  ✔ Auto-fallback dummy data jika API gagal                #
#  ✔ Semua panel tetap berfungsi tanpa internet            #
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
# ⚙️ PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Pilot-Grade Tactical Weather Ops",
    layout="wide"
)


# =========================================================
# 🎨 CSS — AVIONICS STYLE
# =========================================================
st.markdown("""
<style>
body { background-color:#0b0f19; color:#e8e8e8; }
.metric-box {
    background:rgba(255,255,255,0.06);
    padding:14px 20px;
    border-radius:12px;
    border:1px solid rgba(255,255,255,0.1);
    margin-bottom:8px;
}
.big { font-size:28px; font-weight:700; }
.med { font-size:20px; font-weight:600; }
.small { font-size:14px; opacity:0.75; }
.section-title { font-size:24px; margin-top:20px; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 📡 DATA LOADER (AUTO FALLBACK)
# =========================================================
@st.cache_data(ttl=300)
def load_data(url):
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        return df, False
    except:
        # ---------- FALLBACK DUMMY WEATHER DATA ----------
        t0 = datetime.utcnow()
        times = [t0 - timedelta(minutes=10*i) for i in range(20)][::-1]

        df = pd.DataFrame({
            "time": times,
            "t": np.random.uniform(25, 32, 20),
            "rh": np.random.uniform(60, 95, 20),
            "ws": np.random.uniform(2, 18, 20),
            "wd": np.random.uniform(0, 360, 20),
            "vis": np.random.uniform(4, 10, 20),
            "pres": np.random.uniform(1007, 1014, 20),
            "rain": np.random.uniform(0, 5, 20),
            "cloud_base": np.random.uniform(1500, 4000, 20)
        })

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

        return df, True


# =========================================================
# ✈️ RUNWAY WIND COMPONENT
# =========================================================
def compute_wind_components(ws, wd, runway_heading):
    try:
        angle_diff = math.radians(wd - runway_heading)
        hw = ws * math.cos(angle_diff)
        xw = ws * math.sin(angle_diff)
        return hw, xw
    except:
        return None, None


# =========================================================
# ✈️ FLIGHT CATEGORY (ICAO)
# =========================================================
def flight_category(vis, ceiling):
    if vis >= 8 and ceiling >= 3000:
        return "VFR", "green"
    if (vis >= 3 and vis < 8) or (ceiling >= 1000 and ceiling < 3000):
        return "MVFR", "yellow"
    if (vis >= 1 and vis < 3) or (ceiling >= 500 and ceiling < 1000):
        return "IFR", "orange"
    return "LIFR", "red"


# =========================================================
# ✈️ METAR Style Generator
# =========================================================
def generate_metar(last):
    try:
        t = last["t"]
        td = t - ((100 - last["rh"]) / 5)
        ws = int(last["ws"])
        wd = int(last["wd"])
        vis = int(last["vis"] * 1000)
        pres = int(last["pres"])

        return f"METAR XXXX {last.name:%d%H%M}Z {wd:03d}{ws:02d}KT {vis} {pres}"
    except:
        return "METAR unavailable"


# =========================================================
# 🟦 Pilot Snapshot Panel
# =========================================================
def pilot_panel(df):
    last = df.iloc[-1]

    st.markdown("### ✈️ Pilot Weather Snapshot")

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(
        f"<div class='metric-box'><div class='med'>Temp</div><div class='big'>{last['t']:.1f}°C</div></div>",
        unsafe_allow_html=True)

    c2.markdown(
        f"<div class='metric-box'><div class='med'>Humidity</div><div class='big'>{last['rh']:.0f}%</div></div>",
        unsafe_allow_html=True)

    c3.markdown(
        f"<div class='metric-box'><div class='med'>Visibility</div><div class='big'>{last['vis']:.1f} km</div></div>",
        unsafe_allow_html=True)

    c4.markdown(
        f"<div class='metric-box'><div class='med'>Pressure</div><div class='big'>{last['pres']:.0f} hPa</div></div>",
        unsafe_allow_html=True)


# =========================================================
# 🛫 Runway Wind Component
# =========================================================
def runway_panel(df, runway_heading):
    last = df.iloc[-1]

    ws = last["ws"]
    wd = last["wd"]
    hw, xw = compute_wind_components(ws, wd, runway_heading)

    ws_display = f"{ws:.1f}"
    wd_display = f"{wd:.0f}"
    hw_display = f"{hw:.1f} KT"
    xw_display = f"{abs(xw):.1f} KT"

    st.markdown("### 🛫 Runway Wind Component")

    st.markdown(
        f"""
        <div class='metric-box'>
            <div class='med'>Wind</div>
            <div class='big'>{ws_display} KT @ {wd_display}°</div>
            <div class='small'>Runway {runway_heading} → HW {hw_display}, XW {xw_display}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 🟢 Flight Category
# =========================================================
def flight_status(df):
    last = df.iloc[-1]
    ceiling = last["cloud_base"]

    category, color = flight_category(last["vis"], ceiling)

    st.markdown("### 🟢 Flight Category")

    st.markdown(
        f"""
        <div class='metric-box' style='border-left:6px solid {color};'>
            <div class='big'>{category}</div>
            <div class='small'>Visibility: {last['vis']} km — Ceiling: {ceiling:.0f} ft</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 🚨 Alert System
# =========================================================
def alert_panel(df):
    last = df.iloc[-1]
    alerts = []

    if last["ws"] >= 25:
        alerts.append("💨 Strong Wind ≥ 25 KT")
    if last["vis"] <= 3:
        alerts.append("🌫️ Low Visibility ≤ 3 km")
    if last["rain"] >= 10:
        alerts.append("🌧️ Heavy Rain ≥ 10 mm")
    if last["pres"] <= 1005:
        alerts.append("📉 Low Pressure ≤ 1005 hPa")

    st.markdown("### 🚨 Alerts")

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("No active alerts.")


# =========================================================
# 📈 Trends Panel
# =========================================================
def trends(df):
    st.markdown("### 📈 Weather Trends")

    c1, c2 = st.columns(2)

    c1.plotly_chart(px.line(df, y="t", title="Temperature (°C)"), use_container_width=True)
    c2.plotly_chart(px.line(df, y="ws", title="Wind Speed (KT)"), use_container_width=True)


# =========================================================
# 📘 QAM Report
# =========================================================
def qam_report(df):
    last = df.iloc[-1]

    rep = f"""
QAM-MET REPORT
Time: {last.name}

Temp     : {last['t']:.1f} °C
Humidity : {last['rh']:.0f} %
Wind     : {last['ws']:.1f} KT ({last['wd']:.0f}°)
Vis      : {last['vis']:.1f} km
Pressure : {last['pres']:.0f} hPa
Rain     : {last['rain']:.1f} mm
Cloud Base : {last['cloud_base']:.0f} ft
"""

    st.markdown("### 📘 QAM MET Report")
    st.code(rep)


# =========================================================
# 🗺️ Tactical Map
# =========================================================
def tactical_map(df):
    st.markdown("### 🗺️ Tactical Map")

    df_map = df.copy()
    df_map["lat"] = -6.25
    df_map["lon"] = 106.85

    fig = px.scatter_mapbox(
        df_map.iloc[-1:],
        lat="lat",
        lon="lon",
        size="ws",
        color="ws",
        zoom=6,
        height=450,
        color_continuous_scale="Viridis"
    )
    fig.update_layout(mapbox_style="carto-darkmatter")
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Settings")

api_url = st.sidebar.text_input("API URL:", "https://invalid-url-for-fallback.com/data")

# FIX: runway list — NO LEADING ZERO
runway = st.sidebar.selectbox("Runway Heading", [4, 13, 22, 31], index=1)

hours = st.sidebar.slider("Last hours", 3, 48, 12)


# =========================================================
# LOAD DATA (WITH FALLBACK)
# =========================================================
df, using_dummy = load_data(api_url)

if using_dummy:
    st.sidebar.warning("⚠ API tidak dapat diakses → menggunakan dummy data.")
else:
    st.sidebar.success("✔ Data real dari API")


df_sel = df[df.index >= df.index.max() - timedelta(hours=hours)]


# =========================================================
# MAIN PAGE
# =========================================================
st.title("🛩️ Pilot-Grade Tactical Weather Dashboard — v3")

pilot_panel(df_sel)
runway_panel(df_sel, runway)
flight_status(df_sel)
alert_panel(df_sel)
trends(df_sel)
tactical_map(df_sel)
qam_report(df_sel)
