# ==========================================================
# app.py — Tactical Weather Ops (Clean UI Edition)
# ==========================================================
import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ----------------------------------------------------------
# Page Config + Clean Tactical UI
# ----------------------------------------------------------
st.set_page_config(page_title="Tactical Weather Ops", layout="wide")

st.markdown("""
<style>
body { background:#0c0c0c; color:#dcdcdc; font-family:Consolas; }
h1,h2,h3 { color:#a9df52; letter-spacing:1px; text-transform:uppercase; }

section[data-testid="stSidebar"] {
    background:#111; color:#e0e0e0;
}
.stButton>button {
    background:#1a2a1f; border:1px solid #3f4f3f; color:#a9df52;
    border-radius:8px; font-weight:bold;
}
.stButton>button:hover { background:#2b3b2b; border-color:#a9df52; }

.radar {
    position:relative; width:160px; height:160px; border-radius:50%;
    background:radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%),
               radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%);
    background-size:20px 20px;
    border:2px solid #33ff55; overflow:hidden; margin:auto;
    box-shadow:0 0 20px #33ff55;
}
.radar:before {
    content:""; position:absolute; top:0; left:0; width:50%; height:2px;
    background:linear-gradient(90deg,#33ff55,transparent);
    transform-origin:100% 50%; animation:sweep 2.5s linear infinite;
}
@keyframes sweep {
    from { transform:rotate(0deg);} to {transform:rotate(360deg);}
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# OPTIONAL MAP MODULES
# ----------------------------------------------------------
HAVE_FOLIUM = True
try:
    import folium
    from streamlit_folium import st_folium
except:
    HAVE_FOLIUM = False

# ----------------------------------------------------------
# API CONFIG
# ----------------------------------------------------------
API_URL = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

RADAR_TMS = os.getenv("RADAR_TMS", "")
MODEL_TMS = os.getenv("MODEL_TMS", "")

# ----------------------------------------------------------
# DATA FUNCTIONS
# ----------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    r = requests.get(API_URL, params={"adm1": adm1}, timeout=10)
    r.raise_for_status()
    return r.json()

def flatten(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            row = dict(obs)
            row.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"),
                "lat": lokasi.get("lat"),
            })
            row["local_dt"] = pd.to_datetime(row.get("local_datetime"))
            rows.append(row)
    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","wd_deg","tp","vs","tcc"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df.get("ws",0) * MS_TO_KT
    df["wd_deg"] = df.get("wd_deg",0)
    df["u"] = -df.get("ws",0) * np.sin(np.deg2rad(df.get("wd_deg",0)))
    df["v"] = -df.get("ws",0) * np.cos(np.deg2rad(df.get("wd_deg",0)))
    return df


# ----------------------------------------------------------
# SIDEBAR — CLEAN & SIMPLE
# ----------------------------------------------------------
with st.sidebar:
    st.title("Tactical Control")

    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#5f5;'>Scanning weather...</p>", unsafe_allow_html=True)

    st.markdown("---")

    # === FIX: Select Province by Name ===
    ADM1_DISPLAY = {
        "Aceh": "11",
        "Sumatera Utara": "12",
        "Sumatera Barat": "13",
        "Riau": "14",
        "Jambi": "15",
        "Sumatera Selatan": "16",
        "DKI Jakarta": "31",
        "Jawa Barat": "32",
        "Jawa Tengah": "33",
        "DI Yogyakarta": "34",
        "Jawa Timur": "35",
    }

    ADM1 = st.selectbox("Pilih Provinsi", list(ADM1_DISPLAY.keys()), index=3)
    ADM1_CODE = ADM1_DISPLAY[ADM1]

    st.markdown("---")

    param_choice = st.multiselect(
        "Tampilkan Parameter",
        ["Temperature", "Humidity", "Wind Speed", "Rainfall", "Windrose", "Map", "Table"],
        default=["Temperature", "Windrose", "Map"]
    )

    show_windvec = st.checkbox("Tampilkan Wind Vector", value=False)
    show_tiles = st.checkbox("Gunakan Model/Radar Tiles (jika ada)", value=False)


# ----------------------------------------------------------
# FETCH DATA
# ----------------------------------------------------------
try:
    raw = fetch_forecast(ADM1_CODE)
except Exception as e:
    st.error(f"Gagal mengambil data: {e}")
    st.stop()

entries = raw.get("data", [])
if not entries:
    st.error("Data tidak tersedia")
    st.stop()

locations = {e["lokasi"]["kotkab"]: e for e in entries}
loc_choice = st.selectbox("Pilih Kota", list(locations.keys()))

entry = locations[loc_choice]
df = flatten(entry)

# ----------------------------------------------------------
# TIMELINE
# ----------------------------------------------------------
times = sorted(df["local_dt"].dropna().unique())
tid = st.slider("Time Index", 0, len(times)-1, len(times)-1)
current_time = times[tid]

df_sel = df[df["local_dt"] == current_time]
if df_sel.empty():
    df_sel = df.iloc[[0]]

now = df_sel.iloc[0]

# ----------------------------------------------------------
# METRICS PANEL
# ----------------------------------------------------------
st.title("Tactical Weather Ops")
st.subheader(f"Status Cuaca — {loc_choice}")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Temp (°C)", f"{now.t:.1f}" if pd.notna(now.t) else "—")
c2.metric("Humidity", f"{now.hu}%" if pd.notna(now.hu) else "—")
c3.metric("Wind (KT)", f"{now.ws_kt:.1f}" if pd.notna(now.ws_kt) else "—")
c4.metric("Rain (mm)", f"{now.tp}" if pd.notna(now.tp) else "—")

st.markdown("---")

# ----------------------------------------------------------
# CHARTS
# ----------------------------------------------------------
df_sorted = df.sort_values("local_dt")

if "Temperature" in param_choice:
    fig = px.line(df_sorted, x="local_dt", y="t", markers=True, title="Temperature")
    st.plotly_chart(fig, use_container_width=True)

if "Humidity" in param_choice:
    fig = px.line(df_sorted, x="local_dt", y="hu", markers=True, title="Humidity")
    st.plotly_chart(fig, use_container_width=True)

if "Wind Speed" in param_choice:
    fig = px.line(df_sorted, x="local_dt", y="ws_kt", markers=True, title="Wind Speed (KT)")
    st.plotly_chart(fig, use_container_width=True)

if "Rainfall" in param_choice:
    fig = px.bar(df_sorted, x="local_dt", y="tp", title="Rainfall (mm)")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------
# WINDROSE
# ----------------------------------------------------------
if "Windrose" in param_choice:
    df_wr = df.dropna(subset=["wd_deg","ws_kt"])
    if len(df_wr) > 0:
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                      "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir"] = pd.cut(df_wr["wd_deg"], bins=bins_dir, labels=labels_dir)

        speed_bins = [0,5,10,20,30,50,100]
        sp_label = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["spd"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=sp_label)

        freq = df_wr.groupby(["dir","spd"]).size().reset_index(name="count")
        freq["pct"] = freq["count"]/freq["count"].sum()*100

        az = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
              "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
        freq["theta"] = freq["dir"].map(az)

        colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
        fig_wr = go.Figure()
        for i, sc in enumerate(sp_label):
            sub = freq[freq["spd"] == sc]
            fig_wr.add_trace(go.Barpolar(
                r=sub["pct"], theta=sub["theta"], name=f"{sc} KT",
                marker_color=colors[i], opacity=0.85
            ))
        fig_wr.update_layout(title="Windrose", template="plotly_dark")
        st.plotly_chart(fig_wr, use_container_width=True)

# ----------------------------------------------------------
# MAP
# ----------------------------------------------------------
if "Map" in param_choice:
    st.subheader("Tactical Map")
    lat = float(entry["lokasi"]["lat"])
    lon = float(entry["lokasi"]["lon"])

    if HAVE_FOLIUM:
        m = folium.Map(location=[lat, lon], zoom_start=7, tiles="CartoDB Positron")

        if show_tiles and RADAR_TMS:
            folium.TileLayer(tiles=RADAR_TMS, name="Radar", overlay=True).add_to(m)

        folium.CircleMarker(
            [lat, lon],
            tooltip=loc_choice,
            radius=8, color="#33ff55", fill=True
        ).add_to(m)

        if show_windvec:
            for _, r in df_sel.iterrows():
                dlat = -0.02 * r.ws * np.cos(np.deg2rad(r.wd_deg))
                dlon = 0.02 * r.ws * np.sin(np.deg2rad(r.wd_deg))
                folium.PolyLine([[r.lat, r.lon], [r.lat + dlat, r.lon + dlon]],
                                color="#a9df52", weight=2).add_to(m)

        st_folium(m, width=1000, height=550)
    else:
        st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))

# ----------------------------------------------------------
# TABLE
# ----------------------------------------------------------
if "Table" in param_choice:
    st.subheader("Forecast Table")
    st.dataframe(df_sorted, use_container_width=True)

# END
