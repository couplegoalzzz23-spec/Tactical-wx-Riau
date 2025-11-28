# =====================================
# ⚡ METRIC PANEL — DITAMBAHKAN PARAMETER API BMKG
# =====================================
st.markdown("---")
st.subheader("⚡ Tactical Weather Status")

now = df_sel.iloc[0]

# --- BARIS METRIC UTAMA (ASLI) ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("TEMP (°C)", f"{now.get('t', '—')}°C")
with c2: st.metric("HUMIDITY", f"{now.get('hu', '—')}%")
with c3: st.metric("WIND (KT)", f"{now.get('ws_kt', 0):.1f}")
with c4: st.metric("RAIN (mm)", f"{now.get('tp', '—')}")

# =====================================
# 🔵 PENAMBAHAN PARAMETER API BMKG
# =====================================
st.markdown("### 🔍 Detailed Atmospheric Parameters")

c5, c6, c7, c8 = st.columns(4)
with c5:
    st.metric("CLOUD COVER (%)", f"{now.get('tcc','—')} %")
with c6:
    st.metric("WIND DIR (°)", f"{now.get('wd_deg','—')}°")
with c7:
    st.metric("WIND DIR (TEXT)", now.get("wd","—"))
with c8:
    st.metric("VISIBILITY (m)", f"{now.get('vs','—')} m")

# =====================================
# 🔵 PARAMETER DESKRIPSI CUACA
# =====================================
st.markdown("### ⛅ Weather Description")

c9, c10, c11 = st.columns(3)
with c9:
    st.metric("WEATHER CODE", now.get("weather","—"))
with c10:
    st.metric("WEATHER DESC", now.get("weather_desc","—"))
with c11:
    st.metric("VISIBILITY TEXT", now.get("vs_text","—"))

# =====================================
# 🔵 PARAMETER WAKTU & ANALISIS
# =====================================
st.markdown("### 🕒 Time & Analysis Details")

c12, c13, c14 = st.columns(3)
with c12:
    st.metric("TIME INDEX", now.get("time_index","—"))
with c13:
    st.metric("LOCAL TIME", now.get("local_datetime","—"))
with c14:
    st.metric("ANALYSIS DATE", now.get("analysis_date","—"))

# =====================================
# 🔵 PARAMETER LOKASI
# =====================================
st.markdown("### 📍 Location Information")

c15, c16, c17, c18 = st.columns(4)
with c15:
    st.metric("PROVINCE", now.get("provinsi","—"))
with c16:
    st.metric("CITY", now.get("kotkab","—"))
with c17:
    st.metric("LAT", now.get("lat","—"))
with c18:
    st.metric("LON", now.get("lon","—"))
