# ===========================================================
# 📄 MET REPORT — AUTO-FILL & PRINTABLE (NO EXTERNAL LIBS)
# Safe to paste at the BOTTOM of your app.py
# ===========================================================

import streamlit as st
import base64
import datetime
import math


# -----------------------------------------------------------
# SAFE GETTER — tidak error jika now/field tidak ada
# -----------------------------------------------------------
def safe_get(obj, key, default="—"):
    try:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        if hasattr(obj, "get"):
            v = obj.get(key, default)
            return v if v is not None else default
        return getattr(obj, key, default)
    except Exception:
        return default


# -----------------------------------------------------------
# AUTO-DETECT DATA dari script utama
# (now, loc_choice, dll)
# -----------------------------------------------------------
try:
    now_obj = globals().get("now", None)

    # wind
    wd = safe_get(now_obj, "wd_deg", None)
    ws = safe_get(now_obj, "ws_kt", None)
    if wd not in (None, "—") and ws not in (None, "—"):
        wind_auto = f"{wd}° / {float(ws):.1f} KT"
    else:
        wind_auto = "—"

    # vis
    vis_auto = safe_get(now_obj, "vs", "—")

    # cloud
    cloud_auto = safe_get(now_obj, "tcc", None)
    if cloud_auto not in (None, "—"):
        cloud_str = f"{cloud_auto}% (TCC)"
    else:
        cloud_str = "—"

    # wx
    wx_auto = safe_get(now_obj, "weather_desc",
                       safe_get(now_obj, "weather", "—"))

    # temp + dew point
    temp_val = safe_get(now_obj, "t", None)
    rh = safe_get(now_obj, "hu", None)
    dew = None
    try:
        if temp_val not in (None, "—") and rh not in (None, "—"):
            T = float(temp_val)
            RH = float(rh)
            a, b = 17.27, 237.7
            gamma = (a*T)/(b+T) + math.log(RH/100)
            dew = (b * gamma) / (a - gamma)
    except:
        dew = None

    if dew is not None:
        temp_auto = f"{temp_val}°C / {dew:.1f}°C"
    else:
        temp_auto = f"{temp_val}°C / —" if temp_val not in (None, "—") else "— / —"

    # pressure
    qnh_auto = safe_get(now_obj, "qnh", "—")

    # aerodrome
    ad_auto = globals().get("loc_choice", "")

    auto = True
except:
    auto = False
    ad_auto = ""
    wind_auto = "—"
    vis_auto = "—"
    cloud_str = "—"
    wx_auto = "—"
    temp_auto = "— / —"
    qnh_auto = "—"


st.markdown("## 📄 MET REPORT — Printable (Auto-Filled)")

st.info(
    "Semua field akan terisi otomatis berdasarkan data `now`. "
    "Klik **Download HTML**, buka di browser, lalu **Print → Save as PDF**."
)


# -----------------------------------------------------------
# UI FORM
# -----------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    ad = st.text_input("Aerodrome ID", value=ad_auto)
    wind = st.text_input("Surface Wind", value=wind_auto)
    vis = st.text_input("Visibility", value=vis_auto)
    rvr = st.text_input("Runway Visual Range (RVR)", value="-")
    wx = st.text_input("Present Weather", value=wx_auto)
    cloud = st.text_input("Cloud (Amount / Base)", value=cloud_str)

with col2:
    temp = st.text_input("Temperature / Dew Point", value=temp_auto)
    qnh = st.text_input("QNH (hPa)", value=qnh_auto)
    qfe = st.text_input("QFE (hPa)", value="—")
    supp = st.text_area("Supplementary Info", value="-")
    observer = st.text_input("Observer", value="METWATCH OPS")

obs_time = datetime.datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
issue_time = datetime.datetime.utcnow().strftime("%H:%M UTC")


# -----------------------------------------------------------
# BUILD PRINTABLE HTML
# -----------------------------------------------------------
def build_html(ad, wind, vis, rvr, wx, cloud, temp, qnh, qfe, supp, issue, obs, observer):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>MET REPORT</title>
<style>
  @page {{ size: A4; margin: 18mm 12mm; }}
  body {{ font-family: Arial; color:#000; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  td {{ border:1px solid #000; padding:6px; }}
  .label {{ background:#e8dfc4; font-weight:700; width:38%; }}
  .value {{ background:#fffdf6; }}
  @media print {{
    .label, .value {{ -webkit-print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
<h2 style="text-align:center;">METEOROLOGICAL REPORT FOR TAKEOFF / LANDING</h2>
<table>
<tr><td class="label">OBS TIME (UTC)</td><td class="value">{obs}</td></tr>
<tr><td class="label">AERODROME</td><td class="value">{ad}</td></tr>
<tr><td class="label">SURFACE WIND</td><td class="value">{wind}</td></tr>
<tr><td class="label">VISIBILITY</td><td class="value">{vis}</td></tr>
<tr><td class="label">RUNWAY VISUAL RANGE</td><td class="value">{rvr}</td></tr>
<tr><td class="label">PRESENT WEATHER</td><td class="value">{wx}</td></tr>
<tr><td class="label">CLOUD</td><td class="value">{cloud}</td></tr>
<tr><td class="label">TEMP & DEWPOINT</td><td class="value">{temp}</td></tr>
<tr><td class="label">QNH</td><td class="value">{qnh}</td></tr>
<tr><td class="label">QFE</td><td class="value">{qfe}</td></tr>
<tr><td class="label">SUPPLEMENT</td><td class="value">{supp}</td></tr>
<tr><td class="label">ISSUE TIME</td><td class="value">{issue}</td></tr>
<tr><td class="label">OBSERVER</td><td class="value">{observer}</td></tr>
</table>
<p style="font-size:11px; margin-top:6px;">Print → Save as PDF (A4)</p>
</body>
</html>
    """


# -----------------------------------------------------------
# DOWNLOAD FILE (HTML → PDF via browser)
# -----------------------------------------------------------
html_file = build_html(ad, wind, vis, rvr, wx, cloud,
                       temp, qnh, qfe, supp, issue_time, obs_time, observer)

b64 = base64.b64encode(html_file.encode()).decode()
filename = "MET_REPORT_" + datetime.datetime.utcnow().strftime("%Y%m%d_%H%M") + ".html"

st.download_button(
    "📄 Download MET REPORT (HTML)",
    data=html_file,
    file_name=filename,
    mime="text/html"
)

with st.expander("🔎 Preview"):
    st.markdown(html_file, unsafe_allow_html=True)
