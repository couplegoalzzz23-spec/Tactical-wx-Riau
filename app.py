# =====================================
# Tactical Weather Operations Dashboard
# BMKG OFFICIAL PUBLIC API VERSION (STABLE)
# Full Script • Copy–Paste • No Connection Error
# =====================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =====================================
# ⚙️ PAGE CONFIG
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG (Public API)", layout="wide")

# =====================================
# 📡 BMKG OFFICIAL PUBLIC API
# =====================================
BMKG_API = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
METER_TO_SM = 0.000621371

# =====================================
# 🛡️ SAFE FETCH (PUBLIC API)
# =====================================
@st.cache_data(ttl=600)
def fetch_bmkg(adm4: str):
    try:
        r = requests.get(
            BMKG_API,
            params={"adm4": adm4},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("BMKG FETCH ERROR:", e)
        return None

# =====================================
# 🧰 UTILITIES
# =====================================
def safe_float(v):
    try:
        return float(v)
    except:
        return np.nan

# =====================================
# 🧭 SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm4 = st.text_input(
        "ADM4 Code (BMKG)",
        value="31.71.03.1001",
        help="Kode wilayah BMKG (Prov.Kab.Kec.Desa)"
    )
    st.markdown("---")
    st.caption("Contoh ADM4: Jakarta Pusat = 31.71.03.1001")

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.caption("BMKG Official Public Forecast API")

raw = fetch_bmkg(adm4)

if raw is None or "data" not in raw:
    st.error("❌ Gagal mengambil data dari BMKG Public API")
    st.stop()

# =====================================
# 🔄 PARSE DATA
# =====================================
records = []
for area in raw.get("data", []):
    lokasi = area.get("lokasi", {})
    for f in area.get("cuaca", []):
        r = f.copy()
        r.update(lokasi)
        r["time"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
        records.append(r)

# =====================================
# DATAFRAME
# =====================================
df = pd.DataFrame(records)

if df.empty:
    st.warning("Data kosong dari BMKG")
    st.stop()

for c in ["t","hu","ws","wd","vs","tp"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# =====================================
# CURRENT CONDITIONS
# =====================================
now = df.iloc[0]

# =====================================
# ✈ KEY METRICS
# =====================================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Temperature (°C)", now.get("t"))
with col2:
    st.metric("Humidity (%)", now.get("hu"))
with col3:
    st.metric("Visibility (m)", now.get("vs"))
with col4:
    st.metric("Rain (mm)", now.get("tp"))

# =====================================
# 📈 TRENDS
# =====================================
st.markdown("---")
st.subheader("📊 Temperature Trend")

if "time" in df.columns:
    fig = px.line(df, x="time", y="t", title="Temperature Forecast")
    st.plotly_chart(fig, use_container_width=True)

# =====================================
# 📋 TABLE
# =====================================
st.markdown("---")
st.subheader("📋 Raw Forecast Data")
st.dataframe(df)

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7;">
Tactical Weather Ops Dashboard<br>
Data Source: BMKG Official Public API
</div>
""", unsafe_allow_html=True)
