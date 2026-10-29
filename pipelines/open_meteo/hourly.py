"""Separate, bounded Today-only forecast product; rain applies to the preceding hour."""
from datetime import timedelta, datetime, timezone
import math
from pipelines.shared.time_units import instant, daily_period, utc_now, BANGKOK
from pipelines.shared.publication import Publisher, export_local
from pipelines.shared.locations import weather_locations
from pipelines.shared.run_status import start_run
from .budget import request_budget
from .client import fetch_hourly_batch, ProviderRequestError

PRODUCT = 'today_hourly'
COLLECTION = 'weather_hourly_latest'


def check_record(record):
    start, _ = map(instant, daily_period(record['forecast_date']))
    if any(type(value) not in (int, float) or not math.isfinite(value) for point in ('point', 'model_point') for value in record[point].values()):
        raise ValueError('Non-finite hourly coordinates')
    if record['forecast_date'] != instant(record['fetched_at']).astimezone(BANGKOK).date().isoformat():
        raise ValueError('Hourly product must cover its retrieval day')
    if instant(record['fetched_at']) > instant(record['ingested_at']):
        raise ValueError('Invalid hourly ingestion time')
    if instant(record['ingested_at']).astimezone(BANGKOK).date().isoformat() != record['forecast_date']:
        raise ValueError('Hourly collection crossed a calendar boundary')
    for index, period in enumerate(record['valid_hours']):
        if instant(period['valid_start']) != start + timedelta(hours=index) or instant(period['valid_end']) != start + timedelta(hours=index + 1):
            raise ValueError('Hourly interval does not match the Bangkok day')
        if period['temperature_valid_at'] != period['valid_end']:
            raise ValueError('Temperature is an instant at the interval end')
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in
               (period[k] for k in ('rainfall_mm', 'rain_probability_pct', 'temperature_c') if period[k] is not None)):
            raise ValueError('Non-finite hourly value')
    if all(p['rainfall_mm'] is None and p['rain_probability_pct'] is None for p in record['valid_hours']):
        raise ValueError('Entirely missing hourly forecast')


def normalize(payload, area, day, fetched_at):
    from pipelines.shared.schemas import validate_record
    if payload.get('timezone') != 'Asia/Bangkok' or payload.get('utc_offset_seconds') != 25200:
        raise ValueError('Unexpected hourly timezone')
    values, units = payload['hourly'], payload['hourly_units']
    expected = {'precipitation': 'mm', 'precipitation_probability': '%', 'temperature_2m': '°C'}
    if units.get('time') != 'unixtime' or any(units.get(k) != v for k, v in expected.items()):
        raise ValueError('Unexpected hourly units')
    start, _ = map(instant, daily_period(day))
    expected_times = [int((start + timedelta(hours=i + 1)).timestamp()) for i in range(24)]
    if values.get('time') != expected_times or any(type(t) is not int for t in values['time']) or any(len(values.get(k, [])) != 24 for k in expected):
        raise ValueError('Expected all 24 preceding-hour intervals')
    hours = []
    for i, stamp in enumerate(expected_times):
        end = datetime.fromtimestamp(stamp, timezone.utc)
        hours.append({'valid_start': (end - timedelta(hours=1)).isoformat(), 'valid_end': end.isoformat(),
                      'temperature_valid_at': end.isoformat(), 'rainfall_mm': values['precipitation'][i],
                      'rain_probability_pct': values['precipitation_probability'][i], 'temperature_c': values['temperature_2m'][i]})
    record = {'schema_version': '2.0', 'source_id': 'open_meteo', 'product_id': PRODUCT, 'data_state': 'forecast',
              'location_id': area['id'], 'forecast_date': day, 'forecast_reference_time': None,
              'fetched_at': fetched_at, 'ingested_at': utc_now(), 'point': {'lat': area['lat'], 'lon': area['lon']},
              'model_point': {'lat': payload['latitude'], 'lon': payload['longitude']},
              'spatial_method': 'Representative interior point; model grid forecast, not an area average',
              'source_url': 'https://open-meteo.com/en/docs', 'valid_hours': hours,
              'units': {'rainfall': 'mm/1h', 'probability': '%', 'temperature': '°C'}}
    return validate_record('HourlyForecast', record)


