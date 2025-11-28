# =================================================
#    TACTICAL WEATHER OPS — BMKG STREAMLIT APP
# =================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ============================
# ⚙️ KONFIGURASI
# ============================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

API_URL = "https://cuaca.bmkg.go.id/api/forecast-weather"

# ============================
# 🎨 DARK MODE UI
# ============================
st.markdown("""
<style>
body { background-color: #0e1117; color: #e5e5e5; }
.block-container { padding-top: 1rem; }
h1,h2,h3,h4 { color: #f1f1f1; }
</style>
""", unsafe_allow_html=True)

# ============================
# 🔧 Fungsi Panggil API
# ============================
@st.cache_data(ttl=900)
def fetch_weather(adm_code):
    try:
        r = requests.get(f"{API_URL}?adm={adm_code}", timeout=10)
        r.raise_for_status()
        data = r.json()
        return pd.json_normalize(data["data"])
    except Exception:
        st.error("❌ Gagal menghubungi API BMKG. Periksa ADM Code.")
        st.stop()

# ============================
# 🚀 SIDEBAR
# ============================
st.sidebar.header("Tactical Weather Options")
adm = st.sidebar.text_input("Kode ADM BMKG:", "1701")
st.sidebar.info("Contoh: 1701 (Pekanbaru), 3173 (Jakarta), dsb.")

# ============================
# 🚀 LOAD DATA
# ============================
df = fetch_weather(adm)

# ============================
# 🛠️ PREPROCESSING AMAN
# ============================

# DateTime
if "local_datetime" in df.columns:
    df["local_datetime_dt"] = pd.to_datetime(df["local_datetime"], errors="coerce")
else:
    df["local_datetime_dt"] = pd.NaT

# Convert parameter ke numeric
numeric_cols = ["t", "hu", "ws", "wd", "pres", "vis"]
for col in numeric_cols:
    if col in df:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Bersihkan NaN
df_sel = df.dropna(subset=["local_datetime_dt"])

if df_sel.empty:
    st.warning("⚠️ Data kosong setelah diproses. Tidak ada grafik yang bisa ditampilkan.")
    st.stop()

# ============================
# 🛰️ HEADER
# ============================
st.title("🌦️ Tactical Weather Ops — BMKG")
st.caption("Operasional cuaca dengan fokus Pressure, Visibility, dan Tactical Alerts")

st.markdown("---")

# ============================
# 📊 GRAFIK UTAMA
# ============================

col1, col2 = st.columns(2)

# Temperature
with col1:
    if "t" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Kolom suhu (t) tidak tersedia.")

# Humidity
with col2:
    if "hu" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity (%)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Kolom humidity (hu) tidak tersedia.")

# Row 2
col3, col4 = st.columns(2)

# Pressure
with col3:
    if "pres" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="pres", title="Pressure (hPa)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Kolom tekanan (pres) tidak ada.")

# Visibility
with col4:
    if "vis" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="vis", title="Visibility (m)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Kolom visibility (vis) tidak ada.")

# Row 3 — Wind
st.subheader("💨 Wind Analysis")
col5, col6 = st.columns(2)

with col5:
    if "ws" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="ws", title="Wind Speed (kt)")
        st.plotly_chart(fig, use_container_width=True)

with col6:
    if "wd" in df_sel:
        fig = px.line(df_sel, x="local_datetime_dt", y="wd", title="Wind Direction (°)")
        st.plotly_chart(fig, use_container_width=True)

# ============================
# ⚠️ TACTICAL ALERT SYSTEM
# ============================
st.markdown("---")
st.subheader("⚠️ Tactical Weather Alerts")

alerts = []

# --- THRESHOLDS ---
if "ws" in df_sel and df_sel["ws"].max() > 25:
    alerts.append("💨 **Angin kencang (>25 kt)** — Risiko tinggi untuk operasi udara/laut.")

if "pres" in df_sel and df_sel["pres"].min() < 1008:
    alerts.append("🌀 **Tekanan rendah (<1008 hPa)** — Potensi cuaca buruk / sistem siklonik.")

if "vis" in df_sel and df_sel["vis"].min() < 3000:
    alerts.append("🌫️ **Visibility rendah (<3000 m)** — Risiko navigasi dan penerbangan.")

if "hu" in df_sel and df_sel["hu"].max() > 95:
    alerts.append("💧 **Kelembaban sangat tinggi (>95%)** — Potensi hujan intens.")

if len(alerts) == 0:
    st.success("✔ Tidak ada peringatan — kondisi aman.")
else:
    for a in alerts:
        st.error(a)

# ============================
# 📄 TABEL RAW DATA
# ============================
st.markdown("---")
st.subheader("📄 Raw Forecast Data")
st.dataframe(df_sel, use_container_width=True)

