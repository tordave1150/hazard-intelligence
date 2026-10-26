from pipelines.open_meteo.client import ProviderRequestError, fetch_batch
import requests
import pytest


class Response:
    def __init__(self,status,payload,headers=None):self.status_code=status;self.payload=payload;self.headers=headers or {}
    def raise_for_status(self):pass
    def json(self):return self.payload


class Session:
    def __init__(self,responses):self.responses=iter(responses)
    def get(self,*args,**kwargs):return next(self.responses)


def test_rate_limit_backoff_and_success(area,payload):
    sleeps=[]
    result,fetched=fetch_batch([area],session=Session([Response(429,{}, {'Retry-After':'12'}),Response(200,payload)]),sleep=sleeps.append)
    assert result==[payload] and sleeps==[12]


def test_incomplete_multi_location_rejected(area,payload):
    with pytest.raises(ValueError):fetch_batch([area,area],session=Session([Response(200,payload)]))


def test_exhausted_retry_fails_closed(area):
    sleeps=[]
    with pytest.raises(RuntimeError):fetch_batch([area],session=Session([Response(503,{})]*4),sleep=sleeps.append)
    assert sleeps==[2,4,8]


def test_failure_diagnostics_do_not_expose_request_credentials(area):
    class BrokenSession:
        def get(self,*args,**kwargs):
            raise requests.Timeout('https://provider.invalid/?apikey=private-test-value')
    with pytest.raises(ProviderRequestError) as error:
        fetch_batch([area],session=BrokenSession(),sleep=lambda _:None)
    assert error.value.reason=='transport_error' and error.value.retryable
    assert 'private-test-value' not in str(error.value) and 'https://' not in str(error.value)


def test_permanent_http_failure_does_not_retry(area):
    sleeps=[]
    with pytest.raises(ProviderRequestError) as error:
        fetch_batch([area],session=Session([Response(401,{})]),sleep=sleeps.append)
    assert not error.value.retryable and error.value.status_code==401 and sleeps==[]


def test_rate_limit_is_identifiable_after_exhaustion(area):
    with pytest.raises(ProviderRequestError) as error:
        fetch_batch([area],session=Session([Response(429,{})]*4),sleep=lambda _:None)
    assert error.value.reason=='rate_limited' and error.value.status_code==429
