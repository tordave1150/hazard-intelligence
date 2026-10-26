"""python -m pipelines.open_meteo.run --level all [--publish] [--export PATH]"""
import argparse
import json
import os
import time
from uuid import uuid4
from pymongo import MongoClient
from pipelines.shared.locations import weather_locations
from pipelines.shared.publication import Publisher, export_local
from pipelines.shared.quality import check_batch
from pipelines.shared.time_units import utc_now
from .client import fetch_batch
from .transform import normalize


def main():
    parser = argparse.ArgumentParser(description='Validated latest Open-Meteo snapshot; no legacy collection writes')
    parser.add_argument('--level', choices=['province', 'district', 'all'], default='all')
    parser.add_argument('--publish', action='store_true', help='Publish full nationwide scope to Atlas')
    parser.add_argument('--export', help='Write real local snapshot atomically for local preview only')
    args = parser.parse_args()
    if args.publish and args.level != 'all':
        parser.error('Atlas publication requires --level all to avoid replacing national coverage with a subset')
    if not args.publish and not args.export:
        parser.error('Select --publish and/or --export')
    if args.publish and not os.getenv('MONGODB_URI'):
        parser.error('MONGODB_URI is required for publication')
    locations = weather_locations(args.level)
    status = {'source_id': 'open_meteo', 'product_id': 'daily_forecast', 'etl_run_id': str(uuid4()),
              'last_attempt': utc_now(), 'status': 'RUNNING', 'requested_locations': len(locations)}
    client = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=10000) if args.publish else None
    db = client[os.getenv('MONGODB_DB_NAME', 'weather_db')] if client is not None else None
    key = 'open_meteo:daily_forecast'
    records, missing = [], []
    try:
        for offset in range(0, len(locations), 25):
            batch = locations[offset:offset + 25]
            try:
                payloads, fetched = fetch_batch(batch)
                normalized = [normalize(p, a, fetched) for p, a in zip(payloads, batch)]
                records.extend(normalized)
            except (RuntimeError, ValueError, KeyError) as exc:
                missing.extend(a['id'] for a in batch)
                print(json.dumps({'batch_offset': offset, 'error_type': type(exc).__name__}))
            print(json.dumps({'successful_locations': len(records), 'requested_locations': len(locations)}), flush=True)
            time.sleep(3)  # <=500 weighted coordinate calls/minute even with fast responses
        check_batch(records, [a['id'] for a in locations])
        status.update(status='SUCCESS', completed_at=utc_now(), last_success=utc_now(), records_validated=len(records),
                      successful_locations=len(records), missing_locations=[], completeness=1.0)
        if db is not None:
            control = Publisher(db).publish(records, [a['id'] for a in locations])
            status.update(records_published=len(records), active_generation=control['active_run_id'])
            db.source_status.update_one({'_id': key}, {'$set': status}, upsert=True)
        if args.export:
            export_local(args.export, records, [a['id'] for a in locations], status)
        print(json.dumps({'status': 'SUCCESS', 'record_count': len(records)}))
    except Exception as exc:
        status.update(status='FAILED', completed_at=utc_now(), successful_locations=len(records),
                      missing_locations=missing, completeness=len(records) / max(len(locations), 1), error_summary=type(exc).__name__)
        if db is not None:
            db.source_status.update_one({'_id': key}, {'$set': status}, upsert=True)  # keeps last_success from prior run
        raise RuntimeError('Snapshot failed validation/publication; last good data retained') from None
    finally:
        if client is not None:
            client.close()


if __name__ == '__main__':
    main()
