import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------------------------
# SETUP
# ----------------------------------------------------------
st.set_page_config(page_title="Tactical Weather", layout="wide")
API_URL = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# ----------------------------------------------------------
# FETCH DATA SAFELY
# ----------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_data(adm1):
    try:
        r = requests.get(API_URL, params={"adm1": adm1}, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        st.error("Gagal mengambil data BMKG.")
        st.stop()

# ----------------------------------------------------------
# FLATTEN DATA SAFELY
# ----------------------------------------------------------
def flatten(entry):
    rows = []
    lokasi = entry.get("lokasi", {})

    for group in entry.get("cuaca", []) or []:
        for obs in group or []:
            if not isinstance(obs, dict):
                continue

            r = obs.copy()
            r.update({
                "adm1": lokasi.get("adm1"),
                "adm2": lokasi.get("adm2"),
                "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"),
                "lat": lokasi.get("lat"),
            })

            try:
                r["local_dt"] = pd.to_datetime(r.get("local_datetime"))
            except:
                r["local_dt"] = pd.NaT

            rows.append(r)

    df = pd.DataFrame(rows)

    num_cols = ["t","hu","ws","tp","vs","tcc","wd_deg"]
    for c in num_cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["ws_kt"] = df.get("ws",0) * MS_TO_KT
    return df

# ----------------------------------------------------------
# SIDEBAR MENU
# ----------------------------------------------------------
with st.sidebar:
    st.title("Tactical Menu")

    PROV = {
        "Aceh": "11", "Sumatera Utara": "12", "Sumatera Barat": "13",
        "Riau": "14", "Jambi": "15", "Sumatera Selatan": "16",
        "DKI Jakarta": "31", "Jawa Barat": "32", "Jawa Tengah": "33",
        "DI Yogyakarta": "34", "Jawa Timur": "35"
    }

    prov_name = st.selectbox("Pilih Provinsi", list(PROV.keys()), index=3)
    ADM1_CODE = PROV[prov_name]

    menu = st.multiselect(
        "Tampilkan Menu",
        ["Temperature", "Humidity", "Wind Speed", "Rainfall", "Windrose", "Table"],
        default=["Temperature", "Wind Speed", "Windrose"]
    )

# ----------------------------------------------------------
# FETCH DATA
# ----------------------------------------------------------
raw = fetch_data(ADM1_CODE)

entries = raw.get("data", [])
if not entries:
    st.error("Data tidak ditemukan.")
    st.stop()

cities = {e["lokasi"]["kotkab"]: e for e in entries}
city_choice = st.selectbox("Pilih Kota", list(cities.keys()))
entry = cities[city_choice]

df = flatten(entry)
if df.empty:
    st.error("Data kosong.")
    st.stop()

# ----------------------------------------------------------
# TIME SLIDER
# ----------------------------------------------------------
times = sorted(df["local_dt"].dropna().unique())
tid = st.slider("Time Index", 0, len(times)-1, len(times)-1)
current_time = times[tid]
df_now = df[df["local_dt"] == current_time]

if df_now.empty:
    df_now = df.iloc[[0]]

now = df_now.iloc[0]

# ----------------------------------------------------------
# METRIC PANEL
# ----------------------------------------------------------
st.title(f"Tactical Weather — {city_choice}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temp (°C)", f"{now.t:.1f}" if not pd.isna(now.t) else "-")
c2.metric("Humidity (%)", f"{now.hu}" if not pd.isna(now.hu) else "-")
c3.metric("Wind (KT)", f"{now.ws_kt:.1f}" if not pd.isna(now.ws_kt) else "-")
c4.metric("Rain (mm)", f"{now.tp}" if not pd.isna(now.tp) else "-")

st.markdown("---")

# ----------------------------------------------------------
# CHARTS
# ----------------------------------------------------------
df_sorted = df.sort_values("local_dt")

if "Temperature" in menu:
    st.subheader("Temperature")
    fig = px.line(df_sorted, x="local_dt", y="t", markers=True)
    st.plotly_chart(fig, use_container_width=True)

if "Humidity" in menu:
    st.subheader("Humidity (%)")
    fig = px.line(df_sorted, x="local_dt", y="hu", markers=True)
    st.plotly_chart(fig, use_container_width=True)

if "Wind Speed" in menu:
    st.subheader("Wind Speed (KT)")
    fig = px.line(df_sorted, x="local_dt", y="ws_kt", markers=True)
    st.plotly_chart(fig, use_container_width=True)

if "Rainfall" in menu:
    st.subheader("Rainfall (mm)")
    fig = px.bar(df_sorted, x="local_dt", y="tp")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------
# WINDROSE
# ----------------------------------------------------------
if "Windrose" in menu:
    st.subheader("Windrose")

    df_wr = df.dropna(subset=["wd_deg","ws_kt"])
    if len(df_wr) > 0:
        bins_dir = np.arange(-11.25, 360, 22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                      "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir"] = pd.cut(df_wr["wd_deg"], bins=bins_dir, labels=labels_dir)

        speed_bins = [0,5,10,20,30,50,100]
        sp_label = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["spd"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=sp_label)

        freq = df_wr.groupby(["dir","spd"]).size().reset_index(name="count")
        freq["pct"] = freq["count"] / freq["count"].sum() * 100

        az = {
            "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,
            "SE":135,"SSE":157.5,"S":180,"SSW":202.5,"SW":225,
            "WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5
        }
        freq["theta"] = freq["dir"].map(az)

        fig_wr = go.Figure()
        for sp in sp_label:
            sub = freq[freq["spd"] == sp]
            fig_wr.add_trace(go.Barpolar(
                r=sub["pct"], theta=sub["theta"], name=sp
            ))
        fig_wr.update_layout(template="plotly_dark")
        st.plotly_chart(fig_wr, use_container_width=True)

# ----------------------------------------------------------
# TABLE
# ----------------------------------------------------------
if "Table" in menu:
    st.subheader("Forecast Table")
    st.dataframe(df_sorted, use_container_width=True)
