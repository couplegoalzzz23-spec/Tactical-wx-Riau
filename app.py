# =========================================================
# 🛰 Tactical Weather Ops Dashboard — BMKG
# FINAL STABLE VERSION (STREAMLIT CLOUD SAFE)
# =========================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# ⚙️ PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    layout="wide"
)

# =========================================================
# 🎨 CSS — TACTICAL DARK
# =========================================================
st.markdown("""
<style>
body { background:#0b0c0c; color:#cfd2c3; font-family:Consolas, monospace; }
h1,h2,h3 { color:#a9df52; }
section[data-testid="stSidebar"] { background:#111; }
.metric { background:#111; padding:16px; border-radius:10px; border:1px solid #2f3a2f; }
.badge-ok { background:#b6ff6d; color:#002b00; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-warn { background:#ffd86b; color:#4a3b00; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-no { background:#ff6b6b; color:#2b0000; padding:4px 8px; border-radius:6px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 📡 API CONFIG
# =========================================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# =========================================================
# 📡 FETCH DATA (ASLI — TIDAK DIUBAH)
# =========================================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    r = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
    r.raise_for_status()
    return r.json()

def flatten(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            o = obs.copy()
            o.update(lokasi)
            o["local_dt"] = pd.to_datetime(o.get("local_datetime"), errors="coerce")
            rows.append(o)
    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","wd_deg","vs","tp","tcc"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df["ws"] * MS_TO_KT
    return df

# =========================================================
# 🎚 SIDEBAR
# =========================================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm1 = st.text_input("Province ADM1", "32")
    show_map = st.checkbox("Show Map", True)
    show_table = st.checkbox("Show Table", False)

# =========================================================
# 📡 LOAD DATA
# =========================================================
st.title("🛰 Tactical Weather Ops — BMKG")
with st.spinner("Fetching weather intelligence..."):
    raw = fetch_forecast(adm1)

entries = raw.get("data", [])
if not entries:
    st.error("No data available")
    st.stop()

locations = {e["lokasi"]["kotkab"]: e for e in entries if "lokasi" in e}
loc = st.selectbox("Select Location", list(locations.keys()))
df = flatten(locations[loc])

if df.empty:
    st.warning("No valid data")
    st.stop()

df = df.sort_values("local_dt")
now = df.iloc[0]

# =========================================================
# ✈ FLIGHT WEATHER STATUS
# =========================================================
st.markdown("### ✈ Flight Weather Status")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Temp (°C)", now.get("t","—"))
c2.metric("RH (%)", now.get("hu","—"))
c3.metric("Wind (KT)", f"{now.get('ws_kt',0):.1f}")
c4.metric("Visibility (m)", now.get("vs","—"))

# =========================================================
# 📊 TRENDS
# =========================================================
st.markdown("### 📊 Trends")
st.plotly_chart(px.line(df, x="local_dt", y="t", title="Temperature"), use_container_width=True)
st.plotly_chart(px.line(df, x="local_dt", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)
st.plotly_chart(px.bar(df, x="local_dt", y="tp", title="Rainfall"), use_container_width=True)

# =========================================================
# 🌪 WINDROSE
# =========================================================
st.markdown("### 🌪 Windrose")
if {"wd_deg","ws_kt"}.issubset(df.columns):
    d = df.dropna(subset=["wd_deg","ws_kt"])
    d["dir"] = pd.cut(d["wd_deg"]%360, bins=np.arange(-11.25,360,22.5))
    fig = px.histogram(d, x="dir", y="ws_kt")
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 🗺 MAP
# =========================================================
if show_map:
    st.map(pd.DataFrame({"lat":[now["lat"]],"lon":[now["lon"]]}))

# =========================================================
# 🛰️ SATELLITE & RADAR (REFERENCE ONLY)
# =========================================================
st.markdown("### 🛰 Satellite & Radar (Reference Only)")
st.info("For situational awareness only. Tactical decisions rely on METAR / TAF / ATC.")

tab1,tab2,tab3 = st.tabs(["🌑 IR","☁ VIS","🌧 Radar"])

with tab1:
    st.markdown("""
    <iframe src="https://www.bmkg.go.id/satelit/" width="100%" height="500" style="border:none;"></iframe>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("""
    <iframe src="https://www.bmkg.go.id/satelit/" width="100%" height="500" style="border:none;"></iframe>
    """, unsafe_allow_html=True)

with tab3:
    st.markdown("""
    <iframe src="https://www.bmkg.go.id/cuaca/radar-cuaca.bmkg" width="100%" height="500" style="border:none;"></iframe>
    """, unsafe_allow_html=True)

# =========================================================
# 📋 TABLE
# =========================================================
if show_table:
    st.dataframe(df)

# =========================================================
# ⚓ FOOTER
# =========================================================
st.markdown("""
---
<div style="text-align:center;color:#7a7;">
Tactical Weather Ops — BMKG<br>
Situational Awareness Only
</div>
""", unsafe_allow_html=True)
