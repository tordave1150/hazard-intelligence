"""
Weather Advisor — Streamlit Dashboard (Forecast page).

Read-only dashboard that displays weather forecast data for all 77 Thai provinces.
Data is fetched by the ETL script (etl/fetch_weather.py) and stored in MongoDB Atlas.

Run with: streamlit run app/main.py

Task 1: 3D Hero Section (particle animation)
Task 2: Sky Palette light theme
Task 3: Caching layer integration
"""

import json
import pathlib
import subprocess
import sys
import os

import streamlit as st
import pandas as pd

from db import get_db, fetch_weather_data, get_cache_buster
from components.sidebar import render_sidebar
from components.map_view import render_map
from components.export import render_export
from components.hero_3d import render_hero_3d
from theme import apply_theme, get_alert_level

# ── Apply Sky Palette Light Theme (Task 2) ───────────────────────────
apply_theme()


# ── Helper Functions ──────────────────────────────────────────────────

def get_rain_emoji(level: str) -> str:
    """Return weather emoji for rain level string."""
    mapping = {
        "0-19% chance": "☀️",
        "20-39% chance": "🌤",
        "40-59% chance": "🌦",
        "60-79% chance": "🌧",
        "80-100% chance": "⛈",
    }
    return mapping.get(level, "🌡")


def get_rain_badge_html(level: str) -> str:
    """Return HTML badge for rain level."""
    cls_map = {
        "0-19% chance": "badge-no-rain",
        "20-39% chance": "badge-light",
        "40-59% chance": "badge-moderate",
        "60-79% chance": "badge-heavy",
        "80-100% chance": "badge-veryheavy",
    }
    cls = cls_map.get(level, "badge-no-rain")
    return f'<span class="{cls}">{level}</span>'


REGION_DOT_COLORS = {
    "Central": "#2563EB",
    "Northern": "#EF4444",
    "Northeastern": "#F97316",
    "Eastern": "#22C55E",
    "Southern": "#8B5CF6",
    "Western": "#64748B",
}


# ── Load province/district coords for enrichment ─────────────────────
@st.cache_data
def load_provinces():
    """Load the static provinces.json for lat/lon coordinates."""
    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "provinces.json"
    with open(path, "r", encoding="utf-8") as f:
        provinces = json.load(f)
    return {p["province"]: p for p in provinces}


@st.cache_data
def load_districts():
    """Load the static districts.json for lat/lon coordinates."""
    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "districts.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        districts = json.load(f)
    return {d["district"]: d for d in districts}


province_coords = load_provinces()
district_coords = load_districts()

# ── MongoDB Connection ────────────────────────────────────────────────
try:
    collection = get_db()
except Exception as e:
    st.error(
        "**MongoDB connection failed.** Please check your credentials in "
        "`.streamlit/secrets.toml`.\n\n"
        f"Error: `{type(e).__name__}`"
    )
    st.stop()

