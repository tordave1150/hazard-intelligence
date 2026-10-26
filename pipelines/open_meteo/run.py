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
from .client import ProviderRequestError, fetch_batch
from .transform import normalize


def collect_forecasts(locations, fetcher=None, sleep=time.sleep):
    """Keep successful batches; recover transient gaps in at most two passes.

    Invalid data and permanent HTTP failures are never relaxed or retried here.
    The caller still requires complete, matching nationwide forecast periods.
    """
    fetcher = fetcher or fetch_batch
    pending = [(offset, locations[offset:offset + 25]) for offset in range(0, len(locations), 25)]
    records = []
    for recovery_pass in range(3):
        if not pending:
            break
        if recovery_pass:
            print(json.dumps({'event': 'recover_failed_batches', 'recovery_pass': recovery_pass,
                              'batches': len(pending), 'cooldown_seconds': 60}), flush=True)
            sleep(60)
        retry = []
        for offset, batch in pending:
            phase = 'fetch'
            try:
                payloads, fetched = fetcher(batch)
                if len(payloads) != len(batch):
                    raise ValueError('Incomplete provider batch')
                phase = 'normalize'
                normalized = [normalize(p, a, fetched) for p, a in zip(payloads, batch)]
                records.extend(normalized)
            except ProviderRequestError as exc:
                if exc.retryable:
                    retry.append((offset, batch))
                print(json.dumps({'batch_offset': offset, 'recovery_pass': recovery_pass, 'phase': phase,
                                  'error_type': type(exc).__name__, 'reason': exc.reason,
                                  'http_status': exc.status_code, 'retryable': exc.retryable}), flush=True)
            except (RuntimeError, ValueError, KeyError) as exc:
                print(json.dumps({'batch_offset': offset, 'recovery_pass': recovery_pass, 'phase': phase,
                                  'error_type': type(exc).__name__, 'retryable': False}), flush=True)
            print(json.dumps({'successful_locations': len(records), 'requested_locations': len(locations)}), flush=True)
            sleep(3)  # Preserve the conservative request cadence in recovery too.
        pending = retry
    found = {record['location_id'] for record in records}
    return records, [area['id'] for area in locations if area['id'] not in found]


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
        records, missing = collect_forecasts(locations)
        check_batch(records, [a['id'] for a in locations])
        status.update(status='SUCCESS', completed_at=utc_now(), last_success=utc_now(), records_validated=len(records),
                      successful_locations=len(records), missing_locations=[], completeness=1.0)
        if db is not None:
            control = Publisher(db).publish(records, [a['id'] for a in locations])
            status.update(records_published=len(records), active_generation=control['active_run_id'])
            db.source_status.update_one({'_id': key}, {'$set': status, '$unset': {'error_summary': ''}}, upsert=True)
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
