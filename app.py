import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG (Revised API)", layout="wide")

# =====================================
# 🌑 CSS — MILITARY STYLE
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

/* Custom CSS for METAR Block (Dihapus dari skrip utama, namun CSS-nya tetap di sini) */
.metar-block {
    background-color: #1a2a1f;
    border: 1px solid #3f4f3f;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-family: 'Consolas', monospace;
    font-size: 1.1rem;
    color: #b6ff6d;
    overflow-x: auto; /* Untuk METAR yang sangat panjang */
}
.metar-title {
    color: #9adf4f;
    font-size: 0.9rem;
    text-transform: uppercase;
    margin-bottom: 8px;
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

/* -----------------------------
   HUD wrapper specific styles
   ----------------------------- */
#f16hud-wrapper[data-mode='day'] #f16hud-container {
    background: rgba(200, 255, 200, 0.12);
    border-color: #7fbf7f;
    box-shadow: 0 0 10px #7f7 inset;
}
#f16hud-wrapper[data-mode='night'] #f16hud-container {
    background: rgba(0, 10, 0, 0.75);
    border-color: #0f0;
    box-shadow: 0 0 20px #0f0 inset;
}
#f16hud-container {
    width: 100%;
    background: rgba(0, 10, 0, 0.70);
    border: 1px solid #1f3;
    border-radius: 12px;
    padding: 12px;
    margin-top: 18px;
    box-shadow: 0 0 15px #0f0 inset;
}
#f16hud-title {
    color: #0f0;
    font-size: 1.05rem;
    text-align: center;
    margin-bottom: 8px;
    text-shadow: 0 0 6px #0f0;
}
#f16hud-svg {
    width: 100%;
    height: 220px;
    display: block;
    margin: auto;
}
.hud-glow {
    stroke: #0f0;
    stroke-width: 2;
    fill: none;
    filter: drop-shadow(0 0 6px #0f0);
}
#hud-wind-arrow {
    stroke-width: 3;
    stroke-linecap: round;
    animation: windPulse 1.8s infinite ease-in-out;
}
@keyframes windPulse {
    0%   { stroke-opacity: 0.4; }
    50%  { stroke-opacity: 1.0; }
    100% { stroke-opacity: 0.4; }
}
</style>
""", unsafe_allow_html=True)

# =====================================
# 🟢 HUD + DAY/NIGHT LOGIC
# =====================================

# Helper: safe numeric getters to avoid formatting errors
def safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return float(val)
    except Exception:
        return default

def safe_int(val, default=0):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return int(round(float(val)))
    except Exception:
        return default

# Day/night control in sidebar (hybrid Auto + manual override)
with st.sidebar:
    st.markdown("---")
    st.subheader("🌗 Display Mode")
    override_mode = st.selectbox("Override Mode", ["Auto", "Day", "Night"], index=0)

def get_day_night_mode(mode_choice):
    if mode_choice == "Day": return "day"
    if mode_choice == "Night": return "night"
    # AUTO MODE (local)
    hour = datetime.now().hour
    return "day" if 6 <= hour < 18 else "night"

CURRENT_MODE = get_day_night_mode(override_mode)

# =====================================
# 📡 KONFIGURASI API (DIPERBARUI)
# =====================================
# Mengganti ke API Data Terbuka BMKG yang resmi
API_BASE = "https://api.bmkg.go.id/publik/prakiraan-cuaca" 
MS_TO_KT = 1.94384 # konversi ke knot
METER_TO_SM = 0.000621371 # 1 meter = 0.000621371 statute miles (SM)

# =====================================
# 🧰 UTILITAS
# =====================================
@st.cache_data(ttl=300)
# Mengubah parameter ke adm4_code dan menggunakan adm4 di params
def fetch_forecast(adm4_code: str):
    params = {"adm4": adm4_code} 
    resp = requests.get(API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

# Mengubah fungsi flatten agar sesuai dengan struktur API Data Terbuka
def flatten_forecast_list(raw_data: dict):
    # API baru memiliki list forecast di key 'data'
    forecast_list = raw_data.get("data", [])
    rows = []
    
    for obs in forecast_list:
        r = obs.copy()
        
        # Nama key datetime berbeda di API baru (menggunakan 'datetime')
        dt_str = r.get("datetime")
        if dt_str:
            # Format: YYYYMMDDHHmmss. Asumsi UTC dari BMKG, dikonversi ke WIB (Asia/Jakarta)
            r["utc_datetime_dt"] = pd.to_datetime(dt_str, format='%Y%m%d%H%M%S', errors="coerce", utc=True)
            r["local_datetime_dt"] = r["utc_datetime_dt"].dt.tz_convert('Asia/Jakarta')
            r["utc_datetime"] = r["utc_datetime_dt"].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            r["local_datetime"] = r["local_datetime_dt"].dt.strftime('%Y-%m-%d %H:%M:%S WIB')
        else:
            r["utc_datetime_dt"] = pd.NaT
            r["local_datetime_dt"] = pd.NaT
            r["utc_datetime"] = "—"
            r["local_datetime"] = "—"
            
        # Tambahkan placeholder untuk kolom lokasi yang hilang
        r["adm1"] = "N/A"
        r["adm2"] = "N/A"
        r["provinsi"] = "Unknown Province"
        r["kotkab"] = "Specific Location"
        r["lon"] = 0.0
        r["lat"] = 0.0
            
        rows.append(r)

    df = pd.DataFrame(rows)
    # Konversi kolom numerik dengan aman
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    
    # Hitung ws_kt jika 'ws' ada
    if "ws" in df.columns:
        df["ws_kt"] = df["ws"] * MS_TO_KT
    elif "ws_kt" in df.columns:
        df["ws_kt"] = pd.to_numeric(df["ws_kt"], errors="coerce")
    else:
        df["ws_kt"] = np.nan

    return df

def estimate_dewpoint(temp, rh):
    if pd.isna(temp) or pd.isna(rh):
        return None
    # simple approximation (Magnus formula simplification)
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct):
        return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: # 0% - SKC
        return 99999, "SKC (Clear)"
    elif tcc < 25: # 1-25% - FEW
        return 3500, "FEW (>3000 ft)"
    elif tcc < 50: # 25-50% - SCT
        return 2250, "SCT (1500-3000 ft)"
    elif tcc < 75: # 50-75% - BKN
        return 1250, "BKN (1000-1500 ft)"
    else: # >75% - OVC
        return 800, "OVC (<1000 ft)"

def convert_vis_to_sm(visibility_m):
    if pd.isna(visibility_m) or visibility_m is None:
        return "—"
    try:
        vis_m = float(visibility_m)
        vis_sm = vis_m * METER_TO_SM
        if vis_sm < 1:
            return f"{vis_sm:.1f} SM"
        elif vis_sm < 5:
            # Logic untuk menampilkan .0 atau .5 (contoh 3.0 atau 3.5)
            if (vis_sm * 2) % 2 == 0:
                return f"{int(vis_sm)} SM"
            else:
                return f"{vis_sm:.1f} SM"
        else:
            return f"{int(round(vis_sm))} SM"
    except ValueError:
        return "—"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    # Defaulting to 10000m if visibility is missing, for VFR bias (common METAR practice)
    vis_m = safe_float(visibility_m, default=10000)
    vis_sm = vis_m / 1609.34
    
    # Defaulting to a high value if ceiling is missing
    ceil_ft = safe_int(ceiling_ft, default=99999) 

    if vis_sm >= 5 and ceil_ft > 3000: return "VFR"
    if (3 <= vis_sm < 5) or (1000 < ceil_ft <= 3000): return "MVFR"
    if vis_sm < 3 or ceil_ft <= 1000: return "IFR"
    return "Unknown" # Should be rare if defaults applied

def takeoff_landing_recommendation(ws_kt, vs_m, tp_mm):
    rationale = []
    takeoff = "Recommended"
    landing = "Recommended"
    
    ws_kt_val = safe_float(ws_kt)
    vs_m_val = safe_float(vs_m, default=9999) # Default high visibility
    tp_mm_val = safe_float(tp_mm)

    if ws_kt_val >= 30:
        takeoff = "Not Recommended"
        landing = "Not Recommended"
        rationale.append(f"High surface wind: {ws_kt_val:.1f} KT (>=30 KT limit)")
    elif ws_kt_val >= 20:
        rationale.append(f"Strong wind advisory: {ws_kt_val:.1f} KT (>=20 KT advisory)")
        if takeoff == "Recommended": takeoff = "Caution"
        if landing == "Recommended": landing = "Caution"
        
    if vs_m_val < 1000:
        landing = "Not Recommended"
        rationale.append(f"Low visibility: {vs_m_val} m (<1000 m limit)")
    elif vs_m_val < 3000:
        if landing == "Recommended": landing = "Caution"
        rationale.append(f"Reduced visibility: {vs_m_val} m (<3000 m advisory)")

    if tp_mm_val >= 20:
        if takeoff == "Recommended": takeoff = "Caution"
        if landing == "Recommended": landing = "Caution"
        rationale.append(f"Heavy accumulated rain: {tp_mm_val} mm (runway contamination possible)")
    elif tp_mm_val > 5:
        rationale.append(f"Moderate rainfall: {tp_mm_val} mm (slick runway possible)")

    if not rationale:
        rationale.append("Conditions within conservative operational limits.")
        
    return takeoff, landing, rationale

# Visual badge helper
def badge_html(status):
    if status == "VFR" or status == "Recommended" or status == "SKC (Clear)":
        return "<span class='badge-green'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge-yellow'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge-red'>NO-GO</span>"
    return "<span class='badge-yellow'>UNKNOWN</span>"

# =====================================
# 🎚️ SIDEBAR (SEBELUM DATA DIMUAT) - DIPERBARUI
# =====================================
# Definisi awal untuk menghindari UnboundLocalError
df = pd.DataFrame()
df_sel = pd.DataFrame()
now = pd.Series({}) 
icao_code = "WXXX" # Default value
loc_choice = "Specific Location" # Default value

with st.sidebar:
    st.title("🛰️ Tactical Controls")
    # MENGGANTI DARI ADM1 KE ADM4 CODE
    # Contoh Kode ADM4: 31.71.03.1001 (Kel. Kemayoran, Jakarta)
    adm4_code = st.text_input("Village/Kelurahan Code (ADM4)", value="31.71.03.1001")
    icao_code = st.text_input("ICAO Code (WXXX)", value="WXXX", max_chars=4)
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    # Tombol ini hanya memicu rerun, bukan memuat data secara eksplisit di sini
    if st.button("🔄 Fetch Data"):
        st.session_state["rerun_trigger"] = True
    else:
        st.session_state["rerun_trigger"] = False
        
    st.markdown("---")
    # Kontrol Tampilan
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table (Raw Data)", value=False)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True) # Set to True as preferred
    st.markdown("---")
    st.caption("Data Source: BMKG Open Data API · Military Ops v2.2")

# =====================================
# 📡 LOAD DATA (DIPERBARUI)
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Source: BMKG Open Data API — Live Data*")

# BLOK TRY DIMULAI DI SINI
try:
    with st.spinner(f"🛰️ Acquiring weather intelligence for ADM4: {adm4_code}..."):
        # Panggil dengan kode ADM4
        raw = fetch_forecast(adm4_code)
        
    # API Data Terbuka langsung mengembalikan list forecast di key 'data'
    entries = raw.get("data", [])
    
    if not entries:
        st.error(f"Error: API returned no data for ADM4 code: {adm4_code}. Check if the code is correct.")
        # Menghentikan eksekusi
        st.stop()

    # Hapus logic pemilihan lokasi (mapping, selectbox) karena data sudah spesifik
    loc_choice = f"ADM4 Code: {adm4_code}" 

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**🎯 Location Code:** `{adm4_code}`")
    with col2:
        st.metric("📍 Forecast Points", len(entries))

    # Gunakan fungsi flatten yang baru
    df = flatten_forecast_list(raw)

    if df.empty:
        st.warning("No valid weather data found for selected location.")
        st.stop()
    
# =====================================
# 🕓 SLIDER WAKTU
# =====================================
    use_col = None
    min_dt = datetime.now()
    max_dt = min_dt + timedelta(hours=3)

    # Find the correct datetime column and set range
    if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
        df = df.sort_values("local_datetime_dt").reset_index(drop=True)
        # Menghilangkan NaT dan mengonversi ke datetime Python untuk slider
        valid_dt = df["local_datetime_dt"].dropna().dt.to_pydatetime()
        if len(valid_dt) > 0:
            min_dt = valid_dt.min()
            max_dt = valid_dt.max()
            use_col = "local_datetime_dt"
    elif "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
        df = df.sort_values("utc_datetime_dt").reset_index(drop=True)
        valid_dt = df["utc_datetime_dt"].dropna().dt.to_pydatetime()
        if len(valid_dt) > 0:
            min_dt = valid_dt.min()
            max_dt = valid_dt.max()
            use_col = "utc_datetime_dt"

    # slider only when datetime exists and there is data
    if use_col and len(df) > 0:
        # Menentukan nilai default slider
        default_start = min_dt
        # Coba ambil data terdekat dengan sekarang sebagai default_start
        if use_col == "local_datetime_dt":
            current_time = datetime.now()
            # Temukan index waktu terdekat
            closest_idx = (df[use_col].dropna() - current_time).abs().argsort().iloc[0]
            default_start = df.loc[closest_idx, use_col].to_pydatetime()
            
        default_end = default_start + pd.Timedelta(hours=3)
        if default_end > max_dt:
             default_end = max_dt
        if default_start > max_dt:
             default_start = max_dt
             
        # Memindahkan slider ke Sidebar
        with st.sidebar:
            start_dt = st.slider(
                "Time Range",
                min_value=min_dt,
                max_value=max_dt,
                value=(default_start, default_end),
                step=pd.Timedelta(hours=3),
                format="HH:mm, MMM DD"
            )
        mask = (df[use_col] >= pd.to_datetime(start_dt[0])) & (df[use_col] <= pd.to_datetime(start_dt[1]))
        df_sel = df.loc[mask].copy() # Menggunakan .copy()
    else:
        df_sel = df.copy()
        
    if df_sel.empty:
        st.warning("No data in selected time range. Showing the first available forecast point.")
        df_sel = df.head(1).copy()
        if df_sel.empty:
            st.stop()
            
    # Pastikan 'now' adalah baris pertama dari data yang dipilih atau default Series
    now = df_sel.iloc[0].to_dict() if not df_sel.empty else pd.Series({})
    # Konversi kembali ke Series untuk konsistensi dengan kode asli
    now = pd.Series(now)

    # prepare MET REPORT values (diperlukan untuk bagian di bawah dan QAM)
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    
    # Perbaikan: Pastikan tcc adalah float yang valid sebelum dipanggil
    tcc_val = safe_float(now.get("tcc"), default=np.nan)
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(tcc_val)
    ceiling_display = f"{ceiling_est_ft} ft" if ceiling_est_ft is not None and ceiling_est_ft <= 99999 else "—"
    
    # NEW: Konversi Visibilitas ke Statute Miles
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))

    
# =====================================
# ✈ FLIGHT WEATHER STATUS (KEY METRICS)
# =====================================
    st.markdown("---") # Garis pemisah sebelum Key Metrics
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">✈ Key Meteorological Status</div>', unsafe_allow_html=True)
    
    # Ambil nilai dengan aman
    temp_val = now.get('t','—')
    ws_kt_val = safe_float(now.get('ws_kt'), default=0.0)
    wd_deg_val = now.get('wd_deg','—')
    vs_val = now.get('vs','—')
    vs_text_val = now.get('vs_text','—')
    weather_desc_val = now.get('weather_desc','—')
    tp_val = safe_float(now.get('tp'), default=0.0)
    
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.markdown("<div class='metric-label'>Temperature (°C)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{temp_val}</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-note'>Ambient</div>", unsafe_allow_html=True)
    with colB:
        st.markdown("<div class='metric-label'>Wind Speed (KT)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{ws_kt_val:.1f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>{wd_deg_val}°</div>", unsafe_allow_html=True)
    with colC:
        st.markdown("<div class='metric-label'>Visibility (M/SM)</div>", unsafe_allow_html=True) # LABEL DIUBAH
        st.markdown(f"<div class='metric-value'>{vs_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>({vis_sm_disp}) / {vs_text_val}</div>", unsafe_allow_html=True) # NILAI SM DITAMBAH
    with colD:
        st.markdown("<div class='metric-label'>Weather</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{weather_desc_val}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>Rain: {tp_val:.1f} mm (Accum.)</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


    # -----------------------------
    # INSERT HUD (MODE B) — PANEL
    # -----------------------------
    # Render HUD wrapper with data-mode attribute so CSS picks Day/Night
    hud_wrapper_open = f"<div id='f16hud-wrapper' data-mode='{CURRENT_MODE}'>"
    st.markdown(hud_wrapper_open, unsafe_allow_html=True)
    st.markdown("<div id='f16hud-container'>", unsafe_allow_html=True)
    st.markdown("<div id='f16hud-title'>F-16 TACTICAL HUD OVERLAY — PANEL (Mode B)</div>", unsafe_allow_html=True)

    # dynamic HUD variables (safe)
    _wdir = safe_int(now.get("wd_deg"), default=0)
    _wspd = safe_float(now.get("ws_kt"), default=0.0)
    _vis = safe_int(now.get("vs"), default=9999) # Defaulting visibility to high
    _ceil = safe_int(ceiling_est_ft, default=99999)

    # limit wind arrow length so it fits nicely
    max_arrow_len = 120
    arrow_len = min(max_arrow_len, int(_wspd * 3))  # scaling factor for visibility in HUD

    # Compute end point of arrow relative to center (400,150) used below
    dx = np.sin(np.radians(_wdir)) * arrow_len
    dy = -np.cos(np.radians(_wdir)) * arrow_len  # negative because SVG Y increases downward

    hud_svg = f"""
    <svg id="f16hud-svg" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet">
      <line x1="50" y1="150" x2="750" y2="150" class="hud-glow" stroke="#0f0" stroke-width="1.5"/>
      <line x1="140" y1="120" x2="200" y2="120" class="hud-glow" stroke="#0f0" stroke-width="1"/>
      <line x1="140" y1="180" x2="200" y2="180" class="hud-glow" stroke="#0f0" stroke-width="1"/>
      <text x="400" y="42" fill="#0f0" font-size="22" text-anchor="middle">HDG {_wdir:03d}°</text>
      <line id="hud-wind-arrow" x1="400" y1="150" x2="{400 + dx:.1f}" y2="{150 + dy:.1f}" stroke="#0f0" />
      <polygon points="{400 + dx:.1f},{150 + dy:.1f} {400 + dx - 6:.1f},{150 + dy - 6:.1f} {400 + dx + 6:.1f},{150 + dy - 6:.1f}" fill="#0f0"/>
      <text x="400" y="190" fill="#0f0" font-size="18" text-anchor="middle">WIND {_wdir}° / {_wspd:.1f} KT</text>
      <text x="120" y="260" fill="#0f0" font-size="16">VIS: {_vis} m ({convert_vis_to_sm(_vis)})</text>
      <text x="680" y="260" fill="#0f0" font-size="16" text-anchor="end">CEIL: {_ceil} ft</text>
      <rect x="18" y="18" width="110" height="28" fill="rgba(0,0,0,0.3)" stroke="#0f0" rx="6"/>
      <text x="74" y="36" fill="#0f0" font-size="12" text-anchor="middle">TACTICAL</text>
    </svg>
    """

    st.markdown(hud_svg, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)  # close container
    st.markdown("</div>", unsafe_allow_html=True)  # close wrapper

# =====================================
# ☁ METEOROLOGICAL DETAILS (SECONDARY) - REVISI
# =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">☁ Meteorological Details</div>', unsafe_allow_html=True)

    detail_col1, detail_col2 = st.columns(2)

    # Ambil nilai tambahan dengan aman. Nilai lokasi menggunakan placeholder.
    hu_val = now.get('hu','—')
    wd_val = now.get('wd','—')
    provinsi_val = now.get('provinsi','—') # Placeholder
    kotkab_val = now.get('kotkab','—') # Placeholder
    local_dt_val = now.get('local_datetime','—')
    utc_dt_val = now.get('utc_datetime','—')
    # analysis_date tidak ada di API baru, ganti dengan datetime
    analysis_date_val = now.get('utc_datetime','—') 
    weather_val = now.get('weather','—')
    lat_val = now.get('lat','—') # Placeholder
    lon_val = now.get('lon','—') # Placeholder
    
    with detail_col1:
        st.markdown("##### 🌡️ Atmospheric State")
        # Row 1: Temperature & Dew Point
        col_t, col_dp = st.columns(2)
        with col_t:
            st.markdown("<div class='metric-label'>Air Temperature (°C)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{temp_val}°C</div>", unsafe_allow_html=True)
        with col_dp:
            st.markdown("<div class='metric-label'>Dew Point (Est)</div>", unsafe_allow_html=True)
            st.markdown(f"<div classs='detail-value'>{dewpt_disp}</div>", unsafe_allow_html=True)

        # Row 2: Humidity & Wind Dir Code
        col_hu, col_wd = st.columns(2)
        with col_hu:
            st.markdown("<div class='metric-label'>Relative Humidity (%)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{hu_val}%</div>", unsafe_allow_html=True)
        with col_wd:
            st.markdown("<div class='metric-label'>Wind Direction (Code)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{wd_val} ({wd_deg_val}°)</div>", unsafe_allow_html=True)
        
        # Row 3: Location Details (Moved here)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_prov, col_city = st.columns(2)
        with col_prov:
            st.markdown("<div classs='metric-label'>Province</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{provinsi_val}</div>", unsafe_allow_html=True)
        with col_city:
            st.markdown("<div class='metric-label'>City/Regency (ADM4 Location)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{kotkab_val}</div>", unsafe_allow_html=True)


    with detail_col2:
        st.markdown("##### 🌁 Sky and Visibility")
        # Row 1: Visibility & Ceiling
        col_vis, col_ceil = st.columns(2)
        with col_vis:
            st.markdown("<div class='metric-label'>Visibility (Metres/SM)</div>", unsafe_allow_html=True) # LABEL DIUBAH
            st.markdown(f"<div class='detail-value'>{vs_val} m</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='small-note'>({vis_sm_disp}) / {vs_text_val}</div>", unsafe_allow_html=True) # NILAI SM DITAMBAH
        with col_ceil:
            st.markdown("<div class='metric-label'>Est. Ceiling Base</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{ceiling_display}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='small-note'>({ceiling_label.split('(')[0].strip()})</div>", unsafe_allow_html=True)

        # Row 2: Cloud Cover & Weather Desc
        col_tcc, col_wx = st.columns(2)
        with col_tcc:
            tcc_display = f"{tcc_val:.0f}%" if not pd.isna(tcc_val) else "—"
            st.markdown("<div class='metric-label'>Cloud Cover (%)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{tcc_display}</div>", unsafe_allow_html=True)
        with col_wx:
            st.markdown("<div class='metric-label'>Present Weather</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value'>{weather_desc_val} ({weather_val})</div>", unsafe_allow_html=True)
        
        # Row 3: Time Index/Local Time
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_local, col_anal = st.columns(2)
        with col_local:
            st.markdown("<div classs='metric-label'>Local Forecast Time</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{local_dt_val}</div>", unsafe_allow_html=True)
        with col_anal:
            st.markdown("<div class='metric-label'>Forecast Data Time (UTC)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{analysis_date_val}</div>", unsafe_allow_html=True)


    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# === MET REPORT (QAM REPLICATION) - DIPINDAHKAN KE SIDEBAR
# =====================================

    if show_qam_report:
        # prepare MET REPORT values
        wind_info = f"{wd_deg_val}° / {ws_kt_val:.1f} KT"
        wind_variation = "Not available (BMKG Forecast)"  
        ceiling_full_desc = f"Est. Base: {ceiling_est_ft} ft ({ceiling_label.split('(')[0].strip()})" if ceiling_est_ft is not None and ceiling_est_ft <= 99999 else "—"


        # 📌 START: MEMBANGUN HTML UNTUK LAPORAN QAM
        met_report_html_content = f"""
        <div class="met-report-container">
            <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
            <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
            <div class="met-report-header" style="border-top: none;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
            <table class="met-report-table">
                <tr>
                    <th>METEOROLOGICAL OBS AT / DATE / TIME</th>
                    <td>{local_dt_val} (WIB) / {utc_dt_val} (UTC)</td>
                </tr>
                <tr>
                    <th>AERODROME IDENTIFICATION</th>
                    <td>{icao_code} / ADM4: {adm4_code}</td>
                </tr>
                <tr>
                    <th>SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</th>
                    <td>{wind_info} / Variation: {wind_variation}</td>
                </tr>
                <tr>
                    <th>HORIZONTAL VISIBILITY</th>
                    <td>{vs_val} m ({vis_sm_disp}) / {vs_text_val}</td> </tr>
                <tr>
                    <th>RUNWAY VISUAL RANGE</th>
                    <td>— (RVR not available)</td>
                </tr>
                <tr>
                    <th>PRESENT WEATHER</th>
                    <td>{weather_desc_val} (Accum. Rain: {tp_val:.1f} mm)</td>
                </tr>
                <tr>
                    <th>AMOUNT AND HEIGHT OF BASE OF LOW CLOUD</th>
                    <td>Cloud Cover: {tcc_display} / {ceiling_full_desc}</td>
                </tr>
                <tr>
                    <th>AIR TEMPERATURE AND DEW POINT TEMPERATURE</th>
                    <td>Air Temp: {temp_val}°C / Dew Point: {dewpt_disp} / RH: {hu_val}%</td>
                </tr>
                <tr>
                    <th>QNH</th>
                    <td>
                        ................. mbs<br>
                        ................. ins*<br>
                        ................. mm Hg*
                        <span style='font-size: 0.75rem; color:#777;'> (Barometric Data not available from Source)</span>
                    </td>
                </tr>
                <tr>
                    <th>QFE*</th>
                    <td>
                        ................. mbs<br>
                        ................. ins*<br>
                        ................. mm Hg*
                    </td>
                </tr>
                <tr>
                    <th>SUPPLEMENTARY INFORMATION</th>
                    <td>{provinsi_val} / Code: {adm4_code} / Lat: {lat_val}, Lon: {lon_val}</td>
                </tr>
                <tr>
                    <th>TIME OF ISSUE (UTC) / OBSERVER</th>
                    <td>{utc_dt_val} / FCST ON DUTY</td>
                </tr>
            </table>
        </div>
        """
        # 📌 END: MEMBANGUN HTML UNTUK LAPORAN QAM

        # Menggabungkan CSS dan konten HTML untuk file yang diunduh
        qam_datetime_safe = local_dt_val.replace(' ', '_').replace(':','').replace('-','')
        full_qam_html = f"<html><head>{CSS_STYLES}</head><body>{met_report_html_content}</body></html>"

        st.markdown("---")
        st.subheader("📝 Meteorological Report (QAM/Form Replication)")
        st.markdown(met_report_html_content, unsafe_allow_html=True)
        
        # Implementasi tombol Download QAM
        qam_filename = f"MET_REPORT_{adm4_code}_{qam_datetime_safe}.html"
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
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{ifr_badge}  <strong style='margin-left:8px;'>{ifr_vfr}</strong></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("**Takeoff Recommendation**")
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(takeoff_reco)}  <strong style='margin-left:8px;'>{takeoff_reco}</strong></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("**Landing Recommendation**")
        st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(landing_reco)}  <strong style='margin-left:8px;'>{landing_reco}</strong></div>", unsafe_allow_html=True)

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
    # Check if required columns exist and df_sel is not empty before plotting
    if not df_sel.empty and "local_datetime_dt" in df_sel.columns:
        with c1:
            if "t" in df_sel.columns:
                st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
            if "hu" in df_sel.columns:
                st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity"), use_container_width=True)
        with c2:
            if "ws_kt" in df_sel.columns:
                st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind (KT)"), use_container_width=True)
            if "tp" in df_sel.columns:
                st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall"), use_container_width=True)
    else:
        st.info("Insufficient data for plotting trends in the selected time range.")


# =====================================
# 🌪️ WINDROSE (ASLI)
# =====================================
    st.markdown("---")
    st.subheader("🌪️ Windrose — Direction & Speed")
    if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
        df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"]).copy() # Menggunakan .copy()
        if not df_wr.empty:
            bins_dir = np.arange(-11.25,360,22.5)
            labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                          "S","SSW","SW","WSW","W","WNW","NW","NNW"]
            
            # Penggunaan .loc[] untuk menghindari SettingWithCopyWarning
            df_wr.loc[:,"dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)  
            
            speed_bins = [0,5,10,20,30,50,100]
            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
            
            df_wr.loc[:,"speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
            
            # Pastikan kategori arah angin lengkap untuk polar plot
            all_sectors = pd.Categorical(labels_dir, categories=labels_dir, ordered=True)
            freq = df_wr.groupby(["dir_sector","speed_class"], observed=True).size().reset_index(name="count")
            
            # Isi data yang hilang dengan 0
            multi_index = pd.MultiIndex.from_product([all_sectors.categories, speed_labels], names=["dir_sector", "speed_class"])
            freq = freq.set_index(["dir_sector", "speed_class"]).reindex(multi_index).fillna(0).reset_index()
            
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
            # Lat dan Lon disetel ke 0.0 karena API baru tidak menyediakannya.
            # Map akan menampilkan di (0, 0) kecuali Anda mengganti nilai placeholder lat/lon.
            lat = safe_float(now.get("lat", 0.0))
            lon = safe_float(now.get("lon", 0.0))
            if lat != 0.0 or lon != 0.0:
                 st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
            else:
                 st.warning(f"Map coordinates are unavailable for ADM4 code {adm4_code}.")
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
# 💾 EXPORT (DIPERBARUI)
# =====================================
    st.markdown("---")
    st.subheader("💾 Export Data")
    if not df_sel.empty:
        csv = df_sel.to_csv(index=False)
        json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
        colA, colB = st.columns(2)
        with colA:
            # Mengganti adm1 dengan adm4_code
            st.download_button("⬇ CSV", csv, file_name=f"{adm4_code}_{loc_choice}.csv", mime="text/csv")
        with colB:
            # Mengganti adm1 dengan adm4_code
            st.download_button("⬇ JSON", json_text, file_name=f"{adm4_code}_{loc_choice}.json", mime="application/json")
    else:
         st.info("No data available to export.")


# BLOK EXCEPT DIMULAI DI SINI UNTUK MENUTUP BLOK TRY (DIPERBARUI)
except requests.exceptions.HTTPError as e:
    # HTTPError (e.g., 404 Not Found, 500 Server Error)
    st.error(f"API Error: Could not fetch data. Check ADM4 Code and ensure the API is operational. Status code: {e.response.status_code}")
    # st.exception(e) # Uncomment for detailed traceback if needed
except requests.exceptions.ConnectionError:
    # Connection Error yang diharapkan
    st.error("Connection Error: Could not connect to BMKG Data Terbuka API. Check your internet connection or the external API status.")
except Exception as e:
    # Error lain yang tidak terduga.
    st.error(f"An unexpected error occurred: {e}")
    # st.exception(e) # Uncomment for detailed traceback if needed

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data Terbuka © 2025<br>
Military Ops UI · Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