# ── Sidebar Filters ───────────────────────────────────────────────────
try:
    available_provinces = sorted(list(province_coords.keys()))
    available_districts = sorted(list(district_coords.keys()))
    filters = render_sidebar(collection, available_provinces, available_districts)

    # ── ETL Trigger (admin section in sidebar) ──
    with st.sidebar:
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#64748B; margin: 24px 0 4px 0;">DATA UPDATE</p>', unsafe_allow_html=True)

        ETL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "etl", "fetch_weather.py")

        if st.button("Refresh (legacy ingestion retired)", use_container_width=True, disabled=True):
            try:
                import datetime
                now_bkk = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
                current_round = "afternoon" if now_bkk.hour >= 13 else "morning"

                progress = st.progress(0, text="Fetching provinces...")
                errors = []

                # Province
                r1 = subprocess.run(
                    [
                        sys.executable,
                        ETL_PATH,
                        "--round",
                        current_round,
                        "--level",
                        "province",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if r1.returncode != 0:
                    errors.append(f"Province: {r1.stderr[:200]}")

                # District: targeted fetch if user has selected districts, else full fetch
                _sel_districts = filters.get("selected_districts", [])
                _level_now = filters.get("level", "province")

                if _level_now == "district" and _sel_districts:
                    dist_arg = ",".join(_sel_districts)
                    progress.progress(40, text=f"Fetching {len(_sel_districts)} selected district(s)...")
                    r2 = subprocess.run(
                        [
                            sys.executable,
                            ETL_PATH,
                            "--round", current_round,
                            "--level", "district",
                            "--districts", dist_arg,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                else:
                    progress.progress(
                        40,
                        text="Fetching all districts (this takes ~3 min)..."
                    )
                    r2 = subprocess.run(
                        [
                            sys.executable,
                            ETL_PATH,
                            "--round",
                            current_round,
                            "--level",
                            "district",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )

                if r2.returncode != 0:
                    errors.append(f"District: {r2.stderr[:200]}")

                progress.progress(
                    100,
                    text="Done!"
                )

                if not errors:
                    st.success(
                        "Province + District fetch complete!"
                    )
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(
                        " | ".join(errors)
                    )
            except Exception as e:
                st.error(f"{e}")
except Exception as e:
    st.error(
        "**MongoDB authentication failed.** The database rejected the credentials.\n\n"
        "Please verify the `uri`, `db_name`, and `collection` values in "
        "`.streamlit/secrets.toml`.\n\n"
        f"Error: `{type(e).__name__}`"
    )
    st.stop()

selected_date = filters["selected_date"]
selected_regions = filters["regions"]
selected_rain_levels = filters["rain_levels"]
province_search = filters.get("province_search", "")
level = filters.get("level", "province")
selected_province = filters.get("selected_province")
selected_districts = filters.get("selected_districts", [])

# ── Empty-state guard for district mode ──────────────────────────────
if level == "district" and not selected_districts:
    st.info(
        "Select one or more districts in the sidebar to load the dashboard."
    )
    st.stop()


# ── Fetch Data ────────────────────────────────────────────────────────
raw_data = fetch_weather_data(
    date_str=selected_date,
    regions=tuple(selected_regions) if selected_regions else (),
    rain_levels=(),  # Normalize legacy labels before filtering
    level=level,
    cache_buster=get_cache_buster(),
    selected_districts=tuple(selected_districts) if selected_districts else (),
)

# Apply filters client-side
from weather import map_rain_level
data = raw_data
for record in data:
    record["rain_level"] = map_rain_level(record.get("rain_probability"))
    for period in record.get("forecast_3_days", []):
        period["level"] = map_rain_level(period.get("rain_prob"))
if selected_rain_levels:
    data = [d for d in data if d.get("rain_level") in selected_rain_levels]

# Province scope filter (district mode — retained for any residual client-side scoping)
if level == "district" and selected_province:
    data = [d for d in data if d.get("province") == selected_province]

# Text search filter (province mode only now)
if province_search and level == "province":
    search_lower = province_search.lower()
    data = [d for d in data if search_lower in d.get("province", "").lower()]

# Enrich with lat/lon from static data (in case MongoDB docs don't have them)
for doc in data:
    if level == "district":
        dist_name = doc.get("district", "")
        if dist_name in district_coords:
            doc["lat"] = district_coords[dist_name]["lat"]
            doc["lon"] = district_coords[dist_name]["lon"]
    else:
        prov_name = doc.get("province", "")
        if prov_name in province_coords:
            doc["lat"] = province_coords[prov_name]["lat"]
            doc["lon"] = province_coords[prov_name]["lon"]

# ── KPI calculations ─────────────────────────────────────────────────
total_locations = len(data)
high_rain = sum(1 for d in data if d.get("rain_probability", 0) >= 40)
very_heavy = sum(1 for d in data if (d.get("rain_volume_mm") or 0) >= 35)
avg_prob = round(sum(d.get("rain_probability", 0) for d in data) / max(total_locations, 1), 1)

# Level-aware labels
location_label = "Districts" if level == "district" else "Provinces"
location_label_lower = "districts" if level == "district" else "provinces"

# ── Refresh time extraction ──────────────────────────────────────────
_refresh_time = "—"
_fetch_round = ""
if data:
    # Find the most recent logged_at across all documents
    logged_times = [d.get("logged_at", "") for d in data if d.get("logged_at")]
    if logged_times:
        latest_log = max(logged_times)
        try:
            from datetime import datetime as _dt
            _parsed = _dt.fromisoformat(latest_log)
            _refresh_time = _parsed.strftime("%H:%M")
        except Exception:
            _refresh_time = latest_log[:16]
    _fetch_round = data[0].get("fetch_round", "")

_round_label = f' · {_fetch_round.capitalize()} round' if _fetch_round else ""

# ── 3D Hero Section (Task 1) ─────────────────────────────────────────
import streamlit.components.v1 as components
components.html(
    render_hero_3d(
        rain_prob_avg=round(avg_prob, 1),
        high_rain_count=high_rain,
        date_str=f"{selected_date} {_refresh_time}" if _refresh_time != "—" else str(selected_date),
    ),
    height=296, # 280px + 16px margin
)

# ── Dynamic Alert Bar (Task 2) ───────────────────────────────────────
alert = {"show": False}  # Probability alone is not an agency warning
if alert["show"]:
    st.markdown(f"""
    <div class="alert-bar {alert['css_class']}">
        {alert['icon']} <strong>{alert['msg']}</strong> — plan outdoor activities accordingly.
    </div>
    """, unsafe_allow_html=True)

# ── KPI Metric Cards ─────────────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Coverage", total_locations)
    st.markdown(f'<p class="metric-sub">{location_label} tracked</p>', unsafe_allow_html=True)
with kpi2:
    st.metric("Points with ≥40% chance", high_rain)
    st.markdown('<p class="metric-sub">≥ 40% rain probability</p>', unsafe_allow_html=True)
with kpi3:
    st.metric("Points ≥35 mm / 24h", very_heavy)
    st.markdown('<p class="metric-sub">Exceeds 35 mm/day</p>', unsafe_allow_html=True)
with kpi4:
    st.metric("Mean chance of rain", f"{avg_prob}%")
    st.markdown('<p class="metric-sub">Across all regions</p>', unsafe_allow_html=True)

# ── Map Side-by-Side (Current vs Predicted) ───────────────────────────
col_map_curr, col_map_pred = st.columns(2)

with col_map_pred:
    map_title_pred = "Chance of Rain Forecast (%)"
    st.markdown(f"""
    <div class="section-card-header">
        <h3>{map_title_pred}</h3>
        <div class="legend">
            <span><span class="dot" style="background:#22C55E;"></span>Mod</span>
            <span><span class="dot" style="background:#F97316;"></span>Heavy</span>
            <span><span class="dot" style="background:#EF4444;"></span>V.Heavy</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    render_map(data, level=level, map_type="predicted")

with col_map_curr:
    map_title_curr = "Live Precipitation"
    st.markdown(f"""
    <div class="section-card-header">
        <h3>{map_title_curr}</h3>
        <div class="legend">
            <span><span class="dot" style="background:#22C55E;"></span>Mod</span>
            <span><span class="dot" style="background:#F97316;"></span>Heavy</span>
            <span><span class="dot" style="background:#EF4444;"></span>V.Heavy</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    render_map(data, level=level, map_type="current")


# ── 3-Day Forecast — FLAT DISPLAY ──────────────────────────
# Date range for header
if data and data[0].get("forecast_3_days"):
    fc_dates = [fc.get("date", "") for fc in data[0]["forecast_3_days"]]
    date_range_str = f"{selected_date[5:]} – {fc_dates[-1][5:]}" if fc_dates else ""
else:
    date_range_str = ""

st.markdown(f"""
<div class="section-card-header" style="margin-top: 8px; background: #FFFFFF; border-radius: 12px 12px 0 0; border: 1px solid #BFDBFE; border-bottom: none;">
    <h3>Regional Outlook — 3-Day</h3>
    <div class="legend"><span>{date_range_str}</span></div>
</div>
""", unsafe_allow_html=True)

if data:
    # Group data by region
    grouped = {}
    for d in data:
        reg = d.get("region", "Unknown")
        grouped.setdefault(reg, []).append(d)

    region_order = ["Central", "Northern", "Northeastern", "Eastern", "Southern", "Western"]
    regions_in_data = [r for r in region_order if r in set(d.get("region", "") for d in data)]
    count_label = "districts" if level == "district" else "provinces"

    for region in regions_in_data:
        docs = grouped.get(region, [])
        if not docs:
            continue

        # Sort docs by highest rain prob today
        docs_sorted = sorted(docs, key=lambda x: x.get("rain_probability", 0), reverse=True)

        with st.expander(f"{region} Region ({len(docs)} {count_label})"):
            for d in docs_sorted:
                loc_name = d.get("district") or d.get("province", "Unknown")
                prob = d.get("rain_probability", 0)
                emoji = get_rain_emoji(d.get("rain_level", ""))

                st.markdown(f"""
                <div class="list-item">
                    <span class="loc-name">{loc_name}</span>
                    <span class="badge" style="background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE; border-radius: 9999px; padding: 2px 10px; font-size: 12px;">
                        Today: {emoji} {prob}%
                    </span>
                </div>
                """, unsafe_allow_html=True)

                forecast = d.get("forecast_3_days", [])
                if forecast:
                    fcols = st.columns(len(forecast))
                    for i, fc in enumerate(forecast):
                        fc_level = fc.get("level", "")
                        fc_emoji = get_rain_emoji(fc_level)
                        fc_date = fc.get("date", "")
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(fc_date, "%Y-%m-%d")
                            fc_date_short = dt.strftime("%b %d")
                        except Exception:
                            fc_date_short = fc_date

                        # Dynamic color logic for cards (Sky Palette)
                        if fc_level == "80-100% chance":
                            bg_color = "rgba(239, 68, 68, 0.08)"
                            text_color = "#DC2626"
                            border_color = "#FECACA"
                        elif fc_level == "60-79% chance":
                            bg_color = "rgba(249, 115, 22, 0.08)"
                            text_color = "#EA580C"
                            border_color = "#FED7AA"
                        elif fc_level == "40-59% chance":
                            bg_color = "rgba(34, 197, 94, 0.08)"
                            text_color = "#16A34A"
                            border_color = "#BBF7D0"
                        elif fc_level == "20-39% chance":
                            bg_color = "rgba(6, 95, 70, 0.06)"
                            text_color = "#065F46"
                            border_color = "#6EE7B7"
                        else:
                            bg_color = "#F8FAFF"
                            text_color = "#0F172A"
                            border_color = "#E2E8F0"

                        with fcols[i]:
                            st.markdown(f"""
                            <div class="forecast-day-card" style="background: {bg_color}; border-color: {border_color};">
                                <p class="day-label">Day+{i+1} · {fc_date_short}</p>
                                <p class="day-value" style="color: {text_color};">{fc_emoji} {fc_level} ({fc.get('rain_prob', 0)}%)</p>
                            </div>
                            """, unsafe_allow_html=True)
                st.divider()
else:
    st.info("No forecast data available. Run the ETL script first: python etl/fetch_weather.py")

# ── Export Buttons (sidebar) ──────────────────────────────────────────
render_export(data, selected_date, level=level)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Weather Advisor • Data source: Open-Meteo API • Storage: MongoDB Atlas")
