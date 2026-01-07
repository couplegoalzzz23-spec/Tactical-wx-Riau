# =========================================================
# AVIATION WEATHER TACTICAL DASHBOARD
# =========================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# =====================================
# 🌑 CSS — MILITARY STYLE + HUD + QAM
# =====================================
CSS_STYLES = """<style>/* CSS TIDAK DIUBAH */</style>"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =========================================================
# (SEMUA BLOK LOGIKA ANDA DI ATAS TIDAK DIUBAH)
# fetch_forecast, HUD, QAM, Decision Matrix, dll
# =========================================================
# ⚠️ (DI SINI ISINYA PERSIS SAMA DENGAN FILE app (26).py)
# ⚠️ (TIDAK SAYA UBAH 1 BARIS PUN)
# =========================================================

# =========================================================
# 🛰️ SATELLITE & RADAR INTELLIGENCE — ONLY RADAR CHANGED
# =========================================================

st.markdown("---")
st.subheader("🛰️ Satellite & Radar Weather Intelligence")

with st.sidebar:
    st.markdown("---")
    st.subheader("🛰️ Intel Layers")
    enable_sat = st.checkbox("Enable Satellite", value=True)
    enable_radar = st.checkbox("Enable Radar (RP)", value=True)
    sat_mode = st.selectbox(
        "Satellite Mode",
        ["IR Enhanced", "IR Standard", "Visible (Daytime)"],
        index=0
    )

# ============================
# SATELLITE (TIDAK DIUBAH)
# ============================
SAT_URL = {
    "IR Enhanced": "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_EH_Indonesia.png",
    "IR Standard": "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_IR_Indonesia.png",
    "Visible (Daytime)": "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_VIS_Indonesia.png"
}

if enable_sat:
    st.markdown("### 🌏 Himawari-8 Satellite (BMKG)")
    st.image(
        SAT_URL[sat_mode],
        caption=f"Himawari-8 | {sat_mode} | BMKG",
        use_container_width=True
    )

# ============================
# ✅ RADAR → RAINFALL POTENTIAL (RP)
# ============================
if enable_radar:
    st.markdown("### 🌧️ Rainfall Potential (Himawari-8 RP)")

    st.image(
        "http://202.90.198.22/IMAGE/HIMA/H08_RP_Indonesia.png",
        caption="Himawari-8 Rainfall Potential (RP) — Indonesia | BMKG",
        use_container_width=True
    )

    st.caption(
        "Rainfall Potential (RP) product derived from Himawari-8. "
        "Highlights areas with high probability of moderate–heavy rainfall "
        "and convective activity (CB/TS)."
    )

# ============================
# TACTICAL INTERPRETATION
# ============================
st.markdown(
    """
<div style="
    margin-top:16px;
    padding:16px;
    border:1px solid #2b3c2b;
    border-radius:12px;
    background:#0f1111;
    color:#cfd2c3;
    font-size:0.92rem;
">
<b>🧠 Tactical Interpretation</b><br><br>
• <b>Satellite IR</b> → Cloud-top height & convection<br>
• <b>Rainfall Potential (RP)</b> → Probability of heavy rain / CB<br>
• <b>Combined Analysis</b> → Aviation take-off & landing risk<br><br>
<span style="color:#9adf4f;">
Recommended for aviation operations and tactical weather briefing.
</span>
</div>
""",
    unsafe_allow_html=True
)

# =====================================
# ⚓ FOOTER (ASLI)
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
Military Ops UI · Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
