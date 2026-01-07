# =========================================================
# 🛰 Tactical Weather Ops — BMKG (DEPLOY READY)
# =========================================================

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# ⚙️ PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Tactical Weather Ops — BMKG",
    page_icon="🛰",
    layout="wide"
)

# =========================================================
# 🌑 CSS — MILITARY / AVIATION STYLE
# =========================================================
st.markdown("""
<style>
body { background-color:#0b0c0c; color:#cfd2c3; font-family:Consolas, monospace; }
h1,h2,h3 { color:#a9df52; letter-spacing:1px; }
section[data-testid="stSidebar"] { background:#111; }
hr { border-top:1px solid #2f3a2f; }
.metric-label { font-size:0.7rem; color:#9fa8a0; text-transform:uppercase; }
.metric-value { font-size:1.8rem; color:#b6ff6d; font-weight:700; }
.flight-card { background:#0f1111; border:1px solid #2b3c2b; padding:18px; border-radius:10px; margin-bottom:20px; }
.badge-green { background:#b6ff6d; color:#002b00; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-yellow { background:#ffd86b; color:#4a3b00; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-red { background:#ff6b6b; color:#2b0000; padding:4px 8px; border-radius:6px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 📡 BMKG API
# =========================================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# =========================================================
# 🧰 FUNCTIONS
# =========================================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    r = requests.get(API_BASE, params={"adm1": adm1}, timeout=15)
    r.raise_for_status()
    return r.json()

def flatten_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for grp in entry.get("cuaca", []):
        for o in grp:
            r = o.copy()
            r.update(lokasi)
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","hu","tp","tcc","wd_deg","ws","vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df.get("ws",0) * MS_TO_KT
    return df

# =========================================================
# 🎛 SIDEBAR
# =========================================================
with st.sidebar:
    st.title("🛰 Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    show_map = st.checkbox("Show Map", True)
    show_table = st.checkbox("Show Table", False)
    st.caption("BMKG Forecast API")

# =========================================================
# 📡 LOAD DATA
# =========================================================
st.title("🛰 Tactical Weather Operations — BMKG")

try:
    raw = fetch_forecast(adm1)
except Exception as e:
    st.error(f"BMKG API error: {e}")
    st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data available")
    st.stop()

mapping = {}
for e in entries:
    loc = e.get("lokasi", {})
    label = loc.get("kotkab","Unknown")
    mapping[label] = e

loc_choice = st.selectbox("🎯 Select Location", list(mapping.keys()))
entry = mapping[loc_choice]

df = flatten_entry(entry)
if df.empty:
    st.stop()

df = df.sort_values("local_datetime_dt")
df_sel = df.copy()
now = df_sel.iloc[0]

# =========================================================
# ✈ FLIGHT WEATHER STATUS
# =========================================================
st.markdown("---")
st.markdown('<div class="flight-card">', unsafe_allow_html=True)
st.subheader("✈ Flight Weather Status")

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.markdown("<div class='metric-label'>Temperature</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('t','—')} °C</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='metric-label'>Humidity</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('hu','—')} %</div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='metric-label'>Wind</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('ws_kt',0):.1f} KT</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='metric-label'>Rain</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('tp','—')} mm</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ⚠ SIGNIFICANT WEATHER WARNING
# =========================================================
st.markdown("---")
st.subheader("⚠ Significant Weather Advisory")

warnings = []
if now.get("ws_kt",0) >= 30:
    warnings.append(("DANGER","High surface wind ≥30 KT"))
elif now.get("ws_kt",0) >= 20:
    warnings.append(("CAUTION","Strong wind ≥20 KT"))

if now.get("vs",99999) < 3000:
    warnings.append(("DANGER","Low visibility <3000 m"))
elif now.get("vs",99999) < 5000:
    warnings.append(("CAUTION","Marginal visibility"))

if now.get("tp",0) >= 20:
    warnings.append(("DANGER","Heavy rainfall"))
elif now.get("tp",0) > 5:
    warnings.append(("CAUTION","Moderate rainfall"))

if not warnings:
    st.success("No significant aviation hazards detected.")
else:
    for lvl,msg in warnings:
        if lvl=="DANGER": st.error(msg)
        else: st.warning(msg)

# =========================================================
# 📈 TRENDS
# =========================================================
st.markdown("---")
st.subheader("📈 Weather Trends")

c1,c2 = st.columns(2)
with c1:
    st.plotly_chart(px.line(df_sel,x="local_datetime_dt",y="t",title="Temperature (°C)"),use_container_width=True)
    st.plotly_chart(px.line(df_sel,x="local_datetime_dt",y="hu",title="Humidity (%)"),use_container_width=True)
with c2:
    st.plotly_chart(px.line(df_sel,x="local_datetime_dt",y="ws_kt",title="Wind (KT)"),use_container_width=True)
    st.plotly_chart(px.bar(df_sel,x="local_datetime_dt",y="tp",title="Rainfall (mm)"),use_container_width=True)

# =========================================================
# 🌪 WINDROSE
# =========================================================
st.markdown("---")
st.subheader("🌪 Windrose")

wr = df_sel.dropna(subset=["wd_deg","ws_kt"])
if not wr.empty:
    wr["sector"] = pd.cut(wr["wd_deg"]%360,np.arange(-11.25,360,22.5))
    fig = px.histogram(wr,x="wd_deg",y="ws_kt",histfunc="avg",nbins=16,polar=True)
    st.plotly_chart(fig,use_container_width=True)

# =========================================================
# 🛰 SATELLITE (SAFE IMAGE)
# =========================================================
st.markdown("---")
st.subheader("🛰 Satellite Cloud Overview")
st.image(
    "https://rammb-slider.cira.colostate.edu/data/imagery/latest/himawari-9/full_disk/ir/latest.png",
    caption="Himawari IR — Cloud Top (Situational Awareness)",
    use_container_width=True
)

# =========================================================
# 🗺 MAP
# =========================================================
if show_map:
    st.markdown("---")
    st.subheader("🗺 Tactical Map")
    st.map(pd.DataFrame({"lat":[now.get("lat")],"lon":[now.get("lon")]}))

# =========================================================
# 📋 TABLE
# =========================================================
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table")
    st.dataframe(df_sel,use_container_width=True)

# =========================================================
# 💾 EXPORT
# =========================================================
st.markdown("---")
st.subheader("💾 Export")
st.download_button("⬇ CSV", df_sel.to_csv(index=False), "forecast.csv")
st.download_button("⬇ JSON", df_sel.to_json(orient="records"), "forecast.json")

# =========================================================
# ⚓ FOOTER
# =========================================================
st.markdown("""
---
<div style="text-align:center; font-size:0.8rem; color:#7a7;">
Tactical Weather Ops — BMKG © 2025<br>
For situational awareness only. Refer to official METAR/TAF/SIGMET.
</div>
""", unsafe_allow_html=True)
