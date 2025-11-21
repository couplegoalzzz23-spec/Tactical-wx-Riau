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

# =====================================
# 🎨 CSS — DARK STEALTH TACTICAL UI (FINAL)
# =====================================
st.markdown("""
<style>

body {
    background-color: #0b0c0c;
    color: #d8decc;
    font-family: "Consolas", "Roboto Mono", monospace;
}

/* HEADERS */
h1, h2, h3, h4 {
    color: #b4ff72;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* PREMIUM TACTICAL BOX */
.tactical-panel {
    background: linear-gradient(145deg, #0e110e 0%, #0c0f0c 100%);
    border: 1px solid #1b261b;
    border-radius: 12px;
    padding: 15px 20px;
    box-shadow: 0 0 12px rgba(120,255,150,0.12);
    margin-bottom: 20px;
}

/* METRIC ITEM */
.metric-item {
    background: #111611;
    padding: 14px 18px;
    border-radius: 10px;
    border: 1px solid #233223;
    box-shadow: inset 0 0 8px rgba(100,255,140,0.08);
    text-align: center;
}
.metric-title {
    font-size: 0.85rem;
    color: #9fbf9a;
    font-weight: 600;
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    margin-top: -4px;
    color: #caffbf;
}

/* SIDEBAR WRAPPER */
section[data-testid="stSidebar"] {
    background-color: #0e100e;
    padding: 25px 20px 25px 20px !important;
    border-right: 1px solid #1b1f1b;
}

.sidebar-title {
    font-size: 1.2rem;
    font-weight: bold;
    color: #b4ff72;
    margin-bottom: 10px;
    text-align: center;
}

.sidebar-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #9fb99a;
    margin-bottom: -6px;
}

.stCheckbox label {
    color: #d0d6c4 !important;
    font-size: 0.9rem !important;
}

.stButton>button {
    background-color: #1a2a1e;
    color: #b4ff72;
    border: 1px solid #3e513d;
    border-radius: 6px;
    font-weight: 700;
    width: 100%;
    padding: 8px 0px;
}
.stButton>button:hover {
    background-color: #233726;
    border-color: #b4ff72;
    color: #e3ffcd;
}

/* RADAR */
.radar {
  position: relative;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(20,255,50,0.06) 20%, transparent 21%),
              radial-gradient(circle, rgba(20,255,50,0.10) 10%, transparent 11%);
  background-size: 20px 20px;
  border: 2px solid #41ff6c;
  overflow: hidden;
  margin: auto;
  box-shadow: 0 0 20px #39ff61;
}
.radar:before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 60%; height: 2px;
  background: linear-gradient(90deg, #3dff6f, transparent);
  transform-origin: 100% 50%;
  animation: sweep 2.5s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.divider {
    margin: 18px 0px;
    border-top: 1px solid #222822;
}

</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384  

# =====================================
# UTIL
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
            try:
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
            except:
                r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# =====================================
# SIDEBAR
# =====================================
with st.sidebar:

    st.markdown("<div class='sidebar-title'>TACTICAL CONTROLS</div>", unsafe_allow_html=True)

    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#7aff9b;'>System Online — Scanning</p>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>Province Code (ADM1)</div>", unsafe_allow_html=True)
    adm1 = st.text_input("", value="32")

    refresh = st.button("🔄 Fetch Data")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>Display Options</div>", unsafe_allow_html=True)
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table", value=False)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.caption("BMKG API | Tactical Ops UI v3.0")

# =====================================
# FETCH DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Live Weather Intelligence — BMKG Forecast API*")

with st.spinner("🛰️ Acquiring weather intelligence..."):
    raw = fetch_forecast(adm1)

entries = raw.get("data", [])
mapping = {}

for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = {"entry": e}

loc_choice = st.selectbox("🎯 Select Location", list(mapping.keys()))
selected_entry = mapping[loc_choice]["entry"]

df = flatten_cuaca_entry(selected_entry)
df["ws_kt"] = df["ws"] * MS_TO_KT
df = df.sort_values("local_datetime_dt")

# =====================================
# PREMIUM TACTICAL STATUS PANEL
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

now = df.iloc[0]  # tidak diubah, mengikuti script asli

utc_time = now["utc_datetime_dt"].strftime("%Y-%m-%d %H:%M UTC")

st.markdown(f"""
<div class="tactical-panel">

<h4>Operational Weather Snapshot</h4>
<p style="color:#9fbf9a; margin-top:-10px;">Forecast Time: <b>{utc_time}</b></p>

<div style="display:flex; gap:20px;">

    <div class="metric-item">
        <div class="metric-title">🌡 Temperature</div>
        <div class="metric-value">{now.get('t','—')}°C</div>
    </div>

    <div class="metric-item">
        <div class="metric-title">💧 Humidity</div>
        <div class="metric-value">{now.get('hu','—')}%</div>
    </div>

    <div class="metric-item">
        <div class="metric-title">🌬 Wind</div>
        <div class="metric-value">{now.get('ws_kt',0):.1f} KT</div>
    </div>

    <div class="metric-item">
        <div class="metric-title">🌧 Rainfall</div>
        <div class="metric-value">{now.get('tp','—')} mm</div>
    </div>

</div>

</div>
""", unsafe_allow_html=True)

# <<< REST OF ORIGINAL SCRIPT UNCHANGED >>>
