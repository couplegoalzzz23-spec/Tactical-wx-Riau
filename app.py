import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI APP
# =====================================
st.set_page_config(page_title="Wind Analysis Dashboard", layout="wide")

st.title("🌬️ Tactical Wind Analysis Dashboard")


# ============================================================
# 🎨 COLOR FUNCTION UNTUK WIND BARB BERDASARKAN KECEPATAN
# ============================================================
def wind_color(ws):
    try:
        ws = float(ws)
    except:
        return "white"

    if ws < 10:
        return "lime"
    elif ws < 20:
        return "yellow"
    elif ws < 30:
        return "orange"
    else:
        return "red"


# ============================================================
# 📌 PLOTLY WIND BARB TIME SERIES (ICAO/WMO Standard)
# ============================================================
def wind_barb_timeseries(df, speed_col="ws", dir_col="wd", time_col=None):

    if time_col is None:
        x = df.index
    else:
        x = df[time_col]

    # Hitung komponen U/V
    U = df[speed_col] * np.sin(np.radians(df[dir_col]))
    V = df[speed_col] * np.cos(np.radians(df[dir_col]))

    colors = [wind_color(v) for v in df[speed_col]]

    fig = go.Figure()

    fig.add_trace(go.Barbs(
        x=x,
        y=[0] * len(df),
        u=U,
        v=V,
        barbcolor=colors,
        sizeref=0.8,
        showscale=False,
        name="Wind Barbs"
    ))

    fig.update_layout(
        height=250,
        title="Wind Barb Time Series (ICAO Standard)",
        xaxis_title="Time",
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white")
    )

    return fig


# ============================================================
# 🔧 SIMULASI DATA (Jika Anda punya file real, tinggal ganti)
# ============================================================
st.sidebar.subheader("Data Options")

use_demo = st.sidebar.checkbox("Use Demo Wind Data", value=True)

if use_demo:
    # Generate 24 jam data
    time_index = pd.date_range(datetime.now().replace(hour=0, minute=0), periods=24, freq="H")

    np.random.seed(42)
    df = pd.DataFrame({
        "time": time_index,
        "ws": np.random.randint(2, 35, size=24),                 # wind speed
        "wd": np.random.randint(0, 360, size=24),                # wind direction
    })
else:
    uploaded = st.sidebar.file_uploader("Upload CSV (time, ws, wd)", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
    else:
        st.warning("Upload data atau gunakan demo data.")
        st.stop()


df_display = df.copy()
df_display["time"] = df_display["time"].astype(str)
st.dataframe(df_display, hide_index=True)


# ============================================================
# 📈 PANEL: WIND SPEED TREND
# ============================================================
st.subheader("📈 Wind Speed Trend (KT)")

fig_speed = go.Figure()
fig_speed.add_trace(go.Scatter(
    x=df["time"], 
    y=df["ws"],
    mode="lines+markers",
    line=dict(color="cyan"),
    name="Wind Speed"
))

fig_speed.update_layout(
    height=250,
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white"),
    margin=dict(l=10, r=10, t=40, b=10)
)

st.plotly_chart(fig_speed, use_container_width=True)


# ============================================================
# 📈 PANEL: WIND DIRECTION TREND
# ============================================================
st.subheader("🧭 Wind Direction Trend (°)")

fig_dir = go.Figure()
fig_dir.add_trace(go.Scatter(
    x=df["time"], 
    y=df["wd"],
    mode="lines+markers",
    line=dict(color="orange"),
    name="Wind Direction"
))

fig_dir.update_layout(
    height=250,
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white"),
    margin=dict(l=10, r=10, t=40, b=10)
)

st.plotly_chart(fig_dir, use_container_width=True)


# ============================================================
# 🌬️ WIND BARB TIME SERIES (ICAO STANDARD)
# ============================================================
st.subheader("🌬️ Wind Barb Time Series (ICAO/WMO Standard)")

fig_wb = wind_barb_timeseries(df, speed_col="ws", dir_col="wd", time_col="time")
st.plotly_chart(fig_wb, use_container_width=True)


st.success("Wind Barb ICAO berhasil ditampilkan ✔")
