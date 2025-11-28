import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Tactical Weather Ops — BMKG (Robust)", layout="wide")

# ------------------
# CONFIG / API
# ------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"  # sesuai script awal kamu
MS_TO_KT = 1.94384

# ------------------
# UTIL: fetch + flatten (tolerant)
# ------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=12)
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
            # safe datetimes (tolerant)
            r["utc_datetime"] = r.get("utc_datetime") or r.get("utc") or r.get("datetime_utc")
            r["local_datetime"] = r.get("local_datetime") or r.get("local") or r.get("datetime_local")
            rows.append(r)
    df = pd.DataFrame(rows)
    return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map possible column name variants to standard names."""
    col_map = {}
    lower_cols = {c.lower(): c for c in df.columns}

    def find_variant(variants):
        for v in variants:
            if v in lower_cols:
                return lower_cols[v]
        return None

    # common parameters and their variants
    mapping = {
        "t": ["t", "temp", "temperature"],
        "tcc": ["tcc", "cloud", "cloud_cover", "tcloud"],
        "tp": ["tp", "rain", "precip", "precipitation", "tp_mm"],
        "wd_deg": ["wd_deg", "wd", "wind_dir", "wind_direction", "wd_deg_mean"],
        "ws": ["ws", "wind", "wind_speed", "ws_mean"],
        "hu": ["hu", "humidity", "rh"],
        "vs": ["vs", "vis", "visibility"],
        "pres": ["pres", "pressure", "press", "msl"],
        "weather": ["weather","weather_desc","weather_text"],
        "lightning_prob": ["lightning_prob","prob_lightning","ltg_prob"]
    }

    for std, variants in mapping.items():
        found = find_variant(variants)
        if found:
            col_map[found] = std

    # apply rename
    if col_map:
        df = df.rename(columns=col_map)
    return df

# ------------------
# SIDEBAR / INPUT
# ------------------
with st.sidebar:
    st.header("Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value="32")
    show_table = st.checkbox("Show Data Table / Columns", value=True)
    refresh = st.button("Fetch Data")

# ------------------
# Fetch data
# ------------------
st.title("Tactical Weather Ops — Robust Viewer")

try:
    raw = fetch_forecast(adm1)
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    st.stop()

entries = raw.get("data", [])
if not entries:
    st.warning("No forecast data returned by API.")
    st.stop()

# build mapping and select
mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = e

loc_choice = st.selectbox("Select Location", options=list(mapping.keys()))
selected_entry = mapping[loc_choice]

# flatten & normalize
df = flatten_cuaca_entry(selected_entry)
if df.empty:
    st.error("Flattened dataframe is empty.")
    st.stop()

df = normalize_columns(df)

# show columns for debugging if requested
if show_table:
    st.subheader("Detected columns (sample)")
    st.write(list(df.columns))
    st.dataframe(df.head(6), use_container_width=True)

# ------------------
# Parse datetimes safely
# ------------------
if "local_datetime" in df.columns:
    df["local_datetime_dt"] = pd.to_datetime(df["local_datetime"], errors="coerce")
elif "utc_datetime" in df.columns:
    df["local_datetime_dt"] = pd.to_datetime(df["utc_datetime"], errors="coerce")
else:
    # try to find any datetime-like column
    dt_col = None
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower():
            dt_col = c; break
    if dt_col:
        df["local_datetime_dt"] = pd.to_datetime(df[dt_col], errors="coerce")
    else:
        df["local_datetime_dt"] = pd.NaT

# ------------------
# Convert numeric columns safely
# ------------------
for c in ["t","tcc","tp","wd_deg","ws","hu","vs","pres","lightning_prob"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# compute wind kt if ws present (assume m/s if >0 and reasonable)
if "ws" in df.columns:
    df["ws_kt"] = df["ws"] * MS_TO_KT
else:
    df["ws_kt"] = np.nan

# sort by time (if available)
if df["local_datetime_dt"].notna().any():
    df = df.sort_values("local_datetime_dt")
else:
    st.warning("No valid datetime parsed — plotting will use index order.")

# allow user to choose time window if datetime exists
if df["local_datetime_dt"].notna().any():
    min_dt = df["local_datetime_dt"].min()
    max_dt = df["local_datetime_dt"].max()
    start_dt, end_dt = st.slider("Time Range", value=(min_dt, max_dt), min_value=min_dt, max_value=max_dt, step=pd.Timedelta(hours=3))
    mask = (df["local_datetime_dt"] >= pd.to_datetime(start_dt)) & (df["local_datetime_dt"] <= pd.to_datetime(end_dt))
    df_sel = df.loc[mask].copy()
else:
    df_sel = df.copy()

if df_sel.empty:
    st.warning("No rows in selected time range / no valid datetime rows.")
    st.stop()

# ------------------
# Helper to safe-plot
# ------------------
def safe_line(x, y, title):
    if y not in df_sel.columns:
        st.info(f"Column '{y}' not available — skipping {title}.")
        return
    if df_sel[y].dropna().empty:
        st.info(f"Column '{y}' has no numeric data — skipping {title}.")
        return
    try:
        fig = px.line(df_sel, x=x, y=y, title=title)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not plot {title}: {e}")

# ------------------
# METRIC PANEL (defensive)
# ------------------
st.markdown("---")
st.subheader("Tactical Status (current)")

current = df_sel.iloc[0] if len(df_sel) else df_sel.iloc[-1]
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Temp (°C)", str(current.get("t","—")))
col2.metric("Humidity (%)", str(current.get("hu","—")))
col3.metric("Wind (KT)", f"{current.get('ws_kt'):.1f}" if pd.notna(current.get("ws_kt")) else "—")
col4.metric("Pressure (hPa)", str(current.get("pres","—")))
col5.metric("Visibility", str(current.get("vs","—")))

# ------------------
# TREND PLOTS
# ------------------
st.markdown("---")
st.subheader("Parameter Trends")

x_axis = "local_datetime_dt" if "local_datetime_dt" in df_sel.columns and df_sel["local_datetime_dt"].notna().any() else df_sel.index

safe_line(x_axis, "t", "Temperature (°C)")
safe_line(x_axis, "hu", "Humidity (%)")
safe_line(x_axis, "ws_kt", "Wind Speed (KT)")
safe_line(x_axis, "tp", "Rainfall (mm)")
safe_line(x_axis, "pres", "Pressure (hPa)")
safe_line(x_axis, "vs", "Visibility (km)")

# ------------------
# WINDROSE (if possible)
# ------------------
st.markdown("---")
st.subheader("Windrose (if wind dir & speed available)")
if ("wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns and not df_sel[["wd_deg","ws_kt"]].dropna().empty):
    try:
        df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"]).copy()
        bins_dir = np.arange(-11.25,360,22.5)
        labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
        speed_bins = [0,5,10,20,30,50,100]
        speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
        df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
        freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
        freq["percent"] = freq["count"]/freq["count"].sum()*100
        az_map = {k:i*22.5 for i,k in enumerate(labels_dir)}
        freq["theta"] = freq["dir_sector"].map(az_map)
        fig_wr = go.Figure()
        for sc in speed_labels:
            subset = freq[freq["speed_class"]==sc]
            fig_wr.add_trace(go.Barpolar(r=subset["percent"], theta=subset["theta"], name=sc))
        st.plotly_chart(fig_wr, use_container_width=True)
    except Exception as e:
        st.warning(f"Windrose failed: {e}")
else:
    st.info("Insufficient wind data for windrose (need 'wd_deg' and 'ws'/'ws_kt').")

# ------------------
# Tactical Alerts
# ------------------
st.markdown("---")
st.subheader("Tactical Alerts")

alerts = []
# thresholds (tolerant)
if "ws_kt" in df_sel and df_sel["ws_kt"].dropna().gt(25).any():
    alerts.append("💨 Wind > 25 kt detected in time window.")
if "pres" in df_sel and df_sel["pres"].dropna().lt(1008).any():
    alerts.append("🌀 Pressure < 1008 hPa detected.")
if "vs" in df_sel and df_sel["vs"].dropna().lt(3000).any():
    alerts.append("🌫 Visibility < 3000 (units depends on API).")
if len(alerts) == 0:
    st.success("No tactical alerts.")
else:
    for a in alerts:
        st.error(a)

# ------------------
# TABLE + EXPORT
# ------------------
st.markdown("---")
if st.checkbox("Show dataframe (selected)", value=False):
    st.dataframe(df_sel, use_container_width=True)

csv = df_sel.to_csv(index=False)
st.download_button("Export CSV", data=csv, file_name=f"bmkg_{adm1}_{loc_choice}.csv", mime="text/csv")
