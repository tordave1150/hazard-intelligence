from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from .data import PRODUCT, check_batch


class DamPublisher(Publisher):
    collection_name='dam_latest'
    identity_field='dam_id'
    schema_name='DamObservation'

    def validate(self,records,expected_ids):
        quality=check_batch(records,expected_ids)
        for record in records:
            validate_record(self.schema_name,record)
        return quality

    def read(self,source='rid',product=PRODUCT):
        return super().read(source,product)

    def rollback(self,source='rid',product=PRODUCT):
        return super().rollback(source,product)
