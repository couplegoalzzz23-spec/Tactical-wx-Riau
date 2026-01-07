# =========================================================
# AVIATION WEATHER TACTICAL DASHBOARD
# ADM1 + ADM2 + ICAO AUTO SYNC
# =========================================================

import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Aviation Weather Tactical Dashboard",
    layout="wide"
)

# =========================================================
# HEADER
# =========================================================
st.title("🛰️ Aviation Weather Tactical Dashboard")
st.caption("BMKG-based | ADM1 • ADM2 • ICAO | Operational Prototype")

# =========================================================
# ADM1 PROVINCE MAP
# =========================================================
ADM1_MAP = {
    "Aceh": "11", "Sumatera Utara": "12", "Sumatera Barat": "13",
    "Riau": "14", "Jambi": "15", "Sumatera Selatan": "16",
    "Bengkulu": "17", "Lampung": "18", "Kep. Bangka Belitung": "19",
    "Kep. Riau": "21", "DKI Jakarta": "31", "Jawa Barat": "32",
    "Jawa Tengah": "33", "DI Yogyakarta": "34", "Jawa Timur": "35",
    "Banten": "36", "Bali": "51", "NTB": "52", "NTT": "53",
    "Kalimantan Barat": "61", "Kalimantan Tengah": "62",
    "Kalimantan Selatan": "63", "Kalimantan Timur": "64",
    "Kalimantan Utara": "65", "Sulawesi Utara": "71",
    "Sulawesi Tengah": "72", "Sulawesi Selatan": "73",
    "Sulawesi Tenggara": "74", "Gorontalo": "75",
    "Sulawesi Barat": "76", "Maluku": "81",
    "Maluku Utara": "82", "Papua Barat": "91", "Papua": "94"
}

# =========================================================
# ADM2 + ICAO MAP (AIRPORT OPS)
# =========================================================
ADM2_ICAO_MAP = {
    "31": {"Soekarno-Hatta Intl": "WIII", "Halim Perdanakusuma": "WIHH"},
    "32": {"Bandung": "WICC", "Kertajati (Majalengka)": "WICA"},
    "33": {"Semarang (Ahmad Yani)": "WARS", "Solo (Adi Soemarmo)": "WARQ"},
    "34": {"Yogyakarta Intl (YIA)": "WAHI"},
    "35": {"Surabaya (Juanda)": "WARR", "Malang (Abdul Rachman Saleh)": "WARA"},
    "36": {"Tangerang (Soetta)": "WIII"},
    "51": {"Denpasar (Ngurah Rai)": "WADD"},
    "73": {"Makassar (Sultan Hasanuddin)": "WAAA"},
    "71": {"Manado (Sam Ratulangi)": "WAMM"},
    "81": {"Ambon (Pattimura)": "WAPP"},
    "94": {"Jayapura (Sentani)": "WAJJ"}
}

# =========================================================
# SIDEBAR — TACTICAL CONTROLS
# =========================================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")

    province = st.selectbox(
        "Pilih Provinsi (ADM1)",
        list(ADM1_MAP.keys()),
        index=list(ADM1_MAP.keys()).index("Jawa Barat")
    )
    adm1 = ADM1_MAP[province]

    if adm1 in ADM2_ICAO_MAP:
        adm2 = st.selectbox(
            "Pilih Kota / Bandara (ADM2)",
            list(ADM2_ICAO_MAP[adm1].keys())
        )
        icao_code = ADM2_ICAO_MAP[adm1][adm2]
    else:
        adm2 = "-"
        icao_code = "WXXX"

    st.markdown("---")
    st.markdown(f"""
**Wilayah Operasi**
- Provinsi : **{province}**
- ADM1     : `{adm1}`
- ADM2     : **{adm2}**
- ICAO     : **{icao_code}**
""")

    st.markdown("---")
    show_sat = st.checkbox("Show Satellite", value=True)
    show_radar = st.checkbox("Show Radar", value=True)
    show_qam = st.checkbox("Show QAM Report", value=True)

# =========================================================
# MAIN LAYOUT
# =========================================================
col1, col2 = st.columns(2)

# =========================================================
# SATELLITE HIMAWARI-8
# =========================================================
if show_sat:
    with col1:
        st.subheader("🌏 Himawari-8 Satellite (IR Enhanced)")
        st.image(
            "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_EH_Indonesia.png",
            caption="Cold cloud tops → Deep convection / CB",
            use_container_width=True
        )

# =========================================================
# RADAR BMKG (LIVE)
# =========================================================
if show_radar:
    with col2:
        st.subheader("🌧️ Weather Radar BMKG")
        components.iframe(
            "https://inderaja.bmkg.go.id/Radar",
            height=520,
            scrolling=True
        )

# =========================================================
# QAM / MET REPORT
# =========================================================
if show_qam:
    st.markdown("---")
    st.subheader("🧾 QAM / MET Aviation Brief")

    st.code(
        f"""
QAM {icao_code}
AREA {adm2.upper()}
WX ANALYSIS BASED ON IR SATELLITE & RADAR
POTENTIAL CB / SHRA DETECTED
USE CAUTION FOR TAKE-OFF & LANDING
NEXT UPDATE: +6H
""",
        language="text"
    )

# =========================================================
# FOOTER
# =========================================================
st.caption(
    "Educational & Operational Prototype | Data Source: BMKG | STMKG Compatible"
)
