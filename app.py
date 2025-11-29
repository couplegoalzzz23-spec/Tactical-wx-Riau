# =========================================================
# 🚀 TACTICAL WEATHER OPS — BMKG
# Full Dashboard + MET Report Printable
# =========================================================

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import numpy as np

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# BMKG Forecast API
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
@st.cache_data
def load_weather(kab):
    url = f"{API_BASE}/{kab}"
    r = requests.get(url, timeout=10)
    data = r.json()

    now = data["data"]["now"]
    fc = data["data"]["forecast"]

    df = pd.DataFrame(fc)
    df["jam"] = pd.to_datetime(df["jam"])
    df = df.sort_values("jam")

    df["ws_kt"] = df["ws"] * 1.94384  # m/s → kt

    return now, df


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
kab = st.sidebar.selectbox(
    "📍 Pilih Lokasi",
    ["kota_pekanbaru", "kab_kampar", "kab_pelalawan", "kab_siak"],
)

show_map = st.sidebar.checkbox("Tampilkan Map", False)
show_table = st.sidebar.checkbox("Tampilkan Data Tabel", False)

# ---------------------------------------------------------
# MAIN HEADER
# ---------------------------------------------------------
st.title("🛰 Tactical Weather Ops — BMKG")

now, df_sel = load_weather(kab)

loc_choice = kab.replace("_", " ").title()
use_col = "jam"

# ---------------------------------------------------------
# CURRENT CONDITION PANEL
# ---------------------------------------------------------
st.subheader(f"📡 Current Observation — {loc_choice}")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Temperature", f"{now['t']} °C")
c2.metric("Wind", f"{now['wd']}° / {round(now['ws']*1.9438)} KT")
c3.metric("Visibility", f"{now['vs']} m")
c4.metric("Cloud", now["tcc"])

st.markdown("---")

# ---------------------------------------------------------
# WINDROSE
# ---------------------------------------------------------
st.subheader("🧭 Windrose Forecast")

try:
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    from matplotlib.projections.polar import PolarAxes

    fig_wr = px.bar_polar(
        df_sel,
        r="ws_kt",
        theta="wd",
        color="ws_kt",
        title="Windrose"
    )
    st.plotly_chart(fig_wr, use_container_width=True)
except:
    st.warning("Windrose tidak tersedia (matplotlib tidak tersedia).")

st.markdown("---")

# ---------------------------------------------------------
# TRENDS
# ---------------------------------------------------------
st.subheader("📈 Hourly Weather Trends")

time_axis = df_sel[use_col]

# Temperature Trend
fig_temp = go.Figure()
fig_temp.add_trace(go.Scatter(
    x=time_axis, y=df_sel["t"], mode="lines+markers"
))
fig_temp.update_layout(title="Temperature (°C)", height=250)
st.plotly_chart(fig_temp, use_container_width=True)

# Wind Speed Trend
fig_ws = go.Figure()
fig_ws.add_trace(go.Scatter(
    x=time_axis, y=df_sel["ws_kt"], mode="lines+markers"
))
fig_ws.update_layout(title="Wind Speed (KT)", height=250)
st.plotly_chart(fig_ws, use_container_width=True)

# Visibility
fig_vs = go.Figure()
fig_vs.add_trace(go.Scatter(
    x=time_axis, y=df_sel["vs"], mode="lines+markers"
))
fig_vs.update_layout(title="Visibility (m)", height=250)
st.plotly_chart(fig_vs, use_container_width=True)

# Rainfall
fig_tp = go.Figure()
fig_tp.add_trace(go.Bar(
    x=time_axis, y=df_sel["tp"]
))
fig_tp.update_layout(title="Rainfall (mm)", height=250)
st.plotly_chart(fig_tp, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# MAP
# ---------------------------------------------------------
if show_map:
    st.subheader("🗺 Tactical Weather Map")

    try:
        lat = float(now.get("lat", 0))
        lon = float(now.get("lon", 0))

        fig_map = px.scatter_mapbox(
            pd.DataFrame([{"lat": lat, "lon": lon, "label": loc_choice}]),
            lat="lat",
            lon="lon",
            hover_name="label",
            zoom=7
        )
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            height=350,
        )
        st.plotly_chart(fig_map, use_container_width=True)
    except:
        st.warning("Map tidak dapat ditampilkan.")

# ---------------------------------------------------------
# RAW TABLE
# ---------------------------------------------------------
if show_table:
    st.subheader("📋 Raw Forecast Table")
    st.dataframe(df_sel, use_container_width=True, height=350)

st.markdown("---")

# =========================================================
# 📄 MET REPORT PRINTABLE (HTML → Save as PDF via browser)
# =========================================================
st.subheader("📄 MET REPORT — Printable Version")

# Auto-fill data
def deg_to_dir(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ix = int((deg + 22.5) // 45) % 8
    return dirs[ix]

wd_dir = deg_to_dir(now["wd"])
wind_txt = f"{wd_dir} / {round(now['ws']*1.9438)} KT"

temp_dp = f"{now['t']}°C / {now['t']}°C"
qnh = now.get("pressure", "-")

obs_time = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

# HTML Builder
def build_html():
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial;
                padding: 20px;
            }}
            h1 {{
                text-align:center;
                font-size: 20px;
            }}
            table {{
                width:100%;
                border-collapse: collapse;
                font-size: 14px;
            }}
            td {{
                border:1px solid black;
                padding:6px;
            }}
            .label {{
                background:#eee;
                font-weight:bold;
            }}
        </style>
    </head>
    <body>

    <h1>METEOROLOGICAL REPORT FOR TAKE OFF / LANDING</h1>

    <table>
        <tr><td class="label">Observation Time (UTC)</td><td>{obs_time}</td></tr>
        <tr><td class="label">Aerodrome</td><td>{loc_choice}</td></tr>
        <tr><td class="label">Wind</td><td>{wind_txt}</td></tr>
        <tr><td class="label">Visibility</td><td>{now['vs']} m</td></tr>
        <tr><td class="label">Cloud</td><td>{now["tcc"]}</td></tr>
        <tr><td class="label">Temp / Dew Point</td><td>{temp_dp}</td></tr>
        <tr><td class="label">QNH</td><td>{qnh}</td></tr>
    </table>

    </body>
    </html>
    """

html = build_html()
b64 = base64.b64encode(html.encode()).decode()

st.markdown(
    f"""
    <a href="data:text/html;base64,{b64}"
       download="MET_REPORT.html">
       📄 Download MET REPORT (HTML Printable)
    </a>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("Tactical Weather Ops — BMKG • Streamlit Version")
