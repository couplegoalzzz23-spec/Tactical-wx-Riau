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
# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION + FLIGHT PANEL + MET REPORT TABLE
# =====================================

# Menyimpan CSS styling untuk digunakan dalam file HTML QAM yang diunduh
CSS_STYLES = """
<style>
/* Base theme */
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
/* Custom CSS for the MET REPORT TABLE (REVISED QAM FORMAT) */
.met-report-table {
    border: 1px solid #2b3c2b;
    width: 100%;
    margin-bottom: 20px;
    background-color: #0f1111;
    font-size: 0.95rem;
    border-collapse: collapse;
}
.met-report-table th, .met-report-table td {
    border: 1px solid #2b3c2b;
    padding: 8px;
    text-align: left;
    vertical-align: top;
}
.met-report-table th {
    background-color: #111;
    color: #a9df52;
    text-transform: uppercase;
    width: 45%;
    font-size: 0.85rem;
}
.met-report-table td {
    color: #dfffe0;
    width: 55%;
    font-weight: bold;
}
.met-report-header {
    text-align: center;
    background-color: #0b0c0c;
    color: #a9df52;
    font-weight: bold;
    font-size: 1.1rem;
    padding: 10px 0;
    border: 1px solid #2b3c2b;
    border-bottom: none;
}
.met-report-subheader {
    text-align: center;
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-weight: normal;
    font-size: 0.8rem;
    padding-bottom: 5px;
}
/* Print styles untuk memastikan warna tetap muncul saat cetak ke PDF */
@media print {
    body {
        -webkit-print-color-adjust: exact;
        color-adjust: exact;
    }
}
</style>
"""

