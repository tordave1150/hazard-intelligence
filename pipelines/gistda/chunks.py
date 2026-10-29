"""Complete three-day generations in <=1 MiB documents, with atomic A/B promotion."""
from copy import deepcopy
import json
from bson import BSON

from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from pipelines.shared.time_units import utc_now
from . import limits


def size(value):
    return max(len(BSON.encode(value)), len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()))


def split_feed(feed):
    validate_record('GistdaThreeDayFeed', feed)
    if size(feed) > limits.MAX_FEED_BYTES:
        raise ValueError('GISTDA complete feed size budget exceeded')
    metadata = {key: deepcopy(value) for key, value in feed.items() if key != 'records'}
    batches, batch = [], []
    # Include all wrapper/metadata bytes in the document bound, not just geometry.
    def document(rows):
        return {'source_id':'gistda','product_id':limits.PRODUCT,'chunk_id':'0000',
                'chunk_count':limits.MAX_CHUNKS,'feed':metadata,'records':rows}
    for row in feed['records']:
        if batch and (len(batch) >= limits.CHUNK_FEATURES or size(document(batch + [row])) > limits.CHUNK_BYTES - 256):
            batches.append(batch)
            batch = []
        if size(document([row])) > limits.CHUNK_BYTES - 256:
            raise ValueError('GISTDA individual feature exceeds document budget')
        batch.append(row)
    if batch or not batches:
        batches.append(batch)
    if len(batches) > limits.MAX_CHUNKS:
        raise ValueError('GISTDA chunk budget exceeded')
    return [{**document(rows), 'feed':deepcopy(metadata), 'chunk_id':f'{index:04d}', 'chunk_count':len(batches)}
            for index, rows in enumerate(batches)]


def check_chunks(chunks, expected_ids=None):
    if not 1 <= len(chunks) <= limits.MAX_CHUNKS:
        raise ValueError('GISTDA requires one complete bounded generation')
    ordered = sorted(chunks, key=lambda row: row.get('chunk_id', ''))
    expected = [f'{index:04d}' for index in range(len(ordered))]
    if [row.get('chunk_id') for row in ordered] != expected or (expected_ids is not None and expected_ids != expected):
        raise ValueError('GISTDA chunk set is incomplete or duplicated')
    metadata = ordered[0]['feed']
    records = []
    for chunk in ordered:
        validate_record('GistdaThreeDayChunk', chunk)
        if chunk['chunk_count'] != len(ordered) or chunk['feed'] != metadata or size(chunk) > limits.CHUNK_BYTES:
            raise ValueError('GISTDA chunk metadata/size mismatch')
        if not chunk['records'] and metadata['record_count']:
            raise ValueError('Unexpected empty GISTDA chunk')
        records.extend(chunk['records'])
    feed = {**metadata, 'records':records}
    validate_record('GistdaThreeDayFeed', feed)
    if size(feed) > limits.MAX_FEED_BYTES:
        raise ValueError('GISTDA complete feed size budget exceeded')
    return {'completeness':1.0, 'feature_count':len(records), 'scope_area_id':'TH', 'chunk_count':len(ordered)}


class ThreeDayPublisher(Publisher):
    collection_name = limits.COLLECTION
    identity_field = 'chunk_id'
    schema_name = 'GistdaThreeDayChunk'

    def validate(self, records, expected_ids):
        return check_chunks(records, expected_ids)

    def read(self, source='gistda', product=limits.PRODUCT):
        return super().read(source, product)

    def rollback(self, source='gistda', product=limits.PRODUCT):
        key=f'{source}:{product}'
        with self.lock(key):
            control=self.control.find_one({'_id':key})
            previous=control.get('previous') if control else None
            if not previous or not previous.get('active_run_id'):
                raise ValueError('No previous generation available')
            rows=list(self.records.find({'source_id':source,'product_id':product,'slot':previous['active_slot'],
                'etl_run_id':previous['active_run_id']},{'_id':0,'slot':0,'etl_run_id':0}))
            if len(rows)!=previous['record_count']:
                raise ValueError('Previous generation was already reused')
            quality=check_chunks(rows)
            old={name:control[name] for name in ('active_slot','active_run_id','record_count')}
            self.control.update_one({'_id':key},{'$set':{**previous,**quality,'previous':old,'published_at':utc_now()},'$inc':{'revision':1}})
