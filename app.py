# =========================================================
# 🛰 Tactical Weather Ops — BMKG
# FINAL • STABLE • STREAMLIT CLOUD SAFE
# =========================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    layout="wide"
)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
body { background:#0b0c0c; color:#cfd2c3; font-family:Consolas, monospace; }
h1,h2,h3 { color:#a9df52; }
section[data-testid="stSidebar"] { background:#111; }
</style>
""", unsafe_allow_html=True)

# =========================
# API
# =========================
API = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

@st.cache_data(ttl=300)
def fetch(adm1):
    r = requests.get(API, params={"adm1": adm1}, timeout=10)
    r.raise_for_status()
    return r.json()

def flatten(entry):
    rows = []
    loc = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for o in group:
            d = o.copy()
            d.update(loc)
            d["time"] = pd.to_datetime(d.get("local_datetime"), errors="coerce")
            rows.append(d)
    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","wd_deg","vs","tp"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df["ws"] * MS_TO_KT
    return df

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("🛰 Controls")
    adm1 = st.text_input("ADM1 (Provinsi)", "32")
    show_table = st.checkbox("Show Table", False)

# =========================
# LOAD DATA
# =========================
st.title("🛰 Tactical Weather Ops — BMKG")

with st.spinner("Loading BMKG data..."):
    raw = fetch(adm1)

data = raw.get("data", [])
if not data:
    st.error("BMKG API tidak mengembalikan data")
    st.stop()

locations = {e["lokasi"]["kotkab"]: e for e in data if "lokasi" in e}
loc = st.selectbox("Select Location", list(locations.keys()))

df = flatten(locations[loc])
if df.empty:
    st.error("Data kosong")
    st.stop()

df = df.sort_values("time")
now = df.iloc[0]

# =========================
# METRICS
# =========================
c1,c2,c3,c4 = st.columns(4)
c1.metric("Temp (°C)", now.get("t","—"))
c2.metric("RH (%)", now.get("hu","—"))
c3.metric("Wind (KT)", f"{now.get('ws_kt',0):.1f}")
c4.metric("Visibility (m)", now.get("vs","—"))

# =========================
# TRENDS (SAFE)
# =========================
st.subheader("📊 Trends")

try:
    st.plotly_chart(
        px.line(df, x="time", y="t", title="Temperature"),
        use_container_width=True
    )
    st.plotly_chart(
        px.line(df, x="time", y="ws_kt", title="Wind Speed (KT)"),
        use_container_width=True
    )
    st.plotly_chart(
        px.bar(df, x="time", y="tp", title="Rainfall"),
        use_container_width=True
    )
except Exception:
    st.warning("Grafik tidak dapat ditampilkan (data format)")

# =========================
# MAP (SAFE)
# =========================
try:
    st.subheader("🗺 Location")
    st.map(pd.DataFrame({
        "lat":[now["lat"]],
        "lon":[now["lon"]]
    }))
except Exception:
    st.info("Map tidak tersedia")

# =========================
# SATELLITE (REFERENCE)
# =========================
st.subheader("🛰 Satellite & Radar (Reference Only)")
st.info("Situational awareness only. NOT for tactical separation.")

tab1,tab2 = st.tabs(["🌑 Himawari IR","🌧 Radar"])

with tab1:
    st.markdown(
        "<iframe src='https://www.bmkg.go.id/satelit/' "
        "width='100%' height='500'></iframe>",
        unsafe_allow_html=True
    )

with tab2:
    st.markdown(
        "<iframe src='https://www.bmkg.go.id/cuaca/radar-cuaca.bmkg' "
        "width='100%' height='500'></iframe>",
        unsafe_allow_html=True
    )

# =========================
# TABLE
# =========================
if show_table:
    st.dataframe(df)

# =========================
# FOOTER
# =========================
st.markdown("""
---
<div style="text-align:center;color:#7a7;">
Tactical Weather Ops — BMKG<br>
Reference Only · Streamlit Safe
</div>
""", unsafe_allow_html=True)
