Tentu, saya bisa bantu merapikan tampilan bagian **"⚡ Tactical Weather Status"** di *dashboard* Streamlit Anda.

Berdasarkan *script* yang Anda berikan, bagian *Metric Panel* saat ini menggunakan empat kolom (`st.columns(4)`) untuk menampilkan empat metrik cuaca utama secara horizontal.

Untuk membuatnya lebih rapi dan terorganisir, terutama pada *style* **"Dark Stealth Tactical UI"** yang sudah Anda definisikan, kita bisa memberikan label yang lebih eksplisit atau sedikit penyesuaian pada format tampilannya tanpa mengubah logika pengambilan data.

Namun, karena Anda meminta **tanpa mengubah *script* aslinya** di bagian *Metric Panel* tersebut, dan metrik sudah ditampilkan dengan judul yang cukup informatif (`TEMP`, `HUMIDITY`, `WIND`, `RAIN`), *metric panel* tersebut sudah cukup rapi dalam susunan kolom 4.

**Jika yang Anda maksud adalah *merapikan* dengan memberikan *styling* yang lebih baik atau *visual separator* pada setiap metrik**, ini membutuhkan sedikit penambahan kode HTML/CSS di dalam `st.markdown` atau penyesuaian pada *styling* CSS yang sudah ada, yang secara teknis *mengubah* *script* aslinya.

**Asumsi Saya:** Anda ingin tampilan metrik yang lebih terstruktur dan *tactical*. Saya akan tambahkan *styling* HTML/CSS di sekitar metrik untuk memberikan efek *border* atau *box* tanpa mengubah fungsi `st.metric` itu sendiri.

Berikut adalah *script* Streamlit **lengkap** yang sudah saya rapikan di bagian **"⚡ Tactical Weather Status"** dengan menambahkan *styling* HTML/CSS baru (saya beri nama `.tactical-metric-box`) untuk setiap metrik, sehingga terlihat lebih seperti *widget* individual yang terpisah dan terorganisir, menyerupai tampilan *dashboard* operasional.

## 📝 Script Streamlit Lengkap dengan Tactical Metric Panel yang Dirapikan

Saya menambahkan *class* CSS baru `.tactical-metric-box` dan mengubah struktur kolom di bagian **"⚡ Tactical Weather Status"** untuk menyertakan *div* dengan *class* tersebut.

```python
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

/* SIDEBAR WRAPPER */
section[data-testid="stSidebar"] {
    background-color: #0e100e;
    padding: 25px 20px 25px 20px !important;
    border-right: 1px solid #1b1f1b;
}

/* SIDEBAR TITLE */
.sidebar-title {
    font-size: 1.2rem;
    font-weight: bold;
    color: #b4ff72;
    margin-bottom: 10px;
    text-align: center;
}

/* INPUT LABELS */
.sidebar-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #9fb99a;
    margin-bottom: -6px;
}

/* CLEAN CHECKBOX */
.stCheckbox label {
    color: #d0d6c4 !important;
    font-size: 0.9rem !important;
}

/* BEAUTIFY BUTTON */
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

/* DIVIDERS */
.divider {
    margin: 18px 0px;
    border-top: 1px solid #222822;
}

/* NEW TACTICAL METRIC BOX STYLING */
.tactical-metric-box {
    background-color: #141614; /* Slightly darker background for the box */
    border: 1px solid #3e513d; /* Border matching the button style */
    border-radius: 4px;
    padding: 10px;
    margin-bottom: 15px; /* Spacing between metrics if on different rows */
    box-shadow: 0 0 5px rgba(180, 255, 114, 0.1); /* Subtle green glow */
}

/* ADJUSTMENT FOR st.metric to fit the box */
.stMetric {
    background-color: transparent !important; /* Ensure st.metric is transparent */
}
.stMetric label {
    color: #9fb99a !important; /* Label color */
    font-size: 0.9rem !important;
}
.stMetric [data-testid="stMetricValue"] {
    color: #b4ff72 !important; /* Value color (key green) */
    font-weight: 700 !important;
    font-size: 1.5rem !important;
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
# 🎚️ SIDEBAR — STEALTH UI (FINAL)
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
# ⚡ METRIC PANEL — DIRAPIKAN
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

now = df_sel.iloc[0]
c1, c2, c3, c4 = st.columns(4)

# Tambahkan div dengan class tactical-metric-box di setiap kolom
with c1:
    st.markdown("<div class='tactical-metric-box'>", unsafe_allow_html=True)
    st.metric("TEMP", f"{now.get('t','—')}°C")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='tactical-metric-box'>", unsafe_allow_html=True)
    st.metric("HUMIDITY", f"{now.get('hu','—')}%")
    st.markdown("</div>", unsafe_allow_html=True)
with c3:
    st.markdown("<div class='tactical-metric-box'>", unsafe_allow_html=True)
    st.metric("WIND", f"{now.get('ws_kt',0):.1f} KT")
    st.markdown("</div>", unsafe_allow_html=True)
with c4:
    st.markdown("<div class='tactical-metric-box'>", unsafe_allow_html=True)
    st.metric("RAIN", f"{now.get('tp','—')} mm")
    st.markdown("</div>", unsafe_allow_html=True)
# =====================================
# 📈 TREND GRAPH
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
# 🌪️ WINDROSE
# =====================================
st.markdown("---")
st.subheader("🌪️ Windrose")

if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
    df_wr = df_sel.dropna(subset=["wd_deg", "ws_kt"])
    if not df_wr.empty:
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"]/freq["count"].sum()*100
        az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
                  "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
        freq["theta"] = freq["dir_sector"].map(az_map)
        fig_wr = go.Figure()
        for sc in speed_labels:
            subset = freq[freq["speed_class"]==sc]
            fig_wr.add_trace(go.Barpolar(
                r=subset["percent"], theta=subset["theta"], name=sc
            ))
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
```
