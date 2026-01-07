# =========================================================
# 🛰 Tactical Weather Ops — BMKG
# STABLE • STREAMLIT CLOUD SAFE • FINAL
# =========================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
body {
    background:#0b0c0c;
    color:#cfd2c3;
    font-family:Consolas, monospace;
}
h1,h2,h3 {
    color:#a9df52;
}
section[data-testid="stSidebar"] {
    background:#111;
}
hr {
    border-top:1px solid #2f3a2f;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# API CONFIG
# =========================================================
API = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    r = requests.get(API, params={"adm1": adm1}, timeout=10)
    r.raise_for_status()
    return r.json()

def flatten_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            d = obs.copy()
            d.update(lokasi)
            d["time"] = pd.to_datetime(d.get("local_datetime"), errors="coerce")
            rows.append(d)

    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","wd_deg","vs","tp"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["ws_kt"] = df["ws"] * MS_TO_KT
    return df

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm1 = st.text_input("ADM1 (Province Code)", value="32")
    show_table = st.checkbox("Show Table", False)

# =========================================================
# LOAD DATA
# =========================================================
st.title("🛰 Tactical Weather Ops — BMKG")
st.caption("Source: BMKG Forecast API")

with st.spinner("Acquiring BMKG data..."):
    raw = fetch_forecast(adm1)

entries = raw.get("data", [])
if not entries:
    st.error("No BMKG data returned.")
    st.stop()

locations = {
    e.get("lokasi", {}).get("kotkab", f"Location {i+1}"): e
    for i, e in enumerate(entries)
    if "lokasi" in e
}

loc_choice = st.selectbox("Select Location", list(locations.keys()))
df = flatten_entry(locations[loc_choice])

if df.empty:
    st.error("No valid weather data.")
    st.stop()

df = df.sort_values("time")
now = df.iloc[0]

# =========================================================
# METRICS
# =========================================================
c1,c2,c3,c4 = st.columns(4)
c1.metric("Temperature (°C)", now.get("t","—"))
c2.metric("RH (%)", now.get("hu","—"))
c3.metric("Wind (KT)", f"{now.get('ws_kt',0):.1f}")
c4.metric("Visibility (m)", now.get("vs","—"))

# =========================================================
# TRENDS (SAFE)
# =========================================================
st.subheader("📊 Weather Trends")

try:
    st.plotly_chart(px.line(df, x="time", y="t", title="Temperature (°C)"), use_container_width=True)
    st.plotly_chart(px.line(df, x="time", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)
    st.plotly_chart(px.bar(df, x="time", y="tp", title="Rainfall (mm)"), use_container_width=True)
except Exception:
    st.warning("Trend charts unavailable due to data format.")

# =========================================================
# MAP (SAFE)
# =========================================================
try:
    st.subheader("🗺 Location Map")
    st.map(pd.DataFrame({
        "lat": [now["lat"]],
        "lon": [now["lon"]]
    }))
except Exception:
    st.info("Map unavailable.")

# =========================================================
# 🛰 SATELLITE & RADAR (FIXED - NO MORE '0')
# =========================================================
st.markdown("---")
st.subheader("🛰️ Satellite & Radar Imagery (Reference Only)")

st.warning("""
**Operational Notice**  
Satellite imagery is provided for **situational awareness only**.  
Tactical decisions must rely on **METAR / TAF / Radar / ATC clearance**.
""")

tab1, tab2 = st.tabs(["🌑 Himawari-8 IR", "🌧 Radar BMKG"])

with tab1:
    st.caption("Himawari-8 Infrared — Cloud Top Temperature")
    st.markdown("""
    <iframe
        src="https://inderaja.bmkg.go.id/"
        width="100%"
        height="520"
        style="border:none;">
    </iframe>
    """, unsafe_allow_html=True)

with tab2:
    st.caption("BMKG Weather Radar (Composite)")
    st.markdown("""
    <iframe
        src="https://www.bmkg.go.id/cuaca/radar-cuaca.bmkg"
        width="100%"
        height="520"
        style="border:none;">
    </iframe>
    """, unsafe_allow_html=True)

# =========================================================
# TABLE
# =========================================================
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table")
    st.dataframe(df)

# =========================================================
# FOOTER
# =========================================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG<br>
Reference Only · Streamlit Stable Build
</div>
""", unsafe_allow_html=True)
