"""
Weather Advisor — Home page.

Serves as the deliberate landing/loading step so that Forecast and Historical
pages feel instant after the first cold start. Eagerly warms all
@st.cache_data / @st.cache_resource entries that those pages rely on.
"""

import streamlit as st
from datetime import date

from theme import apply_theme
from db import get_client, get_db
from components.map_view import load_province_geojson, load_district_geojson
from components.hero_3d import render_hero_3d

apply_theme()

# ── 3D Hero Section ───────────────────────────────────────────────────────────
today_str = date.today().strftime("%Y-%m-%d")

# Home page uses a fixed "welcome" variant of the hero:
# sky-blue sphere (low-risk palette), neutral text, no live data needed
_hero_html = render_hero_3d(
    rain_prob_avg=20,       # forces sky-blue palette (welcome feel)
    high_rain_count=0,
    date_str=today_str,
).replace(
    "Thailand<br>Weather<br>Forecast",
    "Weather<br>Advisor"
).replace(
    "0 high-rain zones · Avg 20% prob",
    "77 provinces · 913 districts"
).replace(
    "Low risk",
    "Thailand"
)

st.markdown(_hero_html, unsafe_allow_html=True)

# ── Cache Warm-Up ─────────────────────────────────────────────────────────────
# Only warm caches once per session — track with session state flag.
if not st.session_state.get("_home_warmed", False):
    with st.spinner("Connecting to database and loading map data…"):
        try:
            get_client()
            get_db()
            load_province_geojson()
            load_district_geojson()
            st.session_state["_home_warmed"] = True
        except Exception as e:
            st.warning(
                f"Some data could not be pre-loaded: `{type(e).__name__}`. "
                "The dashboards will load normally — initial map render may be slower."
            )
            st.session_state["_home_warmed"] = True  # don't retry on every rerun

# ── Navigation Cards ──────────────────────────────────────────────────────────
st.markdown("""
<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.12em;
          font-family:'IBM Plex Mono',monospace;
          color:#64748b; margin: 24px 0 12px 0;">WHERE WOULD YOU LIKE TO GO?</p>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 3])

with col1:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 1px solid #BFDBFE;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 8px;
    ">
        <p style="font-size:13px; font-weight:600; color:#1E40AF; margin:0 0 6px 0;">Forecast Dashboard</p>
        <p style="font-size:12px; color:#475569; margin:0;">
            Live province and district rainfall forecasts with interactive maps
            and 3-day regional outlook.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Open Forecast Dashboard", use_container_width=True, type="primary"):
        st.switch_page("forecast.py")

with col2:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border: 1px solid #BBF7D0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 8px;
    ">
        <p style="font-size:13px; font-weight:600; color:#15803D; margin:0 0 6px 0;">Historical Rain Report</p>
        <p style="font-size:12px; color:#475569; margin:0;">
            Historical rain data by district — explore past precipitation
            by date, province, and hour.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("View Historical Rain Report", use_container_width=True):
        st.switch_page("historical.py")

# ── Feature Summary ───────────────────────────────────────────────────────────
st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
st.markdown("""
<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.12em;
          font-family:'IBM Plex Mono',monospace; color:#64748b; margin-bottom:12px;">ABOUT THIS TOOL</p>
""", unsafe_allow_html=True)

info1, info2, info3 = st.columns(3)
with info1:
    st.markdown("""
    <div style="padding: 16px; background:#F8FAFF; border-radius:10px; border:1px solid #E2E8F0;">
        <p style="font-size:13px; font-weight:600; color:#1E3A5F; margin:0 0 4px 0;">Data Source</p>
        <p style="font-size:12px; color:#64748B; margin:0;">Open-Meteo API — free, no API key required. Updated twice daily (08:00 &amp; 13:00 BKK).</p>
    </div>
    """, unsafe_allow_html=True)
with info2:
    st.markdown("""
    <div style="padding: 16px; background:#F8FAFF; border-radius:10px; border:1px solid #E2E8F0;">
        <p style="font-size:13px; font-weight:600; color:#1E3A5F; margin:0 0 4px 0;">Storage</p>
        <p style="font-size:12px; color:#64748B; margin:0;">MongoDB Atlas — all forecast and historical records stored with 10-min dashboard cache.</p>
    </div>
    """, unsafe_allow_html=True)
with info3:
    st.markdown("""
    <div style="padding: 16px; background:#F8FAFF; border-radius:10px; border:1px solid #E2E8F0;">
        <p style="font-size:13px; font-weight:600; color:#1E3A5F; margin:0 0 4px 0;">Coverage</p>
        <p style="font-size:12px; color:#64748B; margin:0;">All 77 Thai provinces and 913 districts. Select district mode in the Forecast page for local detail.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Weather Advisor • Data source: Open-Meteo API • Storage: MongoDB Atlas")
