"""
Map view component — pydeck GeoJsonLayer choropleth.
Supports both Predicted (Daily) and Current (Real-time) map types,
and both Province and District granularity levels.

Task 2: Updated with light map style and Sky Palette tooltip.
Task 3: Added @st.cache_data caching for GeoJSON loading.
"""

import copy
import json
import pathlib

import streamlit as st
import pydeck as pdk


# Color mapping: rain_level → RGBA (updated for Sky Palette — Task 2)
RAIN_COLORS = {
    '0-19% chance': [208, 237, 236, 170],
    '20-39% chance': [146, 211, 205, 185],
    '40-59% chance': [74, 172, 175, 200],
    '60-79% chance': [30, 123, 151, 215],
    '80-100% chance': [17, 79, 118, 230],
    "No Rain":         [150, 150, 150, 100],      # gray
    "Light Rain":      [34, 197, 94, 160],         # green
    "Moderate Rain":   [34, 197, 94, 200],         # green #22C55E
    "Heavy Rain":      [249, 115, 22, 220],        # orange #F97316
    "Very Heavy Rain": [239, 68, 68, 240],         # red #EF4444
}

NO_DATA_COLOR = [200, 200, 200, 60]


@st.cache_data
def _load_geojson(level: str):
    """Load and return GeoJSON boundaries."""
    filename = "thailand_districts.geojson" if level == "district" else "thailand_provinces.geojson"
    path = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_province_geojson():
    """Public wrapper — pre-warm the province GeoJSON cache from home.py."""
    return _load_geojson("province")


def load_district_geojson():
    """Public wrapper — pre-warm the district GeoJSON cache from home.py."""
    return _load_geojson("district")


@st.cache_data
def _load_name_map(level: str):
    """Load GeoJSON → canonical name mapping."""
    filename = "district_name_map.json" if level == "district" else "province_name_map.json"
    path = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_current_rain_level(mm: float) -> str:
    """Map current precipitation_mm to a categorical level for consistent coloring."""
    if mm == 0:     return "No Rain"
    if mm < 2.5:    return "Light Rain"
    if mm < 10.0:   return "Moderate Rain"
    if mm < 50.0:   return "Heavy Rain"
    return "Very Heavy Rain"


@st.cache_data(ttl=3600, show_spinner="Preparing map…")
def _build_geojson_features(data_key: str, lookup_data: tuple, level: str):
    """Build colored GeoJSON features from lookup data.

    Cached for 1 hour — map geometry doesn't change often.

    Args:
        data_key:    Unique key for caching (combines filters).
        lookup_data: Tuple of (loc_name, rain_level, display_val, label) tuples.
        level:       "province" | "district"

    Returns:
        Deep-copied GeoJSON dict with fill_color properties set.
    """
    id_key = "district" if level == "district" else "province"
    geo_name_key = "amp_en" if level == "district" else "NAME_1"

    # Rebuild lookup dict from tuple data
    lookup = {}
    for item in lookup_data:
        loc_name, rain_level, display_val, label = item
        lookup[loc_name] = {
            "rain_level": rain_level,
            "display_val": display_val,
            "label": label,
        }

    geojson = _load_geojson(level)
    name_map = _load_name_map(level)

    # Shallow copy features to avoid massive deepcopy overhead for GeoJSON coords
    geojson_copy = {"type": geojson.get("type", "FeatureCollection"), "features": []}

    for feature in geojson["features"]:
        new_feature = {
            "type": feature.get("type", "Feature"),
            "geometry": feature.get("geometry"),  # keep reference to massive geometry array
            "properties": feature.get("properties", {}).copy() # copy properties so we can mutate
        }

        geo_name = new_feature["properties"].get(geo_name_key, "")

        if "Lake" in geo_name:
            new_feature["properties"]["fill_color"] = [0, 0, 0, 0]
            new_feature["properties"]["rain_level"] = ""
            new_feature["properties"]["display_val"] = ""
            new_feature["properties"]["loc_name"] = ""
            geojson_copy["features"].append(new_feature)
            continue

        # Map GeoJSON name to canonical name
        canonical_name = name_map.get(geo_name, geo_name)

        info = lookup.get(canonical_name)
        if info:
            color = RAIN_COLORS.get(info["rain_level"], NO_DATA_COLOR)
            new_feature["properties"]["rain_level"] = info["rain_level"]
            new_feature["properties"]["display_val"] = info["display_val"]
            new_feature["properties"]["label"] = info["label"]
        else:
            color = NO_DATA_COLOR
            new_feature["properties"]["rain_level"] = "No Data"
            new_feature["properties"]["display_val"] = "—"
            new_feature["properties"]["label"] = "Status"

        new_feature["properties"]["fill_color"] = color
        new_feature["properties"]["loc_name"] = canonical_name

        geojson_copy["features"].append(new_feature)

    return geojson_copy


