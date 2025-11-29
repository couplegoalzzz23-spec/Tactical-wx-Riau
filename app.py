# ================================================
# 📄 MET REPORT — PRINTABLE PDF (NO REPORTLAB)
# ================================================
import base64
import datetime
import pdfkit   # jika wkhtmltopdf tidak tersedia → auto fallback HTML

st.markdown("## 📄 MET REPORT — Takeoff / Landing")

# =============================
# 🔘 Input Form MET REPORT
# =============================
col1, col2 = st.columns(2)

with col1:
    ad = st.text_input("Aerodrome ID", "WIBB / Pekanbaru")
    wind = st.text_input("Wind DIR/SPEED", "240/08KT")
    vis = st.text_input("Visibility", "8000 m")
    rvr = st.text_input("Runway Visual Range", "-")
    wx = st.text_input("Present Weather", "Nil")
    cloud = st.text_input("Cloud (Amount/Height)", "FEW 1500 ft")

with col2:
    temp = st.text_input("Temp / Dew Point", "32°C / 24°C")
    qnh = st.text_input("QNH", "1008 hPa")
    qfe = st.text_input("QFE", "-")
    supp = st.text_area("Supplementary Info", "-")
    observer = st.text_input("Observer", "METWATCH OPS")


obs_time = datetime.datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
issue_time = datetime.datetime.utcnow().strftime("%H:%M UTC")

# =============================
# 🔧 Construct HTML Layout
# =============================
def generate_met_html():
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 25px;
            }}
            h1 {{
                text-align: center;
                font-size: 18px;
                margin-bottom: 5px;
            }}
            h2 {{
                text-align: center;
                font-size: 13px;
                font-weight: normal;
                margin-top: 0px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 13px;
            }}
            td {{
                border: 1px solid black;
                padding: 6px;
            }}
            .label {{
                background-color: #f2f2f2;
                font-weight: bold;
                width: 40%;
            }}
        </style>
    </head>

    <body>

        <h1>METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</h1>
        <h2>MARKAS BESAR ANGKATAN UDARA — DINAS PENGEMBANGAN OPERASI</h2>

        <table>
            <tr><td class="label">METEOROLOGICAL OBS AT DATE/TIME (UTC)</td><td>{obs_time}</td></tr>
            <tr><td class="label">AERODROME IDENTIFICATION</td><td>{ad}</td></tr>
            <tr><td class="label">SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION</td><td>{wind}</td></tr>
            <tr><td class="label">HORIZONTAL VISIBILITY</td><td>{vis}</td></tr>
            <tr><td class="label">RUNWAY VISUAL RANGE</td><td>{rvr}</td></tr>
            <tr><td class="label">PRESENT WEATHER</td><td>{wx}</td></tr>
            <tr><td class="label">AMOUNT & HEIGHT OF BASE OF LOW CLOUD</td><td>{cloud}</td></tr>
            <tr><td class="label">AIR TEMPERATURE & DEW POINT TEMPERATURE</td><td>{temp}</td></tr>
            <tr><td class="label">QNH</td><td>{qnh}</td></tr>
            <tr><td class="label">QFE</td><td>{qfe}</td></tr>
            <tr><td class="label">SUPPLEMENTARY INFORMATION</td><td>{supp}</td></tr>
            <tr><td class="label">TIME OF ISSUE (UTC)</td><td>{issue_time}</td></tr>
            <tr><td class="label">OBSERVER</td><td>{observer}</td></tr>
        </table>

    </body>
    </html>
    """

# =============================
# 📤 Download Button (PDF / HTML)
# =============================
def download_pdf_from_html(html, filename="MET_REPORT.pdf"):
    try:
        pdf = pdfkit.from_string(html, False)
        b64 = base64.b64encode(pdf).decode()
        return f"""
            <a href="data:application/pdf;base64,{b64}"
               download="{filename}">
               📄 Download MET REPORT (PDF)
            </a>
        """
    except:
        b64 = base64.b64encode(html.encode()).decode()
        return f"""
            <a href="data:text/html;base64,{b64}"
               download="MET_REPORT.html">
               📄 Download MET REPORT (HTML Printable)
            </a>
        """

# =============================
# ▶️ Build HTML → Provide Download
# =============================
html = generate_met_html()
st.markdown(download_pdf_from_html(html), unsafe_allow_html=True)
