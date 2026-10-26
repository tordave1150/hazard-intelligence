"""Two bounded slots, serialized writers, atomic control-pointer promotion.

    A lock has no automatic expiry: a crashed worker needs explicit recovery
    after confirming it stopped. This prevents an expired writer corrupting a
    reused slot. Readers also select run_id and verify counts on pointer races.
"""
import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from .quality import check_batch
from .schemas import validate_record
from .time_units import utc_now


class Publisher:
    def __init__(self, db):
        self.db = db
        self.records = db.weather_latest
        self.control = db.snapshot_control
        self.records.create_index([('source_id', 1), ('product_id', 1), ('slot', 1), ('location_id', 1)], unique=True)
        self.records.create_index([('source_id', 1), ('product_id', 1), ('slot', 1), ('etl_run_id', 1)])

    @contextmanager
    def lock(self, key):
        token = str(uuid4())
        try:
            self.db.etl_locks.insert_one({'_id': key, 'token': token, 'started_at': utc_now()})
        except DuplicateKeyError as exc:
            raise RuntimeError('Another writer or unrecovered run holds the publication lock') from exc
        try:
            yield token
        finally:
            self.db.etl_locks.delete_one({'_id': key, 'token': token})

    def publish(self, records, expected_ids):
        quality = check_batch(records, expected_ids)
        for record in records:
            validate_record('Forecast', record)
        source, product = records[0]['source_id'], records[0]['product_id']
        if any((r['source_id'], r['product_id']) != (source, product) for r in records):
            raise ValueError('A snapshot must contain one source/product')
        key = f'{source}:{product}'
        with self.lock(key):
            active = self.control.find_one({'_id': key}) or {}
            slot = 'B' if active.get('active_slot') == 'A' else 'A'
            run = str(uuid4())
            query = {'source_id': source, 'product_id': product, 'slot': slot}
            # Only the inactive slot of the new collection is replaced.
            self.records.delete_many(query)
            self.records.insert_many([{**r, 'slot': slot, 'etl_run_id': run} for r in records], ordered=True)
            if self.records.count_documents({**query, 'etl_run_id': run}) != len(records):
                raise RuntimeError('Candidate write incomplete')
            previous = {k: active.get(k) for k in ('active_slot', 'active_run_id', 'record_count')} if active else None
            control = {'source_id': source, 'product_id': product, 'active_slot': slot, 'active_run_id': run,
                       'record_count': len(records), 'published_at': utc_now(), 'previous': previous,
                       'revision': active.get('revision', 0) + 1, **quality}
            self.control.replace_one({'_id': key}, {'_id': key, **control}, upsert=True)
            return control

    def read(self, source='open_meteo', product='daily_forecast'):
        for _ in range(3):
            control = self.control.find_one({'_id': f'{source}:{product}'})
            if not control:
                return []
            records = list(self.records.find({'source_id': source, 'product_id': product, 'slot': control['active_slot'],
                                             'etl_run_id': control['active_run_id']}, {'_id': 0, 'slot': 0, 'etl_run_id': 0}))
            if len(records) == control['record_count']:
                return records
        raise RuntimeError('Snapshot changed while reading; retry later')

    def rollback(self, source='open_meteo', product='daily_forecast'):
        key = f'{source}:{product}'
        with self.lock(key):
            control = self.control.find_one({'_id': key})
            previous = control.get('previous') if control else None
            if not previous or not previous['active_run_id']:
                raise ValueError('No previous generation available')
            count = self.records.count_documents({'source_id': source, 'product_id': product,
                'slot': previous['active_slot'], 'etl_run_id': previous['active_run_id']})
            if count != previous['record_count']:
                raise ValueError('Previous generation was already reused; rollback unavailable')
            old = {k: control[k] for k in ('active_slot', 'active_run_id', 'record_count')}
            self.control.update_one({'_id': key}, {'$set': {**previous, 'previous': old, 'published_at': utc_now()}, '$inc': {'revision': 1}})


def export_local(path, records, expected_ids, status):
    check_batch(records, expected_ids)
    for record in records:
        validate_record('Forecast', record)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix('.tmp')
    temp.write_text(json.dumps({'schema_version': '2.0', 'records': records, 'status': status}, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    os.replace(temp, destination)
