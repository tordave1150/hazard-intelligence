#!/usr/bin/env python3
"""
Daily ETL — fetch Open-Meteo forecasts for Thai provinces/districts → upsert MongoDB.

Spec: OPEN_METEO_FETCH.md sections 7, 9

Usage:
    python etl/fetch_weather.py                                            # province, morning
    python etl/fetch_weather.py --round afternoon                          # province, afternoon
    python etl/fetch_weather.py --level district                           # district, morning (all 913)
    python etl/fetch_weather.py --level district --round afternoon         # district, afternoon (all 913)
    python etl/fetch_weather.py --level district --province "Chiang Mai"   # scope to one province's districts
    python etl/fetch_weather.py --level district --districts "Bang Rak,Din Daeng"  # fetch specific districts

Cron schedule (UTC):
    0 1 * * *   python etl/fetch_weather.py --round morning    (= 08:00 Bangkok)
    0  6 * * *   python etl/fetch_weather.py --round afternoon  (= 13:00 Bangkok)

This script runs standalone without Streamlit — secrets loaded via toml.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import os

import toml
from pymongo import MongoClient

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).parents[1]
PROVINCES_PATH = ROOT / "data/provinces.json"
DISTRICTS_PATH = ROOT / "data/districts.json"


# ── SECRETS loading (env vars first, fall back to secrets.toml) ───────────────
def _load_secrets() -> dict:
    """Load MongoDB credentials.
    Priority: environment variables (GitHub Actions) → .streamlit/secrets.toml (local).
    """
    uri      = os.getenv("MONGODB_URI")
    db_name  = os.getenv("MONGODB_DB_NAME")
    col_name = os.getenv("MONGODB_COLLECTION")

    if uri and db_name and col_name:
        return {"mongodb": {"uri": uri, "db_name": db_name, "collection": col_name}}

    secrets_path = ROOT / ".streamlit/secrets.toml"
    if secrets_path.exists():
        return toml.load(secrets_path)

    raise RuntimeError(
        "No MongoDB credentials found. "
        "Set MONGODB_URI, MONGODB_DB_NAME, MONGODB_COLLECTION env vars "
        "or provide .streamlit/secrets.toml."
    )

SECRETS = _load_secrets()

# ── Import shared weather client ──────────────────────────────────────────────
sys.path.insert(0, str(ROOT))
from app.weather import fetch_all_provinces  # noqa: E402

TZ_BANGKOK = timezone(timedelta(hours=7))


def get_collection():
    """Return the MongoDB collection using credentials from secrets.toml."""
    client = MongoClient(SECRETS["mongodb"]["uri"])
    db     = client[SECRETS["mongodb"]["db_name"]]
    return db[SECRETS["mongodb"]["collection"]]


def upsert_all(collection, docs: list[dict]) -> int:
    """Upsert all forecast documents, keyed by (date, province/district, level).

    Spec: OPEN_METEO_FETCH.md section 7 — afternoon round overwrites morning
    """
    success = 0
    for doc in docs:
        try:
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
            success += 1
        except Exception as e:
            label = doc.get("district", doc.get("province", "?"))
            print(f"  Upsert failed for {label}: {e}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Weather & Routing Advisor ETL")
    parser.add_argument(
        "--round",
        choices=["morning", "afternoon"],
        default="morning",
        help="Fetch round: morning (08:00 BKK) or afternoon (13:00 BKK)"
    )
    parser.add_argument(
        "--level",
        choices=["province", "district"],
        default="province",
        help="Granularity level: province (77 locations) or district (~913 locations)"
    )
    parser.add_argument(
        "--districts",
        default="",
        help="Comma-separated list of district names to fetch (district level only). "
             "When provided, only those districts are fetched instead of all 913."
    )
    parser.add_argument(
        "--province",
        default="",
        help="Scope district fetch to one province's districts (district level only). "
             "Uses the 'province' field in districts.json to filter."
    )
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"Weather ETL -- {args.round.upper()} ROUND -- {args.level.upper()} LEVEL")
    print(f"{datetime.now(tz=TZ_BANGKOK).strftime('%Y-%m-%d %H:%M:%S')} (Bangkok)")
    print(f"{'='*55}\n")

    # Load location list based on level
    if args.level == "district":
        locations = json.loads(DISTRICTS_PATH.read_text(encoding="utf-8"))
        print(f"Loaded {len(locations)} districts from file")

        # Apply subset filters if provided (additive: both --districts and --province can narrow the list)
        if args.districts:
            requested = {d.strip() for d in args.districts.split(",") if d.strip()}
            locations = [loc for loc in locations if loc.get("district") in requested]
            print(f"  --districts filter applied: {len(locations)} districts selected")
        elif args.province:
            locations = [loc for loc in locations if loc.get("province") == args.province.strip()]
            print(f"  --province filter applied: {len(locations)} districts in '{args.province.strip()}'")
        else:
            print(
                "  WARNING: No --districts or --province filter specified. "
                "Fetching all 913 districts (slow path — may take 45+ min)."
            )

        print(f"  Fetching {len(locations)} districts\n")
    else:
        locations = json.loads(PROVINCES_PATH.read_text(encoding="utf-8"))
        print(f"Loaded {len(locations)} provinces\n")

    # Fetch from Open-Meteo (free tier — no API key)
    docs = fetch_all_provinces(locations, fetch_round=args.round, level=args.level, sleep_sec=0.3)

    if not docs:
        print("No data fetched. Check network or Open-Meteo API status.")
        sys.exit(1)

    # Upsert to MongoDB Atlas
    print(f"\nUpserting {len(docs)} documents to MongoDB ...")
    collection = get_collection()
    saved = upsert_all(collection, docs)

    date_label = docs[0]["date"] if docs else "unknown"
    level_label = "districts" if args.level == "district" else "provinces"
    print(f"\n{'='*55}")
    print(f"Done: {saved}/{len(docs)} {level_label} saved  |  Date: {date_label}")
    print(f"{'='*55}\n")


    # Update cache-buster file to notify Streamlit to invalidate cache instantly
    cache_buster_path = ROOT / "data/last_update.txt"
    try:
        cache_buster_path.write_text(datetime.now(tz=TZ_BANGKOK).isoformat(), encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not write cache buster file: {e}")

if __name__ == "__main__":
    main()
