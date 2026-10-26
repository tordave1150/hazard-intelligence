from bson import BSON
import json
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from .data import PRODUCT,MAX_DOCUMENT_BYTES


def check_envelope(records,expected_ids):
    if len(records)!=1 or expected_ids!=['latest']:raise ValueError('Warning publication requires one complete feed envelope')
    validate_record('WarningFeed',records[0])
    if max(len(BSON.encode(records[0])),len(json.dumps(records[0],ensure_ascii=False,separators=(',',':')).encode('utf-8')))>MAX_DOCUMENT_BYTES:
        raise ValueError('Warning snapshot exceeds bounded response/BSON size')
    return {'requested_messages':records[0]['feed_item_count'],'successful_messages':len(records[0]['records']),
            'ignored_messages':records[0]['ignored_item_count'],'completeness':1.0}


class WarningPublisher(Publisher):
    collection_name='agency_warning_latest'
    identity_field='snapshot_id'
    schema_name='WarningFeed'

    def validate(self,records,expected_ids):return check_envelope(records,expected_ids)

    def read(self,source='tmd',product=PRODUCT):return super().read(source,product)
    def rollback(self,source='tmd',product=PRODUCT):return super().rollback(source,product)
