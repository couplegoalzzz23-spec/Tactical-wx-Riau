# ===========================================================
# APPEND-ON: MET REPORT — Printable HTML (NO external libs)
# Safe to paste at the BOTTOM of your existing Streamlit app
# - Will auto-fill from existing 'now' and 'loc_choice' if available
# - Will NOT raise NameError if they are missing
# - No external dependencies (no pdfkit, no reportlab)
# ===========================================================
# If 'st' isn't defined in this module (rare), import it.
if 'st' not in globals():
    import streamlit as st

import base64
import datetime
import math

# Helper: safe extractor for objects like dict, pandas Series, or attribute-like
def safe_get(obj, key, default="—"):
    try:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        # pandas Series supports .get
        if hasattr(obj, "get"):
            v = obj.get(key, default)
            return v if v is not None else default
        # attribute access fallback
        return getattr(obj, key, default)
    except Exception:
        return default

# Try to auto-detect common globals from the main script
_auto = {}
try:
    # 'now' often defined as df_sel.iloc[0] (pandas Series)
    if 'now' in globals():
        now_obj = globals()['now']
    else:
        now_obj = None

    # fill fields from now if possible
    wd_deg = safe_get(now_obj, "wd_deg", None)
    ws_kt = safe_get(now_obj, "ws_kt", None)
    if wd_deg is not None and wd_deg != "—" and ws_kt is not None and ws_kt != "—":
        wind_auto = f"{wd_deg}° / {float(ws_kt):.1f} KT"
    else:
        wind_auto = "—"

    vis_auto = safe_get(now_obj, "vs", "—")
    cloud_auto = safe_get(now_obj, "tcc", "—")
    # weather description
    wx_auto = safe_get(now_obj, "weather_desc", safe_get(now_obj, "weather", "—"))
    temp_val = safe_get(now_obj, "t", None)
    rh_val = safe_get(now_obj, "hu", None)

    # attempt dew point via Magnus formula if t and rh available
    dew_calc = None
    try:
        if temp_val is not None and temp_val != "—" and rh_val not in (None, "—"):
            T = float(temp_val)
            RH = float(rh_val)
            # Magnus-Tetens approximation
            a = 17.27
            b = 237.7
            gamma = (a * T) / (b + T) + math.log(RH/100.0)
            dew_calc = (b * gamma) / (a - gamma)
    except Exception:
        dew_calc = None

    if dew_calc is not None:
        temp_auto = f"{temp_val}°C / {dew_calc:.1f}°C"
    elif temp_val not in (None, "—"):
        temp_auto = f"{temp_val}°C / —"
    else:
        temp_auto = "— / —"

    # try loc_choice for aerodrome label
    ad_auto = globals().get('loc_choice', "")

    # basic qnh if present in 'now' or globals
    qnh_auto = safe_get(now_obj, "qnh", "—")
    if qnh_auto in (None, ""):
        qnh_auto = "—"

    _auto = {
        "ad": ad_auto or "",
        "wind": wind_auto,
        "vis": vis_auto,
        "rvr": "-",
        "wx": wx_auto,
        "cloud": f"{cloud_auto}% (TCC)" if cloud_auto not in (None,"—") else "—",
        "temp": temp_auto,
        "qnh": qnh_auto,
        "qfe": "—",
        "supp": "-",
        "observer": "METWATCH OPS"
    }
    auto_ok = True
except Exception:
    _auto = {
        "ad": "",
        "wind": "—",
        "vis": "—",
        "rvr": "-",
        "wx": "—",
        "cloud": "—",
        "temp": "— / —",
        "qnh": "—",
        "qfe": "—",
        "supp": "-",
        "observer": "METWATCH OPS"
    }
    auto_ok = False

# UI: headline + small guidance
st.markdown("## 📄 MET REPORT — Takeoff / Landing (Printable)")
st.info("Form bisa diisi manual. Jika app Anda mendefinisikan variabel `now` dan `loc_choice`, beberapa field akan terisi otomatis. Klik 'Download HTML' lalu buka & Print → Save as PDF di browser untuk menghasilkan PDF.")

