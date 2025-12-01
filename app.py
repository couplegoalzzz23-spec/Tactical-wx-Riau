# app_f16hud.py
# Tactical Weather Ops — BMKG (Pilot-grade + F-16 HUD overlay)
# Preserves original logic, adds runway tools, decision band, HUD, and UX fixes.

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import math

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Tactical Weather Ops — F-16 HUD Edition", layout="wide")

# ----------------------------
# Small helper: safe number formatting
# ----------------------------
def fmt(val, fmt_spec="{:.1f}", na="—"):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return na
        return fmt_spec.format(val)
    except Exception:
        return na

# ----------------------------
# CSS: base + HUD styling
# ----------------------------
HUD_CSS = """
<style>
:root{
  --hud-green: #7CFF6A;
  --hud-dark: #06110b;
  --panel-bg: rgba(6,17,11,0.7);
  --muted: #9aa29a;
}
body { background-color:#06110b; color:#dfffe0; font-family: "Consolas", "Roboto Mono", monospace; }

/* General metric box */
.metric-box{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(124,255,106,0.07);
  padding: 10px 14px;
  border-radius: 10px;
  margin-bottom: 8px;
}
.metric-label{ color: var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.6px; }
.metric-value{ color: var(--hud-green); font-size:20px; font-weight:700; }

/* Decision band */
.decision-band{
  width:100%;
  padding:12px;
  border-radius:6px;
  font-weight:800;
  font-size:18px;
  text-align:center;
  margin-bottom:12px;
  color:#001;
}
.band-go{ background: linear-gradient(90deg,#0ff78a,#00b24b); color:#001; }
.band-marginal{ background: linear-gradient(90deg,#ffd86b,#ffb347); color:#111; }
.band-nogo{ background: linear-gradient(90deg,#ff6b6b,#b30000); color:#fff; }

/* HUD overlay */
.hud-container{
  position: relative;
  width:100%;
  min-height:160px;
  margin-bottom:14px;
}
.hud {
  background: rgba(0,0,0,0.45);
  border:1px solid rgba(124,255,106,0.12);
  padding:10px;
  border-radius:8px;
  color:var(--hud-green);
  font-family: "Consolas", monospace;
}
.hud-row{ display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }
.hud-large{ font-size:36px; font-weight:900; color:var(--hud-green); }
.hud-small{ font-size:13px; color:var(--muted); }

/* F-16 pitch ladder mock */
.pitch-ladder {
  width: 240px;
  height: 120px;
  background: linear-gradient(180deg, rgba(0,0,0,0.2), rgba(0,0,0,0.05));
  border-radius:6px;
  border:1px solid rgba(124,255,106,0.06);
  padding:6px;
  color: var(--hud-green);
  font-size:12px;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
}

/* small badges */
.badge { padding:6px 8px; border-radius:6px; font-weight:700; font-size:13px; display:inline-block; }
.badge-ok { background:#b6ff6d; color:#002b00; }
.badge-caution { background:#ffd86b; color:#4a3b00; }
.badge-nogo { background:#ff6b6b; color:#2b0000; }

/* compact tactical strip */
.tactical-strip{
  background: linear-gradient(90deg, rgba(0,0,0,0.4), rgba(0,0,0,0.2));
  padding:8px;
  border-radius:6px;
  border:1px solid rgba(255,255,255,0.03);
  font-size:13px;
  color:var(--muted);
}

/* small table-like labels */
.info-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.info-cell { background: rgba(255,255,255,0.02); padding:8px; border-radius:6px; font-size:13px; }
</style>
"""
st.markdown(HUD_CSS, unsafe_allow_html=True)

# ----------------------------
# Config & API (preserve original)
# ----------------------------
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"  # original
MS_TO_KT = 1.94384
METER_TO_SM = 0.000621371
DEFAULT_ADM1 = "32"

# ----------------------------
# Utilities (preserve & enhance)
# ----------------------------
@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=10)
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
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs","ws_kt"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def estimate_dewpoint(temp, rh):
    if pd.isna(temp) or pd.isna(rh):
        return None
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct):
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

