import streamlit as st
import pandas as pd
import numpy as np
from math import log
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Tactical Weather Sheet — Printable", layout="wide")

# =====================================================
# 1. Fungsi Perhitungan Dew Point
# =====================================================
def calc_dew_point(temp_c, rh):
    # Rumus Magnus
    a = 17.625
    b = 243.04
    alpha = ((a * temp_c) / (b + temp_c)) + np.log(rh / 100)
    dew = (b * alpha) / (a - alpha)
    return round(dew, 1)

# =====================================================
# 2. Fungsi Perhitungan QNH
# =====================================================
def calc_qnh(pressure_station, elevation_m):
    # Rumus barometrik standar
    qnh = pressure_station / ((1 - (0.0065 * elevation_m) / 288.15) ** 5.2561)
    return round(qnh, 1)

# =====================================================
# 3. Input Data
# =====================================================
st.title("📄 Tactical Weather Sheet — Printable PDF")

col1, col2, col3 = st.columns(3)

with col1:
    temp = st.number_input("Temperature (°C)", value=30.0)
    rh = st.number_input("Relative Humidity (%)", value=70)

with col2:
    pressure = st.number_input("Station Pressure (hPa)", value=1008.0)
    elevation = st.number_input("Elevation (m)", value=50)

with col3:
    wind = st.text_input("Wind (kt)", value="090/10")
    vis = st.text_input("Visibility", value="8000 m")

# Auto calculate
dew_point = calc_dew_point(temp, rh)
qnh = calc_qnh(pressure, elevation)

# =====================================================
# 4. Tampilkan Data Table-style
# =====================================================
st.subheader("🧮 Hasil Perhitungan Otomatis")

df = pd.DataFrame({
    "Parameter": ["Temperature", "Relative Humidity", "Wind", "Visibility", "Dew Point", "QNH"],
    "Value": [f"{temp} °C", f"{rh} %", wind, vis, f"{dew_point} °C", f"{qnh} hPa"]
})

st.dataframe(df, use_container_width=True)

# =====================================================
# 5. Fungsi Generate PDF
# =====================================================
def generate_pdf():

    filename = "/mnt/data/tactical_weather_sheet.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)

    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("<b>Tactical Weather Sheet</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))

    # Tabel untuk PDF
    data = [["Parameter", "Value"]] + df.values.tolist()

    table = Table(data, colWidths=[120, 250])

    # Styling seperti kertas kuning krem
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8d9b5")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fcf6e8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ])

    table.setStyle(table_style)
    story.append(table)

    doc.build(story)
    return filename

# =====================================================
# 6. Tombol Download
# =====================================================
if st.button("📥 Download Printable PDF"):
    pdf_file = generate_pdf()

    with open(pdf_file, "rb") as f:
        st.download_button(
            label="⬇️ Download Tactical Weather PDF",
            data=f,
            file_name="tactical_weather_sheet.pdf",
            mime="application/pdf"
        )

st.success("PDF siap dicetak — format mirip lembar kertas asli.")
