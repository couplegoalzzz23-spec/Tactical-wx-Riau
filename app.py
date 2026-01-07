import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    page_icon="🛰",
    layout="wide"
)

API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# =====================================
# 🎨 STYLE (RINGAN & AMAN)
# =====================================
st.markdown("""
<style>
body { background-color:#0b0c0c; color:#cfd2c3; }
h1,h2,h3 { color:#9adf4f; letter-spacing:1px; }
hr { border:1px solid #223322; }
.alert-ok { background:#0d2b0d; padding:10px; border-radius:6px; }
.alert-warn { background:#3b2f00; padding:10px; border-radius:6px; }
.alert-bad { background:#3b0000; padding:10px; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 AMBIL DATA BMKG (FAIL-SAFE)
# =====================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    try:
        r = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}

def flatten_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({
                "provinsi": lokasi.get("provinsi"),
                "kotkab": lokasi.get("kotkab"),
                "lat": lokasi.get("lat"),
                "lon": lokasi.get("lon"),
                "local_dt": pd.to_datetime(r.get("local_datetime"), errors="coerce")
            })
            rows.append(r)

    df = pd.DataFrame(rows)

    for c in ["t","hu","ws","wd_deg","tp","vs","tcc"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "ws" in df.columns:
        df["ws_kt"] = df["ws"] * MS_TO_KT

    return df

# =====================================
# 🎚 SIDEBAR
# =====================================
with st.sidebar:
    st.header("🛰 Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    show_map = st.checkbox("Show Tactical Map", True)
    show_table = st.checkbox("Show Table", False)

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("🛰 Tactical Weather Operations — BMKG")

raw = fetch_forecast(adm1)
entries = raw.get("data", [])

if not entries:
    st.error("❌ Data BMKG tidak tersedia.")
    st.stop()

loc_map = {
    e.get("lokasi", {}).get("kotkab","Unknown"): e
    for e in entries
}

loc_choice = st.selectbox("📍 Select Location", list(loc_map.keys()))
entry = loc_map[loc_choice]
df = flatten_entry(entry)

if df.empty:
    st.error("❌ Tidak ada data cuaca valid.")
    st.stop()

df = df.sort_values("local_dt")
now = df.iloc[0]

# =====================================
# ✈ SNAPSHOT PANEL
# =====================================
st.markdown("---")
c1,c2,c3,c4 = st.columns(4)

c1.metric("🌡 Temp (°C)", now.get("t","—"))
c2.metric("💧 RH (%)", now.get("hu","—"))
c3.metric("🌬 Wind (KT)", f"{now.get('ws_kt',0):.1f}")
c4.metric("🌧 Rain (mm)", now.get("tp","—"))

# =====================================
# ⚠ SIGNIFICANT WEATHER WARNING
# =====================================
warnings = []

if now.get("ws_kt",0) >= 20:
    warnings.append("Strong surface wind ≥ 20 KT")

if now.get("vs",99999) < 5000:
    warnings.append("Reduced visibility < 5 km")

if now.get("tp",0) >= 10:
    warnings.append("Heavy accumulated rainfall")

st.markdown("### ⚠ Significant Weather")

if warnings:
    st.markdown(
        "<div class='alert-bad'>" + "<br>".join(warnings) + "</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<div class='alert-ok'>No significant weather detected</div>",
        unsafe_allow_html=True
    )

# =====================================
# ✈ FLIGHT CATEGORY (SIMPLE AVIATION RULE)
# =====================================
def flight_category(vis, wind):
    if vis < 3000 or wind >= 30:
        return "IFR / NO-GO"
    if vis < 5000 or wind >= 20:
        return "MVFR / CAUTION"
    return "VFR / OK"

category = flight_category(
    now.get("vs",99999),
    now.get("ws_kt",0)
)

st.markdown("### ✈ Flight Operational Status")
st.info(category)

# =====================================
# 🛰 SATELLITE & RADAR
# =====================================
st.markdown("---")
st.subheader("🛰 Satellite & Radar")

colA,colB = st.columns(2)

with colA:
    st.image(
        "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_EH_Indonesia.png",
        caption="Himawari-8 Infrared (BMKG)"
    )

with colB:
    st.image(
        "https://inderaja.bmkg.go.id/IMAGE/RadarComposite.png",
        caption="BMKG Radar Composite"
    )

# =====================================
# 📈 TRENDS
# =====================================
st.markdown("---")
st.subheader("📈 Weather Trends")

st.plotly_chart(
    px.line(df, x="local_dt", y="t", title="Temperature (°C)"),
    use_container_width=True
)

st.plotly_chart(
    px.line(df, x="local_dt", y="ws_kt", title="Wind Speed (KT)"),
    use_container_width=True
)

st.plotly_chart(
    px.bar(df, x="local_dt", y="tp", title="Rainfall (mm)"),
    use_container_width=True
)

# =====================================
# 🗺 MAP
# =====================================
if show_map and "lat" in df.columns and "lon" in df.columns:
    st.markdown("---")
    st.subheader("🗺 Tactical Position")
    st.map(df[["lat","lon"]].dropna().head(1))

# =====================================
# 📋 TABLE
# =====================================
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Data")
    st.dataframe(df)

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<center>
Tactical Weather Ops — BMKG  
Aviation-Oriented | Streamlit Stable Build  
</center>
""", unsafe_allow_html=True)
