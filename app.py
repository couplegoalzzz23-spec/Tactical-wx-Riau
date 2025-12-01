############################################################
#  TACTICAL WEATHER OPS — PILOT GRADE VERSION (FIXED)      #
#  - Perbaikan: tidak ada integer dengan leading zero     #
#  - Pilot snapshot, runway HW/XW, flight category, QAM   #
############################################################

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math
import html
import base64

# =========================================================
# ⚙️ PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Pilot-Grade Tactical Weather Ops",
    layout="wide"
)

# =========================================================
# 🎨 CSS – AVIONICS STYLE
# =========================================================
st.markdown("""
<style>
body { background-color:#0b0f19; color:#e8e8e8; }
.metric-box {
    background:rgba(255,255,255,0.03);
    padding:12px 18px;
    border-radius:12px;
    border:1px solid rgba(255,255,255,0.04);
    margin-bottom:8px;
}
.big { font-size:28px; font-weight:700; }
.med { font-size:18px; font-weight:600; }
.small { font-size:13px; opacity:0.78; }
.section-title { font-size:20px; margin-top:14px; color:#9adf4f; }
.codebox { background:#0a0b0a; padding:8px; border-radius:6px; border:1px solid #1e2b1e; color:#dfffe0; font-family: monospace; white-space: pre-wrap; }
.radar-placeholder { width:100%; height:240px; border-radius:8px; background:linear-gradient(90deg, rgba(50,60,50,0.04), rgba(20,25,20,0.02)); display:flex; align-items:center; justify-content:center; color:#7a7; border:1px dashed #2b3c2b; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 📡 CONFIG & HELPERS
# =========================================================
API_BASE_EXAMPLE = "https://sample-api/cuaca"  # Replace with your real endpoint if available
MS_TO_KT = 1.94384
METER_TO_SM = 0.000621371

def safe_float(x):
    try:
        if x is None:
            return np.nan
        return float(x)
    except:
        return np.nan

def vis_to_sm(vis_m):
    try:
        return float(vis_m) * METER_TO_SM
    except:
        return None

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct) or tcc_pct is None:
        return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1:
        return 99999, "SKC (Clear)"
    elif tcc < 25:
        return 3500, "FEW (>3000 ft)"
    elif tcc < 50:
        return 2250, "SCT (1500-3000 ft)"
    elif tcc < 75:
        return 1250, "BKN (1000-1500 ft)"
    else:
        return 800, "OVC (<1000 ft)"

def classify_flight_cat(vis_m, ceiling_ft):
    vis_sm = vis_to_sm(vis_m)
    if vis_sm is None:
        return "Unknown"
    if vis_sm >= 8 and (ceiling_ft is None or ceiling_ft > 3000):
        return "VFR"
    if (3 <= vis_sm < 8) or (ceiling_ft is not None and 1000 < ceiling_ft <= 3000):
        return "MVFR"
    if (1 <= vis_sm < 3) or (ceiling_ft is not None and 500 < ceiling_ft <= 1000):
        return "IFR"
    if vis_sm < 1 or (ceiling_ft is not None and ceiling_ft <= 500):
        return "LIFR"
    return "Unknown"

def compute_wind_components(ws, wd, runway_heading):
    """Return (headwind, crosswind) in same units as ws."""
    try:
        ws_f = float(ws)
        wd_f = float(wd) % 360
        rwy = float(runway_heading) % 360
    except:
        return None, None
    angle = (wd_f - rwy + 360) % 360
    if angle > 180:
        angle -= 360
    rad = math.radians(angle)
    headwind = ws_f * math.cos(rad)
    crosswind = ws_f * math.sin(rad)
    return headwind, crosswind

def badge_html(text, kind="ok"):
    if kind == "ok":
        cls = "background:#b6ff6d; color:#002b00; padding:4px 8px; border-radius:6px; font-weight:700;"
    elif kind == "caut":
        cls = "background:#ffd86b; color:#4a3b00; padding:4px 8px; border-radius:6px; font-weight:700;"
    else:
        cls = "background:#ff6b6b; color:#2b0000; padding:4px 8px; border-radius:6px; font-weight:700;"
    return f"<span style='{cls}'>{html.escape(str(text))}</span>"

# =========================================================
# 🔁 DATA LOADERS (simple examples)
# =========================================================
@st.cache_data(ttl=180)
def fetch_json_api(url):
    """Simple GET -> JSON; adapt to your BMKG schema."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def df_from_bmkg_forecast(api_json):
    """
    Try to convert BMKG-like forecast object to a flat DataFrame.
    This function attempts to be flexible; adjust to your real payload.
    Expected each 'entry' to have 'lokasi' and 'cuaca' list of lists with obs dicts.
    If API returns simple timeseries with 'time', 't','ws',... you can skip this.
    """
    if not isinstance(api_json, dict):
        # If the API already returns a list-of-rows
        try:
            return pd.DataFrame(api_json)
        except:
            return pd.DataFrame()

    entries = api_json.get("data") or api_json.get("rows") or []
    rows = []
    for e in entries:
        lok = e.get("lokasi", {})
        for group in e.get("cuaca", []):
            for obs in group:
                r = obs.copy()
                r.update({
                    "adm1": lok.get("adm1"),
                    "adm2": lok.get("adm2"),
                    "provinsi": lok.get("provinsi"),
                    "kotkab": lok.get("kotkab"),
                    "lon": lok.get("lon"),
                    "lat": lok.get("lat"),
                })
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
                # numeric conversions for common keys
                for k in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
                    r[k] = safe_float(r.get(k))
                if not pd.isna(r.get("ws")):
                    r["ws_kt"] = r["ws"] * MS_TO_KT
                else:
                    r["ws_kt"] = np.nan
                rows.append(r)
    df = pd.DataFrame(rows)
    return df

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
st.sidebar.title("Controls")
api_url = st.sidebar.text_input("BMKG API URL or sample JSON URL", value=API_BASE_EXAMPLE)
st.sidebar.markdown("---")
# NOTE: removed leading-zero integer; use 4 instead of 04
runway_choices = [13, 31, 22, 4]
runway = st.sidebar.selectbox("Runway Heading (deg)", runway_choices, index=0)
st.sidebar.markdown("Select runway heading (true degrees) used for HW/XW calculation.")
st.sidebar.markdown("---")
time_hours = st.sidebar.slider("Show last hours", min_value=3, max_value=72, value=12, step=3)
show_qam = st.sidebar.checkbox("Enable QAM download", value=True)
st.sidebar.markdown("---")
st.sidebar.caption("Adjust API URL & runway for your environment")

# =========================================================
# FETCH & PARSE DATA
# =========================================================
st.title("✈️ Pilot-Grade Tactical Weather Ops — Fixed")

try:
    api_json = fetch_json_api(api_url)
except requests.exceptions.HTTPError as e:
    st.error(f"API Error: {e}")
    st.stop()
except Exception as e:
    st.error(f"Connection error: {e}")
    st.stop()

# Try to build dataframe
df = df_from_bmkg_forecast(api_json)
if df.empty:
    # Try a fallback: if API returns a plain timeseries list-of-dicts
    try:
        if isinstance(api_json, list):
            df = pd.DataFrame(api_json)
            # attempt to parse a time column if present
            for candidate in ["time","timestamp","datetime"]:
                if candidate in df.columns:
                    df[candidate] = pd.to_datetime(df[candidate], errors="coerce")
                    df = df.set_index(candidate)
                    break
    except:
        pass

if df.empty:
    st.warning("No usable forecast rows found. Please verify the API payload/schema.")
    st.stop()

# pick time column
time_col = None
if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
    df = df.sort_values("local_datetime_dt")
    time_col = "local_datetime_dt"
elif "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
    df = df.sort_values("utc_datetime_dt")
    time_col = "utc_datetime_dt"
else:
    # try index if datetime-like
    if np.issubdtype(df.index.dtype, np.datetime64):
        time_col = df.index.name or "index"
    else:
        # try to convert 'time' column if present
        for c in ["time","timestamp","datetime"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
                df = df.set_index(c)
                time_col = c
                break

if time_col is None:
    st.warning("No datetime column detected in data.")
    st.stop()

# filter timeframe
end = df[time_col].max()
start = end - timedelta(hours=time_hours)
df_sel = df[(df[time_col] >= start) & (df[time_col] <= end)].copy()

if df_sel.empty:
    st.warning("No rows in the selected time window.")
    st.stop()

# Choose 'now' as nearest to current time (or first if no better)
now_idx = (df_sel[time_col] - datetime.utcnow()).abs().idxmin() if not df_sel[time_col].isna().all() else df_sel.index[0]
now_row = df_sel.loc[now_idx] if now_idx in df_sel.index else df_sel.iloc[0]

# Safe extraction of common fields (adapt to your payload names)
t = safe_float(now_row.get("t"))
hu = safe_float(now_row.get("hu"))
ws = safe_float(now_row.get("ws"))
wd = safe_float(now_row.get("wd_deg") or now_row.get("wd") or now_row.get("wd_deg"))
vs_m = safe_float(now_row.get("vs"))  # metres
tp = safe_float(now_row.get("tp"))
tcc = safe_float(now_row.get("tcc"))
prov = now_row.get("provinsi", "")
kotkab = now_row.get("kotkab", "")
lat = now_row.get("lat", "")
lon = now_row.get("lon", "")

# compute derived values
ws_kt = ws * MS_TO_KT if not pd.isna(ws) else np.nan
ceiling_ft, ceiling_label = ceiling_proxy_from_tcc(tcc)
flight_cat = classify_flight_cat(vs_m, ceiling_ft)
hw, xw = compute_wind_components(ws_kt if not pd.isna(ws_kt) else 0, wd if not pd.isna(wd) else 0, runway)

# Safe display strings
ws_display = f"{ws_kt:.1f}" if (ws_kt is not None and not pd.isna(ws_kt)) else "—"
wd_display = f"{int(round(wd))}" if (wd is not None and not pd.isna(wd)) else "—"
hw_display = f"{hw:.1f} KT" if (hw is not None and not pd.isna(hw)) else "—"
if xw is not None and not pd.isna(xw):
    side = "from right" if xw > 0 else ("from left" if xw < 0 else "")
    xw_display = f"{abs(xw):.1f} KT {side}".strip()
else:
    xw_display = "—"
vis_sm = vis_to_sm(vs_m)
vis_sm_display = f"{vis_sm:.1f} SM" if vis_sm is not None else "—"
vs_display = f"{int(round(vs_m))} m" if (vs_m is not None and not pd.isna(vs_m)) else "—"
tp_display = f"{tp:.1f} mm" if (tp is not None and not pd.isna(tp)) else "0.0 mm"
t_display = f"{t:.1f} °C" if (t is not None and not pd.isna(t)) else "—"

# Decision logic
def decision_summary(ws_kt_val, vs_m_val, ceiling_ft_val, tp_mm):
    takeoff = "Recommended"
    landing = "Recommended"
    reasons = []
    try:
        if ws_kt_val is not None and not pd.isna(ws_kt_val):
            if ws_kt_val >= 30:
                takeoff = landing = "Not Recommended"
                reasons.append(f"High surface wind: {ws_kt_val:.1f} KT")
            elif ws_kt_val >= 20:
                reasons.append(f"Strong wind advisory: {ws_kt_val:.1f} KT")
    except:
        pass
    try:
        if vs_m_val is not None and not pd.isna(vs_m_val) and vs_m_val < 1000:
            landing = "Not Recommended"
            reasons.append(f"Low visibility: {int(round(vs_m_val))} m")
    except:
        pass
    try:
        if tp_mm is not None and not pd.isna(tp_mm):
            if tp_mm >= 20:
                takeoff = landing = "Caution"
                reasons.append(f"Heavy accumulated rain ({tp_mm:.1f} mm)")
            elif tp_mm > 5:
                reasons.append(f"Moderate rain ({tp_mm:.1f} mm)")
    except:
        pass
    try:
        if ceiling_ft_val is not None and ceiling_ft_val <= 500:
            landing = "Not Recommended"
            reasons.append(f"Low cloud base ({ceiling_ft_val} ft)")
    except:
        pass
    if not reasons:
        reasons.append("Conditions within conservative operational limits.")
    return takeoff, landing, reasons

takeoff_reco, landing_reco, reasons = decision_summary(ws_kt, vs_m, ceiling_ft, tp)

# ------------------------------
# UI: Top flight snapshot
# ------------------------------
st.markdown("## ✈️ Pilot Snapshot")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("<div class='metric-box'><div class='med'>Air Temperature</div><div class='big'>{}</div></div>".format(t_display), unsafe_allow_html=True)
    st.markdown("<div class='metric-box'><div class='med'>Humidity</div><div class='big'>{}%</div></div>".format(int(hu) if not pd.isna(hu) else "—"), unsafe_allow_html=True)
with c2:
    st.markdown("<div class='metric-box'><div class='med'>Wind</div><div class='big'>{} KT @ {}°</div><div class='small'>Runway {} → HW {}, XW {}</div></div>".format(ws_display, wd_display, runway, hw_display, xw_display), unsafe_allow_html=True)
with c3:
    st.markdown("<div class='metric-box'><div class='med'>Visibility</div><div class='big'>{} ({})</div></div>".format(vs_display, vis_sm_display), unsafe_allow_html=True)
with c4:
    st.markdown("<div class='metric-box'><div class='med'>Ceiling</div><div class='big'>{} / {} ft</div></div>".format(ceiling_label, ceiling_ft if ceiling_ft is not None else "—"), unsafe_allow_html=True)

st.markdown("---")

# Decision summary / one-liner
summary_sent = f"{flight_cat} conditions. Wind {ws_display} KT at {wd_display}°. RWY {runway} HW {hw_display}, XW {xw_display}. {', '.join(reasons[:2])}"
st.info(f"Decision Summary — {summary_sent}")

# Rationale
st.markdown("**Rationale / Notes**")
for r in reasons:
    st.markdown(f"- {r}")

# METAR-style synthetic for quick reading
def generate_metar_synthetic(now_row, station="XXXX"):
    try:
        dt = now_row.get("utc_datetime") or now_row.get("utc_datetime_dt") or now_row.get("local_datetime_dt")
        dt_parsed = pd.to_datetime(dt)
        time_token = dt_parsed.strftime("%d%H%M") + "Z"
    except:
        time_token = "000000Z"
    wind_token = "00000KT"
    try:
        if not pd.isna(now_row.get("wd_deg")) and not pd.isna(now_row.get("ws_kt")):
            wd_i = int(round(now_row.get("wd_deg")))
            ws_i = int(round(now_row.get("ws_kt")))
            wind_token = f"{wd_i:03d}{ws_i:02d}KT"
    except:
        pass
    vis_token = f"{int(round(now_row.get('vs',9999)))}m" if not pd.isna(now_row.get("vs")) else "9999m"
    wx = now_row.get("weather_desc","-") if "weather_desc" in now_row.index or "weather_desc" in now_row else now_row.get("weather","-")
    t_val = now_row.get("t")
    dew = None
    if not pd.isna(t_val) and not pd.isna(now_row.get("hu")):
        dew = t_val - ((100 - now_row.get("hu"))/5)
    t_token = f"{int(round(t_val))}/{int(round(dew))}" if dew is not None else "//"
    return f"{station} {time_token} {wind_token} {vis_token} {wx} {t_token} QNH_NA"

metar_text = generate_metar_synthetic(now_row, station="ICAO")
st.markdown("### METAR-style (synthetic)")
st.markdown(f"<div class='codebox'>{html.escape(metar_text)}</div>", unsafe_allow_html=True)

# ------------------------------
# Trends & Windrose
# ------------------------------
st.markdown("## Trends")
c1, c2, c3 = st.columns(3)
with c1:
    if "t" in df_sel.columns:
        fig = px.line(df_sel, x=time_col, y="t", title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)
with c2:
    if "ws_kt" in df_sel.columns:
        fig = px.line(df_sel, x=time_col, y="ws_kt", title="Wind (KT)")
        st.plotly_chart(fig, use_container_width=True)
with c3:
    if "tp" in df_sel.columns:
        fig = px.bar(df_sel, x=time_col, y="tp", title="Rainfall (mm)")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("## Windrose")
if {"wd_deg","ws_kt"}.issubset(df_sel.columns) and not df_sel[["wd_deg","ws_kt"]].dropna().empty:
    df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"]).copy()
    bins = np.arange(-11.25,360,22.5)
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins, labels=labels, include_lowest=True)
    speed_bins = [0,5,10,20,30,50,100]
    speed_labels = ["<5","5-10","10-20","20-30","30-50",">50"]
    df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
    freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
    if not freq.empty:
        freq["percent"] = freq["count"] / freq["count"].sum() * 100
        az_map = {lab: i*22.5 for i, lab in enumerate(labels)}
        freq["theta"] = freq["dir_sector"].map(az_map)
        fig_wr = go.Figure()
        colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
        for i, sc in enumerate(speed_labels):
            subset = freq[freq["speed_class"]==sc]
            fig_wr.add_trace(go.Barpolar(
                r=subset["percent"], theta=subset["theta"],
                name=f"{sc} KT", marker_color=colors[i] if i < len(colors) else None, opacity=0.85
            ))
        fig_wr.update_layout(title="Windrose (%)", template="plotly_dark", polar=dict(angularaxis=dict(direction="clockwise", rotation=90)))
        st.plotly_chart(fig_wr, use_container_width=True)
    else:
        st.info("Insufficient wind data for windrose")
else:
    st.info("Wind data not available for windrose")

# Radar placeholder
st.markdown("## Radar / Convective (placeholder)")
st.markdown("<div class='radar-placeholder'>Radar tiles or convective overlay placeholder — integrate BMKG/WMS if available.</div>", unsafe_allow_html=True)

# QAM MET report download
if show_qam:
    qam_html = f"""
    <html><head><meta charset='utf-8'><title>MET_REPORT</title></head><body style='font-family:Arial; background:#0b0f19; color:#dfffe0;'>
    <h3>METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</h3>
    <table border='1' cellpadding='6' style='border-collapse:collapse; color:#dfffe0;'>
      <tr><th>Station</th><td>{html.escape(str(kotkab or prov or 'Unknown'))}</td></tr>
      <tr><th>Time</th><td>{html.escape(str(now_row.get('local_datetime','—')))} / {html.escape(str(now_row.get('utc_datetime','—')))}</td></tr>
      <tr><th>Surface wind</th><td>{wd_display}° / {ws_display} KT (HW {html.escape(hw_display)}, XW {html.escape(xw_display)})</td></tr>
      <tr><th>Visibility</th><td>{vs_display} ({vis_sm_display})</td></tr>
      <tr><th>Present weather</th><td>{html.escape(str(now_row.get('weather_desc','—')))} (Rain acc: {tp_display})</td></tr>
      <tr><th>Cloud</th><td>{ceiling_label} / {ceiling_ft if ceiling_ft is not None else '—'} ft</td></tr>
      <tr><th>Temp / Dewpoint</th><td>{t_display} / Dewpoint est: {'—'}</td></tr>
      <tr><th>Decision</th><td>Takeoff: {takeoff_reco} — Landing: {landing_reco}</td></tr>
      <tr><th>Notes</th><td>{html.escape('; '.join(reasons))}</td></tr>
    </table>
    </body></html>
    """
    b64 = base64.b64encode(qam_html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="MET_REPORT.html">⬇ Download QAM MET Report (HTML)</a>'
    st.markdown(href, unsafe_allow_html=True)

# Export selected forecast table
st.markdown("---")
colx, coly = st.columns(2)
with colx:
    csv = df_sel.to_csv(index=False)
    st.download_button("⬇ Download CSV (selection)", data=csv, file_name="forecast_selection.csv", mime="text/csv")
with coly:
    json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
    st.download_button("⬇ Download JSON (selection)", data=json_text, file_name="forecast_selection.json", mime="application/json")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center; color:#7a7;'>Pilot-Grade Tactical Weather Ops — © 2025</div>", unsafe_allow_html=True)
