"""
Open-Meteo API client for fetching Thai province weather forecasts.

Spec: OPEN_METEO_FETCH.md — sections 2, 3, 4, 5, 8
Free tier: api.open-meteo.com (no API key required)
Commercial tier: customer-api.open-meteo.com (requires apikey param)
"""

import time
import requests
from datetime import datetime, timezone, timedelta

TZ_BANGKOK = timezone(timedelta(hours=7))
BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Daily variables — see OPEN_METEO_FETCH.md section 3.1
DAILY_VARS = ",".join([
    "precipitation_probability_max",
    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "weather_code",
    "wind_gusts_10m_max",
])

# Current condition variables — see OPEN_METEO_FETCH.md section 3.2
CURRENT_VARS = ",".join([
    "weather_code",
    "precipitation",
    "rain",
])

# WMO weather code mapping — (description, icon, risk_level)
# risk_level: none | low | medium | high | critical
WMO_MAP = {
    0:  ("Clear Sky",                "☀️",  "none"),
    1:  ("Mainly Clear",             "🌤️",  "none"),
    2:  ("Partly Cloudy",            "⛅",  "none"),
    3:  ("Overcast",                 "☁️",  "none"),
    45: ("Fog",                      "🌫️",  "low"),
    48: ("Rime Fog",                 "🌫️",  "low"),
    51: ("Light Drizzle",            "🌦️",  "low"),
    53: ("Moderate Drizzle",         "🌦️",  "low"),
    55: ("Dense Drizzle",            "🌧️",  "medium"),
    61: ("Slight Rain",              "🌧️",  "low"),
    63: ("Moderate Rain",            "🌧️",  "medium"),
    65: ("Heavy Rain",               "🌧️",  "high"),
    80: ("Slight Rain Showers",      "🌦️",  "low"),
    81: ("Moderate Rain Showers",    "🌧️",  "medium"),
    82: ("Violent Rain Showers",     "⛈️",  "high"),
    95: ("Thunderstorm",             "⛈️",  "high"),
    96: ("Thunderstorm + Hail",      "⛈️",  "critical"),
    99: ("Thunderstorm + Heavy Hail","⛈️",  "critical"),
}


def map_rain_level(rain_prob: int | None) -> str:
    """Legacy display compatibility: probability bands never imply intensity."""
    if rain_prob is None or not 0 <= rain_prob <= 100:
        return 'No data'
    if rain_prob < 20: return '0-19% chance'
    if rain_prob < 40: return '20-39% chance'
    if rain_prob < 60: return '40-59% chance'
    if rain_prob < 80: return '60-79% chance'
    return '80-100% chance'


def parse_wmo(code: int) -> tuple[str, str, str]:
    """Return (description, icon, risk_level) for a WMO weather code.

    Spec: OPEN_METEO_FETCH.md section 4
    """
    return WMO_MAP.get(int(code), ("Unknown", "❓", "none"))


