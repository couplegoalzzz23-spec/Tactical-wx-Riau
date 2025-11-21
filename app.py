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
# 🎨 IMPROVED ULTRA-PREMIUM STEALTH UI
# =====================================
st.markdown("""
<style>

body {
    background-color: #0b0c0c;
    color: #d8decc;
    font-family: "Consolas", "Roboto Mono", monospace;
}

/* HEADER STYLE */
h1, h2, h3, h4 {
    color: #b4ff72 !important;
    text-transform: uppercase;
}

/* ------------ SIDEBAR ------------- */
section[data-testid="stSidebar"] {
    background-color: #0f110f !important;
    padding: 25px !important;
    border-right: 1px solid #1f271f;
}

/* Sidebar Title */
.sidebar-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #b4ff72;
    text-align: center;
    padding-bottom: 8px;
}

/* Tactical Container */
.tactical-box {
    border: 1px solid #223122;
    border-radius: 8px;
    padding: 15px 12px;
    margin-bottom: 20px;
    background-color: #111411;
    box-shadow: inset 0 0 5px #132113;
}

/* LABEL */
.sidebar-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #98b792;
    margin-bottom: 4px;
}

/* Radar */
.radar {
  position: relative;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(20,255,50,0.06) 20%, transparent 21%);
  background-size: 22px 22px;
  border: 2px solid #41ff6c;
  overflow: hidden;
  margin: auto;
  margin-bottom: 5px;
  box-shadow: 0 0 14px #39ff61;
}
.radar:before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 65%; height: 2px;
  background: linear-gradient(90deg, #3dff6f, transparent);
  transform-origin: 100% 50%;
  animation: sweep 2.8s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Divider */
.divider {
    margin: 12px 0;
    border-top: 1px solid #223322;
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
# 🎚️ SIDEBAR — IMPROVED PERFECT VERSION
# =====================================
with st.sidebar:

    st.markdown("<div class='sidebar-title'>TACTICAL CONTROL PANEL</div>", unsafe_allow_html=True)

    # Radar
    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#82ff9b;'>System Online — Scanning...</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- PROVINCE INPUT ----------------
    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>Province Code (ADM1)</div>", unsafe_allow_html=True)
    adm1 = st.text_input("", value="32")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh Data")
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- DISPLAY OPTIONS ----------------
    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>Display Options</div>", unsafe_allow_html=True)
    show_map = st.checkbox("🗺 Show Map", value=True)
    show_table = st.checkbox("📋 Show Table", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- FOOTER ----------------
    st.caption("BMKG API | Tactical Ops UI v3.0")

# =====================================
# 📡 API FETCH
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Live Weather Intelligence — BMKG Forecast API*")

with st.spinner("🛰 Acquiring weather data…"):
    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"API Error: {e}")
        st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data available.")
    st.stop()

# LOCATION SELECTOR
mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = {"entry": e}

col1, col2 = st.columns([2, 1])
with col1:
    loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
with col2:
    st.metric("📍 Locations", len(mapping))

selected_entry = mapping[loc_choice]["entry"]
df = flatten_cuaca_entry(selected_entry)

if df.empty:
    st.warning("No valid weather data found.")
    st.stop()

df["ws_kt"] = df["ws"] * MS_TO_KT
df = df.sort_values("local_datetime_dt")

# TIME RANGE SLIDER
st.markdown("### ⏱ Time Filter")
min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()

start_dt = st.slider(
    "Select Time Window",
    min_value=min_dt,
    max_value=max_dt,
    value=(min_dt, max_dt),
    step=pd.Timedelta(hours=3)
)

mask = (df["local_datetime_dt"] >= start_dt[0]) & (df["local_datetime_dt"] <= start_dt[1])
df_sel = df.loc[mask].copy()

# =====================================
# METRICS PANEL
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

now = df_sel.iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("🌡 TEMP", f"{now.get('t','—')}°C")
with c2: st.metric("💧 HUM", f"{now.get('hu','—')}%")
with c3: st.metric("🌬 WIND", f"{now.get('ws_kt',0):.1f} KT")
with c4: st.metric("🌧 RAIN", f"{now.get('tp','—')} mm")

# =====================================
# TREND GRAPH
# =====================================
st.markdown("---")
st.subheader("📊 Parameter Trends")

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity"), use_container_width=True)
with c2:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)
    st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall"), use_container_width=True)

# =====================================
# WINDROSE
# =====================================
st.markdown("---")
st.subheader("🌪 Windrose")

if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
    wr = df_sel.dropna(subset=["wd_deg","ws_kt"])
    if not wr.empty:

        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                      "S","SSW","SW","WSW","W","WNW","NW","NNW"]

        wr["dir_sector"] = pd.cut(wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)

        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        wr["spd"] = pd.cut(wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)

        freq = wr.groupby(["dir_sector","spd"]).size().reset_index(name="count")
        freq["percent"] = freq["count"]/freq["count"].sum()*100

        theta = {
            "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
            "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5
        }
        freq["theta"] = freq["dir_sector"].map(theta)

        fig = go.Figure()
        for sc in speed_labels:
            sub = freq[freq["spd"] == sc]
            fig.add_trace(go.Barpolar(
                r=sub["percent"], theta=sub["theta"], name=f"{sc} KT", opacity=0.8
            ))

        fig.update_layout(template="plotly_dark", title="Windrose (KT)")
        st.plotly_chart(fig, use_container_width=True)

# =====================================
# MAP
# =====================================
if show_map:
    st.markdown("---")
    st.subheader("🗺 Tactical Map")
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", 0))
        lon = float(selected_entry.get("lokasi", {}).get("lon", 0))
        st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))
    except:
        st.warning("Map unavailable.")

# =====================================
# TABLE
# =====================================
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table")
    st.dataframe(df_sel)

# =====================================
# EXPORT
# =====================================
st.markdown("---")
st.subheader("💾 Export Data")

csv = df_sel.to_csv(index=False)
json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")

c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇️ CSV", data=csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
with c2:
    st.download_button("⬇️ JSON", data=json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")

# FOOTER
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
Stealth Tactical UI v3.0 | Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
