import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
h1, h2, h3, h4 {
    color: #a9df52;
    text-transform: uppercase;
    letter-spacing: 1px;
}
section[data-testid="stSidebar"] {
    background-color: #111;
    color: #d0d3ca;
}
.stButton>button {
    background-color: #1a2a1f;
    color: #a9df52;
    border: 1px solid #3f4f3f;
    border-radius: 8px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #2b3b2b;
    border-color: #a9df52;
}
div[data-testid="stMetricValue"] {
    color: #a9df52 !important;
}
.radar {
  position: relative;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%),
              radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%);
  background-size: 20px 20px;
  border: 2px solid #33ff55;
  overflow: hidden;
  margin: auto;
  box-shadow: 0 0 20px #33ff55;
}
.radar:before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 50%; height: 2px;
  background: linear-gradient(90deg, #33ff55, transparent);
  transform-origin: 100% 50%;
  animation: sweep 2.5s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
hr, .stDivider {
    border-top: 1px solid #2f3a2f;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 KONFIGURASI API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# =====================================
# 🧰 UTILITAS
# =====================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "provinsi": lokasi.get("provinsi"),
                "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"),
                "lat": lokasi.get("lat"),
            })
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    refresh = st.button("🔄 Fetch Data")
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table", value=False)
    st.markdown("---")
    st.caption("Data Source: BMKG API · Military Ops v1.0")

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Source: BMKG Forecast API — Live Data*")

with st.spinner("🛰️ Acquiring weather intelligence..."):
    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data.")
    st.stop()

mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2")
    mapping[label] = {"entry": e}

col1, col2 = st.columns([2,1])
with col1:
    loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
with col2:
    st.metric("📍 Locations", len(mapping))

selected_entry = mapping[loc_choice]["entry"]
df = flatten_cuaca_entry(selected_entry)
df["ws_kt"] = df["ws"] * MS_TO_KT

df = df.sort_values("local_datetime_dt")
min_dt = df["local_datetime_dt"].min().to_pydatetime()
max_dt = df["local_datetime_dt"].max().to_pydatetime()

start_dt = st.sidebar.slider(
    "Time Range",
    min_value=min_dt,
    max_value=max_dt,
    value=(min_dt, max_dt),
    step=pd.Timedelta(hours=3)
)

mask = (df["local_datetime_dt"] >= start_dt[0]) & (df["local_datetime_dt"] <= start_dt[1])
df_sel = df.loc[mask].copy()

# =====================================
# ⚡ TACTICAL WEATHER STATUS (UPDATED)
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

now = df_sel.iloc[0]

# Baris metric asli
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("TEMP (°C)", f"{now.get('t','—')}°C")
with c2: st.metric("HUMIDITY (%)", f"{now.get('hu','—')}")
with c3: st.metric("WIND (KT)", f"{now.get('ws_kt',0):.1f}")
with c4: st.metric("RAIN (mm)", f"{now.get('tp','—')}")

st.markdown("### 🔍 Additional Weather Parameters")

c5, c6, c7, c8 = st.columns(4)
with c5: st.metric("CLOUD COVER (%)", now.get("tcc","—"))
with c6: st.metric("WIND DIR (°)", now.get("wd_deg","—"))
with c7: st.metric("WIND DIR", now.get("wd","—"))
with c8: st.metric("VISIBILITY (m)", now.get("vs","—"))

c9, c10, c11 = st.columns(3)
with c9: st.metric("WEATHER CODE", now.get("weather","—"))
with c10: st.metric("DESCRIPTION", now.get("weather_desc","—"))
with c11: st.metric("VIS DESC", now.get("vs_text","—"))

c12, c13, c14 = st.columns(3)
with c12: st.metric("TIME INDEX", now.get("time_index","—"))
with c13: st.metric("LOCAL TIME", now.get("local_datetime","—"))
with c14: st.metric("ANALYSIS", now.get("analysis_date","—"))

c15, c16, c17, c18 = st.columns(4)
with c15: st.metric("PROVINCE", now.get("provinsi","—"))
with c16: st.metric("CITY", now.get("kotkab","—"))
with c17: st.metric("LAT", now.get("lat","—"))
with c18: st.metric("LON", now.get("lon","—"))

# =====================================
# 📈 TRENDS
# =====================================
st.markdown("---")
st.subheader("📊 Parameter Trends")

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity"), use_container_width=True)
with c2:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind (KT)"), use_container_width=True)
    st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall"), use_container_width=True)

# =====================================
# 🌪️ WINDROSE
# =====================================
st.markdown("---")
st.subheader("🌪️ Windrose")

if "wd_deg" in df_sel.columns:
    df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"])
    if not df_wr.empty:
        bins_dir = np.arange(-11.25,360,22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir)
        fig_wr = px.bar_polar(df_wr, r="ws_kt", theta="dir_sector", color="ws_kt")
        st.plotly_chart(fig_wr, use_container_width=True)

# =====================================
# 🗺️ MAP
# =====================================
if show_map:
    st.markdown("---")
    st.subheader("🗺️ Tactical Map")
    st.map(pd.DataFrame({"lat":[now.get("lat")],"lon":[now.get("lon")]}))

# =====================================
# 📋 TABLE
# =====================================
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table")
    st.dataframe(df_sel)

# =====================================
# 💾 EXPORT
# =====================================
st.markdown("---")
st.subheader("💾 Export Data")

csv = df_sel.to_csv(index=False)
json_text = df_sel.to_json(orient="records")

colA, colB = st.columns(2)
with colA:
    st.download_button("⬇ CSV", csv, file_name="forecast.csv")
with colB:
    st.download_button("⬇ JSON", json_text, file_name="forecast.json")

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
Military Ops UI · Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
