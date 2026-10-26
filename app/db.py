"""
MongoDB connection and query helpers for the Weather Advisor.
"""

import pandas as pd
import streamlit as st
from pymongo import MongoClient


@st.cache_resource
def get_client():
    """Return a shared MongoClient. Streamlit reuses this across all reruns."""
    return MongoClient(st.secrets["mongodb"]["uri"], serverSelectionTimeoutMS=5000)


@st.cache_resource
def get_db():
    """Return the MongoDB collection, cached as a Streamlit resource.

    Uses st.secrets for connection details — never hard-code credentials.
    """
    client = get_client()
    db = client[st.secrets["mongodb"]["db_name"]]
    return db[st.secrets["mongodb"]["collection"]]


def get_cache_buster() -> str:
    """Read the last_update.txt file to act as a cache buster."""
    import pathlib
    path = pathlib.Path(__file__).resolve().parent.parent / "data" / "last_update.txt"
    try:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "0"


@st.cache_data(ttl=600)
def fetch_weather_data(date_str: str, regions: tuple, rain_levels: tuple, level: str = "province", cache_buster: str = "", selected_districts: tuple = ()) -> list[dict]:
    """Query MongoDB with filter parameters, cached for 10 minutes.

    Uses tuple parameters instead of lists because st.cache_data
    requires hashable argument types.

    Args:
        date_str:            Date string in YYYY-MM-DD format.
        regions:             Tuple of region names, e.g. ("Central", "Northern").
        rain_levels:         Tuple of rain level strings, e.g. ("Heavy Rain",).
        level:               "province" | "district" — granularity level.
        selected_districts:  Tuple of district names to filter (district mode only).
                             When non-empty, adds a $in filter on district.

    Returns:
        List of forecast dicts (without _id field).
    """
    client = get_client()
    db = client[st.secrets["mongodb"]["db_name"]]
    col = db[st.secrets["mongodb"]["collection"]]

    query: dict = {"date": date_str, "level": level}

    if regions:
        query["region"] = {"$in": list(regions)}
    if rain_levels:
        query["rain_level"] = {"$in": list(rain_levels)}
    if selected_districts and level == "district":
        query["district"] = {"$in": list(selected_districts)}

    sort_key = "district" if level == "district" else "province"
    docs = list(col.find(query, {"_id": 0}).sort(sort_key, 1))
    return docs


def upsert_forecast(collection, doc: dict):
    """Insert or replace a document keyed by (date, province/district, level).

    Used by the ETL script only — the dashboard is read-only.

    Args:
        collection: PyMongo collection object.
        doc: Forecast document dict.
    """
    level = doc.get("level", "province")
    if level == "district" and "district" in doc:
        key = {"date": doc["date"], "district": doc["district"], "level": level}
    else:
        key = {"date": doc["date"], "province": doc["province"], "level": level}

    collection.update_one(
        filter=key,
        update={"$set": doc},
        upsert=True,
    )


def get_forecasts(collection, date: str, regions: list[str] | None = None,
                  level: str = "province",
                  selected_districts: list[str] | None = None) -> list[dict]:
    """Return all location docs for a given date, optionally filtered by region.

    Args:
        collection:          PyMongo collection object.
        date:                Date string in YYYY-MM-DD format.
        regions:             Optional list of region names to filter by.
        level:               "province" | "district" — granularity level.
        selected_districts:  Optional list of district names to filter (district mode only).

    Returns:
        List of forecast dicts (without _id field).
    """
    query = {"date": date}
    # Only filter by level if the field exists in any document
    # (backward-compatible with documents that pre-date the level field)
    query["level"] = level
    if regions:
        query["region"] = {"$in": regions}
    if selected_districts and level == "district":
        query["district"] = {"$in": selected_districts}
    sort_key = "district" if level == "district" else "province"
    return list(collection.find(query, {"_id": 0}).sort(sort_key, 1))


def get_date_range(collection) -> tuple[str | None, str | None]:
    """Return (min_date, max_date) of logged data.

    Args:
        collection: PyMongo collection object.

    Returns:
        Tuple of (earliest_date, latest_date) strings, or (None, None) if empty.
    """
    pipeline = [
        {"$group": {"_id": None, "min": {"$min": "$date"}, "max": {"$max": "$date"}}}
    ]
    result = list(collection.aggregate(pipeline))
    if result:
        return result[0]["min"], result[0]["max"]
    return None, None


def get_historical_rain(
    selected_date,
    province: str = None,
    hour: int = None,
) -> pd.DataFrame:
    """
    Query ข้อมูลฝนจริงรายอำเภอจาก MongoDB
    
    ปัจจุบัน collection หลัก (weather_forecast) เก็บระดับจังหวัด
    ถ้ามี collection แยกสำหรับอำเภอให้ใช้ collection นั้นแทน
    ถ้ายังไม่มี — function นี้จะ fallback ไปใช้ collection จังหวัดก่อน
    แล้วค่อย migrate ทีหลังเมื่อ district-level data พร้อม
    """
    client = get_client()
    db = client[st.secrets["mongodb"]["db_name"]]
    
    # ดึงจาก collection weather_historical ที่ได้จาก backfill script
    col = db["weather_historical"]

    query = {"date": str(selected_date)}
    if province:
        query["province"] = province

    # ถ้ามีการระบุชั่วโมง เราต้องหาเอกสารที่มีชั่วโมงนั้นอยู่ใน rainy_hours_detail
    # rainy_hours_detail หน้าตาเป็นแบบนี้: ["05:00 (1.2mm)", "14:00 (3.4mm)"]
    if hour is not None:
        hour_prefix = f"{hour:02d}:00"
        # query แบบ Regex หรือ text match ใน array
        query["rainy_hours_detail"] = {"$regex": f"^{hour_prefix}"}

    docs = list(col.find(query, {"_id": 0}))
    df = pd.DataFrame(docs)
    
    # ถ้า collection ระดับจังหวัดยังไม่มี district field ให้ใส่ placeholder
    if not df.empty and "district" not in df.columns:
        df["district"] = "(Province Level)"
    
    return df