def fetch_province_forecast(province: dict, fetch_round: str = "morning",
                            level: str = "province") -> dict | None:
    """Fetch 4-day daily forecast + current conditions for one location.

    Uses the Open-Meteo free tier (no API key).
    Spec: OPEN_METEO_FETCH.md section 8

    Args:
        province: Dict with keys province, region, lat, lon and optionally district.
        fetch_round: "morning" | "afternoon" — stored in MongoDB doc for traceability
        level: "province" | "district" — granularity level

    Returns:
        MongoDB document dict, or None on failure.
    """
    params = {
        "latitude":     province["lat"],
        "longitude":    province["lon"],
        "daily":        DAILY_VARS,
        "current":      CURRENT_VARS,
        "timezone":     "Asia/Bangkok",
        "forecast_days": 4,
    }

    max_retries = 2
    data = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            break  # Success
        except Exception as e:
            if attempt < max_retries - 1:
                if attempt == 0:
                    # Delay 15s on the very first error
                    label = province.get("district", province["province"])
                    print(f"\n  ⚠️ API error for {label}. Delaying 15s before retrying...", end="", flush=True)
                    time.sleep(3)
                else:
                    time.sleep(1)  # Wait 1 second for subsequent retries
            else:
                label = province.get("district", province["province"])
                print(f"  ❌ {label} (Failed after {max_retries} attempts): {e}")
                return None

    daily   = data["daily"]
    current = data.get("current", {})
    today   = daily["time"][0]  # YYYY-MM-DD (Bangkok time, index 0 = today)

    # Today's values (index 0)
    rain_prob   = int(daily["precipitation_probability_max"][0] or 0)
    precip_sum  = float(daily["precipitation_sum"][0] or 0.0)
    rain_sum    = float(daily["rain_sum"][0] or 0.0)
    showers_sum = float(daily["showers_sum"][0] or 0.0)
    wmo_today   = int(daily["weather_code"][0] or 0)
    wind_gusts  = float(daily["wind_gusts_10m_max"][0] or 0.0)

    wmo_desc, wmo_icon, wmo_risk = parse_wmo(wmo_today)

    # 3-day forecast (index 1, 2, 3)
    forecast_3_days = []
    for i in range(1, 4):
        rp  = int(daily["precipitation_probability_max"][i] or 0)
        wmo = int(daily["weather_code"][i] or 0)
        forecast_3_days.append({
            "date":                 daily["time"][i],
            "rain_prob":            rp,
            "level":                map_rain_level(rp),
            "precipitation_sum_mm": float(daily["precipitation_sum"][i] or 0.0),
            "showers_sum_mm":       float(daily["showers_sum"][i] or 0.0),
            "weather_code":         wmo,
        })

    doc = {
        "date":             today,
        "level":            level,
        "region":           province["region"],
        "province":         province["province"],

        "rain_probability": rain_prob,
        "rain_level":       map_rain_level(rain_prob),
        "rain_volume_mm":   precip_sum,

        "rain_sum_mm":      rain_sum,
        "showers_sum_mm":   showers_sum,

        "weather_code":     wmo_today,
        "weather_desc":     wmo_desc,
        "weather_icon":     wmo_icon,
        "weather_risk":     wmo_risk,

        "wind_gusts_kmh":   wind_gusts,

        "current": {
            "weather_code":     int(current.get("weather_code") or 0),
            "precipitation_mm": float(current.get("precipitation") or 0.0),
            "rain_mm":          float(current.get("rain") or 0.0),
        },

        "forecast_3_days":  forecast_3_days,
        "fetch_round":      fetch_round,
        "logged_at":        datetime.now(tz=TZ_BANGKOK).isoformat(),
    }

    # Add district field when operating at district level
    if level == "district" and "district" in province:
        doc["district"] = province["district"]

    return doc


def fetch_all_provinces(provinces: list[dict], fetch_round: str = "morning",
                        sleep_sec: float = 0.15,
                        level: str = "province") -> list[dict]:
    """Fetch forecasts for all locations sequentially.

    sleep_sec=0.15 → 77 provinces ≈ 12 seconds, 913 districts ≈ 2.3 minutes
    Safe for free tier rate limit (600 calls/min = max 10 calls/sec)
    Spec: OPEN_METEO_FETCH.md section 8

    Args:
        provinces: List of location dicts (province or district).
        fetch_round: "morning" | "afternoon"
        sleep_sec: Delay between requests (default 0.15s)
        level: "province" | "district" — granularity level

    Returns:
        List of successfully fetched forecast dicts.
    """
    results = []
    total   = len(provinces)
    label_key = "district" if level == "district" else "province"

    for i, prov in enumerate(provinces, 1):
        label = prov.get(label_key, prov.get("province", "Unknown"))
        print(f"  [{i:03d}/{total}] {label} ...", end=" ", flush=True)
        doc = fetch_province_forecast(prov, fetch_round, level=level)
        if doc:
            results.append(doc)
            print(f"OK  rain={doc['rain_probability']}%  [{doc['weather_risk']}]")
        else:
            print("FAILED")
        time.sleep(sleep_sec)

    level_label = "districts" if level == "district" else "provinces"
    print(f"\nFetched {len(results)}/{total} {level_label} ({fetch_round} round)")
    return results
