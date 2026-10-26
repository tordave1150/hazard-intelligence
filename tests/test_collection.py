"""Recovery must fill only transient gaps and still meet the publication gate."""
from copy import deepcopy
import pytest
from pipelines.open_meteo.client import ProviderRequestError
from pipelines.open_meteo.run import collect_forecasts
from pipelines.shared.quality import check_batch


def locations(count):
    return [{'id':f'TH-D-{1000+i}', 'lat':13.75, 'lon':100.5} for i in range(count)]


def test_recovers_only_failed_batch_without_losing_good_records(payload):
    areas=locations(30)
    calls=[]
    sleeps=[]
    def fetch(batch):
        ids=[a['id'] for a in batch]
        calls.append(ids)
        if len(calls)==1:
            raise ProviderRequestError('upstream_unavailable',503)
        return [deepcopy(payload) for _ in batch], '2026-10-25T01:00:00Z'
    records,missing=collect_forecasts(areas,fetcher=fetch,sleep=sleeps.append)
    assert missing==[] and len(records)==30
    assert calls==[[a['id'] for a in areas[:25]],[a['id'] for a in areas[25:]],[a['id'] for a in areas[:25]]]
    assert sleeps==[3,3,60,3]
    assert check_batch(records,[a['id'] for a in areas])['completeness']==1


def test_exhausted_recovery_cannot_pass_publication_gate(payload):
    areas=locations(30)
    calls=[]
    def fetch(batch):
        calls.append(batch[0]['id'])
        if len(batch)==25:
            raise ProviderRequestError('transport_error')
        return [deepcopy(payload) for _ in batch], '2026-10-25T01:00:00Z'
    records,missing=collect_forecasts(areas,fetcher=fetch,sleep=lambda _:None)
    assert len(records)==5 and missing==[a['id'] for a in areas[:25]]
    assert calls.count(areas[0]['id'])==3 and calls.count(areas[25]['id'])==1
    with pytest.raises(ValueError,match='Incomplete'):
        check_batch(records,[a['id'] for a in areas])


@pytest.mark.parametrize('failure',['invalid_units','permanent_http'])
def test_does_not_retry_or_publish_invalid_data(payload,failure):
    areas=locations(1)
    calls=[]
    def fetch(batch):
        calls.append(1)
        if failure=='permanent_http':
            raise ProviderRequestError('http_error',401,retryable=False)
        bad=deepcopy(payload)
        bad['daily_units']['precipitation_sum']='inch'
        return [bad], '2026-10-25T01:00:00Z'
    records,missing=collect_forecasts(areas,fetcher=fetch,sleep=lambda _:None)
    assert calls==[1] and records==[] and missing==[areas[0]['id']]
    with pytest.raises(ValueError):
        check_batch(records,[areas[0]['id']])
