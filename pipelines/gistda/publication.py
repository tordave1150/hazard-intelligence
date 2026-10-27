import json
from bson import BSON
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from .data import PRODUCT, COLLECTION, MAX_DOCUMENT_BYTES


def check_envelope(records, expected_ids):
    if len(records) != 1 or expected_ids != ['latest']:
        raise ValueError('GISTDA requires one complete district envelope')
    feed = validate_record('GistdaFloodFeed', records[0])
    if max(len(BSON.encode(feed)), len(json.dumps(feed,ensure_ascii=False,separators=(',',':')).encode())) > MAX_DOCUMENT_BYTES:
        raise ValueError('GISTDA envelope size limit exceeded')
    return {'completeness':1.0, 'feature_count':feed['record_count'], 'scope_area_id':feed['area_id']}


class FloodPublisher(Publisher):
    collection_name = COLLECTION
    identity_field = 'snapshot_id'
    schema_name = 'GistdaFloodFeed'

    def validate(self, records, expected_ids): return check_envelope(records, expected_ids)
    def read(self, source='gistda', product=PRODUCT): return super().read(source, product)
    def rollback(self, source='gistda', product=PRODUCT): return super().rollback(source, product)


def check_national_envelope(records, expected_ids):
    from scripts.gistda_national import MAX_BYTES
    if len(records) != 1 or expected_ids != ['latest']:
        raise ValueError('GISTDA requires one complete national envelope')
    feed = validate_record('GistdaNationalFloodFeed', records[0])
    if max(len(BSON.encode(feed)), len(json.dumps(feed,ensure_ascii=False,separators=(',',':')).encode())) > MAX_BYTES:
        raise ValueError('GISTDA envelope size limit exceeded')
    return {'completeness':1.0, 'feature_count':feed['record_count'], 'scope_area_id':'TH'}


class NationalFloodPublisher(Publisher):
    collection_name = 'satellite_flood_national_latest'
    identity_field = 'snapshot_id'
    schema_name = 'GistdaNationalFloodFeed'

    def validate(self, records, expected_ids): return check_national_envelope(records, expected_ids)
    def read(self, source='gistda', product='flood_1day_thailand'): return super().read(source, product)
    def rollback(self, source='gistda', product='flood_1day_thailand'): return super().rollback(source, product)
