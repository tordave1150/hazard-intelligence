#!/usr/bin/env python3
"""
Backfill historical weather data from Open-Meteo Archive API to MongoDB.
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
import toml
from pymongo import MongoClient

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).parents[1]
PROVINCES_PATH = ROOT / "data/provinces.json"
DISTRICTS_PATH = ROOT / "data/districts.json"

TZ_BANGKOK = timezone(timedelta(hours=7))
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# ── SECRETS loading ───────────────────────────────────────────────────────────
def _load_secrets() -> dict:
    uri      = os.getenv("MONGODB_URI")
    db_name  = os.getenv("MONGODB_DB_NAME")
    
    if uri and db_name:
        return {"mongodb": {"uri": uri, "db_name": db_name}}

    secrets_path = ROOT / ".streamlit/secrets.toml"
    if secrets_path.exists():
        return toml.load(secrets_path)

    raise RuntimeError("No MongoDB credentials found.")

SECRETS = _load_secrets()

def get_collection():
    client = MongoClient(SECRETS["mongodb"]["uri"])
    db     = client[SECRETS["mongodb"]["db_name"]]
    # Always use a dedicated historical collection to keep schemas clean
    return db["weather_historical"]

# ── Data Processing ───────────────────────────────────────────────────────────
def map_rain_status(precip_sum: float) -> str:
    if precip_sum <= 0.0: return "No Rain"
    if precip_sum <= 10.0: return "Light Rain"
    if precip_sum <= 35.0: return "Moderate Rain"
    if precip_sum <= 90.0: return "Heavy Rain"
    return "Very Heavy Rain"

def fetch_historical_data(loc: dict, start_date: str, end_date: str, level: str) -> list[dict]:
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum,showers_sum,precipitation_hours,temperature_2m_max,temperature_2m_min,wind_gusts_10m_max",
        "hourly": "precipitation",
        "timezone": "Asia/Bangkok"
    }

    max_retries = 3
    data = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                label = loc.get("district", loc.get("province", "?"))
                print(f"  ❌ {label} API Error: {e}")
                return []

    if not data or "daily" not in data:
        return []

    daily = data["daily"]
    hourly = data.get("hourly", {})
    hourly_precip = hourly.get("precipitation", [])
    
    num_days = len(daily["time"])
    docs = []

    for i in range(num_days):
        date_str = daily["time"][i]
        
        # Calculate daily fields
        precip_sum = float(daily["precipitation_sum"][i] or 0.0)
        rain_sum = float(daily["rain_sum"][i] or 0.0)
        showers_sum = float(daily["showers_sum"][i] or 0.0)
        precip_hours = float(daily["precipitation_hours"][i] or 0.0)
        temp_max = float(daily["temperature_2m_max"][i] or 0.0)
        temp_min = float(daily["temperature_2m_min"][i] or 0.0)
        wind_max = float(daily["wind_gusts_10m_max"][i] or 0.0)
        
        has_rain = precip_sum > 0.0
        rain_status = map_rain_status(precip_sum)
        
        # Process hourly detail (24 hours per day)
        start_idx = i * 24
        end_idx = start_idx + 24
        day_hourly = hourly_precip[start_idx:end_idx] if len(hourly_precip) >= end_idx else []
        
        rainy_hours_detail = []
        for h, precip in enumerate(day_hourly):
            if precip is not None and precip > 0:
                rainy_hours_detail.append(f"{h:02d}:00 ({precip}mm)")
                
        doc = {
            "date": date_str,
            "district": loc.get("district", "(Province Level)"),
            "province": loc.get("province", ""),
            "region": loc.get("region", ""),
            "has_rain": has_rain,
            "rain_status": rain_status,
            "precip_sum_mm": precip_sum,
            "rain_sum_mm": rain_sum,
            "showers_sum_mm": showers_sum,
            "precip_hours": precip_hours,
            "temp_max_c": temp_max,
            "temp_min_c": temp_min,
            "wind_max_kmh": wind_max,
            "rainy_hours_detail": rainy_hours_detail,
        }
        docs.append(doc)
        
    return docs

def upsert_all(collection, docs: list[dict]) -> int:
    success = 0
    for doc in docs:
        try:
            key = {
                "date": doc["date"], 
                "province": doc["province"], 
                "district": doc["district"]
            }
            collection.update_one(filter=key, update={"$set": doc}, upsert=True)
            success += 1
        except Exception as e:
            print(f"  Upsert failed for {doc['district']}/{doc['province']} on {doc['date']}: {e}")
    return success

def main():
    parser = argparse.ArgumentParser(description="Backfill Historical Weather Data")
    parser.add_argument("--days", type=int, default=7, help="Number of days to backfill")
    parser.add_argument("--level", choices=["province", "district"], default="province")
    args = parser.parse_args()

    # The archive API is often delayed by a few days. We start the end_date 2 days ago.
    today = datetime.now(tz=TZ_BANGKOK).date()
    end_date = today - timedelta(days=2)
    start_date = end_date - timedelta(days=args.days - 1)

    print(f"\n{'='*55}")
    print(f"Historical Backfill -- {args.level.upper()} LEVEL")
    print(f"Period: {start_date} to {end_date} ({args.days} days)")
    print(f"{'='*55}\n")

    if args.level == "district":
        locations = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))
    else:
        locations = json.loads(PROVINCES_PATH.read_text(encoding="utf-8"))
    
    print(f"Loaded {len(locations)} locations.")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_docs = []
    
    def process_location(idx, loc):
        url = f"{BASE_URL}?latitude={loc['lat']}&longitude={loc['lon']}&start_date={start_date}&end_date={end_date}&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,wind_gusts_10m_max,rain_sum,showers_sum,precipitation_hours&hourly=precipitation&timezone=Asia%2FBangkok"
        
        for attempt in range(5):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 429:
                    time.sleep(1 + (2 ** attempt))
                    continue
                r.raise_for_status()
                data = r.json()
                
                docs = []
                if "daily" not in data or "time" not in data["daily"]:
                    return docs

                dates = data["daily"]["time"]
                for i, date_str in enumerate(dates):
                    precip_sum_mm = data["daily"].get("precipitation_sum", [])[i]
                    rain_sum_mm = data["daily"].get("rain_sum", [])[i]
                    showers_sum_mm = data["daily"].get("showers_sum", [])[i]
                    precip_hours = data["daily"].get("precipitation_hours", [])[i]
                    temp_max_c = data["daily"].get("temperature_2m_max", [])[i]
                    temp_min_c = data["daily"].get("temperature_2m_min", [])[i]
                    wind_max_kmh = data["daily"].get("wind_gusts_10m_max", [])[i]

                    has_rain = precip_sum_mm > 0 if precip_sum_mm is not None else False
                    rain_status = "No Rain"
                    if has_rain:
                        if precip_sum_mm >= 35: rain_status = "Very Heavy Rain"
                        elif precip_sum_mm >= 10: rain_status = "Heavy Rain"
                        elif precip_sum_mm >= 0.1: rain_status = "Light Rain"

                    rainy_hours_detail = []
                    if "hourly" in data and "time" in data["hourly"]:
                        hourly_times = data["hourly"]["time"]
                        hourly_precip = data["hourly"].get("precipitation", [])
                        for t, p in zip(hourly_times, hourly_precip):
                            if t.startswith(date_str) and p and p > 0:
                                time_only = t.split("T")[1]
                                rainy_hours_detail.append(f"{time_only} ({p}mm)")

                    doc = {
                        "date": date_str,
                        "district": loc.get("district", "(Province Level)"),
                        "province": loc.get("province", ""),
                        "region": loc.get("region", ""),
                        "has_rain": has_rain,
                        "rain_status": rain_status,
                        "precip_sum_mm": precip_sum_mm,
                        "rain_sum_mm": rain_sum_mm,
                        "showers_sum_mm": showers_sum_mm,
                        "precip_hours": precip_hours,
                        "temp_max_c": temp_max_c,
                        "temp_min_c": temp_min_c,
                        "wind_max_kmh": wind_max_kmh,
                        "rainy_hours_detail": rainy_hours_detail
                    }
                    docs.append(doc)
                return docs
            except Exception as e:
                if attempt < 4:
                    time.sleep(1 + (2 ** attempt))
                    continue
                print(f"Error fetching {loc.get('district', '')}: {e}")
                return []
        return []

    print(f"\nFetching data for {len(locations)} locations using ThreadPoolExecutor (max 10 threads)...")
    collection = get_collection()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_loc = {executor.submit(process_location, idx, loc): loc for idx, loc in enumerate(locations, 1)}
        
        count = 0
        for future in as_completed(future_to_loc):
            docs = future.result()
            if docs:
                all_docs.extend(docs)
            count += 1
            if count % 10 == 0:
                print(f"  [{count:03d}/{len(locations)}] processed.")
                
            if len(all_docs) >= 500:
                print(f"  >> Upserting batch of {len(all_docs)} documents...")
                upsert_all(collection, all_docs)
                all_docs = []
                
    if all_docs:
        print(f"\nUpserting final {len(all_docs)} documents to MongoDB 'weather_historical' collection...")
    else:
        print("\nAll batches upserted successfully.")
        
    print("\n✅ Backfill completed successfully!")

if __name__ == "__main__":
    main()
