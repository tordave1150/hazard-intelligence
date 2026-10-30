import json
from bson import BSON
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from .data import PRODUCT,COLLECTION,MAX_DOCUMENT_BYTES


def check_envelope(records,expected_ids):
    if len(records)!=1 or expected_ids!=['latest']:raise ValueError('One complete national station response is required')
    feed=validate_record('ThaiWaterFeed',records[0])
    if len(BSON.encode(feed))>MAX_DOCUMENT_BYTES:raise ValueError('Station envelope exceeds storage limit')
    return {'completeness':1.0,'feature_count':feed['record_count'],'scope_area_id':'TH'}


class GaugePublisher(Publisher):
    collection_name=COLLECTION
    identity_field='snapshot_id'
    schema_name='ThaiWaterFeed'
    def validate(self,records,expected_ids):return check_envelope(records,expected_ids)
    def read(self,source='thaiwater',product=PRODUCT):return super().read(source,product)
    def rollback(self,source='thaiwater',product=PRODUCT):return super().rollback(source,product)
