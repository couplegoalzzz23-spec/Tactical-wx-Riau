import streamlit as st
import requests
import pandas as pd
# Import lainnya tetap sama (numpy, plotly, datetime)
from datetime import datetime
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
# ... (lanjutan import)

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Naval Meteorology & Oceanography Command | Public Facing", layout="wide")

# Placeholder untuk URL Gambar Banner yang Anda buat di Canva (WAJIB DIGANTI!)
NMOC_BANNER_IMAGE_URL = "https://i.imgur.com/your-custom-nmoc-banner-image.jpg" 
# Ganti dengan URL gambar kolase lebar yang Anda desain!

# =====================================
# 🎨 CSS — NMOC FORMAL STYLE
# =====================================
CSS_STYLES_NMOC = f"""
<style>
/* ---------------------------------
   NMOC Global Theme
   --------------------------------- */
body {{
    background-color: #f0f2f6; /* Light gray background */
    color: #333; /* Default text color */
    font-family: Arial, sans-serif;
}}
/* Override Streamlit container background for white look */
section[data-testid="stSidebar"] {{
    background-color: #0d1a2f; /* Dark Navy Blue for sidebar controls */
    color: #fff;
}}
.stApp {{
    background-color: #fff;
}}
h1, h2, h3, h4 {{
    color: #0d1a2f; /* Deep Navy Blue for headers */
    font-family: 'Georgia', serif; 
    text-transform: none; /* Remove uppercase for formal look */
    letter-spacing: 0;
}}
/* ---------------------------------
   Custom Header and Navigation (Replicating NMOC Site)
   --------------------------------- */
.nmoc-header-banner {{
    width: 100%;
    height: 120px; /* Sesuaikan tinggi banner */
    background: url('{NMOC_BANNER_IMAGE_URL}') no-repeat center center;
    background-size: cover; /* Pastikan gambar mengisi lebar */
    margin-bottom: 20px;
}}
.nmoc-main-title {{
    background-color: #4b6cb7; /* Lighter Blue bar */
    color: white;
    font-size: 1.5rem;
    font-weight: bold;
    padding: 10px 20px;
    border-top: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    margin-top: 0;
}}
.nmoc-navigation-panel {{
    background-color: #fff;
    border: 1px solid #ccc;
    padding: 15px;
    margin-bottom: 20px;
}}
.nav-link {{
    display: block;
    padding: 8px 0;
    font-weight: bold;
    color: #004080; /* Navy blue link */
    text-decoration: none;
}}
.nav-link:hover {{
    color: #007bff;
    text-decoration: underline;
}}

/* ---------------------------------
   Metric & Report Card Styling (Formal)
   --------------------------------- */
.formal-card {{
    padding: 15px;
    background-color: #f9f9f9;
    border: 1px solid #ddd;
    border-radius: 5px;
    margin-bottom: 15px;
}}
.metric-label {{
    font-size: 0.85rem;
    text-transform: uppercase;
    color: #666; /* Gray label */
    letter-spacing: 0.5px;
}}
.metric-value {{
    font-size: 1.5rem;
    color: #0d1a2f; /* Navy value */
    font-weight: 700;
}}
/* Ganti warna badge ke formal */
.badge-green {{ color:#fff; background:#28a745; padding:4px 8px; border-radius:4px; font-weight:700; font-size: 0.9rem; }}
.badge-yellow {{ color:#333; background:#ffc107; padding:4px 8px; border-radius:4px; font-weight:700; font-size: 0.9rem; }}
.badge-red {{ color:#fff; background:#dc3545; padding:4px 8px; border-radius:4px; font-weight:700; font-size: 0.9rem; }}
</style>
"""