def check_hourly_batch(records, expected_ids):
    from pipelines.shared.schemas import validate_record
    if len({r['forecast_date'] for r in records}) != 1:
        raise ValueError('Mixed hourly forecast days')
    for record in records:
        validate_record('HourlyForecast', record)
    ids = [r['location_id'] for r in records]
    if not expected_ids or len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise ValueError('Incomplete hourly coverage')
    return {'requested_locations': len(expected_ids), 'successful_locations': len(ids), 'completeness': 1.0}


class HourlyPublisher(Publisher):
    collection_name = COLLECTION
    schema_name = 'HourlyForecast'

    def validate(self, records, expected_ids): return check_hourly_batch(records, expected_ids)
    def read(self, source='open_meteo', product=PRODUCT): return super().read(source, product)
    def rollback(self, source='open_meteo', product=PRODUCT): return super().rollback(source, product)


def collect(locations, day, fetcher=fetch_hourly_batch, sleep=__import__('time').sleep):
    records,offset,batch_size = [],0,25
    while offset<len(locations):
        batch = locations[offset:offset + batch_size]
        try:
            payloads, fetched = fetcher(batch, day)
        except ProviderRequestError as exc:
            if batch_size==25 and len(batch)>5 and exc.reason=='transport_error' and exc.transport_type=='ReadTimeout':
                batch_size=5
                print(__import__('json').dumps({'event':'hourly_batch_size_reduced','from':25,'to':5,
                    'reason':'ReadTimeout','completed_locations':len(records)}),flush=True)
                continue
            raise
        if len(payloads) != len(batch):
            raise ValueError('Incomplete hourly provider batch')
        records.extend(normalize(p, area, day, fetched) for p, area in zip(payloads, batch))
        offset+=len(batch)
        sleep(1 if batch_size==5 else 3)
    check_hourly_batch(records, [a['id'] for a in locations])
    return records


def main():
    import argparse
    import os
    import json
    from pymongo import MongoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--export')
    args = parser.parse_args()
    if not args.publish and not args.export: parser.error('Select --publish or --export')
    if args.publish and not os.getenv('MONGODB_URI'): parser.error('MONGODB_URI is required')
    client = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=10000) if args.publish else None
    db = client[os.getenv('MONGODB_DB_NAME', 'weather_db')] if client is not None else None
    day = instant(utc_now()).astimezone(BANGKOK).date().isoformat()
    status = {'source_id': 'open_meteo', 'product_id': PRODUCT, 'last_attempt': utc_now()}
    stage = 'collect'
    try:
        start_run(db, 'open_meteo:' + PRODUCT, status)
        locations = weather_locations('all')
        with request_budget(db):
            records = collect(locations, day)
        stage = 'publish'
        if db is not None:
            pointer = HourlyPublisher(db).publish(records, [a['id'] for a in locations])
            status['active_generation'] = pointer['active_run_id']
        status.update(status='SUCCESS', last_success=utc_now(), completed_at=utc_now(), record_count=len(records), forecast_date=day)
        stage = 'save_status'
        if db is not None:
            db.source_status.update_one({'_id': 'open_meteo:' + PRODUCT}, {'$set': status,
                '$unset': {'error_summary': '', 'error_stage': '', 'http_status': ''}}, upsert=True)
        if args.export: export_local(args.export, records, [a['id'] for a in locations], status, kind='HourlyForecast', check=check_hourly_batch)
        print(json.dumps({'status': 'SUCCESS', 'product_id': PRODUCT, 'record_count': len(records), 'forecast_date': day}))
    except Exception as exc:
        reason = exc.reason if isinstance(exc, ProviderRequestError) else type(exc).__name__
        status.update(status='FAILED', completed_at=utc_now(), error_summary=reason, error_stage=stage)
        if isinstance(exc, ProviderRequestError):status['http_status'] = exc.status_code
        if db is not None:
            try:db.source_status.update_one({'_id': 'open_meteo:' + PRODUCT}, {'$set': status}, upsert=True)
            except Exception:pass
        print(json.dumps({'status': 'FAILED', 'product_id': PRODUCT, 'stage': stage, 'reason': reason,
            'http_status': status.get('http_status'), 'transport_type': getattr(exc,'transport_type',None)}), flush=True)
        raise RuntimeError('Hourly refresh failed; last complete hourly product retained') from None
    finally:
        if client is not None: client.close()


if __name__ == '__main__': main()