def convert_vis_to_sm(visibility_m):
    if pd.isna(visibility_m) or visibility_m is None:
        return "—"
    try:
        vis_m = float(visibility_m)
        vis_sm = vis_m * METER_TO_SM
        if vis_sm < 1:
            return f"{vis_sm:.1f} SM"
        elif vis_sm < 5:
            if (vis_sm * 2) % 2 == 0:
                return f"{int(vis_sm)} SM"
            else:
                return f"{vis_sm:.1f} SM"
        else:
            return f"{int(round(vis_sm))} SM"
    except Exception:
        return "—"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    if visibility_m is None or pd.isna(visibility_m):
        return "Unknown"
    vis_sm = float(visibility_m) / 1609.34
    if ceiling_ft is None:
        if vis_sm >= 3: return "VFR"
        elif vis_sm >= 1: return "MVFR"
        else: return "IFR"
    if vis_sm >= 5 and ceiling_ft > 3000: return "VFR"
    if (3 <= vis_sm < 5) or (1000 < ceiling_ft <= 3000): return "MVFR"
    if vis_sm < 3 or ceiling_ft <= 1000: return "IFR"
    return "Unknown"

def takeoff_landing_recommendation(ws_kt, vs_m, tp_mm):
    rationale = []
    takeoff = "Recommended"
    landing = "Recommended"
    if pd.notna(ws_kt) and float(ws_kt) >= 30:
        takeoff = "Not Recommended"
        landing = "Not Recommended"
        rationale.append(f"High surface wind: {ws_kt:.1f} KT (>=30 KT limit)")
    elif pd.notna(ws_kt) and float(ws_kt) >= 20:
        rationale.append(f"Strong wind: {ws_kt:.1f} KT (>=20 KT advisory)")
    if pd.notna(vs_m) and float(vs_m) < 1000:
        landing = "Not Recommended"
        rationale.append(f"Low visibility: {vs_m} m (<1000 m)")
    if pd.notna(tp_mm) and float(tp_mm) >= 20:
        takeoff = "Caution"
        landing = "Caution"
        rationale.append(f"Heavy accumulated rain: {tp_mm} mm (runway contamination possible)")
    elif pd.notna(tp_mm) and float(tp_mm) > 5:
        rationale.append(f"Moderate rainfall: {tp_mm} mm")
    if not rationale:
        rationale.append("Conditions within conservative operational limits.")
    return takeoff, landing, rationale

def badge_html(status):
    if status == "VFR" or status == "Recommended" or status == "SKC (Clear)":
        return "<span class='badge badge-ok'>OK</span>"
    if status == "MVFR" or status == "Caution":
        return "<span class='badge badge-caution'>CAUTION</span>"
    if status == "IFR" or status == "Not Recommended":
        return "<span class='badge badge-nogo'>NO-GO</span>"
    return "<span class='badge badge-caution'>UNKNOWN</span>"

# New: wind components for runway
def wind_components(ws_kt, wd_deg, rwy_deg):
    try:
        if ws_kt is None or pd.isna(ws_kt) or wd_deg is None or pd.isna(wd_deg):
            return None, None, None
        # angle difference where positive means wind is clockwise from runway heading
        diff = ((wd_deg - rwy_deg + 360) % 360)
        # convert to [-180, 180]
        if diff > 180:
            diff -= 360
        rad = math.radians(diff)
        head = ws_kt * math.cos(rad)
        cross = ws_kt * math.sin(rad)
        side = "L" if diff < 0 else "R"
        # rounding
        return round(head,1), round(abs(cross),1), side
    except Exception:
        return None, None, None

# New: gust proxy from recent df (max-min)
def gust_proxy_from_series(df, ws_col="ws_kt", window_hours=1):
    try:
        if ws_col not in df.columns:
            return None
        recent = df[df.index >= df.index.max() - pd.Timedelta(hours=window_hours)]
        if recent.empty:
            return None
        ws_vals = recent[ws_col].dropna().astype(float)
        if ws_vals.empty:
            return None
        proxy = ws_vals.max() - ws_vals.min()
        return round(proxy,1)
    except Exception:
        return None

# New: runway contamination estimate from tp (accumulated rainfall mm)
def runway_state_from_rain(tp_mm):
    try:
        if tp_mm is None or pd.isna(tp_mm):
            return "Unknown", "No data"
        tp = float(tp_mm)
        if tp >= 20:
            return "Severe (standing water likely)", "Poor braking"
        elif tp >= 10:
            return "Wet (water patches likely)", "Reduced braking"
        elif tp >= 2:
            return "Damp / Wet", "Minor reduction"
        else:
            return "Dry", "Good"
    except Exception:
        return "Unknown", "No data"

