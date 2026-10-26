from pipelines.open_meteo.client import fetch_batch
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
