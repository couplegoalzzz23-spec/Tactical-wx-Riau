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

.sidebar-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: #b4ff72;
    text-align: center;
    padding-bottom: 8px;
}

.tactical-box {
    border: 1px solid #223122;
    border-radius: 8px;
    padding: 15px 12px;
    margin-bottom: 20px;
    background-color: #111411;
    box-shadow: inset 0 0 5px #132113;
}

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

.divider {
    margin: 12px 0;
    border-top: 1px solid #223322;
}

/* Tactical status cards (Design A) */
.tw-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  color: #eaf6e3;
  margin: 6px;
}
.tw-time {
  font-size: 0.85rem;
  color: #cfe8c8;
  margin-bottom: 6px;
}
.tw-icon {
  font-size: 30px;
  margin-bottom: 6px;
}
.tw-temp {
  font-size: 18px;
  font-weight: 800;
  color: #ffd24d;
}
.tw-sub {
  font-size: 12px;
  color: #b6d7b1;
  margin-top: 6px;
}

.tw-row { display:flex; flex-wrap:nowrap; justify-content:flex-start; align-items:flex-start; gap:6px; overflow-x:auto; padding-bottom:6px; }

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
    resp = requests.get(API_BASE, params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []) or []:
        for obs in group or []:
            r = obs.copy() if isinstance(obs, dict) else {}
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

# helper: simple condition to emoji mapping (kept lightweight)
def cond_to_emoji(tcc_val):
    # tcc = total cloud cover (0-8 often); if unavailable fallback
    try:
        t = float(tcc_val)
        # rough mapping
        if t <= 2: return "☀️"
        if t <= 5: return "⛅"
        if t <= 7: return "☁️"
        return "🌧️"
    except Exception:
        return "⛅"

