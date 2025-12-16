# =====================================
# Tactical Weather Operations Dashboard
# BMKG OFFICIAL PUBLIC API (FUTURE‑SAFE)
# Full Script • Copy–Paste • Defensive Coding
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
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG Public",
    layout="wide"
)

# =====================================
# 📡 BMKG OFFICIAL PUBLIC API
# =====================================
BMKG_API = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
REQUEST_TIMEOUT = 15

# =====================================
# 🛡️ SAFE FETCH (ANTI ERROR)
# =====================================
@st.cache_data(ttl=600)
def fetch_bmkg(adm4: str):
    """
    Defensive BMKG fetch:
    - timeout
    - user-agent
    - never raises exception
    """
    try:
        resp = requests.get(
            BMKG_API,
            params={"adm4": adm4},
            headers={"User-Agent": "Mozilla/5.0 (TacticalWx/1.0)"},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print("[BMKG API ERROR]", e)
        return None

# =====================================
# 🧰 UTILITIES (SAFE)
# =====================================
def safe_float(v):
    try:
        return float(v)
    except Exception:
        return np.nan

# =====================================
# 🧭 SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm4 = st.text_input(
        "ADM4 Code (BMKG)",
        value="31.71.01.1001",
        help="Format: Prov.Kab.Kec.Desa (BMKG)"
    )
    st.markdown("---")
    st.caption("Contoh ADM4 valid:")
    st.caption("31.71.01.1001  (Jakarta Pusat)")
    st.caption("32.73.01.1001  (Bandung)")
    st.caption("33.74.01.1001  (Semarang)")

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.caption("Data Source: BMKG Official Public API")

raw = fetch_bmkg(adm4)

# ---- CONNECTION FAILURE ----
if raw is None:
    st.error("❌ Tidak dapat terhubung ke server BMKG")
    st.info("Periksa koneksi internet atau coba beberapa saat lagi.")
    st.stop()

# ---- INVALID / EMPTY ADM4 ----
if "data" not in raw or not raw.get("data"):
    st.warning("⚠️ Kode ADM4 tidak tersedia di database BMKG")
    st.info("""
Gunakan ADM4 wilayah representatif, contoh:
- 31.71.01.1001 (Jakarta Pusat)
- 32.73.01.1001 (Bandung)
- 33.74.01.1001 (Semarang)
""")
    st.stop()

# =====================================
# 🔄 PARSE DATA (DEFENSIVE)
# =====================================
records = []
for area in raw.get("data", []):
    lokasi = area.get("lokasi", {})
    for fc in area.get("cuaca", []):
        # fc kadang LIST (bukan dict) → harus diamankan
        if isinstance(fc, list):
            for item in fc:
                if not isinstance(item, dict):
                    continue
                row = {}
                row.update(lokasi)
                row.update(item)
                row["time"] = pd.to_datetime(item.get("local_datetime"), errors="coerce")
                records.append(row)
        elif isinstance(fc, dict):
            row = {}
            row.update(lokasi)
            row.update(fc)
            row["time"] = pd.to_datetime(fc.get("local_datetime"), errors="coerce")
            records.append(row)
        # tipe lain diabaikan

df = pd.DataFrame(records)

if df.empty:
    st.warning("Data cuaca tersedia tetapi tidak dapat diproses")
    st.stop()

# =====================================
# NORMALIZE NUMERIC COLUMNS
# =====================================
for col in ["t", "hu", "ws", "wd", "vs", "tp"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# =====================================
# CURRENT CONDITIONS
# =====================================
now = df.iloc[0]

# =====================================
# ✈ KEY METRICS
# =====================================
st.markdown("---")
st.subheader("✈ Key Weather Conditions")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Temperature (°C)", safe_float(now.get("t")))
with c2:
    st.metric("Humidity (%)", safe_float(now.get("hu")))
with c3:
    st.metric("Visibility (m)", safe_float(now.get("vs")))
with c4:
    st.metric("Rainfall (mm)", safe_float(now.get("tp")))

# =====================================
# 📈 TRENDS
# =====================================
st.markdown("---")
st.subheader("📊 Temperature Forecast Trend")

if "time" in df.columns:
    fig = px.line(df, x="time", y="t", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# =====================================
# 📋 DATA TABLE
# =====================================
st.markdown("---")
st.subheader("📋 Forecast Data (Raw)")
st.dataframe(df, use_container_width=True)

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard<br>
BMKG Official Public API • Defensive Mode<br>
UI will not crash even if data source fails
</div>
""", unsafe_allow_html=True)
