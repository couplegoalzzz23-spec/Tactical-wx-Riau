############################################################
#  TACTICAL WEATHER OPS — PILOT GRADE VERSION (FINAL)      #
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
# 🎨 CSS – AVIONICS STYLE
# =========================================================
st.markdown("""
<style>
body { background-color:#0b0f19; color:#e8e8e8; }
.metric-box {
    background:rgba(255,255,255,0.05);
    padding:12px 18px;
    border-radius:12px;
    border:1px solid rgba(255,255,255,0.08);
    margin-bottom:6px;
}
.big { font-size:28px; font-weight:700; }
.med { font-size:20px; font-weight:600; }
.small { font-size:14px; opacity:0.75; }
.section-title { font-size:24px; margin-top:20px; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 📡 DATA LOADER
# =========================================================
@st.cache_data(ttl=300)
def load_data(url):
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        return df
    except:
        st.error("Gagal memuat data dari API!")
        return pd.DataFrame()


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
# ✈️ METAR STYLE GENERATOR
# =========================================================
def generate_metar(last):
    try:
        t = last["t"]
        td = t - ((100 - last["rh"]) / 5)  # simple dewpoint approx
        ws = int(last["ws"])
        wd = int(last["wd"])
        vis = int(last["vis"] * 1000)
        pres = int(last["pres"])

        return f"METAR XXXX {last.name:%d%H%M}Z {wd:03d}{ws:02d}KT {vis} {pres}"
    except:
        return "METAR data unavailable"


# =========================================================
# ✈️ PILOT QUICK PANEL
# =========================================================
def pilot_panel(df):
    last = df.iloc[-1]

    st.markdown("### ✈️ Pilot Weather Snapshot")

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f"""
        <div class='metric-box'>
        <div class='med'>Temperature</div>
        <div class='big'>{last['t']:.1f}°C</div>
        </div>
    """, unsafe_allow_html=True)

    c2.markdown(f"""
        <div class='metric-box'>
        <div class='med'>Humidity</div>
        <div class='big'>{last['rh']:.0f}%</div>
        </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
        <div class='metric-box'>
        <div class='med'>Visibility</div>
        <div class='big'>{last['vis']:.1f} km</div>
        </div>
    """, unsafe_allow_html=True)

    c4.markdown(f"""
        <div class='metric-box'>
        <div class='med'>Pressure</div>
        <div class='big'>{last['pres']:.0f} hPa</div>
        </div>
    """, unsafe_allow_html=True)


# =========================================================
# ✈️ RUNWAY WIND COMPONENT PANEL
# =========================================================
def runway_panel(df, runway_heading):
    last = df.iloc[-1]
    ws = last["ws"]
    wd = last["wd"]

    hw, xw = compute_wind_components(ws, wd, runway_heading)

    ws_display = f"{ws:.1f}" if not pd.isna(ws) else "—"
    wd_display = f"{wd:.0f}" if not pd.isna(wd) else "—"
    hw_display = f"{hw:.1f} KT" if hw is not None else "—"
    xw_display = f"{abs(xw):.1f} KT" if xw is not None else "—"

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
# ✈️ FLIGHT CATEGORY PANEL
# =========================================================
def flight_status(df):
    last = df.iloc[-1]

    ceiling = last["cloud_base"] if "cloud_base" in df.columns else 3000
    category, color = flight_category(last["vis"], ceiling)

    st.markdown("### 🟢 Flight Category")

    st.markdown(
        f"""
        <div class='metric-box' style='border-left:6px solid {color};'>
        <div class='big'>{category}</div>
        <div class='small'>Visibility: {last['vis']} km — Ceiling: {ceiling} ft</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 📈 WEATHER TRENDS PANEL
# =========================================================
def trends(df):
    st.markdown("### 📈 Weather Trends")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.line(df, y="t", title="Temperature (°C)"), use_container_width=True)
    with c2:
        st.plotly_chart(px.line(df, y="ws", title="Wind Speed (KT)"), use_container_width=True)


# =========================================================
# 🚨 ALERT SYSTEM
# =========================================================
def alert_panel(df):
    last = df.iloc[-1]
    alerts = []

    if last["ws"] >= 25:
        alerts.append("💨 Strong Wind Warning ≥ 25 KT")
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
        st.success("No active weather alerts.")


# =========================================================
# 📘 QAM MET REPORT
# =========================================================
def qam_report(df):
    last = df.iloc[-1]

    rep = f"""
QAM-MET REPORT
Time: {last.name}

Temp     : {last['t']} °C
Humidity : {last['rh']} %
Wind     : {last['ws']} KT ({last['wd']}°)
Vis      : {last['vis']} km
Pressure : {last['pres']} hPa
Rain     : {last['rain']} mm
    """

    st.markdown("### 📘 QAM MET Report")
    st.code(rep)


# =========================================================
# 🗺️ TACTICAL MAP (OPTIONAL)
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
        color="ws",
        size="ws",
        zoom=5,
        height=450,
        color_continuous_scale="viridis"
    )
    fig.update_layout(mapbox_style="carto-darkmatter")

    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Settings")
api_url = st.sidebar.text_input("API URL:", "https://sample-api/cuaca")

runway = st.sidebar.selectbox("Runway Heading", [13, 31, 22, 04], index=0)

hours = st.sidebar.slider("Last hours", 3, 48, 12)


# =========================================================
# LOAD DATA
# =========================================================
df = load_data(api_url)
if df.empty:
    st.stop()

df_sel = df[df.index >= df.index.max() - timedelta(hours=hours)]


# =========================================================
# MAIN PAGE
# =========================================================
st.title("🛩️ Pilot-Grade Tactical Weather Dashboard")

pilot_panel(df_sel)
runway_panel(df_sel, runway)
flight_status(df_sel)
alert_panel(df_sel)
trends(df_sel)
tactical_map(df_sel)
qam_report(df_sel)