# ----------------------------
# Sidebar controls (original preserved + new)
# ----------------------------
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    adm1 = st.text_input("Province Code (ADM1)", value=DEFAULT_ADM1, max_chars=3)
    icao_code = st.text_input("ICAO Code (WXXX)", value="WXXX", max_chars=4)
    st.markdown("<div style='text-align:center'><div style='width:120px; margin:auto;'><svg width='120' height='120'><circle cx='60' cy='60' r='56' stroke='#33ff55' stroke-width='2' fill='rgba(0,0,0,0)' opacity='0.08'/></svg></div></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#7fbf7f;'>Scanning Weather...</p>", unsafe_allow_html=True)
    # Fetch button should trigger reload; we'll just allow manual fetch via rerun pattern
    if st.button("🔄 Fetch Data"):
        st.experimental_rerun()
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table (Raw Data)", value=False)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    # New: runway selector + units
    rwy_deg = st.number_input("Runway Heading (deg)", min_value=0, max_value=359, value=130, step=1)
    units = st.selectbox("Units", options=["Metric (m, km)", "Imperial (ft, SM)"], index=0)
    refresh_minutes = st.number_input("Auto-refresh (min, 0=off)", min_value=0, max_value=60, value=0, step=1)
    st.markdown("---")
    st.caption("Data Source: BMKG API · Military Ops UI")

# ----------------------------
# Load Data (original preserved)
# ----------------------------
st.title("Tactical Weather Operations Dashboard — F-16 HUD Edition")
st.markdown("*Source: BMKG Forecast API — Live Data*")

# Try fetch with graceful fallback
try:
    raw = fetch_forecast(adm1)
    entries = raw.get("data", []) if isinstance(raw, dict) else []
except Exception as e:
    entries = []
    fetch_error = e

if not entries:
    # fallback: inform and create dummy sample
    st.warning("API data unavailable — using sample/fallback forecast (check ADM1 or connectivity).")
    # create sample similar to earlier fallback
    now = pd.Timestamp.utcnow().floor("H")
    times = [now + pd.Timedelta(hours=i) for i in range(0, 24)]
    sample_rows = []
    for t in times:
        sample_rows.append({
            "utc_datetime": t.isoformat(),
            "local_datetime": (t + pd.Timedelta(hours=7)).isoformat(),
            "t": float(26 + 3*np.sin((t.hour/24)*2*math.pi)),
            "tcc": float(np.random.choice([10,30,60,90])),
            "tp": float(max(0, np.random.normal(2,3))),
            "wd_deg": float(np.random.uniform(0,360)),
            "ws": float(np.random.uniform(0,10)),
            "hu": float(np.random.uniform(60,95)),
            "vs": float(np.random.uniform(2000,10000)),
            "weather_desc": np.random.choice(["Clear","Cloudy","Light Rain","Heavy Rain"]),
            "weather": np.random.choice(["CLR","SCT","RA","TS"]),
            "vs_text": None
        })
    sample_entry = {
        "lokasi": {"adm1": adm1, "adm2": adm1, "provinsi":"Prov", "kotkab":"City", "lon":"106.8", "lat":"-6.2"},
        "cuaca": [sample_rows]
    }
    entries = [sample_entry]
    use_sample = True
else:
    use_sample = False

mapping = {}
for e in entries:
    lok = e.get("lokasi", {})
    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
    mapping[label] = {"entry": e}

col1, col2 = st.columns([2,1])
with col1:
    loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
with col2:
    st.metric("📍 Locations", len(mapping))

selected_entry = mapping[loc_choice]["entry"]
df = flatten_cuaca_entry(selected_entry)

if df.empty:
    st.warning("No valid weather data found for this location.")
    st.stop()

# compute ws_kt if not present
if "ws_kt" not in df.columns or df["ws_kt"].isna().all():
    # convert if 'ws' in m/s to kt
    if "ws" in df.columns:
        df["ws_kt"] = pd.to_numeric(df["ws"], errors="coerce") * MS_TO_KT
    else:
        df["ws_kt"] = np.nan
else:
    df["ws_kt"] = pd.to_numeric(df["ws_kt"], errors="coerce")

# choose datetime column
if "local_datetime_dt" in df.columns and df["local_datetime_dt"].notna().any():
    df = df.sort_values("local_datetime_dt")
    min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
    max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()
    use_col = "local_datetime_dt"