# Form inputs (two-column)
col1, col2 = st.columns(2)
with col1:
    ad = st.text_input("Aerodrome ID", value=_auto.get("ad",""))
    wind = st.text_input("Surface Wind (DIR/Speed)", value=_auto.get("wind",""))
    vis = st.text_input("Horizontal Visibility", value=_auto.get("vis",""))
    rvr = st.text_input("Runway Visual Range (RVR)", value=_auto.get("rvr",""))
    wx = st.text_input("Present Weather", value=_auto.get("wx",""))
    cloud = st.text_input("Cloud amount & base (amount / height)", value=_auto.get("cloud",""))
with col2:
    temp = st.text_input("Air Temp / Dew Point", value=_auto.get("temp",""))
    qnh = st.text_input("QNH (hPa)", value=_auto.get("qnh",""))
    qfe = st.text_input("QFE (hPa)", value=_auto.get("qfe",""))
    supp = st.text_area("Supplementary Information", value=_auto.get("supp",""))
    observer = st.text_input("Observer", value=_auto.get("observer",""))

obs_time = datetime.datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
issue_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

# Build printable HTML (A4-friendly CSS)
def build_met_html(ad, wind, vis, rvr, wx, cloud, temp, qnh, qfe, supp, issue_time, obs_time, observer):
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>MET REPORT</title>
<style>
  @page {{ size: A4; margin: 18mm 12mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; color:#0b0c0c; }}
  .container {{ width: 100%; max-width: 820px; margin: 0 auto; }}
  h1 {{ text-align:center; font-size:18px; margin-bottom:4px; }}
  h2 {{ text-align:center; font-size:12px; margin-top:0; color:#333; }}
  table {{ width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; }}
  td {{ border:1px solid #222; padding:8px; vertical-align:top; }}
  .label {{ background:#efe6c9; font-weight:700; width:35%; }}
  .value {{ background:#fffdf6; }}
  .small {{ font-size:11px; color:#444; margin-top:8px; }}
  /* ensure print uses these colors */
  @media print {{
    .label {{ -webkit-print-color-adjust: exact; background:#efe6c9; }}
    .value {{ -webkit-print-color-adjust: exact; background:#fffdf6; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</h1>
  <h2>MARKAS BESAR ANGKATAN UDARA — DINAS PENGEMBANGAN OPERASI</h2>

  <table>
    <tr><td class="label">METEOROLOGICAL OBS AT DATE/TIME (UTC)</td><td class="value">{obs_time}</td></tr>
    <tr><td class="label">AERODROME IDENTIFICATION</td><td class="value">{ad}</td></tr>
    <tr><td class="label">SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</td><td class="value">{wind}</td></tr>
    <tr><td class="label">HORIZONTAL VISIBILITY</td><td class="value">{vis}</td></tr>
    <tr><td class="label">RUNWAY VISUAL RANGE (RVR)</td><td class="value">{rvr}</td></tr>
    <tr><td class="label">PRESENT WEATHER</td><td class="value">{wx}</td></tr>
    <tr><td class="label">AMOUNT & HEIGHT OF BASE OF LOW CLOUD</td><td class="value">{cloud}</td></tr>
    <tr><td class="label">AIR TEMPERATURE & DEW POINT TEMPERATURE</td><td class="value">{temp}</td></tr>
    <tr><td class="label">QNH</td><td class="value">{qnh}</td></tr>
    <tr><td class="label">QFE</td><td class="value">{qfe}</td></tr>
    <tr><td class="label">SUPPLEMENTARY INFORMATION</td><td class="value">{supp}</td></tr>
    <tr><td class="label">TIME OF ISSUE (UTC)</td><td class="value">{issue_time}</td></tr>
    <tr><td class="label">OBSERVER</td><td class="value">{observer}</td></tr>
  </table>

  <div class="small">Note: Open the downloaded HTML in a browser and use Print → Save as PDF to produce a PDF file (A4).</div>
</div>
</body>
</html>"""

# Build HTML and provide download link (HTML file)
html_content = build_met_html(ad, wind, vis, rvr, wx, cloud, temp, qnh, qfe, supp, issue_time, obs_time, observer)
b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
download_filename = f"MET_REPORT_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.html"
download_link = f'<a href="data:text/html;base64,{b64}" download="{download_filename}">📄 Download MET REPORT (HTML) — Open & Print to PDF</a>'

st.markdown(download_link, unsafe_allow_html=True)

# Preview (safe)
with st.expander("Preview MET REPORT (Printable)"):
    st.markdown(html_content, unsafe_allow_html=True)

# Done — end of append-on block