# Menyuntikkan seluruh CSS ke Streamlit (termasuk yang tidak relevan untuk QAM, untuk tampilan dashboard)
st.markdown(CSS_STYLES + """
<style>
/* CSS Streamlit Khusus */
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
/* ... (lanjutan CSS Streamlit) ... */
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
.badge-green { color:#002b00; background:#b6ff6d; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-yellow { color:#4a3b00; background:#ffd86b; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-red { color:#2b0000; background:#ff6b6b; padding:4px 8px; border-radius:6px; font-weight:700; }
.detail-value {
    font-size: 1.2rem;
    color: #dfffe0;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 KONFIGURASI API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384 # konversi ke knot

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

def estimate_dewpoint(temp, rh):
    if pd.isna(temp) or pd.isna(rh):
        return None
    # simple approximation
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    """
    Proxy estimate for ceiling (feet) using cloud cover percentage.
    Returns estimated ceiling category in feet (median of category) and as label.
    """
    if pd.isna(tcc_pct):
        return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 25:
        return 3500, "SKC/FEW (>3000 ft)"
    elif tcc < 50:
        return 2250, "SCT (1500-3000 ft)"
    elif tcc < 75:
        return 1250, "BKN (1000-1500 ft)"
    else:
        return 800, "OVC (<1000 ft)"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    """
    Classify into VFR / MVFR / IFR using conservative thresholds.
    """
    if visibility_m is None or pd.isna(visibility_m):
        return "Unknown"
    vis = float(visibility_m)
    if ceiling_ft is None:
        if vis >= 5000: return "VFR"
        elif vis >= 3000: return "MVFR"
        else: return "IFR"
    if vis >= 5000 and ceiling_ft > 1500: return "VFR"
    if (3000 <= vis < 5000) or (1000 < ceiling_ft <= 1500): return "MVFR"
    if vis < 3000 or ceiling_ft <= 1000: return "IFR"
    return "Unknown"

def takeoff_landing_recommendation(ws_kt, vs_m, tp_mm):
    """
    Simple tactical recommendation rules (conservative).
    """
    rationale = []
    takeoff = "Recommended"
    landing = "Recommended"
    if pd.notna(ws_kt) and float(ws_kt) >= 30:
        takeoff = "Not Recommended"
        landing = "Not Recommended"
        rationale.append(f"High surface wind: {ws_kt:.1f} KT (>=30 KT limit)")
    elif pd.notna(ws_kt) and float(ws_kt) >= 20:
        rationale.append(f"Strong wind: {ws_kt:.1f} KT (>=20 KT advisory)")
    if pd.notna(vs_m) and float(vs_m) < 1000:
        landing = "Not Recommended"
        rationale.append(f"Low visibility: {vs_m} m (<1000 m)")
    if pd.notna(tp_mm) and float(tp_mm) >= 20:
        takeoff = "Caution"
        landing = "Caution"
        rationale.append(f"Heavy accumulated rain: {tp_mm} mm (runway contamination possible)")
    elif pd.notna(tp_mm) and float(tp_mm) > 5:
        rationale.append(f"Moderate rainfall: {tp_mm} mm")
    if not rationale:
        rationale.append("Conditions within conservative operational limits.")
    return takeoff, landing, rationale

# Visual badge helper
def badge_html(status):
    if status == "VFR" or status == "Recommended":
        return "<span class='badge-green'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge-yellow'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge-red'>NO-GO</span>"
    return "<span class='badge-yellow'>UNKNOWN</span>"

# =====================================
# 🎚️ SIDEBAR (SEBELUM DATA DIMUAT)
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    st.button("🔄 Fetch Data")
    st.markdown("---")
    # Kontrol Tampilan
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table", value=False)
    # Kontrol baru untuk MET Report
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=False)
    st.markdown("---")
    st.caption("Data Source: BMKG API · Military Ops v2.2")

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Source: BMKG Forecast API — Live Data*")

# BLOK TRY DIMULAI DI SINI
try:
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
    # Find the correct datetime column and set range
    if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
        df = df.sort_values("local_datetime_dt")
        min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
        max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()
        use_col = "local_datetime_dt"
    elif "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
        df = df.sort_values("utc_datetime_dt")
        min_dt = df["utc_datetime_dt"].dropna().min().to_pydatetime()
        max_dt = df["utc_datetime_dt"].dropna().max().to_pydatetime()
        use_col = "utc_datetime_dt"
    else:
        min_dt = 0
        max_dt = len(df)-1
        use_col = None

    # slider only when datetime exists
    if use_col:
        # Memindahkan slider ke Sidebar
        with st.sidebar:
            start_dt = st.slider(
                "Time Range",
                min_value=min_dt,
                max_value=max_dt,
                # Set default range to cover only the first forecast time
                value=(min_dt, min_dt + pd.Timedelta(hours=3)) if len(df) > 1 else (min_dt, max_dt),
                step=pd.Timedelta(hours=3),
                format="HH:mm, MMM DD"
            )
        mask = (df[use_col] >= pd.to_datetime(start_dt[0])) & (df[use_col] <= pd.to_datetime(start_dt[1]))
        df_sel = df.loc[mask].copy()
    else:
        df_sel = df.copy()

    if df_sel.empty:
        st.warning("No data in selected time range.")
        st.stop()
    
    now = df_sel.iloc[0]

# =====================================
# ✈ FLIGHT WEATHER STATUS (KEY METRICS)
# =====================================
    st.markdown("---")
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">✈ Key Meteorological Status</div>', unsafe_allow_html=True)
    
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.markdown("<div class='metric-label'>Temperature (°C)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('t','—')}</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-note'>Ambient</div>", unsafe_allow_html=True)
    with colB:
        st.markdown("<div class='metric-label'>Wind Speed (KT)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('ws_kt',0):.1f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>{now.get('wd_deg','—')}°</div>", unsafe_allow_html=True)
    with colC:
        st.markdown("<div class='metric-label'>Visibility (M)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('vs','—')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>{now.get('vs_text','—')}</div>", unsafe_allow_html=True)
    with colD:
        st.markdown("<div class='metric-label'>Weather</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>Rain: {now.get('tp',0):.1f} mm (Accum.)</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# =====================================
# ☁ METEOROLOGICAL DETAILS (SECONDARY) - REVISI
# =====================================
    # prepare MET REPORT values (diperlukan untuk bagian di bawah dan QAM)
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
    ceiling_display = f"{ceiling_est_ft} ft" if ceiling_est_ft is not None else "—"


    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">☁ Meteorological Details</div>', unsafe_allow_html=True)

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        st.markdown("##### 🌡️ Atmospheric State")
        # Row 1: Temperature & Dew Point
        col_t, col_dp = st.columns(2)
        with col_t:
            st.markdown("<div class='metric-label'>Air Temperature (°C)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('t','—')}°C</div>", unsafe_allow_html=True)
        with col_dp:
            st.markdown("<div class='metric-label'>Dew Point (Est)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{dewpt_disp}</div>", unsafe_allow_html=True)

        # Row 2: Humidity & Wind Dir Code
        col_hu, col_wd = st.columns(2)
        with col_hu:
            st.markdown("<div class='metric-label'>Relative Humidity (%)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('hu','—')}%</div>", unsafe_allow_html=True)
        with col_wd:
            st.markdown("<div class='metric-label'>Wind Direction (Code)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('wd','—')} ({now.get('wd_deg','—')}°)</div>", unsafe_allow_html=True)
        
        # Row 3: Location Details (Moved here)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_prov, col_city = st.columns(2)
        with col_prov:
            st.markdown("<div class='metric-label'>Province</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('provinsi','—')}</div>", unsafe_allow_html=True)
        with col_city:
            st.markdown("<div class='metric-label'>City/Regency</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('kotkab','—')}</div>", unsafe_allow_html=True)


    with detail_col2:
        st.markdown("##### 🌁 Sky and Visibility")
        # Row 1: Visibility & Ceiling
        col_vis, col_ceil = st.columns(2)
        with col_vis:
            st.markdown("<div class='metric-label'>Visibility (Metres)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('vs','—')} m</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='small-note'>{now.get('vs_text','—')}</div>", unsafe_allow_html=True)
        with col_ceil:
            st.markdown("<div class='metric-label'>Est. Ceiling Base</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{ceiling_display}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='small-note'>({ceiling_label.split('(')[0].strip()})</div>", unsafe_allow_html=True)

        # Row 2: Cloud Cover & Weather Desc
        col_tcc, col_wx = st.columns(2)
        with col_tcc:
            st.markdown("<div class='metric-label'>Cloud Cover (%)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('tcc','—')}%</div>", unsafe_allow_html=True)
        with col_wx:
            st.markdown("<div class='metric-label'>Present Weather</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{now.get('weather_desc','—')} ({now.get('weather','—')})</div>", unsafe_allow_html=True)
        
        # Row 3: Time Index/Local Time
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_local, col_anal = st.columns(2)
        with col_local:
            st.markdown("<div class='metric-label'>Local Forecast Time</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('local_datetime','—')}</div>", unsafe_allow_html=True)
        with col_anal:
            st.markdown("<div class='metric-label'>Analysis Time (UTC)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('analysis_date','—')}</div>", unsafe_allow_html=True)


    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# === MET REPORT (QAM REPLICATION) - DIPINDAHKAN KE SIDEBAR
# =====================================

    if show_qam_report:
        # prepare MET REPORT values
        visibility_m = now.get('vs')
        wind_info = f"{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT"
        wind_variation = "Not available (BMKG Forecast)" 
        ceiling_full_desc = f"Est. Base: {ceiling_est_ft} ft ({ceiling_label.split('(')[0].strip()})" if ceiling_est_ft is not None else "—"


        # 📌 START: MEMBANGUN HTML UNTUK LAPORAN QAM
        met_report_html_content = f"""
        <div class="met-report-container">
            <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
            <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
            <div class="met-report-header" style="border-top: none;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
            <table class="met-report-table">
                <tr>
                    <th>METEOROLOGICAL OBS AT / DATE / TIME</th>
                    <td>{now.get('local_datetime','—')} (Local) / {now.get('utc_datetime','—')} (UTC)</td>
                </tr>
                <tr>
                    <th>AERODROME IDENTIFICATION</th>
                    <td>{now.get('kotkab','—')} ({now.get('adm2','—')})</td>
                </tr>
                <tr>
                    <th>SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</th>
                    <td>{wind_info} / Variation: {wind_variation}</td>
                </tr>
                <tr>
                    <th>HORIZONTAL VISIBILITY</th>
                    <td>{visibility_m} m ({now.get('vs_text','—')})</td>
                </tr>
                <tr>
                    <th>RUNWAY VISUAL RANGE</th>
                    <td>— (RVR not available)</td>
                </tr>
                <tr>
                    <th>PRESENT WEATHER</th>
                    <td>{now.get('weather_desc','—')} (Accum. Rain: {now.get('tp',0):.1f} mm)</td>
                </tr>
                <tr>
                    <th>AMOUNT AND HEIGHT OF BASE OF LOW CLOUD</th>
                    <td>Cloud Cover: {now.get('tcc','—')}% / {ceiling_full_desc}</td>
                </tr>
                <tr>
                    <th>AIR TEMPERATURE AND DEW POINT TEMPERATURE</th>
                    <td>Air Temp: {now.get('t','—')}°C / Dew Point: {dewpt_disp} / RH: {now.get('hu','—')}%</td>
                </tr>
                <tr>
                    <th>QNH</th>
                    <td>
                        .................. mbs<br>
                        .................. ins*<br>
                        .................. mm Hg*
                        <span style='font-size: 0.75rem; color:#777;'> (Barometric Data not available from Source)</span>
                    </td>
                </tr>
                <tr>
                    <th>QFE*</th>
                    <td>
                        .................. mbs<br>
                        .................. ins*<br>
                        .................. mm Hg*
                    </td>
                </tr>
                <tr>
                    <th>SUPPLEMENTARY INFORMATION</th>
                    <td>{now.get('provinsi','—')} / Latitude: {now.get('lat','—')}, Longitude: {now.get('lon','—')}</td>
                </tr>
                <tr>
                    <th>TIME OF ISSUE (UTC) / OBSERVER</th>
                    <td>{now.get('utc_datetime','—')} / FCST ON DUTY</td>
                </tr>
            </table>
        </div>
        """
        # 📌 END: MEMBANGUN HTML UNTUK LAPORAN QAM

        # Menggabungkan CSS dan konten HTML untuk file yang diunduh
        full_qam_html = f"<html><head>{CSS_STYLES}</head><body>{met_report_html_content}</body></html>"

        st.markdown("---")
        st.subheader("📝 Meteorological Report (QAM/Form Replication)")
        st.markdown(met_report_html_content, unsafe_allow_html=True)
        
        # Implementasi tombol Download QAM
        qam_filename = f"MET_REPORT_{loc_choice}_{now.get('local_datetime','—').replace(' ', '_').replace(':','')}.html"
        st.download_button(
            label="⬇ Download QAM Report (HTML)",
            data=full_qam_html,
            file_name=qam_filename,
            mime="text/html",
            help="Unduh laporan QAM sebagai file HTML. Buka di browser dan gunakan fungsi 'Cetak ke PDF' untuk konversi formal."
        )
        st.markdown("---")

# =====================================
# === DECISION MATRIX (KRUSIAL)
# =====================================
    ifr_vfr = classify_ifr_vfr(now.get("vs"), ceiling_est_ft)
    takeoff_reco, landing_reco, reco_rationale = takeoff_landing_recommendation(now.get("ws_kt"), now.get("vs"), now.get("tp"))

    st.markdown("---")
    st.subheader("🔴 Operational Decision Matrix")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Regulatory Category**")
        ifr_badge = badge_html(ifr_vfr)
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{ifr_badge}  <strong style='margin-left:8px;'>{ifr_vfr}</strong></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("**Takeoff Recommendation**")
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(takeoff_reco)}  <strong style='margin-left:8px;'>{takeoff_reco}</strong></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("**Landing Recommendation**")
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(landing_reco)}  <strong style='margin-left:8px;'>{landing_reco}</strong></div>", unsafe_allow_html=True)

    # Rationale / Notes
    st.markdown("**Rationale / Notes:**")
    for r in reco_rationale:
        st.markdown(f"- {r}")
    st.markdown("---")

# =====================================
# 📈 TRENDS
# =====================================
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
            
            # PERBAIKAN: Menghapus observed=True
            df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True) 
            
            speed_bins = [0,5,10,20,30,50,100]
            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
            
            # PERBAIKAN: Menghapus observed=True
            df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
            
            # PERBAIKAN: Menghapus observed=True dari groupby
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
        else:
            st.info("Insufficient wind data for Windrose plot.")
    else:
        st.info("Wind data (wd_deg, ws_kt) not available in dataset for windrose.")

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
    # Tombol download QAM sudah dipindahkan ke dalam blok show_qam_report di atas.
    csv = df_sel.to_csv(index=False)
    json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
    colA, colB = st.columns(2)
    with colA:
        st.download_button("⬇ CSV", csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
    with colB:
        st.download_button("⬇ JSON", json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")


# BLOK EXCEPT DIMULAI DI SINI UNTUK MENUTUP BLOK TRY
except requests.exceptions.HTTPError as e:
    st.error(f"API Error: Could not fetch data. Check Province Code (ADM1). Status code: {e.response.status_code}")
except requests.exceptions.ConnectionError:
    st.error("Connection Error: Could not connect to BMKG API.")
except Exception as e:
    # Error ini akan menangkap error lain yang tidak terduga.
    st.error(f"An unexpected error occurred: {e}")

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
