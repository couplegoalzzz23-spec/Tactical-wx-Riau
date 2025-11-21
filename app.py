import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from datetime import datetime

# ================================
# ⚙️ PREMIUM TACTICAL UI SETTINGS
# ================================
st.set_page_config(page_title="Tactical WX Riau — Premium", layout="wide")

# Inject Premium UI CSS
st.markdown(
    """
    <style>
        /* ---- Global UI ---- */
        body {
            background-color: #0d0f12 !important;
        }
        .stApp {
            background-color: #0d0f12 !important;
        }

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {
            background: #0f1115 !important;
            padding: 1.5rem !important;
            border-right: 1px solid #1f2227 !important;
        }

        /* Sidebar Header */
        .sidebar-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #00eaff;
            margin-bottom: 0.5rem;
            letter-spacing: 1px;
        }

        /* Sidebar Labels */
        .sidebar-label {
            font-size: 0.85rem;
            text-transform: uppercase;
            font-weight: 600;
            color: #9aa0a6;
            margin-top: 15px;
            margin-bottom: 5px;
        }

        /* Buttons */
        .stButton>button {
            width: 100%;
            background: linear-gradient(90deg, #005f73, #0a9396);
            border: none;
            padding: 0.7rem 1rem;
            border-radius: 10px;
            color: white;
            font-weight: 600;
            font-size: 1rem;
            transition: 0.2s;
        }
        .stButton>button:hover {
            filter: brightness(120%);
        }

        /* Checkbox */
        .stCheckbox label {
            color: #d7d7d7 !important;
            font-size: 0.9rem;
        }

        /* Cards */
        .data-card {
            background: #111418;
            border: 1px solid #1d2127;
            padding: 1.2rem;
            border-radius: 14px;
            margin-bottom: 1rem;
        }
        .data-title {
            font-size: 1rem;
            font-weight: 700;
            color: #00c6ff;
            margin-bottom: 5px;
        }
        .data-value {
            font-size: 2rem;
            font-weight: 700;
            color: #e9f1f7;
        }

        /* Map Border */
        .fmap iframe {
            border-radius: 16px !important;
            border: 2px solid #1e242c !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===============================
# 🔧 API CONFIG
# ===============================
API_URL = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"

# ===============================
# 🧭 SIDEBAR — PREMIUM VERSION
# ===============================
with st.sidebar:

    st.markdown("<div class='sidebar-title'>TACTICAL WEATHER PANEL</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-label'>Province (ADM1)</div>", unsafe_allow_html=True)
    adm1 = st.text_input("", value="14", placeholder="ex: 14 (Riau)")

    st.markdown("<div class='sidebar-label'>Display Options</div>", unsafe_allow_html=True)
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Data Table", value=True)

    st.markdown("<div class='sidebar-label'>Execute</div>", unsafe_allow_html=True)
    run = st.button("Fetch Data")

# ===============================
# 🚀 MAIN PROCESS
# ===============================
if run:
    try:
        r = requests.get(f"{API_URL}/{adm1}")
        data = r.json()

        df = pd.json_normalize(data["data"]) if "data" in data else None

        if df is None or df.empty:
            st.error("Data tidak ditemukan. Cek ADM1.")
            st.stop()

        # Clean NaN
        df = df.fillna(0)

        st.subheader("📡 Tactical Weather Report — Premium UI")
        st.caption(f"Updated: {datetime.now().strftime('%d %B %Y %H:%M:%S')} WIB")

        # ----------------------
        # 🌍 MAP VIEW
        # ----------------------
        if show_map:
            if "lat" in df.columns and "lon" in df.columns:
                midpoint = [df["lat"].mean(), df["lon"].mean()]

                m = folium.Map(location=midpoint, zoom_start=7, tiles="CartoDB dark_matter")

                for _, row in df.iterrows():
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=5,
                        color="#00eaff",
                        fill=True,
                        fill_color="#00eaff",
                        fill_opacity=0.7,
                        tooltip=f"{row.get('lokasi', 'NA')}<br>Temp: {row.get('t', '?')}°C",
                    ).add_to(m)

                st_folium(m, height=480, width=900)

            else:
                st.warning("Data tidak memiliki koordinat (lat/lon). Map tidak bisa ditampilkan.")

        # ----------------------
        # 🗂 TABLE VIEW
        # ----------------------
        if show_table:
            st.markdown("### 📘 Data Table (Premium View)")
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Terjadi error: {str(e)}")
