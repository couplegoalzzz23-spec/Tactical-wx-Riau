# ============================================================
# 🛰️ SATELLITE IMAGERY (OPTIONAL — SAFE)
# ============================================================
st.markdown("---")
st.subheader("🛰️ Satellite Overview (Situational Awareness)")

with st.expander("📡 Show Satellite Imagery", expanded=False):
    st.caption("Static satellite imagery for situational awareness only")

    sat_tabs = st.tabs(["IR Enhanced", "Visible", "Water Vapor"])

    with sat_tabs[0]:
        st.image(
            "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_IR_ENHANCED.png",
            caption="Himawari-8 IR Enhanced — BMKG",
            use_container_width=True
        )

    with sat_tabs[1]:
        st.image(
            "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_VIS.png",
            caption="Himawari-8 Visible — BMKG",
            use_container_width=True
        )

    with sat_tabs[2]:
        st.image(
            "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_WV.png",
            caption="Himawari-8 Water Vapor — BMKG",
            use_container_width=True
        )

    st.caption("⚠️ Delay ±10–15 minutes | Not for navigation")


# ============================================================
# ⚠️ SIGNIFICANT WEATHER WARNING (AUTO — NO API EXTRA)
# ============================================================
st.markdown("---")
st.subheader("⚠️ Significant Weather Assessment")

warnings = []

# --- WIND ---
if pd.notna(now.get("ws_kt")):
    if now["ws_kt"] >= 30:
        warnings.append(("🔴 HIGH WIND", "Surface wind ≥ 30 KT"))
    elif now["ws_kt"] >= 20:
        warnings.append(("🟠 STRONG WIND", "Surface wind ≥ 20 KT"))

# --- VISIBILITY ---
if pd.notna(now.get("vs")):
    if now["vs"] < 1000:
        warnings.append(("🔴 LOW VISIBILITY", "< 1000 m"))
    elif now["vs"] < 3000:
        warnings.append(("🟠 REDUCED VISIBILITY", "< 3000 m"))

# --- RAINFALL ---
if pd.notna(now.get("tp")):
    if now["tp"] >= 20:
        warnings.append(("🔴 HEAVY RAIN", "Runway contamination risk"))
    elif now["tp"] > 5:
        warnings.append(("🟠 MODERATE RAIN", "Wet runway"))

# --- CLOUD / CB PROXY ---
if pd.notna(now.get("tcc")) and now["tcc"] >= 75:
    warnings.append(("🟠 OVERCAST", "Potential low ceiling"))

if warnings:
    for w in warnings:
        st.warning(f"**{w[0]}** — {w[1]}")
else:
    st.success("✅ No significant weather hazards detected")


# ============================================================
# 🧊 ICING & CB POTENTIAL (HEURISTIC — AVIATION AWARENESS)
# ============================================================
st.markdown("---")
st.subheader("🧊 Aviation Hazard Potential")

hazards = []

# --- ICING (very simple proxy) ---
if pd.notna(now.get("t")) and pd.notna(now.get("hu")):
    if -10 <= now["t"] <= 5 and now["hu"] >= 80:
        hazards.append("🧊 Possible Airframe Icing (High RH + Low Temp)")

# --- CONVECTIVE ---
if pd.notna(now.get("tcc")) and pd.notna(now.get("tp")):
    if now["tcc"] > 70 and now["tp"] > 5:
        hazards.append("⛈️ Convective / CB Potential (Cloud + Rain)")

if hazards:
    for h in hazards:
        st.error(h)
else:
    st.success("No icing or convective hazard detected")


# ============================================================
# 🧭 CROSSWIND ADVISORY (RUNWAY-AGNOSTIC)
# ============================================================
st.markdown("---")
st.subheader("🧭 Crosswind Advisory (Generic)")

if pd.notna(now.get("ws_kt")):
    if now["ws_kt"] >= 25:
        st.error("🚨 Severe crosswind potential — Check runway alignment")
    elif now["ws_kt"] >= 15:
        st.warning("⚠️ Moderate crosswind — Pilot discretion")
    else:
        st.success("✅ Crosswind within normal operational range")
else:
    st.info("Wind data unavailable for crosswind assessment")


# ============================================================
# 📘 DISCLAIMER — OPERATIONAL SAFETY
# ============================================================
st.markdown("""
---
### ⚠️ Operational Disclaimer
- This dashboard is **NOT a replacement** for official **METAR / TAF / SIGMET**
- Satellite & hazard analysis are **heuristic / advisory**
- Use **ATC, MET Office & Pilot-in-Command judgement** for final decision

**Tactical Weather Ops Dashboard — BMKG**
""", unsafe_allow_html=True)
