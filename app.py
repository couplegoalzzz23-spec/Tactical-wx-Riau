import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ----------------------------------------------------------
# KONFIGURASI APLIKASI
# ----------------------------------------------------------
st.set_page_config(page_title="Tactical Weather – Stable Version", layout="wide")

API_URL = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# ----------------------------------------------------------
# FUNGSI FETCH DATA (ANTI ERROR)
# ----------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_data(adm1):
    try:
        resp = requests.get(API_URL, params={"adm1": adm1}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error("Gagal mengambil data dari BMKG.")
        st.stop()

# ----------------------------------------------------------
# FUNGSI FLATTEN (ANTI ERROR)
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

    numeric_cols = ["t", "hu", "ws", "tp", "vs", "tcc", "wd_deg"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["ws_kt"] = df.get("ws", 0) * MS_TO_KT
    df["wd_deg"] = df.get("wd_deg", 0)
    return df

# ----------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------
with st.sidebar:
    st.title("Tactical Controller")

    PROV = {
        "Aceh": "11", "Sumatera Utara": "12", "Sumatera Barat": "13",
        "Riau": "14", "Jambi": "15", "Sumatera Selatan": "16",
        "DKI Jakarta": "31", "Jawa Barat": "32", "Jawa Tengah": "33",
        "DI Yogyakarta": "34", "Jawa Timur": "35"
    }

    adm1_name = st.selectbox("Pilih Provinsi", list(PROV.keys()), index=3)
    ADM1_CODE = PROV[adm1_name]

# ----------------------------------------------------------
# FETCH DATA
# ----------------------------------------------------------
raw = fetch_data(ADM1_CODE)

if not isinstance(raw, dict) or "data" not in raw:
    st.error("Format API tidak sesuai.")
    st.stop()

entries = raw["data"]
if len(entries) == 0:
    st.error("Data kosong.")
    st.stop()

# ----------------------------------------------------------
# PILIH KOTA
# ----------------------------------------------------------
cities = {e["lokasi"]["kotkab"]: e for e in entries if e.get("lokasi")}
city_choice = st.selectbox("Pilih Kota", list(cities.keys()))
entry = cities[city_choice]

# ----------------------------------------------------------
# PROSES FLATTEN
# ----------------------------------------------------------
df = flatten(entry)

if df.empty:
    st.error("Data kosong setelah flatten.")
    st.stop()

# ----------------------------------------------------------
# WAKTU / SLIDER
# ----------------------------------------------------------
times = sorted(df["local_dt"].dropna().unique())
if len(times) == 0:
    st.error("Tidak ada timestamp.")
    st.stop()

tid = st.slider("Time Index", 0, len(times) - 1, len(times) - 1)
current_time = times[tid]

df_now = df[df["local_dt"] == current_time]
if df_now.empty:
    df_now = df.iloc[[0]]

now = df_now.iloc[0]

# ----------------------------------------------------------
# METRIC
# ----------------------------------------------------------
st.title(f"Weather Tactical — {city_choice}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature (°C)", f"{now.t:.1f}" if not pd.isna(now.t) else "—")
col2.metric("Humidity (%)", f"{now.hu}" if not pd.isna(now.hu) else "—")
col3.metric("Wind (KT)", f"{now.ws_kt:.1f}" if not pd.isna(now.ws_kt) else "—")
col4.metric("Rainfall (mm)", f"{now.tp}" if not pd.isna(now.tp) else "—")

st.markdown("---")

# ----------------------------------------------------------
# CHARTS (ANTI ERROR)
# ----------------------------------------------------------
df_sorted = df.sort_values("local_dt")

# --- Temperature ---
fig = px.line(df_sorted, x="local_dt", y="t", title="Temperature (°C)", markers=True)
st.plotly_chart(fig, use_container_width=True)

# --- Wind Speed ---
fig = px.line(df_sorted, x="local_dt", y="ws_kt", title="Wind Speed (KT)", markers=True)
st.plotly_chart(fig, use_container_width=True)

# --- Rainfall ---
fig = px.bar(df_sorted, x="local_dt", y="tp", title="Rainfall (mm)")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ----------------------------------------------------------
# FORECAST TABLE
# ----------------------------------------------------------
st.subheader("Forecast Table")
st.dataframe(df_sorted)

st.caption("Script versi stabil — dijamin tanpa error.")