elif "utc_datetime_dt" in df.columns and df["utc_datetime_dt"].notna().any():
    df = df.sort_values("utc_datetime_dt")
    min_dt = df["utc_datetime_dt"].dropna().min().to_pydatetime()
    max_dt = df["utc_datetime_dt"].dropna().max().to_pydatetime()
    use_col = "utc_datetime_dt"
else:
    df.index = pd.RangeIndex(len(df))
    min_dt = 0
    max_dt = len(df)-1
    use_col = None

# slider (preserve behavior)
if use_col:
    with st.sidebar:
        start_dt = st.slider(
            "Time Range",
            min_value=min_dt,
            max_value=max_dt,
            value=(min_dt, min_dt + pd.Timedelta(hours=3)) if len(df) > 1 else (min_dt, max_dt),
            step=pd.Timedelta(hours=3),
            format="HH:mm, MMM DD"
        )
    mask = (df[use_col] >= pd.to_datetime(start_dt[0])) & (df[use_col] <= pd.to_datetime(start_dt[1]))
    df_sel = df.loc[mask].copy()
else:
    df_sel = df.copy()

if df_sel.empty:
    st.warning("No data in selected time range.")
    st.stop()

now = df_sel.iloc[0]

# prepare formatted metrics
dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
ceiling_display = f"{ceiling_est_ft} ft" if ceiling_est_ft is not None and ceiling_est_ft <= 99999 else "—"
vis_sm_disp = convert_vis_to_sm(now.get('vs'))

# Data age and confidence
obs_time = now.get("utc_datetime")
try:
    obs_ts = pd.to_datetime(obs_time)
    age_min = (pd.Timestamp.utcnow() - obs_ts).total_seconds() / 60.0
    age_min_int = int(round(age_min))
except Exception:
    age_min = None
    age_min_int = None

# Confidence: simple: more fields present -> higher
present_fields = sum([0 if pd.isna(now.get(f)) else 1 for f in ["t","hu","ws_kt","wd_deg","vs","tcc"]])
if present_fields >= 5:
    data_conf = "High"
elif present_fields >= 3:
    data_conf = "Medium"
else:
    data_conf = "Low"

# ----------------------------
# TOP DECISION BAND (F-16 HUD style summary)
# ----------------------------
# compute IFR/VFR etc and takeoff/landing recs
ifr_vfr = classify_ifr_vfr(now.get("vs"), ceiling_est_ft)
takeoff_reco, landing_reco, reco_rationale = takeoff_landing_recommendation(now.get("ws_kt"), now.get("vs"), now.get("tp"))

# Decide band color
if takeoff_reco == "Recommended" and landing_reco == "Recommended":
    band_cls = "band-go"
    band_text = f"TAKEOFF: {takeoff_reco} • LANDING: {landing_reco} • {ifr_vfr}"
elif takeoff_reco == "Not Recommended" or landing_reco == "Not Recommended":
    band_cls = "band-nogo"
    band_text = f"TAKEOFF: {takeoff_reco} • LANDING: {landing_reco} • {ifr_vfr}"
else:
    band_cls = "band-marginal"
    band_text = f"TAKEOFF: {takeoff_reco} • LANDING: {landing_reco} • {ifr_vfr}"

st.markdown(f"<div class='decision-band {band_cls}'>{band_text}</div>", unsafe_allow_html=True)

# Stale / confidence indicator
st.markdown(f"<div class='tactical-strip'><strong>Data age:</strong> {age_min_int if age_min_int is not None else '—'} min • <strong>Confidence:</strong> {data_conf}</div>", unsafe_allow_html=True)

# ----------------------------
# Key Meteorological Status (main cards) — preserve original look but improved
# ----------------------------
st.markdown("---")
st.markdown('<div class="hud-container">', unsafe_allow_html=True)
st.markdown('<div class="hud">', unsafe_allow_html=True)

# HUD top row (big quick facts)
colA, colB, colC, colD = st.columns([1.2,1,1,1])
with colA:
    st.markdown("<div class='metric-box'><div class='metric-label'>Temperature</div><div class='metric-value'>{}</div></div>".format(fmt(now.get('t'), "{:.1f} °C")), unsafe_allow_html=True)
