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
# 🌐 TRANSLATION DICTIONARY
# =====================================
# Define language options and their corresponding keys
LANGUAGES = {
    "Bahasa Indonesia 🇮🇩": "ID",
    "English (US) 🇺🇸": "EN"
}

# Core application texts translated (minimal set for demonstration)
TRANSLATIONS = {
    "ID": {
        "title_main": "Tactical Weather Operations Dashboard",
        "title_subtitle": "Sumber: BMKG Forecast API — Data Langsung",
        "nav_home": "Beranda (Info)",
        "nav_dashboard": "Dasbor (Operasi Langsung)",
        "sidebar_controls": "🛰️ Kontrol Taktis",
        "dashboard_config": "Konfigurasi Dasbor",
        "fetch_data": "🔄 Ambil Data",
        "show_map": "Tampilkan Peta",
        "show_table": "Tampilkan Tabel (Data Mentah)",
        "show_qam": "Tampilkan Laporan MET (QAM)",
        "home_page_title": "Selamat Datang di Dasbor Operasi Cuaca Taktis",
        "warning_title": "PERINGATAN OPERASIONAL:",
        "warning_text_1": "Data ini bersumber dari",
        "warning_text_2": ". Ini adalah",
        "warning_text_3": "(FORECAST), bukan Observasi Real-Time (METAR). Gunakan untuk perencanaan, bukan untuk keputusan Take-Off/Landing final tanpa data METAR/AWOS aktual.",
        "about_system": "1. Tentang Sistem Ini",
        "data_source_limits": "2. Sumber Data dan Batasan",
        "key_features": "3. Fitur Kunci",
        # Tambahkan terjemahan lain di sini jika diperlukan
    },
    "EN": {
        "title_main": "Tactical Weather Operations Dashboard",
        "title_subtitle": "Source: BMKG Forecast API — Live Data",
        "nav_home": "Home (Info)",
        "nav_dashboard": "Dashboard (Live Ops)",
        "sidebar_controls": "🛰️ Tactical Controls",
        "dashboard_config": "Dashboard Configuration",
        "fetch_data": "🔄 Fetch Data",
        "show_map": "Show Map",
        "show_table": "Show Table (Raw Data)",
        "show_qam": "Show MET Report (QAM)",
        "home_page_title": "Welcome to the Tactical Weather Operations Dashboard",
        "warning_title": "OPERATIONAL WARNING:",
        "warning_text_1": "This data is sourced from the",
        "warning_text_2": ". This is a",
        "warning_text_3": "(FORECAST), not Real-Time Observation (METAR). Use for planning, not for final Take-Off/Landing decisions without actual METAR/AWOS data.",
        "about_system": "1. About This System",
        "data_source_limits": "2. Data Source and Limitations",
        "key_features": "3. Key Features",
    }
}

# Set default language if not in session state
if 'language' not in st.session_state:
    st.session_state['language'] = "ID"

# Helper function to get translated text
def get_text(key):
    lang_key = st.session_state['language']
    # Fallback logic: 1. Selected Lang -> 2. ID Lang -> 3. Key as string
    return TRANSLATIONS.get(lang_key, TRANSLATIONS['ID']).get(key, TRANSLATIONS['ID'].get(key, key))


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
/* Custom CSS for METAR Block */
.metar-block {
    background-color: #1a2a1f;
    border: 1px solid #3f4f3f;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-family: 'Consolas', monospace;
    font-size: 1.1rem;
    color: #b6ff6d;
    overflow-x: auto;
}
.metar-title {
    color: #9adf4f;
    font-size: 0.9rem;
    text-transform: uppercase;
    margin-bottom: 8px;
}

