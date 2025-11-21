# app.py — Tactical Weather Dashboard (Clean Modern Style)
# Dependencies:
#   pip install streamlit requests pandas numpy plotly folium streamlit_folium branca

import os
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Page Setup
# -----------------------------
st.set_page_config(page_title="Tactical Weather Ops", layout="wide")

st.markdown("""
<style>
body {
    font-family: 'Roboto','Segoe UI',sans-serif;
}
.block-container {
    padding-top: 1rem;
}
h1 {
    color: #a9df52;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.card {
    padding: 18px;
    border-radius: 12px;
    background-color: #141614;
    border: 1px solid #2d322d;
    margin-bottom: 15px;
}
.metric-title {
    color: #9dbf7b;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.metric-value {
    font-size: 26px;
    font-weight: bold;
    color: #d6f5a3;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Try Import Folium (Optional)
# -----------------------------
HAVE_FOLIUM = True
st_folium = None
try:
    import folium
    from streamlit_folium import st_folium
except Exception:
    HAVE_FOLIUM = False

# -----------------------------
# Config
# -----------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384

# -----------------------------
# Fetch BMKG Data
# -----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=12)
    resp.raise_for_status()
    return resp.json()

def flatten_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})

    for group in entry.get("cuaca", []):
        for obs in group:
            r = dict(obs)
            for k in ["adm1","adm2","provinsi","kotkab","lat","lon"]:
                r[k] = lokasi.get(k)

            # Parse datetime
            try:
                r["local_dt"] = pd.to_datetime(r.get("local_datetime"))
            except:
                r["local_dt"] = pd.NaT

            rows.append(r)

    df = pd.DataFrame(rows)
    numeric_cols = ["t","tcc","tp","wd_deg","ws","hu","vs"]
    for c in numeric_cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

# -----------------------------
# Sidebar Controls
# -----------------------------
with st.sidebar:
    st.title("Controls")
    adm1 = st.text_input("Province ADM1 Code", value="32")

    st.markdown("---")
    selected_params = st.multiselect(
        "Show Parameters:", 
        ["Temperature","Humidity","Wind Speed","Rain","Cloud Cover","Windrose","Map","Table"],
        default=["Temperature","Humidity","Wind Speed","Rain","Map"]
    )

    st.caption("Tactical Weather Ops © 2025")

# -----------------------------
# Fetch BMKG data
# -----------------------------
try:
    raw = fetch_forecast(adm1)
except:
    st.error("Failed to fetch BMKG data. Check ADM1 code or connection.")
    st.stop()

entries = raw.get("data", [])
if not entries:
    st.error("No forecast available for this ADM1.")
    st.stop()

# Location selector
mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or "Location"
    mapping[label] = e

loc_choice = st.selectbox("Select Location", list(mapping.keys()))
entry = mapping[loc_choice]

df = flatten_entry(entry)
df["ws_kt"] = df["ws"] * MS_TO_KT if "ws" in df else np.nan

# Timeline
df = df.sort_values("local_dt")
times = df["local_dt"].dropna().unique()
time_index = st.slider("Time Index", 0, len(times)-1, len(times)-1)
current_time = times[time_index]

df_sel = df[df["local_dt"] == current_time].copy()
if df_sel.empty:
    df_sel = df.iloc[[df["local_dt"].sub(current_time).abs().idxmin()]]

# -----------------------------
# HEADER
# -----------------------------
st.title("Tactical Weather Operations Dashboard")

st.markdown(
    f"### 🟢 {loc_choice} — {current_time.strftime('%Y-%m-%d %H:%M')}"
)

# -----------------------------
# METRIC CARDS
# -----------------------------
st.markdown("#### Conditions")

col1, col2, col3, col4 = st.columns(4)

def metric(card, title, value):
    card.markdown(f"""
    <div class='card'>
        <div class='metric-title'>{title}</div>
        <div class='metric-value'>{value}</div>
    </div>
    """, unsafe_allow_html=True)

row = df_sel.iloc[0]

metric(col1, "Temperature (°C)", f"{row['t']:.1f}" if pd.notna(row['t']) else "—")
metric(col2, "Humidity (%)", f"{row['hu']:.0f}" if pd.notna(row['hu']) else "—")
metric(col3, "Wind (kt)", f"{row['ws_kt']:.1f}" if pd.notna(row['ws_kt']) else "—")
metric(col4, "Rain (mm)", f"{row['tp']:.1f}" if pd.notna(row['tp']) else "—")

# -----------------------------
# TABS Interface
# -----------------------------
tabs = st.tabs(["Charts", "Windrose", "Map", "Table"])

# -----------------------------
# CHARTS TAB
# -----------------------------
with tabs[0]:

    st.subheader("Parameter Trends")

    if "Temperature" in selected_params and "t" in df:
        fig = px.line(df, x="local_dt", y="t", title="Temperature (°C)", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    if "Humidity" in selected_params and "hu" in df:
        fig = px.line(df, x="local_dt", y="hu", title="Humidity (%)", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    if "Wind Speed" in selected_params and "ws_kt" in df:
        fig = px.line(df, x="local_dt", y="ws_kt", title="Wind Speed (kt)", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    if "Rain" in selected_params and "tp" in df:
        fig = px.bar(df, x="local_dt", y="tp", title="Rainfall (mm)")
        st.plotly_chart(fig, use_container_width=True)

    if "Cloud Cover" in selected_params and "tcc" in df:
        fig = px.line(df, x="local_dt", y="tcc", title="Cloud Cover (%)", markers=True)
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# WINDROSE TAB
# -----------------------------
with tabs[1]:
    st.subheader("Windrose")

    if "Windrose" not in selected_params:
        st.info("Windrose not selected.")
    elif "wd_deg" not in df or df["wd_deg"].isna().all():
        st.info("No wind direction data.")
    else:
        try:
            df_wr = df.dropna(subset=["wd_deg","ws_kt"])
            bins = np.arange(-11.25, 360, 22.5)
            labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            df_wr["sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins, labels=labels)

            freq = df_wr.groupby("sector")["ws_kt"].mean().reset_index()
            freq["theta"] = freq["sector"].map({
                "N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,
                "S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5
            })

            fig = go.Figure(go.Barpolar(
                theta=freq["theta"],
                r=freq["ws_kt"],
                marker_color="#9fe89c",
                opacity=0.85
            ))
            fig.update_layout(template="plotly_dark", title="Windrose (kt)")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Windrose failed: {e}")

# -----------------------------
# MAP TAB
# -----------------------------
with tabs[2]:
    st.subheader("Map View")

    if "Map" not in selected_params:
        st.info("Map not selected.")

    else:
        lat = float(entry["lokasi"].get("lat", 0))
        lon = float(entry["lokasi"].get("lon", 0))

        if HAVE_FOLIUM and st_folium:
            m = folium.Map(location=[lat, lon], zoom_start=8)

            folium.Marker(
                [lat, lon],
                popup=f"{loc_choice}",
                icon=folium.Icon(color="green")
            ).add_to(m)

            st_folium(m, width=900, height=500)
        else:
            st.map(pd.DataFrame({"lat":[lat], "lon":[lon]}))

# -----------------------------
# TABLE TAB
# -----------------------------
with tabs[3]:

    if "Table" not in selected_params:
        st.info("Table not selected.")
    else:
        st.dataframe(df.reset_index(drop=True))

        st.subheader("Export Data")
        st.download_button("Download CSV", df.to_csv(index=False), "forecast.csv", "text/csv")
        st.download_button("Download JSON", df.to_json(orient="records"), "forecast.json", "application/json")