with colB:
    st.markdown("<div class='metric-box'><div class='metric-label'>Wind (KT)</div><div class='metric-value'>{}</div></div>".format(fmt(now.get('ws_kt'), "{:.1f}")), unsafe_allow_html=True)
with colC:
    vis_display = fmt(now.get('vs'), "{:.0f} m") if now.get('vs') is not None else "—"
    st.markdown("<div class='metric-box'><div class='metric-label'>Visibility</div><div class='metric-value'>{}</div></div>".format(f"{vis_display} / {vis_sm_disp}"), unsafe_allow_html=True)
with colD:
    st.markdown("<div class='metric-box'><div class='metric-label'>Cloud Base</div><div class='metric-value'>{}</div></div>".format(ceiling_display), unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# HUD overlay (F-16 feel)
# ----------------------------
st.markdown("<div class='hud'>", unsafe_allow_html=True)
st.markdown("<div class='hud-row'>", unsafe_allow_html=True)

# Left: Pitch ladder mock / runway heading prominent
left_col, mid_col, right_col = st.columns([1,2,1])
with left_col:
    st.markdown("<div class='pitch-ladder'>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px;'>RWY</div><div class='hud-large'>{int(rwy_deg):03d}</div><div class='hud-small'>HDG</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with mid_col:
    # large HUD center showing mission status and major cues
    mission_color = "#7CFF6A" if band_cls=="band-go" else ("#FFD86B" if band_cls=="band-marginal" else "#FF6B6B")
    st.markdown(f"<div style='text-align:center; padding:8px;'><div style='font-size:20px; font-weight:900; color:{mission_color}'>MISSION: {band_text}</div><div style='font-size:12px; color:#9aa29a;'>ICAO: {icao_code} • LOC: {now.get('kotkab','—')} • {now.get('provinsi','—')}</div></div>", unsafe_allow_html=True)

with right_col:
    # show quick numeric stack
    st.markdown("<div style='display:flex; flex-direction:column; gap:6px;'>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-cell'>QNH: {fmt(now.get('qnh', None), '{:.0f}', na='—')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-cell'>TP Accum: {fmt(now.get('tp',0), '{:.1f} mm')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='info-cell'>Data Age: {age_min_int if age_min_int is not None else '—'} min</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Meteorological Details (preserve original with fixes)
# ----------------------------
st.markdown("## ☁ Meteorological Details")
detail_col1, detail_col2 = st.columns(2)

with detail_col1:
    st.markdown("##### Atmospheric State")
    col_t, col_dp = st.columns(2)
    with col_t:
        st.markdown("<div class='metric-label'>Air Temperature</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{fmt(now.get('t'), '{:.1f} °C')}</div>", unsafe_allow_html=True)
    with col_dp:
        st.markdown("<div class='metric-label'>Dew Point (Est)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{dewpt_disp}</div>", unsafe_allow_html=True)
    col_hu, col_wd = st.columns(2)
    with col_hu:
        st.markdown("<div class='metric-label'>Relative Humidity</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{fmt(now.get('hu'), '{:.0f} %')}</div>", unsafe_allow_html=True)
    with col_wd:
        st.markdown("<div class='metric-label'>Wind Direction</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{fmt(now.get('wd_deg'), '{:.0f}')}°</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px;'/>", unsafe_allow_html=True)
    st.markdown("<div class='tactical-strip'><strong>Location:</strong> {} • Lat:{}, Lon:{} </div>".format(now.get('kotkab','—'), now.get('lat','—'), now.get('lon','—')), unsafe_allow_html=True)

with detail_col2:
    st.markdown("##### Sky and Visibility")
    col_vis, col_ceil = st.columns(2)
    with col_vis:
        st.markdown("<div class='metric-label'>Visibility</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{fmt(now.get('vs'), '{:.0f} m')} / {vis_sm_disp}</div>", unsafe_allow_html=True)
    with col_ceil:
        st.markdown("<div class='metric-label'>Estimated Ceiling</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{ceiling_display}</div>", unsafe_allow_html=True)
    col_tcc, col_wx = st.columns(2)
    with col_tcc:
        st.markdown("<div class='metric-label'>Cloud Cover (%)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{fmt(now.get('tcc'), '{:.0f}')}%</div>", unsafe_allow_html=True)
    with col_wx:
        st.markdown("<div class='metric-label'>Present Weather</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='detail-value'>{now.get('weather_desc','—')} ({now.get('weather','—')})</div>", unsafe_allow_html=True)

# ----------------------------
# Runway-specific components: HW / XW / gust / runway state
# ----------------------------
st.markdown("## 🛫 Runway & Operational Components")
hw, xw, side = wind_components(now.get("ws_kt"), now.get("wd_deg"), rwy_deg)
gust_proxy = gust_proxy_from_series(df_sel, ws_col="ws_kt", window_hours=1)
rwy_state, braking = runway_state_from_rain(now.get("tp", 0))

hw_display = fmt(hw, "{:.1f} KT") if hw is not None else "—"
xw_display = fmt(xw, "{:.1f} KT") if xw is not None else "—"
side_display = side if side is not None else "—"
gust_display = fmt(gust_proxy, "{:.1f} KT") if gust_proxy is not None else "—"

st.markdown(f"""
<div class='metric-box'>
  <div class='metric-label'>Runway {int(rwy_deg):03d} — Wind Components</div>
  <div style='display:flex; gap:14px; flex-wrap:wrap;'>
    <div class='metric-value'>HW: {hw_display}</div>
    <div class='metric-value'>XW: {xw_display} ({side_display})</div>
    <div class='metric-value'>Gust Proxy: {gust_display}</div>
  </div>
  <div class='small'>Runway state: <strong>{rwy_state}</strong> — Braking: {braking}</div>
</div>
""", unsafe_allow_html=True)

# Crosswind advisory
crosswind_warning = ""
if xw is not None:
    if xw >= 25:
        crosswind_warning = "Strong CROSSWIND > 25 KT — NO-GO"
    elif xw >= 15:
        crosswind_warning = "Crosswind >=15 KT — CAUTION"
    elif xw >= 8:
        crosswind_warning = "Crosswind advisory"
if crosswind_warning:
    st.markdown(f"<div class='tactical-strip'><strong>Advisory:</strong> {crosswind_warning}</div>", unsafe_allow_html=True)

# ----------------------------
# Decision Matrix (preserve, but show thresholds)
# ----------------------------
st.markdown("---")
st.subheader("🔴 Operational Decision Matrix")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Regulatory Category**")
    st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(ifr_vfr)}  <strong style='margin-left:8px;'>{ifr_vfr}</strong></div>", unsafe_allow_html=True)
with col2:
    st.markdown("**Takeoff Recommendation**")
    st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(takeoff_reco)}  <strong style='margin-left:8px;'>{takeoff_reco}</strong></div>", unsafe_allow_html=True)
with col3:
    st.markdown("**Landing Recommendation**")
    st.markdown(f"<div style='padding:8px; border-radius:8px; background:#081108'>{badge_html(landing_reco)}  <strong style='margin-left:8px;'>{landing_reco}</strong></div>", unsafe_allow_html=True)

st.markdown("**Rationale / Notes:**")
for r in reco_rationale:
    st.markdown(f"- {r}")

# Also show explicit thresholds used
st.markdown("<div class='tactical-strip'><strong>Decision thresholds:</strong> XW limit=25KT NO-GO / 15KT caution; Visibility <3 km = IFR; Ceiling <1000 ft = IFR</div>", unsafe_allow_html=True)

# ----------------------------
# Trends (preserve)
# ----------------------------
st.markdown("---")
st.subheader("📊 Parameter Trends")
c1, c2 = st.columns(2)
with c1:
    try:
        c1.plotly_chart(px.line(df_sel, x=use_col if use_col else df_sel.index, y="t", title="Temperature"), use_container_width=True)
    except Exception:
        c1.write("Temperature plot unavailable")
    try:
        c1.plotly_chart(px.line(df_sel, x=use_col if use_col else df_sel.index, y="hu", title="Humidity"), use_container_width=True)
    except Exception:
        c1.write("Humidity plot unavailable")
with c2:
    try:
        c2.plotly_chart(px.line(df_sel, x=use_col if use_col else df_sel.index, y="ws_kt", title="Wind (KT)"), use_container_width=True)
    except Exception:
        c2.write("Wind plot unavailable")
    try:
        c2.plotly_chart(px.bar(df_sel, x=use_col if use_col else df_sel.index, y="tp", title="Rainfall"), use_container_width=True)
    except Exception:
        c2.write("Rainfall plot unavailable")

# ----------------------------
# Windrose (preserve with guard)
# ----------------------------
st.markdown("---")
st.subheader("🌪️ Windrose — Direction & Speed")
if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
    df_wr = df_sel.dropna(subset=["wd_deg","ws_kt"]).copy()
    if not df_wr.empty:
        try:
            bins_dir = np.arange(-11.25,360+22.5,22.5)
            labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
            speed_bins = [0,5,10,20,30,50,100]
            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
            df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
            freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
            freq["percent"] = freq["count"]/freq["count"].sum()*100
            az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,"S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
            freq["theta"] = freq["dir_sector"].map(az_map)
            colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
            fig_wr = go.Figure()
            for i, sc in enumerate(speed_labels):
                subset = freq[freq["speed_class"]==sc]
                fig_wr.add_trace(go.Barpolar(r=subset["percent"], theta=subset["theta"], name=f"{sc} KT", marker_color=colors[i], opacity=0.85))
            fig_wr.update_layout(title="Windrose (KT)", polar=dict(angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0,360,45))), radialaxis=dict(ticksuffix="%", showline=True, gridcolor="#333")), legend_title="Wind Speed Class", template="plotly_dark")
            st.plotly_chart(fig_wr, use_container_width=True)
        except Exception as e:
            st.info(f"Windrose generation failed: {e}")
    else:
        st.info("Insufficient wind data for Windrose plot.")
