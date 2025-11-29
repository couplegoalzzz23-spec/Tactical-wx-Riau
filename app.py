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
# Tambahkan <style> block ke variabel untuk dimasukkan dalam file HTML yang diunduh.
# Ini memastikan laporan yang diunduh memiliki styling yang sama.
CSS_STYLES = """
<style>
/* Base theme */
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
/* Hanya masukkan CSS yang relevan untuk laporan QAM */
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
/* Menambahkan gaya untuk cetak, agar background tetap hitam/gelap saat dicetak */
@media print {
    body {
        -webkit-print-color-adjust: exact;
        color-adjust: exact;
    }
    .met-report-table {
        border-color: #777 !important;
    }
    .met-report-table th, .met-report-table td {
        border-color: #777 !important;
    }
    /* Sembunyikan semua elemen lain kecuali laporan QAM saat mencetak (opsional) */
    /* * { display: none !important; } .met-report-container { display: block !important; } */
}
</style>
"""

# Menyuntikkan seluruh CSS (termasuk yang tidak relevan untuk QAM, untuk tampilan Streamlit)
st.markdown(CSS_STYLES + """
<style>
/* Streamlit Specific Styles (Dilewatkan untuk file QAM) */
h1, h2, h3, h4 { color: #a9df52; text-transform: uppercase; letter-spacing: 1px; }
/* ... (CSS Streamlit lainnya) ... */
.radar { /* ... */ }
.flight-card { /* ... */ }
.badge-green { /* ... */ }
</style>
""", unsafe_allow_html=True)

# =====================================
# 📡 KONFIGURASI API
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384  # konversi ke knot

# =====================================
# 🧰 UTILITAS (Fungsi tetap sama)
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
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
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
    if status == "VFR" or status == "Recommended":
        return "<span class='badge-green'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge-yellow'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge-red'>NO-GO</span>"
    return "<span class='badge-yellow'>UNKNOWN</span>"

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
    st.caption("Data Source: BMKG API · Military Ops v2.2")

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown("*Source: BMKG Forecast API — Live Data*")

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

    if "ws_kt" not in df.columns:
        df["ws_kt"] = df["ws"] * MS_TO_KT
    else:
        df["ws_kt"] = pd.to_numeric(df["ws_kt"], errors="coerce")

# =====================================
# 🕓 SLIDER WAKTU
# =====================================
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

    if use_col:
        start_dt = st.sidebar.slider(
            "Time Range",
            min_value=min_dt,
            max_value=max_dt,
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
    # Tampilan metrik kunci (tidak diubah)
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
# ☁ METEOROLOGICAL DETAILS (SECONDARY)
# =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">☁ Meteorological Details</div>', unsafe_allow_html=True)
    # Tampilan detail (tidak diubah)
    row1, row2, row3, row4 = st.columns(4)
    with row1:
        st.markdown("<div class='metric-label'>Cloud Cover (%)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-value'>{now.get('tcc','—')}</div>", unsafe_allow_html=True)
    # ... (lanjutan metrik sekunder) ...
    st.markdown("</div>", unsafe_allow_html=True)


# =====================================
# === MET REPORT (QAM REPLACEMENT) - SESUAI LAMPIRAN
# =====================================

    # prepare MET REPORT values
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
    ceiling_display = f"Est. Base: {ceiling_est_ft} ft ({ceiling_label})" if ceiling_est_ft is not None else "—"
    
    visibility_m = now.get('vs')
    wind_info = f"{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT"
    wind_variation = "Not available (BMKG Forecast)" 
    
    # 📌 START: MEMBANGUN HTML UNTUK LAPORAN QAM
    # Seluruh konten HTML laporan QAM dibuat di sini.
    met_report_html_content = f"""
<div class="met-report-container">
    <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
    <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
    <div class="met-report-header" style="border-top: none;">METEOROLOGICAL REPORT FOR TAE OFF AND LANDING</div>
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
            <td>Cloud Cover: {now.get('tcc','—')}% / {ceiling_display}</td>
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
# 📈 TRENDS, 🌪️ WINDROSE, 🗺️ MAP, 📋 TABLE (Tidak ada perubahan signifikan)
# =====================================
    # ... (Bagian TRENDS dan WINDROSE dilewati karena tidak ada perubahan fungsional) ...

# =====================================
# 💾 EXPORT - DITAMBAHKAN TOMBOL QAM DOWNLOAD
# =====================================
    st.markdown("---")
    st.subheader("💾 Export Data & Report")
    
    # 🌟 TOMBOL BARU UNTUK DOWNLOAD QAM
    qam_filename = f"MET_REPORT_{loc_choice}_{now.get('local_datetime','—').replace(' ', '_').replace(':','')}.html"
    st.download_button(
        label="⬇ Download QAM Report (HTML)",
        data=full_qam_html,
        file_name=qam_filename,
        mime="text/html",
        help="Unduh laporan QAM sebagai file HTML. Buka di browser dan gunakan fungsi 'Cetak ke PDF' untuk konversi formal."
    )

    # Tombol data mentah (CSV/JSON)
    csv = df_sel.to_csv(index=False)
    json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
    colA, colB = st.columns(2)
    with colA:
        st.download_button("⬇ Data Mentah (CSV)", csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
    with colB:
        st.download_button("⬇ Data Mentah (JSON)", json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")


except requests.exceptions.HTTPError as e:
    st.error(f"API Error: Could not fetch data. Check Province Code (ADM1). Status code: {e.response.status_code}")
except requests.exceptions.ConnectionError:
    st.error("Connection Error: Could not connect to BMKG API.")
except Exception as e:
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
