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

# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION + FLIGHT PANEL
st.markdown("""
<style>
/* Base theme */
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

/* Tactical card (kept for compatibility) */
.tacti-card {
    padding: 18px 22px;
    background-color: #111;
    border: 1px solid #2f3a2f;
    border-radius: 12px;
    margin-bottom: 20px;
}
.tacti-title {
    font-size: 1.3rem;
    color: #a9df52;
    font-weight: bold;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Flight-style panel */
.flight-card {
    padding: 20px 24px;
    background-color: #0f1111;
    border: 1px solid #2b3c2b;
    border-radius: 10px;
    margin-bottom: 22px;
}
.flight-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #9adf4f;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 14px;
}
.metric-label {
    font-size: 0.70rem;
    text-transform: uppercase;
    color: #9fa8a0;
    letter-spacing: 0.6px;
    margin-bottom: -6px;
}
.metric-value {
    font-size: 1.9rem;
    color: #b6ff6d;
    margin-top: -6px;
    font-weight: 700;
}
.small-note {
    font-size: 0.78rem;
    color: #9fa8a0;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 KONFIGURASI API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384  # konversi ke knot

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
            # safe datetime parse
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs","ws_kt"]:
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
    st.button("🔄 Fetch Data")
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
    raw = fetch_forecast(adm1)

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data available.")
    st.stop()

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

# compute ws_kt if not already present
if "ws_kt" not in df.columns:
    df["ws_kt"] = df["ws"] * MS_TO_KT
else:
    df["ws_kt"] = pd.to_numeric(df["ws_kt"], errors="coerce")

# =====================================
# 🕓 SLIDER WAKTU
# =====================================
# ensure sort by local time if available, otherwise UTC
if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
    df = df.sort_values("local_datetime_dt")
elif "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
    df = df.sort_values("utc_datetime_dt")
else:
    df = df.sort_index()

# check datetimes exist
if "local_datetime_dt" not in df.columns or df["local_datetime_dt"].isna().all():
    # fallback to utc or index
    if "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
        min_dt = df["utc_datetime_dt"].dropna().min().to_pydatetime()
        max_dt = df["utc_datetime_dt"].dropna().max().to_pydatetime()
        use_col = "utc_datetime_dt"
    else:
        # no datetimes: use index
        min_dt = 0
        max_dt = len(df)-1
        use_col = None
else:
    min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
    max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()
    use_col = "local_datetime_dt"

# slider only when datetime exists
if use_col:
    start_dt = st.sidebar.slider(
        "Time Range",
        min_value=min_dt,
        max_value=max_dt,
        value=(min_dt, max_dt),
        step=pd.Timedelta(hours=3)
    )
    mask = (df[use_col] >= pd.to_datetime(start_dt[0])) & (df[use_col] <= pd.to_datetime(start_dt[1]))
    df_sel = df.loc[mask].copy()
else:
    # select all
    df_sel = df.copy()

if df_sel.empty:
    st.warning("No data in selected time range.")
    st.stop()

# =====================================
# ✈ FLIGHT WEATHER STATUS (PROFESSIONAL)
# =====================================
st.markdown("---")
st.markdown('<div class="flight-card">', unsafe_allow_html=True)
st.markdown('<div class="flight-title">✈ Flight Weather Status</div>', unsafe_allow_html=True)

now = df_sel.iloc[0]

colA, colB, colC, colD = st.columns(4)

with colA:
    st.markdown("<div class='metric-label'>Temperature (°C)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('t','—')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-note'>Ambient</div>", unsafe_allow_html=True)

with colB:
    st.markdown("<div class='metric-label'>Relative Humidity (%)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('hu','—')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-note'>RH</div>", unsafe_allow_html=True)

with colC:
    st.markdown("<div class='metric-label'>Wind Speed (KT)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('ws_kt',0):.1f}</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-note'>Sustained</div>", unsafe_allow_html=True)

with colD:
    st.markdown("<div class='metric-label'>Rainfall (mm)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('tp','—')}</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-note'>Accum.</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# =====================================
# ☁ METEOROLOGICAL DETAILS (SECONDARY)
# =====================================
st.markdown('<div class="flight-card">', unsafe_allow_html=True)
st.markdown('<div class="flight-title">☁ Meteorological Details</div>', unsafe_allow_html=True)

row1, row2, row3, row4 = st.columns(4)
with row1:
    st.markdown("<div class='metric-label'>Cloud Cover (%)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('tcc','—')}</div>", unsafe_allow_html=True)
with row2:
    st.markdown("<div class='metric-label'>Wind Direction (°)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('wd_deg','—')}</div>", unsafe_allow_html=True)
with row3:
    st.markdown("<div class='metric-label'>Wind Dir Code</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('wd','—')}</div>", unsafe_allow_html=True)
with row4:
    st.markdown("<div class='metric-label'>Visibility (m)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('vs','—')}</div>", unsafe_allow_html=True)

row5, row6, row7, row8 = st.columns(4)
with row5:
    st.markdown("<div class='metric-label'>Weather Code</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('weather','—')}</div>", unsafe_allow_html=True)
with row6:
    st.markdown("<div class='metric-label'>Description</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
with row7:
    st.markdown("<div class='metric-label'>Visibility Desc</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('vs_text','—')}</div>", unsafe_allow_html=True)
with row8:
    st.markdown("<div class='metric-label'>Time Index</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('time_index','—')}</div>", unsafe_allow_html=True)

row9, row10, row11, row12 = st.columns(4)
with row9:
    st.markdown("<div class='metric-label'>Local Time</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('local_datetime','—')}</div>", unsafe_allow_html=True)
with row10:
    st.markdown("<div class='metric-label'>Analysis Time</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('analysis_date','—')}</div>", unsafe_allow_html=True)
with row11:
    st.markdown("<div class='metric-label'>Province</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('provinsi','—')}</div>", unsafe_allow_html=True)
with row12:
    st.markdown("<div class='metric-label'>City</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{now.get('kotkab','—')}</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


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
# 🌪️ WINDROSE (ASLI)
# =====================================
st.markdown("---")
st.subheader("🌪️ Windrose — Direction & Speed")

if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
    df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"])
    if not df_wr.empty:
        bins_dir = np.arange(-11.25,360,22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                      "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)

        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)

        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"]/freq["count"].sum()*100

        az_map = {
            "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,
            "SSE":157.5,"S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,
            "WNW":292.5,"NW":315,"NNW":337.5
        }

        freq["theta"] = freq["dir_sector"].map(az_map)

        colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]

        fig_wr = go.Figure()
        for i, sc in enumerate(speed_labels):
            subset = freq[freq["speed_class"]==sc]
            fig_wr.add_trace(go.Barpolar(
                r=subset["percent"], theta=subset["theta"],
                name=f"{sc} KT", marker_color=colors[i], opacity=0.85
            ))

        fig_wr.update_layout(
            title="Windrose (KT)",
            polar=dict(
                angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0,360,45))),
                radialaxis=dict(ticksuffix="%", showline=True, gridcolor="#333")
            ),
            legend_title="Wind Speed Class",
            template="plotly_dark"
        )

        st.plotly_chart(fig_wr, use_container_width=True)


# =====================================
# 🗺️ MAP
# =====================================
if show_map:
    st.markdown("---")
    st.subheader("🗺️ Tactical Map")
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", 0))
        lon = float(selected_entry.get("lokasi", {}).get("lon", 0))
        st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
    except Exception as e:
        st.warning(f"Map unavailable: {e}")


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
json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")

colA, colB = st.columns(2)
with colA:
    st.download_button("⬇ CSV", csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
with colB:
    st.download_button("⬇ JSON", json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")


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
