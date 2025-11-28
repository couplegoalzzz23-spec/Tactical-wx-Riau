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
# 🎨 CSS — DARK STEALTH TACTICAL UI (FINAL + ICON WEATHER)
# =====================================
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #d8decc;
    font-family: "Consolas", "Roboto Mono", monospace;
}
h1, h2, h3, h4 { color: #b4ff72; text-transform: uppercase; letter-spacing: 1px; }
section[data-testid="stSidebar"] { background-color: #0e100e; padding: 25px 20px; border-right: 1px solid #1b1f1b; }
.sidebar-title { font-size: 1.2rem; font-weight: bold; color: #b4ff72; margin-bottom: 10px; text-align: center; }
.sidebar-label { font-size: 0.85rem; font-weight: 600; color: #9fb99a; margin-bottom: -6px; }
.stCheckbox label { color: #d0d6c4 !important; font-size: 0.9rem !important; }
.stButton>button { background-color: #1a2a1e; color: #b4ff72; border: 1px solid #3e513d; border-radius: 6px; font-weight: 700; width: 100%; padding: 8px 0px; }
.stButton>button:hover { background-color: #233726; border-color: #b4ff72; color: #e3ffcd; }
.radar { position: relative; width: 170px; height: 170px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.06) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.10) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #41ff6c; overflow: hidden; margin: auto; box-shadow: 0 0 20px #39ff61; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 60%; height: 2px; background: linear-gradient(90deg, #3dff6f, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.divider { margin: 18px 0px; border-top: 1px solid #222822; }

/* WEATHER ICON SVG */
.weather-icon {
    width: 60px;
    height: 60px;
    margin: auto;
}
.weather-label {
    text-align: center;
    color: #7aff9b;
    font-size: 0.95rem;
    font-weight: 600;
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
    # >>> PENAMBAHAN PARAMETER BARU DI SINI <<<
    # Menambahkan 'p' (Tekanan Udara) dan 'td' (Suhu Titik Embun)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs", "p", "td"]: 
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# =====================================
# 🎚️ SIDEBAR — STEALTH UI
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
    st.caption("BMKG API | Tactical Ops UI v2.0")

# =====================================
# 📡 PENGAMBILAN DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Live Weather Intelligence — BMKG Forecast API*")

with st.spinner("🛰️ Acquiring weather intelligence..."):
    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        st.stop()

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

df["ws_kt"] = df["ws"] * MS_TO_KT
df = df.sort_values("utc_datetime_dt")

if df["local_datetime_dt"].isna().all():
    st.error("No valid datetime available.")
    st.stop()

min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()

start_dt = st.sidebar.slider(
    "Time Range",
    min_value=min_dt,
    max_value=max_dt,
    value=(min_dt, max_dt),
    step=pd.Timedelta(hours=3)
)

mask = (df["local_datetime_dt"] >= pd.to_datetime(start_dt[0])) & \
       (df["local_datetime_dt"] <= pd.to_datetime(start_dt[1]))
df_sel = df.loc[mask].copy()

# =====================================
# ⚡ METRIC PANEL + WEATHER ICON
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

def weather_svg(row):
    """
    Return inline SVG icon based on weather condition.
    """
    tcc = row.get("tcc",0)
    tp = row.get("tp",0)
    if tp > 10:
        return """<svg class="weather-icon" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#ffec00"/><polygon points="32,16 28,32 36,32" fill="#ff3300"/></svg>"""  # thunderstorm
    elif tp > 0:
        return """<svg class="weather-icon" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#00aaff"/><ellipse cx="32" cy="32" rx="20" ry="12" fill="#fff"/></svg>"""  # rain
    elif tcc >= 0.75:
        return """<svg class="weather-icon" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#aaaaaa"/></svg>"""  # cloudy
    elif tcc >= 0.4:
        return """<svg class="weather-icon" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#ffd966"/></svg>"""  # partly cloudy
    else:
        return """<svg class="weather-icon" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#ffec00"/></svg>"""  # sunny

now = df_sel.iloc[0]
svg_icon = weather_svg(now)

# Mengubah jumlah kolom menjadi 7 untuk menampung parameter baru
c1, c2, c3, c4, c5, c6, c7 = st.columns([1,1,1,1,1,1,1]) 

with c1:
    st.markdown(svg_icon + "<div class='weather-label'>Weather</div>", unsafe_allow_html=True)
with c2: st.metric("TEMP", f"{now.get('t','—')}°C")
with c3: st.metric("HUMIDITY", f"{now.get('hu','—')}%")
with c4: st.metric("WIND", f"{now.get('ws_kt',0):.1f} KT")
with c5: st.metric("RAIN", f"{now.get('tp','—')} mm")
# >>> PENAMBAHAN METRIC BARU DI SINI <<<
with c6: st.metric("PRESSURE", f"{now.get('p','—')} hPa")
with c7: st.metric("DEW POINT", f"{now.get('td','—')}°C")

# =====================================
# 📈 TREND GRAPH
# =====================================
st.markdown("---")
st.subheader("📊 Parameter Trends")
c1, c2 = st.columns(2)
# Menambah 2 grafik baru ke kolom 1
with c1:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity"), use_container_width=True)
    # >>> GRAFIK BARU: SUHU TITIK EMBUN (Td) <<<
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="td", title="Dew Point Temperature (°C)"), use_container_width=True)
# Menambah 1 grafik baru ke kolom 2
with c2:
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)
    st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall"), use_container_width=True)
    # >>> GRAFIK BARU: TEKANAN UDARA (P) <<<
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="p", title="Pressure (hPa)"), use_container_width=True)


# =====================================
# 🌪️ WINDROSE
# =====================================
st.markdown("---")
st.subheader("🌪️ Windrose")
if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
    df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"])
    if not df_wr.empty:
        bins_dir = np.arange(-11.25,360,22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"]/freq["count"].sum()*100
        az_map = {k:i*22.5 for i,k in enumerate(labels_dir)}
        freq["theta"] = freq["dir_sector"].map(az_map)
        fig_wr = go.Figure()
        for sc in speed_labels:
            subset = freq[freq["speed_class"]==sc]
            fig_wr.add_trace(go.Barpolar(r=subset["percent"], theta=subset["theta"], name=sc))
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
# 📋 TABEL
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
c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇️ CSV", data=csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
with c2:
    st.download_button("⬇️ JSON", data=json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
Dark Stealth Tactical UI v2.0 | Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