else:
    st.info("Wind data (wd_deg, ws_kt) not available in dataset for windrose.")

# ----------------------------
# Map (preserve)
# ----------------------------
if show_map:
    st.markdown("---")
    st.subheader("🗺️ Tactical Map")
    try:
        lat = float(selected_entry.get("lokasi", {}).get("lat", -6.2))
        lon = float(selected_entry.get("lokasi", {}).get("lon", 106.8))
        st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
    except Exception as e:
        st.warning(f"Map unavailable: {e}")

# ----------------------------
# Raw table (in expander)
# ----------------------------
if show_table:
    st.markdown("---")
    st.subheader("📋 Forecast Table (selected time range)")
    st.dataframe(df_sel)

# ----------------------------
# QAM Report + Download (preserve)
# ----------------------------
if show_qam_report:
    st.markdown("---")
    st.subheader("📝 Meteorological Report (QAM/Form Replication)")
    # build simple QAM html content
    met_html = f"""
    <div style='background:#0b0c0c; padding:12px; border-radius:8px; border:1px solid rgba(255,255,255,0.03);'>
    <h4>MET REPORT — {now.get('local_datetime','—')}</h4>
    <div><b>ICAO:</b> {icao_code} • <b>LOC:</b> {now.get('kotkab','—')}, {now.get('provinsi','—')}</div>
    <table style='width:100%; margin-top:8px;'>
      <tr><td><b>Wind</b></td><td>{fmt(now.get('wd_deg'), '{:.0f}')}° / {fmt(now.get('ws_kt'), '{:.1f}')} KT</td></tr>
      <tr><td><b>Visibility</b></td><td>{fmt(now.get('vs'), '{:.0f}')} m ({vis_sm_disp})</td></tr>
      <tr><td><b>Cloud</b></td><td>{fmt(now.get('tcc'), '{:.0f}')}% / {ceiling_display}</td></tr>
      <tr><td><b>Temp / Dew</b></td><td>{fmt(now.get('t'), '{:.1f} °C')} / {dewpt_disp}</td></tr>
      <tr><td><b>Accum Rain</b></td><td>{fmt(now.get('tp',0), '{:.1f} mm')}</td></tr>
    </table>
    </div>
    """
    st.markdown(met_html, unsafe_allow_html=True)
    full_qam_html = f"<html><head>{HUD_CSS}</head><body>{met_html}</body></html>"
    filename = f"MET_REPORT_{loc_choice}_{str(now.get('local_datetime','—')).replace(' ','_').replace(':','')}.html"
    st.download_button("⬇ Download QAM Report (HTML)", full_qam_html, file_name=filename, mime="text/html")

# ----------------------------
# Export CSV/JSON
# ----------------------------
st.markdown("---")
st.subheader("💾 Export Data")
csv = df_sel.to_csv(index=False)
json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
colA, colB = st.columns(2)
with colA:
    st.download_button("⬇ CSV", csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
with colB:
    st.download_button("⬇ JSON", json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")

# ----------------------------
# Footer
# ----------------------------
st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
F-16 HUD Edition · Military Ops UI · Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
