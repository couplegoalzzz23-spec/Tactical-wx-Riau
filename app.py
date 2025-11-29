# ================================================
# 📄 MET REPORT — PRINTABLE HTML (NO pdfkit / reportlab)
# Tambahkan ini di BAWAH script Anda (paling akhir)
# ================================================
import base64
import datetime

st.markdown("## 📄 MET REPORT — Takeoff / Landing (Printable)")

# --- try auto-fill from existing 'now' variable (from your dashboard) ---
_try_now = {}
try:
    # 'now' is defined earlier in your script as `now = df_sel.iloc[0]`
    _try_now["ad"] = loc_choice if 'loc_choice' in globals() else ""
    _try_now["wind"] = f"{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT"
    _try_now["vis"] = f"{now.get('vs','—')} m"
    _try_now["rvr"] = "-"
    _try_now["wx"] = now.get("weather_desc", now.get("weather", "—"))
    _try_now["cloud"] = f"{now.get('tcc','—')}% (TCC)"
    temp_val = now.get('t')
    dew_est = None
    try:
        if temp_val is not None and now.get('hu') is not None:
            # Magnus approximation
            a = 17.625; b = 243.04
            T = float(temp_val)
            RH = float(now.get('hu'))
            alpha = (a * T) / (b + T) + np.log(RH/100.0)
            dew_est = (b * alpha) / (a - alpha)
    except Exception:
        dew_est = None
    if dew_est is not None:
        _try_now["temp"] = f"{temp_val}°C / {dew_est:.1f}°C"
    else:
        _try_now["temp"] = f"{temp_val}°C / —"
    # QNH estimation: if 'pressure' provided in data (BMKG often doesn't), use placeholder
    _try_now["qnh"] = now.get("qnh","—") if isinstance(now, dict) else "—"
    _try_now["qfe"] = "—"
    _try_now["supp"] = "-"
    _try_now["observer"] = "METWATCH OPS"
    auto_ok = True
except Exception:
    # fallback: no auto-fill available
    _try_now = {
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

# =============================
# Form (user can edit/fill)
# =============================
col1, col2 = st.columns(2)
with col1:
    ad = st.text_input("Aerodrome ID", value=_try_now.get("ad",""))
    wind = st.text_input("Wind DIR/SPEED", value=_try_now.get("wind",""))
    vis = st.text_input("Visibility", value=_try_now.get("vis",""))
    rvr = st.text_input("Runway Visual Range", value=_try_now.get("rvr",""))
    wx = st.text_input("Present Weather", value=_try_now.get("wx",""))
    cloud = st.text_input("Cloud (Amount/Height)", value=_try_now.get("cloud",""))
with col2:
    temp = st.text_input("Temp / Dew Point", value=_try_now.get("temp",""))
    qnh = st.text_input("QNH", value=_try_now.get("qnh",""))
    qfe = st.text_input("QFE", value=_try_now.get("qfe",""))
    supp = st.text_area("Supplementary Info", value=_try_now.get("supp",""))
    observer = st.text_input("Observer", value=_try_now.get("observer",""))

obs_time = datetime.datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
issue_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

# =============================
# Build HTML
# =============================
def generate_met_html(ad, wind, vis, rvr, wx, cloud, temp, qnh, qfe, supp, issue_time, obs_time, observer):
    return f"""
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8"/>
    <title>MET REPORT</title>
    <style>
        body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color:#0b0c0c; }}
        h1 {{ font-size:16px; text-align:center; margin-bottom:6px; }}
        h2 {{ font-size:12px; text-align:center; margin-top:0; color:#3a3a3a; }}
        table {{ width:100%; border-collapse:collapse; margin-top:12px; font-size:13px; }}
        td {{ border:1px solid #222; padding:8px; vertical-align:top; }}
        .label {{ background:#efe6c9; font-weight:700; width:35%; }}
        .value {{ background:#fffdf6; }}
        .footer {{ margin-top:10px; font-size:11px; color:#333; }}
    </style>
    </head>
    <body>
        <h1>METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</h1>
        <h2>MARKAS BESAR ANGKATAN UDARA — DINAS PENGEMBANGAN OPERASI</h2>

        <table>
            <tr><td class="label">METEOROLOGICAL OBS AT DATE/TIME (UTC)</td><td class="value">{obs_time}</td></tr>
            <tr><td class="label">AERODROME IDENTIFICATION</td><td class="value">{ad}</td></tr>
            <tr><td class="label">SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</td><td class="value">{wind}</td></tr>
            <tr><td class="label">HORIZONTAL VISIBILITY</td><td class="value">{vis}</td></tr>
            <tr><td class="label">RUNWAY VISUAL RANGE</td><td class="value">{rvr}</td></tr>
            <tr><td class="label">PRESENT WEATHER</td><td class="value">{wx}</td></tr>
            <tr><td class="label">AMOUNT & HEIGHT OF BASE OF LOW CLOUD</td><td class="value">{cloud}</td></tr>
            <tr><td class="label">AIR TEMPERATURE & DEW POINT TEMPERATURE</td><td class="value">{temp}</td></tr>
            <tr><td class="label">QNH</td><td class="value">{qnh}</td></tr>
            <tr><td class="label">QFE</td><td class="value">{qfe}</td></tr>
            <tr><td class="label">SUPPLEMENTARY INFORMATION</td><td class="value">{supp}</td></tr>
            <tr><td class="label">TIME OF ISSUE (UTC)</td><td class="value">{issue_time}</td></tr>
            <tr><td class="label">OBSERVER</td><td class="value">{observer}</td></tr>
        </table>

        <div class="footer">
            <p><i>Note: This HTML is printable. Use your browser's Print → Save as PDF to make a PDF copy.</i></p>
        </div>
    </body>
    </html>
    """

html = generate_met_html(ad, wind, vis, rvr, wx, cloud, temp, qnh, qfe, supp, issue_time, obs_time, observer)

# =============================
# Provide download link (HTML, printable)
# =============================
b64 = base64.b64encode(html.encode('utf-8')).decode('utf-8')
download_filename = f"MET_REPORT_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.html"
download_link = f'<a href="data:text/html;base64,{b64}" download="{download_filename}">📄 Download MET REPORT (HTML) — Open & Print to PDF</a>'

st.markdown(download_link, unsafe_allow_html=True)

# =============================
# Optional: show preview in app
# =============================
with st.expander("Preview MET REPORT (printed view)"):
    st.markdown(html, unsafe_allow_html=True)

# =================================================================
# End of MET REPORT block — NO external libraries needed (pdfkit/reportlab)
# =================================================================
