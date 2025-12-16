# =====================================
# Tactical Weather Ops — BMKG (SAFE MODE)
# Full Script • Copy–Paste • Anti Connection Error
# =====================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =====================================
# ⚙️ PAGE CONFIG
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# =====================================
# 📡 API CONFIG
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384
METER_TO_SM = 0.000621371

# =====================================
# 🛡️ SAFE FETCH (ANTI ERROR)
# =====================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (TacticalWx/1.0)",
        "Accept": "application/json"
    }
    try:
        r = requests.get(API_BASE, params={"adm1": adm1}, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"[BMKG API WARNING] {e}")
        return {}

# =====================================
# 🧰 UTILITIES
# =====================================
def safe_float(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d

def safe_int(v, d=0):
    try:
        return int(float(v))
    except Exception:
        return d

def convert_vis_to_sm(m):
    if m is None or pd.isna(m):
        return "—"
    sm = m * METER_TO_SM
    return f"{sm:.1f} SM" if sm < 5 else f"{int(round(sm))} SM"

# =====================================
# 🧭 SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    icao = st.text_input("ICAO", value="WXXX")
    if st.button("🔄 Fetch Data"):
        st.session_state["go"] = True
    st.markdown("---")
    show_map = st.checkbox("Show Map", True)
    show_table = st.checkbox("Show Table", False)

# =====================================
# 📡 LOAD DATA (SAFE)
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.caption("BMKG Forecast API — Safe Mode")

raw = fetch_forecast(adm1)
entries = raw.get("data", [])

if not entries:
    st.warning("⚠️ BMKG API unavailable or blocked")
    st.info("Dashboard running in SAFE MODE — no live data")
    st.stop()

# =====================================
# 📍 LOCATION SELECT
# =====================================
mapping = {}
for e in entries:
    loc = e.get("lokasi", {})
    label = loc.get("kotkab") or loc.get("adm2") or "Unknown"
    mapping[label] = e

loc_choice = st.selectbox("Select Location", list(mapping.keys()))
entry = mapping[loc_choice]

# =====================================
# 🔄 FLATTEN DATA
# =====================================
rows = []
for group in entry.get("cuaca", []):
    for o in group:
        r = o.copy()
        r.update(entry.get("lokasi", {}))
        r["local_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
        rows.append(r)

df = pd.DataFrame(rows)
if df.empty:
    st.warning("No usable weather data")
    st.stop()

for c in ["t","hu","ws","wd_deg","vs","tp"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

if "ws" in df.columns:
    df["ws_kt"] = df["ws"] * MS_TO_KT

now = df.iloc[0]

# =====================================
# ✈ KEY METRICS
# =====================================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Temp (°C)", safe_float(now.get("t")))
with col2:
    st.metric("Wind (KT)", f"{safe_float(now.get('ws_kt')):.1f}")
with col3:
    st.metric("Visibility", f"{safe_int(now.get('vs'))} m")
with col4:
    st.metric("Rain (mm)", safe_float(now.get("tp")))

# =====================================
# 📈 TRENDS
# =====================================
st.markdown("---")
st.subheader("📊 Trends")
if "local_dt" in df.columns:
    st.plotly_chart(px.line(df, x="local_dt", y="t", title="Temperature"), use_container_width=True)

# =====================================
# 🗺 MAP
# =====================================
if show_map:
    lat = safe_float(entry.get("lokasi", {}).get("lat"))
    lon = safe_float(entry.get("lokasi", {}).get("lon"))
    if lat != 0 and lon != 0:
        st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))

# =====================================
# 📋 TABLE
# =====================================
if show_table:
    st.dataframe(df)

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style='text-align:center; color:#7a7;'>
Tactical Weather Ops — SAFE MODE<br>
UI active even when BMKG API is unavailable
</div>
""", unsafe_allow_html=True)
