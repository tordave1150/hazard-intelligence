"""
Sidebar filter controls for the Weather Advisor dashboard.
"""

import json
import pathlib
from datetime import datetime, date

import streamlit as st

from db import get_date_range

ALL_REGIONS = ["Northern", "Northeastern", "Central", "Eastern", "Western", "Southern"]
ALL_RAIN_LEVELS = ["0-19% chance", "20-39% chance", "40-59% chance", "60-79% chance", "80-100% chance"]

MAX_DISTRICT_WARNING = 50  # Warn if more than this many districts are selected


@st.cache_data
def _load_province_districts_map() -> dict[str, list[str]]:
    """Build a province → sorted list of district names mapping from districts.json."""
    path = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "districts.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        districts = json.load(f)
    mapping: dict[str, list[str]] = {}
    for d in districts:
        prov = d.get("province", "")
        dist = d.get("district", "")
        if prov and dist:
            mapping.setdefault(prov, []).append(dist)
    # Sort each province's district list
    for prov in mapping:
        mapping[prov].sort()
    return mapping


def render_sidebar(collection, available_provinces: list[str],
                   available_districts: list[str] | None = None) -> dict:
    """Render sidebar filters and return selected filter values.

    Args:
        collection: PyMongo collection object.
        available_provinces: Sorted list of all province names.
        available_districts: Sorted list of all district names (for district mode).

    Returns:
        Dict with keys: 'selected_date', 'regions', 'rain_levels',
        'province_search', 'level', 'selected_province', 'selected_districts'.
    """
    province_districts_map = _load_province_districts_map()

    with st.sidebar:
        # ── Logo row ──────────────────────────────────────────────────
        st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px; padding: 4px 0;">
            <div style="
                width:26px; height:26px;
                background:#1D9E75;
                border-radius:7px;
                display:flex; align-items:center; justify-content:center;
                font-size:14px; color:white;
            ">⛈</div>
            <span style="font-size:14px; font-weight:500; color:var(--color-text-primary, #E8E6DE);">Weather Advisor</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Granularity toggle (FEAT-01) ─────────────────────────────
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin-bottom:4px;">GRANULARITY</p>', unsafe_allow_html=True)
        level = st.radio(
            "Granularity",
            ["Province", "District"],
            horizontal=True,
            label_visibility="collapsed",
        )
        level_value = level.lower()  # "province" or "district"

        # ── Date picker ───────────────────────────────────────────────
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin-bottom:4px;">DATE</p>', unsafe_allow_html=True)

        min_date_str, max_date_str = get_date_range(collection)
        if min_date_str and max_date_str:
            min_date = datetime.strptime(min_date_str, "%Y-%m-%d").date()
            max_date = datetime.strptime(max_date_str, "%Y-%m-%d").date()
        else:
            min_date = date.today()
            max_date = date.today()

        selected_date = st.date_input(
            "Select Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
        )

        # ── Region multi-select ───────────────────────────────────────
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin: 16px 0 4px 0;">REGION</p>', unsafe_allow_html=True)
        regions = st.multiselect(
            "Regions",
            options=ALL_REGIONS,
            default=ALL_REGIONS,
            label_visibility="collapsed",
        )

        # ── Rain level filter ─────────────────────────────────────────
        st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin: 16px 0 4px 0;">RAIN LEVEL</p>', unsafe_allow_html=True)
        rain_levels = st.multiselect(
            "Rain Level",
            options=ALL_RAIN_LEVELS,
            default=["40-59% chance", "60-79% chance", "80-100% chance"],
            label_visibility="collapsed",
        )

        # ── Province / District filter ────────────────────────────────
        selected_province = None
        province_search = ""
        selected_districts: list[str] = []

        if level_value == "district":
            # Province scope selector — narrows the district multiselect
            st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin: 16px 0 4px 0;">PROVINCE (SCOPE)</p>', unsafe_allow_html=True)
            selected_province = st.selectbox(
                "Province",
                options=["All Provinces"] + available_provinces,
                label_visibility="collapsed",
            )
            if selected_province == "All Provinces":
                selected_province = None

            # Build the options list — scoped to province or full 913
            if selected_province and selected_province in province_districts_map:
                district_options = province_districts_map[selected_province]
            else:
                # All districts across all provinces
                district_options = sorted(available_districts) if available_districts else []

            st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin: 16px 0 4px 0;">DISTRICTS</p>', unsafe_allow_html=True)

            # Restore previous selection from session state, but only keep
            # districts that are valid in the current options list
            prev_key = f"_districts_sel_{selected_province or 'all'}"
            prev_sel = [d for d in st.session_state.get(prev_key, []) if d in district_options]

            selected_districts = st.multiselect(
                "Select districts",
                options=district_options,
                default=prev_sel,
                placeholder="Choose districts…",
                label_visibility="collapsed",
            )

            # Persist selection
            st.session_state[prev_key] = selected_districts

            if len(selected_districts) > MAX_DISTRICT_WARNING:
                st.warning(
                    f"Large selection ({len(selected_districts)} districts) — "
                    "rendering may be slow. Consider selecting fewer than 50."
                )

        else:
            # Province mode: free-text search
            st.markdown('<p style="font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#6B6A63; margin: 16px 0 4px 0;">PROVINCE</p>', unsafe_allow_html=True)
            province_search = st.text_input(
                "Filter province",
                placeholder="Filter province...",
                label_visibility="collapsed",
            )

    return {
        "selected_date": selected_date.strftime("%Y-%m-%d") if isinstance(selected_date, date) else str(selected_date),
        "regions": regions,
        "rain_levels": rain_levels,
        "province_search": province_search,
        "level": level_value,
        "selected_province": selected_province,
        "selected_districts": selected_districts,
    }