def render_map(data: list[dict], level: str = "province", map_type: str = "predicted"):
    """Render a pydeck GeoJsonLayer choropleth map.

    Args:
        data: List of forecast dicts.
        level: "province" | "district"
        map_type: "predicted" (Daily aggregated) | "current" (Real-time snapshot)
    """
    if not data:
        st.info("📍 No data to display on map.")
        return

    # Determine key mapping
    id_key = "district" if level == "district" else "province"

    # Build lookup tuples (hashable for caching)
    lookup_items = []
    for d in data:
        loc_name = d.get(id_key, "")
        if not loc_name:
            continue

        if map_type == "current":
            current_data = d.get("current", {})
            precip_mm = float(current_data.get("precipitation_mm", 0.0))
            r_level = _get_current_rain_level(precip_mm)
            lookup_items.append((
                loc_name, r_level, f"{precip_mm} mm (interval unrecorded)", "Modeled current precipitation"
            ))
        else:
            r_level = d.get("rain_level", "No Rain")
            prob = d.get("rain_probability", 0)
            vol = round(d.get("rain_volume_mm", 0), 1)
            lookup_items.append((
                loc_name, r_level, f"{prob}% (Vol: {vol} mm)", "Chance of rain / forecast mm per local day"
            ))

    # Create cache key from sorted lookup items
    lookup_tuple = tuple(sorted(lookup_items, key=lambda x: x[0]))
    cache_key = f"{level}_{map_type}_{hash(lookup_tuple)}"

    geojson_copy = _build_geojson_features(cache_key, lookup_tuple, level)

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_copy,
        get_fill_color="properties.fill_color",
        get_line_color=[100, 116, 139, 60] if level == "province" else [100, 116, 139, 20],
        line_width_min_pixels=1 if level == "province" else 0,
        pickable=True,
        opacity=0.75,
        stroked=True,
    )

    # Calculate map center and zoom dynamically
    lats = [d.get("lat") for d in data if d.get("lat") is not None]
    lons = [d.get("lon") for d in data if d.get("lon") is not None]
    
    if lats and lons:
        avg_lat = sum(lats) / len(lats)
        avg_lon = sum(lons) / len(lons)
        
        # Calculate appropriate zoom based on coordinate spread
        lat_spread = max(lats) - min(lats)
        lon_spread = max(lons) - min(lons)
        max_spread = max(lat_spread, lon_spread)
        
        if max_spread > 0:
            import math
            zoom_level = math.log2(360.0 / max_spread) - 1.5
            zoom_level = max(5.0, min(zoom_level, 9.0)) # Clamp between country (5) and district cluster (9)
        else:
            zoom_level = 9.0 if level == "district" else 6.0
            
        view_state = pdk.ViewState(
            latitude=avg_lat,
            longitude=avg_lon,
            zoom=zoom_level,
            pitch=0,
        )
    else:
        # Fallback to whole Thailand
        view_state = pdk.ViewState(
            latitude=13.0,
            longitude=101.0,
            zoom=5.0,
            pitch=0,
        )

    # Light-themed tooltip (Task 2 — Sky Palette)
    tooltip = {
        "html": (
            "<b>{loc_name}</b><br/>"
            "Level: {rain_level}<br/>"
            "{label}: {display_val}"
        ),
        "style": {
            "backgroundColor": "white",
            "color": "#0F172A",
            "fontSize": "13px",
            "padding": "8px 12px",
            "borderRadius": "8px",
            "border": "1px solid #BFDBFE",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
        },
    }

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            # Light basemap — CartoDB Positron (no API key needed)
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        ),
        use_container_width=True,  # TODO: migrate to width='stretch' when min Streamlit >= 1.44
    )