# =====================================
# 🎚️ SIDEBAR — PREMIUM
# =====================================
with st.sidebar:

    st.markdown("<div class='sidebar-title'>TACTICAL CONTROL PANEL</div>", unsafe_allow_html=True)

    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#82ff9b;'>System Online — Scanning...</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>Province Code (ADM1)</div>", unsafe_allow_html=True)
    adm1 = st.text_input("", value="32")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh Data")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='tactical-box'>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>Display Options</div>", unsafe_allow_html=True)
    show_map = st.checkbox("🗺 Show Map (Premium)", value=True)
    show_table = st.checkbox("📋 Show Table", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("BMKG API | Tactical Ops UI v4.2")

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

# LOCATION SELECTOR (you requested NOT to change)
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

# TIME RANGE
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

# ===========================
# === NEW: Tactical Status (A)
# ===========================
# We'll render a horizontal scrollable row of small time-cards (Design A),
# showing upcoming slots (first 8 slots in df_sel). Each card: time, icon, temp, subinfo (wind/hum).
st.markdown("---")
st.subheader("⚡ Tactical Weather Status — Timeline (Design A)")

# prepare up to N slots for display
N = 8
slots = df_sel.sort_values("local_datetime_dt").head(N)
if slots.empty:
    st.warning("No timeslots available to display.")
else:
    # build HTML for each card and display in a single horizontal row
    cards_html = "<div class='tw-row'>"
    for _, row in slots.iterrows():
        # time label (local)
        tlabel = ""
        try:
            tlabel = pd.to_datetime(row["local_datetime_dt"]).strftime("%H:%M")
        except Exception:
            tlabel = str(row.get("local_datetime_dt", "—"))
        # icon from tcc/cloudcover
        icon = cond_to_emoji(row.get("tcc", None))
        temp = "—" if pd.isna(row.get("t")) else f"{row.get('t'):.0f}°C"
        # wind direction + speed
        wd = row.get("wd_deg", None)
        ws = row.get("ws_kt", None)
        wind_txt = "—"
        if pd.notna(ws) and pd.notna(wd):
            # convert wd_deg to compass short (N, NNE, NE...)
            dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            sector = int(((wd + 11.25) % 360) / 22.5)
            wind_txt = f"{dirs[sector]} {ws:.0f}kt"
        elif pd.notna(ws):
            wind_txt = f"{ws:.0f}kt"
        hum_txt = "—" if pd.isna(row.get("hu")) else f"{int(row.get('hu'))}%"
        rain_txt = "—" if pd.isna(row.get("tp")) else f"{row.get('tp'):.1f} mm"

        # small card HTML
        card = f"""
        <div class="tw-card" style="min-width:120px; max-width:140px;">
            <div class="tw-time">{tlabel}</div>
            <div class="tw-icon">{icon}</div>
            <div class="tw-temp">{temp}</div>
            <div class="tw-sub">{wind_txt} · {hum_txt}</div>
        </div>
        """
        cards_html += card
    cards_html += "</div>"

    st.markdown(cards_html, unsafe_allow_html=True)

    # beneath timeline show a compact current-condition row (larger)
    now = slots.iloc[0]
    try:
        utc_str = pd.to_datetime(now.get("utc_datetime_dt")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        utc_str = str(now.get("utc_datetime_dt", "—"))

    # Current big summary (three columns)
    st.markdown("---")
    st.subheader("Current / Forecast Slot Summary")
    big_col1, big_col2, big_col3 = st.columns([2, 1, 1])

    with big_col1:
        # show location + time + big icon + temp
        st.markdown(f"**Location:** {selected_entry.get('lokasi',{}).get('kotkab') or selected_entry.get('lokasi',{}).get('adm2','-')}  ")
        st.markdown(f"**Valid time (local):** {pd.to_datetime(now.get('local_datetime_dt'))}  ")
        st.markdown(f"<div style='font-size:48px;'> {cond_to_emoji(now.get('tcc'))} <span style='font-size:40px; color:#ffd24d; font-weight:800;'>{now.get('t','—')}°C</span></div>", unsafe_allow_html=True)

    with big_col2:
        st.markdown("**Wind**")
        wd = now.get("wd_deg")
        ws = now.get("ws_kt")
        if pd.notna(wd) and pd.notna(ws):
            dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            sector = int(((wd + 11.25) % 360) / 22.5)
            st.markdown(f"- Direction: **{dirs[sector]}** ({wd:.0f}°)")
            st.markdown(f"- Speed: **{ws:.1f} kt**")
        elif pd.notna(ws):
            st.markdown(f"- Speed: **{ws:.1f} kt**")
        else:
            st.markdown("- Speed: —")

        st.markdown(f"- Gust / range: —")

    with big_col3:
        st.markdown("**Other**")
        st.markdown(f"- Humidity: **{now.get('hu','—')}%**")
        st.markdown(f"- Rain: **{now.get('tp','—')} mm**")
        # dewpoint & visibility if available
        dew = now.get("dew_point") if "dew_point" in now.index else None
        if pd.notna(dew):
            st.markdown(f"- Dew point: **{dew:.1f}°C**")
        if "vs" in now.index and pd.notna(now.get("vs")):
            vism = now.get("vs")
            vis_text = "Good" if vism>=8000 else ("Moderate" if vism>=3000 else "Poor")
            st.markdown(f"- Visibility: **{int(vism)} m ({vis_text})**")

    # small note about data being forecast slot, not instant obs
    st.caption("Note: displayed slots are BMKG forecast time slots (nearest forecast), not live station observations.")

# =====================================
# TREND GRAPH (original)
# =====================================
st.markdown("---")
st.subheader("📊 Parameter Trends")

c1, c2 = st.columns(2)
with c1:
    if not df_sel["t"].isna().all():
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
    if not df_sel["hu"].isna().all():
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity"), use_container_width=True)
with c2:
    if not df_sel["ws_kt"].isna().all():
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)
    if not df_sel["tp"].isna().all():
        st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall"), use_container_width=True)

# =====================================
# WINDROSE (original style preserved)
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
# PREMIUM OPS MAP — FOLIUM (Safe; unchanged)
# =====================================
if show_map:
    st.markdown("---")
    st.subheader("🗺 Tactical Ops Map (Premium)")
    lat = 0.0
    lon = 0.0
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", 0))
        lon = float(selected_entry.get("lokasi", {}).get("lon", 0))
    except Exception:
        lat, lon = 0.0, 0.0

    try:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[lat, lon], zoom_start=9, tiles="CartoDB dark_matter")
        folium.Marker([lat, lon], tooltip=f"{loc_choice}", icon=folium.Icon(color="green", icon="crosshairs")).add_to(m)
        folium.Circle(radius=15000, location=[lat, lon], color="#39ff14", fill=True, fill_opacity=0.15).add_to(m)
        st_folium(m, width=900, height=500)
    except Exception:
        # Folium not available or failed — fallback
        st.warning("Map unavailable (folium not installed). Falling back to simple st.map.")
        try:
            st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
        except Exception as e:
            st.error(f"Map fallback failed: {e}")

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
Stealth Tactical UI v4.2 | Streamlit + Plotly + Folium
</div>
""", unsafe_allow_html=True)
