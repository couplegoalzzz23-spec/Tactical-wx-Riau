import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import math

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
# 🌀 ICAO WIND BARB BUILDER (Tanpa go.Barbs)
# ============================================================
def create_wind_barb(x, y, speed, direction, color):
    """
    Membuat shape wind barb ICAO di Plotly menggunakan scatter lines.
    - speed dalam KT
    - direction dalam derajat
    """

    shapes = []

    # panjang utama
    L = 0.08
    barb_len = 0.03

    # rotasi
    ang = math.radians(direction)

    # titik garis utama
    x1 = x
    y1 = y
    x2 = x + L * math.sin(ang)
    y2 = y - L * math.cos(ang)

    # base shape (tiang)
    shapes.append(dict(
        type="line",
        x0=x1, y0=y1,
        x1=x2, y1=y2,
        line=dict(color=color, width=2)
    ))

    # Hitung komponen ICAO
    sp = int(round(speed))
    pennant = sp // 50
    sp = sp % 50
    full = sp // 10
    sp = sp % 10
    half = 1 if sp >= 5 else 0

    # posisi awal barb
    px = x2
    py = y2

    # offset secara terbalik sepanjang garis utama
    dx = (x1 - x2) / (pennant + full + half + 1.5)
    dy = (y1 - y2) / (pennant + full + half + 1.5)

    # sudut barb = 70°
    barb_ang = math.radians(direction - 70)

    # Tambahkan komponen ICAO
    for _ in range(pennant):
        bx = px
        by = py
        bx2 = bx + barb_len * math.sin(barb_ang)
        by2 = by - barb_len * math.cos(barb_ang)

        shapes.append(dict(
            type="line",
            x0=bx, y0=by,
            x1=bx2, y1=by2,
            line=dict(color=color, width=4)
        ))

        px += dx
        py += dy

    for _ in range(full):
        bx = px
        by = py
        bx2 = bx + (barb_len * 0.75) * math.sin(barb_ang)
        by2 = by - (barb_len * 0.75) * math.cos(barb_ang)

        shapes.append(dict(
            type="line",
            x0=bx, y0=by,
            x1=bx2, y1=by2,
            line=dict(color=color, width=3)
        ))

        px += dx
        py += dy

    if half == 1:
        bx = px
        by = py
        bx2 = bx + (barb_len * 0.45) * math.sin(barb_ang)
        by2 = by - (barb_len * 0.45) * math.cos(barb_ang)

        shapes.append(dict(
            type="line",
            x0=bx, y0=by,
            x1=bx2, y1=by2,
            line=dict(color=color, width=3)
        ))

    return shapes


# ============================================================
# 🌬️ WIND BARB TIME SERIES (custom tanpa go.Barbs)
# ============================================================
def wind_barb_timeseries(df, speed_col, dir_col, time_col):

    fig = go.Figure()

    fig.update_layout(
        height=260,
        title="Wind Barb Time Series (ICAO Standard)",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white"),
        xaxis=dict(title="Time"),
        yaxis=dict(showgrid=False, visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        shapes=[]
    )

    # generate wind barbs
    for i, row in df.iterrows():
        x = row[time_col]
        y = 0

        speed = row[speed_col]
        direction = row[dir_col]
        color = wind_color(speed)

        wb_shapes = create_wind_barb(x, y, speed, direction, color)

        for shp in wb_shapes:
            fig.add_shape(shp)

    return fig


# ============================================================
# 🔧 SIMULASI DATA (Jika Anda punya file real, tinggal ganti)
# ============================================================
st.sidebar.subheader("Data Options")

use_demo = st.sidebar.checkbox("Gunakan Demo Data", value=True)

if use_demo:
    time_index = pd.date_range(datetime.now().replace(hour=0, minute=0), periods=24, freq="H")

    np.random.seed(42)
    df = pd.DataFrame({
        "time": time_index,
        "ws": np.random.randint(2, 35, size=24),
        "wd": np.random.randint(0, 360, size=24),
    })
else:
    uploaded = st.sidebar.file_uploader("Upload CSV (time, ws, wd)", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        df["time"] = pd.to_datetime(df["time"])
    else:
        st.warning("Upload data atau gunakan demo.")
        st.stop()


# ============================================================
# 📈 PANEL: WIND SPEED
# ============================================================
st.subheader("📈 Wind Speed Trend (KT)")

fig_speed = go.Figure()
fig_speed.add_trace(go.Scatter(
    x=df["time"], y=df["ws"],
    mode="lines+markers",
    line=dict(color="cyan")
))

fig_speed.update_layout(
    height=250,
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white")
)

st.plotly_chart(fig_speed, use_container_width=True)


# ============================================================
# 📈 PANEL: WIND DIRECTION
# ============================================================
st.subheader("🧭 Wind Direction Trend (°)")

fig_dir = go.Figure()
fig_dir.add_trace(go.Scatter(
    x=df["time"], y=df["wd"],
    mode="lines+markers",
    line=dict(color="orange")
))

fig_dir.update_layout(
    height=250,
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white")
)

st.plotly_chart(fig_dir, use_container_width=True)


# ============================================================
# 🌬️ ICAO WIND BARB TIME SERIES
# ============================================================
st.subheader("🌬️ Wind Barb Time Series (ICAO/WMO Standard)")

fig_wb = wind_barb_timeseries(df, "ws", "wd", "time")
st.plotly_chart(fig_wb, use_container_width=True)

st.success("Wind Barb berhasil ditampilkan ✔ tanpa go.Barbs()")