# Suntikkan CSS Baru
st.markdown(CSS_STYLES_NMOC, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS (Tetap sama)
# =====================================
# (Semua fungsi utilitas seperti safe_float, estimate_dewpoint, 
#  ceiling_proxy_from_tcc, classify_ifr_vfr, dll. TIDAK BERUBAH. 
#  Salin-tempel semua kode fungsi utilitas dari app (14).py ke sini)
# ...
# START: BLOCK SALIN-TEMPEL FUNGSI UTILITIES (TIDAK DITAMPILKAN DI SINI AGAR SCRIPT RINGKAS)
# ...
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
    
def get_day_night_mode():
    # Keep auto/manual mode but CSS will be ignored now for HUD
    hour = datetime.now().hour
    return "day" if 6 <= hour < 18 else "night"

CURRENT_MODE = get_day_night_mode()

# --- Placeholder untuk fungsi-fungsi ---
# fetch_forecast, flatten_cuaca_entry, estimate_dewpoint, 
# ceiling_proxy_from_tcc, convert_vis_to_sm, classify_ifr_vfr, 
# takeoff_landing_recommendation, badge_html harus dicantumkan di sini.
# ---
def fetch_forecast(adm1: str):
    # DARI app (14).py
    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    # DARI app (14).py
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
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs","ws_kt"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def estimate_dewpoint(temp, rh):
    # DARI app (14).py
    if pd.isna(temp) or pd.isna(rh): return None
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    # DARI app (14).py
    if pd.isna(tcc_pct): return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: return 99999, "SKC (Clear)"
    elif tcc < 25: return 3500, "FEW (>3000 ft)"
    elif tcc < 50: return 2250, "SCT (1500-3000 ft)"
    elif tcc < 75: return 1250, "BKN (1000-1500 ft)"
    else: return 800, "OVC (<1000 ft)"

def convert_vis_to_sm(visibility_m):
    # DARI app (14).py
    METER_TO_SM = 0.000621371
    if pd.isna(visibility_m) or visibility_m is None: return "—"
    try:
        vis_sm = float(visibility_m) * METER_TO_SM
        if vis_sm < 1: return f"{vis_sm:.1f} SM"
        elif vis_sm < 5:
            if (vis_sm * 2) % 2 == 0: return f"{int(vis_sm)} SM"
            else: return f"{vis_sm:.1f} SM"
        else: return f"{int(round(vis_sm))} SM"
    except ValueError: return "—"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    # DARI app (14).py
    if visibility_m is None or pd.isna(visibility_m): return "Unknown"
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
    # DARI app (14).py
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

def badge_html(status):
    # DARI app (14).py
    if status == "VFR" or status == "Recommended" or status == "SKC (Clear)":
        return "<span class='badge-green'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge-yellow'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge-red'>NO-GO</span>"
    return "<span class='badge-yellow'>UNKNOWN</span>"

# =====================================
# 🎚️ SIDEBAR (KONTROL)
# =====================================
with st.sidebar:
    st.title("⚙️ Command Center")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    icao_code = st.text_input("ICAO Code (WXXX)", value="WXXX", max_chars=4)
    st.markdown("---")
    # Kontrol yang tetap di sidebar
    override_mode = st.selectbox("Display Mode", ["Auto", "Day", "Night"], index=0)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    show_table = st.checkbox("Show Raw Data Table", value=False)
    st.markdown("---")
    st.caption("Data Source: BMKG Forecast API")

# =====================================
# 🖼️ CUSTOM HEADER HTML
# =====================================
# Menggantikan st.title() lama dengan header kustom NMOC
st.markdown("<div class='nmoc-header-banner'></div>", unsafe_allow_html=True)
st.markdown("<div class='nmoc-main-title'>Naval Meteorology & Oceanography Command | Public Facing Website</div>", unsafe_allow_html=True)

# =====================================
# 📡 LOAD DATA (Tetap sama)
# =====================================
try:
    # ... (blok load data sama seperti app (14).py) ...
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

    # Pilihan Lokasi dan Metrik Tetap di Area Utama (BISA DIPINDAH KE KONTEN)
    col1, col2 = st.columns([4, 1])
    with col1:
        loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
    with col2:
        st.metric("Locations Available", len(mapping))

    selected_entry = mapping[loc_choice]["entry"]
    df = flatten_cuaca_entry(selected_entry)

    if df.empty: st.stop()

    MS_TO_KT = 1.94384
    if "ws_kt" not in df.columns: df["ws_kt"] = df["ws"] * MS_TO_KT
    
    # 🕓 SLIDER WAKTU DIPINDAH KE SIDEBAR (Sudah dilakukan di app (14).py)
    # Gunakan logika waktu yang sama untuk df_sel dan now
    if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
        df = df.sort_values("local_datetime_dt")
        min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
        max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()
        use_col = "local_datetime_dt"
    else:
        min_dt, max_dt, use_col = datetime.now(), datetime.now(), None

    # slider only when datetime exists (tetap di sidebar, tapi logika di sini)
    start_dt = (min_dt, min_dt + pd.Timedelta(hours=3)) if len(df) > 1 and use_col else (min_dt, max_dt)
    if use_col:
        with st.sidebar:
            start_dt = st.slider("Time Range", min_value=min_dt, max_value=max_dt, value=start_dt, step=pd.Timedelta(hours=3), format="HH:mm, MMM DD")
        mask = (df[use_col] >= pd.to_datetime(start_dt[0])) & (df[use_col] <= pd.to_datetime(start_dt[1]))
        df_sel = df.loc[mask].copy()
    else:
        df_sel = df.copy()

    if df_sel.empty: st.warning("No data in selected time range."); st.stop()
        
    now = df_sel.iloc[0]

    # prepare MET REPORT values
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))

    # =====================================
    # 🗺️ TATA LETAK NMOC (Navigasi Samping + Konten Utama)
    # =====================================
    st.markdown("---")
    
    # Kolom untuk Navigasi Samping Kiri (1 unit) dan Konten Utama (4 unit)
    nav_col, main_content_col = st.columns([1, 4])
    
    with nav_col:
        st.subheader("Navigation")
        st.markdown("<div class='nmoc-navigation-panel'>", unsafe_allow_html=True)
        # Placeholder link/logo NMOC (Anda bisa menambahkan gambar logo di sini)
        st.markdown(" **JTWC** (Link ke website)", unsafe_allow_html=True)
        st.markdown(" **FWC-SD** (Link ke website)", unsafe_allow_html=True)
        st.markdown(" **FWC-N** (Link ke website)", unsafe_allow_html=True)
        st.markdown("<a href='#' class='nav-link'>NOAC-Y</a>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Area kecil untuk peta
        st.subheader("Current Location Map")
        try:
            lat = safe_float(selected_entry.get("lokasi", {}).get("lat", 0))
            lon = safe_float(selected_entry.get("lokasi", {}).get("lon", 0))
            # Menampilkan peta kecil di kolom navigasi
            st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}), zoom=6)
        except:
            st.info("Map data unavailable.")

    with main_content_col:
        st.header(f"Operational Weather Briefing for {loc_choice}")

        # Ganti FLIGHT CARD dengan FORMAL CARD
        st.markdown("<div class='formal-card'>", unsafe_allow_html=True)
        st.markdown("### 📈 Key Operational Metrics", unsafe_allow_html=True)
        
        colA, colB, colC, colD = st.columns(4)
        with colA:
            st.markdown("<div class='metric-label'>Temperature (°C)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{now.get('t','—')}</div>", unsafe_allow_html=True)
        with colB:
            st.markdown("<div class='metric-label'>Wind Speed (KT)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{now.get('ws_kt',0):.1f}</div>", unsafe_allow_html=True)
            st.caption(f"Dir: {now.get('wd_deg','—')}° ({now.get('wd','—')})")
        with colC:
            st.markdown("<div class='metric-label'>Visibility (SM)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{vis_sm_disp}</div>", unsafe_allow_html=True)
            st.caption(f"Raw: {now.get('vs','—')} m")
        with colD:
            st.markdown("<div class='metric-label'>Present Weather</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
            st.caption(f"Rain: {now.get('tp',0):.1f} mm")
        st.markdown("</div>", unsafe_allow_html=True)

        # Hapus F-16 Tactical HUD dan ganti dengan Decision Matrix
        
        ifr_vfr = classify_ifr_vfr(now.get("vs"), ceiling_est_ft)
        takeoff_reco, landing_reco, reco_rationale = takeoff_landing_recommendation(now.get("ws_kt"), now.get("vs"), now.get("tp"))

        st.subheader("🔴 Operational Decision Matrix")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.markdown("**Regulatory Category**")
            st.markdown(f"{badge_html(ifr_vfr)}  <strong style='margin-left:8px;'>{ifr_vfr}</strong>", unsafe_allow_html=True)
        with col_r2:
            st.markdown("**Takeoff Recommendation**")
            st.markdown(f"{badge_html(takeoff_reco)}  <strong style='margin-left:8px;'>{takeoff_reco}</strong>", unsafe_allow_html=True)
        with col_r3:
            st.markdown("**Landing Recommendation**")
            st.markdown(f"{badge_html(landing_reco)}  <strong style='margin-left:8px;'>{landing_reco}</strong>", unsafe_allow_html=True)
        
        st.markdown("**Rationale / Notes:**")
        for r in reco_rationale:
            st.markdown(f"- {r}")
        st.markdown("---")
        
        # Tampilkan QAM Report jika dipilih
        if show_qam_report:
            # (Salin-tempel seluruh blok QAM Report dari app (14).py ke sini)
            st.subheader("📝 Meteorological Report (QAM/Form Replication)")
            # (met_report_html_content dan download button)
            st.info("QAM Report content and Download button go here...")
            st.markdown("---")

        # Tampilkan Trend Grafik
        st.subheader("📊 Parameter Trends")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)
        with c2:
            st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind (KT)"), use_container_width=True)

    # =====================================
    # ... (Lanjutan Windrose, Table, Export)
    # =====================================

# BLOK EXCEPT DIMULAI DI SINI
except requests.exceptions.HTTPError as e:
    st.error(f"API Error: Could not fetch data. Status code: {e.response.status_code}")
except requests.exceptions.ConnectionError:
    st.error("Connection Error: Could not connect to BMKG API.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")

# =====================================
# ⚓ FOOTER
# =====================================
st.markdown("""
---
<div style="text-align:center; color:#777; font-size:0.9rem;">
NMOC Weather Briefing — BMKG Data © 2025<br>
Streamlit Framework
</div>
""", unsafe_allow_html=True)