</style>
"""

# Menyuntikkan seluruh CSS ke Streamlit
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
/* Wind Barb specific styles */
.wind-barb-line {
    stroke: #0f0;
    stroke-width: 2.5;
    fill: none;
    stroke-linecap: round;
}
.wind-barb-flag {
    fill: #0f0;
}
/* CSS untuk inline Wind Barb */
.inline-barb-container {
    display: flex; 
    align-items: center;
    gap: 5px; /* Spasi antar elemen */
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
        
# Fungsi 1: Menghasilkan kode SVG Wind Barb Skala Besar (untuk HUD)
def generate_hud_wind_barb_svg(wdir, wspd_kt, center_x, center_y, scale=1.0):
    if wspd_kt < 2.5: # Kurang dari 2 knot, anggap Calm
        return f'<circle cx="{center_x}" cy="{center_y}" r="{5*scale}" class="hud-glow" fill="none" stroke="#0f0" stroke-width="2"/>' # Simbol Calm
    
    rotation_angle = wdir - 180 
    barb_length = 30 * scale
    y_end = center_y - barb_length

    svg_barb = f'<g transform="translate({center_x}, {center_y}) rotate({rotation_angle})">'
    svg_barb += f'<line x1="0" y1="0" x2="0" y2="{-barb_length}" class="wind-barb-line"/>'
    
    y_feather_start = -barb_length
    y_offset = 0
    remaining_wspd = wspd_kt
    
    while remaining_wspd >= 47.5:
        svg_barb += f'<polygon points="0, {y_feather_start + y_offset} 6, {y_feather_start + y_offset + 5} 0, {y_feather_start + y_offset + 10}" class="wind-barb-flag"/>'
        y_offset += 10
        remaining_wspd -= 50
    
    while remaining_wspd >= 7.5:
        svg_barb += f'<line x1="0" y1="{y_feather_start + y_offset}" x2="10" y2="{y_feather_start + y_offset + 5}" class="wind-barb-line"/>'
        y_offset += 7
        remaining_wspd -= 10
        
    if remaining_wspd >= 2.5:
        svg_barb += f'<line x1="0" y1="{y_feather_start + y_offset}" x2="5" y2="{y_feather_start + y_offset + 2.5}" class="wind-barb-line"/>'
    
    svg_barb += '</g>'
    return svg_barb

# Fungsi 2: Menghasilkan kode HTML/SVG Wind Barb Skala Kecil (untuk Inline)
def generate_inline_wind_barb_html(wdir, wspd_kt, size=30):
    # size = tinggi SVG viewBox
    # center_x dan center_y untuk viewBox kecil (e.g., 15, 15)
    center_x = size / 2
    center_y = size / 2
    barb_length = size * 0.7 
    COLOR = "#b6ff6d" # Warna hijau neon

    if wspd_kt < 2.5: 
        # Simbol Calm
        calm_symbol = f'''
            <circle cx="{center_x}" cy="{center_y}" r="{(size*0.1)}" fill="none" stroke="{COLOR}" stroke-width="1.5"/>
            <line x1="{center_x-4}" y1="{center_y}" x2="{center_x+4}" y2="{center_y}" stroke="{COLOR}" stroke-width="1.5" stroke-linecap="round"/>
        '''
        return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="vertical-align: middle; flex-shrink: 0; margin-top: -3px;">{calm_symbol}</svg>'

    # Rotasi: WDIR (dari mana angin datang) - 180 derajat
    rotation_angle = wdir - 180
    
    svg_content = f'<g transform="translate({center_x}, {center_y}) rotate({rotation_angle})">'
    
    # Garis utama barb
    svg_content += f'<line x1="0" y1="0" x2="0" y2="{-barb_length}" stroke="{COLOR}" stroke-width="1.5" stroke-linecap="round"/>'
    
    y_feather_start = -barb_length
    y_offset = 0

    remaining_wspd = wspd_kt
    
    # 50 KT Flags
    while remaining_wspd >= 47.5:
        svg_content += f'<polygon points="0, {y_feather_start + y_offset} 4, {y_feather_start + y_offset + 3} 0, {y_feather_start + y_offset + 6}" fill="{COLOR}"/>'
        y_offset += 6
        remaining_wspd -= 50
    
    # 10 KT Full Barb
    while remaining_wspd >= 7.5:
        svg_content += f'<line x1="0" y1="{y_feather_start + y_offset}" x2="7" y2="{y_feather_start + y_offset + 3.5}" stroke="{COLOR}" stroke-width="1.5" stroke-linecap="round"/>'
        y_offset += 5
        remaining_wspd -= 10
        
    # 5 KT Half Barb
    if remaining_wspd >= 2.5:
        svg_content += f'<line x1="0" y1="{y_feather_start + y_offset}" x2="3.5" y2="{y_feather_start + y_offset + 1.75}" stroke="{COLOR}" stroke-width="1.5" stroke-linecap="round"/>'
    
    svg_content += '</g>'
    
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="vertical-align: middle; flex-shrink: 0; margin-top: -3px;">{svg_content}</svg>'


# Day/night control in sidebar (hybrid Auto + manual override)
with st.sidebar:
    st.markdown("---")
    st.subheader("🌗 Display Mode")
    override_mode = st.selectbox("Override Mode", ["Auto", "Day", "Night"], index=0)

def get_day_night_mode():
    if override_mode == "Day": return "day"
    if override_mode == "Night": return "night"
    # AUTO MODE (local)
    hour = datetime.now().hour
    return "day" if 6 <= hour < 18 else "night"

CURRENT_MODE = get_day_night_mode()

# =====================================
# 📡 KONFIGURASI API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384 # konversi ke knot
METER_TO_SM = 0.000621371 # 1 meter = 0.000621371 statute miles (SM)

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
            if (vis_sm * 2) % 2 == 0:
                return f"{int(vis_sm)} SM"
            else:
                return f"{vis_sm:.1f} SM"
        else:
            return f"{int(round(vis_sm))} SM"
    except ValueError:
        return "—"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    if visibility_m is None or pd.isna(visibility_m):
        return "Unknown"
    vis_sm = float(visibility_m) / 1609.34
    if ceiling_ft is None:
        if vis_sm >= 3: return "VFR"
        elif vis_sm >= 1: return "MVFR"
        else: return "IFR"
    if vis_sm >= 5 and ceiling_ft > 3000: return "VFR"
    if (3 <= vis_sm < 5) or (1000 < ceiling_ft <= 3000): return "MVFR"
    if vis_sm < 3 or ceiling_ft <= 1000: return "IFR"
    return "Unknown"

def takeoff_landing_recommendation(ws_kt, vs_m, tp_mm):
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
    if status == "VFR" or status == "Recommended" or status == "SKC (Clear)":
        return "<span class='badge-green'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge-yellow'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge-red'>NO-GO</span>"
    return "<span class='badge-yellow'>UNKNOWN</span>"


# =====================================
# 🏠 HOME PAGE FUNCTION (NEW)
# =====================================
def home_page():
    # Menggunakan terjemahan
    st.title(get_text("home_page_title"))
    
    # Operational Warning (MOVED HERE)
    st.markdown(f"""
    <div style='background-color: #3a2a1f; color: #ffd86b; padding: 15px; border-radius: 6px; margin-bottom: 30px; border: 1px solid #ffaa00; font-size: 1.1rem;'>
        ⚠️ <strong style='color: #fff;'>{get_text('warning_title')}</strong> {get_text('warning_text_1')} <strong style='color: #fff;'>BMKG FORECAST API</strong>{get_text('warning_text_2')} <strong style='color: #fff;'>RAMALAN</strong> {get_text('warning_text_3')}
    </div>
    """, unsafe_allow_html=True)
    
    # Bagian 1: Tentang Sistem Ini
    st.header(get_text("about_system"))
    st.markdown("""
    Sistem **Tactical Weather Operations Dashboard** ini dikembangkan untuk menyediakan analisis prakiraan cuaca meteorologi secara cepat. Data bersumber dari BMKG (Badan Meteorologi, Klimatologi, dan Geofisika) dan disajikan dalam format visual operasional untuk mendukung perencanaan penerbangan.
    """)
    
    # Bagian 2: Sumber Data dan Batasan
    st.header(get_text("data_source_limits"))
    st.markdown("""
    * **Sumber Data:** BMKG Public API for Regional Forecasts.
    * **Jenis Data:** Prakiraan (Forecast) 3-jam ke depan.
    * **Keakuratan:** Data ini merupakan *ramalan* dan mungkin berbeda secara signifikan dari kondisi cuaca aktual di lapangan. Selalu verifikasi dengan laporan observasi cuaca bandara aktual (**METAR** atau **AWOS**) sebelum membuat keputusan Take-Off/Landing final.
    * **Estimasi:** Nilai seperti Dew Point dan Batas Dasar Awan (Ceiling) adalah hasil perhitungan **estimasi** berdasarkan data yang tersedia, bukan observasi langsung.
    """)
    
    # Bagian 3: Fitur Kunci
    st.header(get_text("key_features"))
    st.markdown("""
    * **F-16 Tactical HUD:** Visualisasi cepat status cuaca kritis termasuk angin (menggunakan Wind Barb), visibilitas, dan ketinggian dasar awan.
    * **Operational Decision Matrix:** Klasifikasi otomatis kondisi penerbangan (VFR/MVFR/IFR) dan rekomendasi Take-Off/Landing.
    * **Wind Barb Integration:** Simbol Wind Barb yang akurat diintegrasikan ke dalam metrik kunci dan laporan QAM.
    * **MET Report (QAM):** Replikasi format Laporan Cuaca Militer (QAM) untuk tujuan dokumentasi dan pelaporan.
    """)
    
    st.markdown("---")
    st.caption(f"Versi Aplikasi: v4.0 | Waktu Muat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} WIB")


# =====================================
# 🌐 LANGUAGE SELECTOR UI (TOP RIGHT)
# =====================================
# Gunakan kolom untuk menempatkan pemilih bahasa di kanan atas
lang_col_left, lang_col_right = st.columns([0.8, 0.2])

with lang_col_right:
    # Mendapatkan nama tampilan bahasa yang saat ini dipilih
    current_lang_display = next((k for k, v in LANGUAGES.items() if v == st.session_state['language']), "Bahasa Indonesia 🇮🇩")
    
    # Selectbox untuk memilih bahasa
    selected_lang_display = st.selectbox(
        "Language", 
        options=list(LANGUAGES.keys()), 
        index=list(LANGUAGES.keys()).index(current_lang_display),
        label_visibility="collapsed", # Sembunyikan label "Language"
        key="language_select_ui"
    )
    # Update session state saat pilihan berubah
    st.session_state['language'] = LANGUAGES[selected_lang_display]


# =====================================
# 🎚️ SIDEBAR (SEBELUM DATA DIMUAT)
# =====================================
with st.sidebar:
    # Menggunakan terjemahan
    st.title(get_text("sidebar_controls"))
    
    # 📌 KONTROL NAVIGASI
    nav_options = [get_text("nav_home"), get_text("nav_dashboard")]
    
    # Tentukan index awal yang benar (default ke Dasbor)
    default_index = nav_options.index(get_text("nav_dashboard")) if get_text("nav_dashboard") in nav_options else 1
    
    page_choice = st.radio("Navigation", nav_options, index=default_index, key="nav_radio")
    st.markdown("---")
    
    # Menggunakan terjemahan untuk perbandingan
    if page_choice == get_text("nav_dashboard"):
        # Menggunakan terjemahan
        st.subheader(get_text("dashboard_config"))
        adm1 = st.text_input("Province Code (ADM1)", value="32", key="adm1_input")
        icao_code = st.text_input("ICAO Code (WXXX)", value="WXXX", max_chars=4, key="icao_input")
        st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
        # Menggunakan terjemahan
        st.button(get_text("fetch_data"), key="fetch_button")
        st.markdown("---")
        
        # Menggunakan terjemahan
        show_map = st.checkbox(get_text("show_map"), value=True)
        show_table = st.checkbox(get_text("show_table"), value=False)
        show_qam_report = st.checkbox(get_text("show_qam"), value=True)
        
        # Slider Waktu (Hanya muncul jika Dashboard dipilih dan data ada)
        # Akan didefinisikan kemudian setelah data dimuat
    else:
        adm1 = "32" # Default value needed for the function calls later, though not used here
        icao_code = "WXXX"
        # Dummy variables needed for the main function block, though they won't be used
        show_map = False
        show_table = False
        show_qam_report = False

    st.markdown("---")
    st.caption("Data Source: BMKG API · Military Ops v4.0")


# =====================================
# 🖥️ MAIN CONTROL BLOCK
# =====================================

# Menggunakan terjemahan untuk perbandingan
if page_choice == get_text("nav_home"):
    home_page()
    st.stop() # Stop further execution for Home page

# --- BLOCK BELOW IS FOR DASHBOARD (LIVE OPS) ---

# Menggunakan terjemahan
st.title(get_text("title_main"))
st.markdown(f"*{get_text('title_subtitle')}*")


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
        st.subheader("Pilih Lokasi")
        loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()), label_visibility="collapsed")
    with col2:
        st.metric("📍 Lokasi Tersedia", len(mapping))

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
            st.markdown("---")
            start_dt = st.slider(
                "Time Range (Forecast Time)",
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

    # prepare MET REPORT values (diperlukan untuk bagian di bawah dan QAM)
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
    ceiling_display = f"{ceiling_est_ft} ft" if ceiling_est_ft is not None and ceiling_est_ft <= 99999 else "—"
    
    # Konversi Visibilitas ke Statute Miles
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))

    # dynamic HUD variables (safe) 
    _wdir = safe_int(now.get("wd_deg"), default=0)
    _wspd = safe_float(now.get("ws_kt"), default=0.0)
    _vis = safe_int(now.get("vs"), default=0)
    _ceil = safe_int(ceiling_est_ft, default=0)
    
# =====================================
# ✈ FLIGHT WEATHER STATUS (KEY METRICS)
# =====================================
    st.markdown("---") # Garis pemisah sebelum Key Metrics
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">✈ Key Meteorological Status</div>', unsafe_allow_html=True)
    
    colA, colB, colC, colD = st.columns(4)
    
    # Generate inline wind barb for Key Metrics
    wind_barb_inline_key = generate_inline_wind_barb_html(_wdir, _wspd, size=30)
    
    with colA:
        st.markdown("<div class='metric-label'>Temperature (°C)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('t','—')}</div>", unsafe_allow_html=True)
        st.markdown("<div class='small-note'>Ambient</div>", unsafe_allow_html=True)
    with colB:
        st.markdown("<div class='metric-label'>Wind Speed (KT)</div>", unsafe_allow_html=True)
        # Menyertakan Wind Barb inline
        st.markdown(f"<div class='metric-value inline-barb-container'>{wind_barb_inline_key} {_wspd:.1f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>{_wdir}°</div>", unsafe_allow_html=True)
    with colC:
        st.markdown("<div class='metric-label'>Visibility (M/SM)</div>", unsafe_allow_html=True) 
        st.markdown(f"<div class='metric-value'>{now.get('vs','—')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>({vis_sm_disp}) / {now.get('vs_text','—')}</div>", unsafe_allow_html=True) 
    with colD:
        st.markdown("<div class='metric-label'>Weather</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small-note'>Rain: {now.get('tp',0):.1f} mm (Accum.)</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


    # -----------------------------
    # INSERT HUD (MODE B) — PANEL
    # -----------------------------
    # Render HUD wrapper with data-mode attribute so CSS picks Day/Night
    hud_wrapper_open = f"<div id='f16hud-wrapper' data-mode='{CURRENT_MODE}'>"
    st.markdown(hud_wrapper_open, unsafe_allow_html=True)
    st.markdown("<div id='f16hud-container'>", unsafe_allow_html=True)
    st.markdown("<div id='f16hud-title'>F-16 TACTICAL HUD OVERLAY — PANEL (Mode B)</div>", unsafe_allow_html=True)

    # Generate Wind Barb SVG (Skala Besar)
    wind_barb_svg_code = generate_hud_wind_barb_svg(
        wdir=_wdir, 
        wspd_kt=_wspd, 
        center_x=400, 
        center_y=150, 
        scale=1.0
    )


    hud_svg = f"""
    <svg id="f16hud-svg" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet">
      <line x1="50" y1="150" x2="750" y2="150" class="hud-glow" stroke="#0f0" stroke-width="1.5"/>
      <line x1="140" y1="120" x2="200" y2="120" class="hud-glow" stroke="#0f0" stroke-width="1"/>
      <line x1="140" y1="180" x2="200" y2="180" class="hud-glow" stroke="#0f0" stroke-width="1"/>
      <text x="400" y="42" fill="#0f0" font-size="22" text-anchor="middle">HDG {_wdir:03d}°</text>
      {wind_barb_svg_code}
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
    
    # Generate inline wind barb for Meteorological Details
    wind_barb_inline_detail = generate_inline_wind_barb_html(_wdir, _wspd, size=25)

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
            # Menyertakan Wind Barb inline
            st.markdown(f"<div class='detail-value inline-barb-container'>{wind_barb_inline_detail} {now.get('wd','—')} ({_wdir}°)</div>", unsafe_allow_html=True)
        
        # Row 3: Location Details (Moved here)
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_prov, col_city = st.columns(2)
        with col_prov:
            st.markdown("<div classs='metric-label'>Province</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('provinsi','—')}</div>", unsafe_allow_html=True)
        with col_city:
            st.markdown("<div class='metric-label'>City/Regency</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='detail-value' style='font-size: 1.0rem;'>{now.get('kotkab','—')}</div>", unsafe_allow_html=True)


    with detail_col2:
        st.markdown("##### 🌁 Sky and Visibility")
        # Row 1: Visibility & Ceiling
        col_vis, col_ceil = st.columns(2)
        with col_vis:
            st.markdown("<div class='metric-label'>Visibility (Metres/SM)</div>", unsafe_allow_html=True) 
            st.markdown(f"<div class='detail-value'>{now.get('vs','—')} m</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='small-note'>({vis_sm_disp}) / {now.get('vs_text','—')}</div>", unsafe_allow_html=True) 
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
# === MET REPORT (QAM REPLICATION)
# =====================================

    if show_qam_report:
        # Generate inline wind barb for QAM report (slightly smaller)
        wind_barb_inline_qam = generate_inline_wind_barb_html(_wdir, _wspd, size=20)
        
        # Menyertakan Wind Barb inline dalam wind_info_qam
        wind_info_qam = f"<div class='inline-barb-container' style='font-size: 1.0rem; margin-left: -5px;'>{wind_barb_inline_qam} {_wdir}° / {_wspd:.1f} KT</div>"
        wind_variation = "Not available (BMKG Forecast - No Variation Data)"  
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
                    <td>{now.get('local_datetime','—')} (Local) / {now.get('utc_datetime','—')} (UTC) <span style='font-size: 0.75rem; color:#ffd86b;'>(FORECAST DATA)</span></td>
                </tr>
                <tr>
                    <th>AERODROME IDENTIFICATION</th>
                    <td>{icao_code} / {now.get('kotkab','—')} ({now.get('adm2','—')})</td>
                </tr>
                <tr>
                    <th>SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</th>
                    <td>{wind_info_qam} / Variation: {wind_variation}</td>
                </tr>
                <tr>
                    <th>HORIZONTAL VISIBILITY</th>
                    <td>{now.get('vs','—')} m ({vis_sm_disp}) / {now.get('vs_text','—')}</td> </tr>
                <tr>
                    <th>RUNWAY VISUAL RANGE</th>
                    <td>— (RVR not available from Forecast)</td>
                </tr>
                <tr>
                    <th>PRESENT WEATHER</th>
                    <td>{now.get('weather_desc','—')} (Accum. Rain: {now.get('tp',0):.1f} mm)</td>
                </tr>
                <tr>
                    <th>AMOUNT AND HEIGHT OF BASE OF LOW CLOUD</th>
                    <td>Cloud Cover: {now.get('tcc','—')}% / {ceiling_full_desc} <span style='font-size: 0.75rem; color:#ffd86b;'>(ESTIMATED BASE)</span></td>
                </tr>
                <tr>
                    <th>AIR TEMPERATURE AND DEW POINT TEMPERATURE</th>
                    <td>Air Temp: {now.get('t','—')}°C / Dew Point: {dewpt_disp} / RH: {now.get('hu','—')}%</td>
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
