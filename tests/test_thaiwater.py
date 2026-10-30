import json
from copy import deepcopy
from pathlib import Path
import mongomock
import pytest
import requests
from jsonschema import ValidationError
from pipelines.thaiwater.data import normalize,KEY
from pipelines.thaiwater.client import fetch,ProviderRequestError
from pipelines.thaiwater.publication import GaugePublisher
from pipelines.shared.schemas import validate_record
from scripts.mongo_admin import verify_database

STAMP='2026-10-29T16:38:43Z'
@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent/'fixtures/thaiwater/public-station-subset.json').read_text(encoding='utf-8'))

def test_public_rows_keep_units_wall_time_and_all_provinces(payload):
    feed=normalize(payload,STAMP)
    assert feed['record_count']==2 and feed['provider_automatic_count']==3
    assert len(feed['coverage_by_province'])==2 and feed['provider_manual_count']==1
    assert feed['excluded_stations'][0]['provider_province_code']=='10499'
    assert feed['time_unknown_count']==2 and all(r['observed_at'] is None for r in feed['records'])
    assert feed['records'][0]['source_observed_at']==payload['waterlevel_data']['data'][0]['waterlevel_datetime']
    assert feed['records'][0]['source_station_id']==str(payload['waterlevel_data']['data'][0]['station']['id'])
    assert 'discharge' not in feed['records'][0] and 'situation_level' not in feed['records'][0]

def test_missing_zero_negative_levels_are_distinct_and_bad_fields_are_flagged(payload):
    rows=payload['waterlevel_data']['data'];rows[0].update(waterlevel_msl=0,waterlevel_m=-1.25)
    rows[1].update(waterlevel_msl='NaN',waterlevel_m=None,waterlevel_datetime='2026-02-30 12:00')
    rows[1]['station']['tele_station_lat']='invalid'
    feed=normalize(payload,STAMP);first,bad=feed['records']
    assert first['water_level_msl']==0 and first['water_level_m']==-1.25
    assert bad['water_level_msl'] is None and bad['point'] is None
    assert {'INVALID_LEVEL','NO_LEVEL','INVALID_POINT','INVALID_PROVIDER_TIME'}<=set(bad['quality_flags'])
    assert feed['quality_issue_count']==1

@pytest.mark.parametrize('mode',['duplicate','unsupported','provider_failure'])
def test_untrustworthy_response_does_not_publish(payload,mode):
    if mode=='duplicate':payload['waterlevel_data']['data'].append(deepcopy(payload['waterlevel_data']['data'][0]))
    if mode=='unsupported':payload['waterlevel_data']['data'][0]['station_type']='manual'
    if mode=='provider_failure':payload['waterlevel_data']['result']='ERROR'
    with pytest.raises(ValueError):normalize(payload,STAMP)

@pytest.mark.parametrize('field,value',[('record_count',20),('quality_issue_count',1),('time_unknown_count',0),('coverage_by_province',[])])
def test_cross_field_accounting_fails_closed(payload,field,value):
    feed=normalize(payload,STAMP);feed[field]=value
    with pytest.raises((ValueError,ValidationError)):validate_record('ThaiWaterFeed',feed)

def test_atomic_bounded_publication_rollback_and_bad_candidate_retention(payload):
    db=mongomock.MongoClient().test;publisher=GaugePublisher(db);feed=normalize(payload,STAMP)
    for _ in range(4):publisher.publish([feed],['latest'])
    assert db.gauge_latest.count_documents({})==2 and publisher.read()==[feed]
    before=db.snapshot_control.find_one({'_id':KEY});bad=deepcopy(feed);bad['records'].pop()
    with pytest.raises((ValueError,ValidationError)):publisher.publish([bad],['latest'])
    assert db.snapshot_control.find_one({'_id':KEY})==before
    publisher.rollback();assert publisher.read()==[feed]
    report=verify_database(db)
    assert next(r for r in report if r['source_id']=='thaiwater')['status']=='VERIFIED'

class Response:
    def __init__(self,status,body=b'{}'):self.status_code=status;self.body=body;self.headers={'Retry-After':'1000'}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,size):yield self.body
class Session:
    def __init__(self,replies):self.replies=iter(replies);self.options=[]
    def get(self,url,**options):
        self.options.append((url,options));value=next(self.replies)
        if isinstance(value,Exception):raise value
        return value

def test_bounded_retries_fixed_public_endpoint_and_no_redirects():
    session=Session([requests.ConnectionError('private diagnostics'),Response(429),Response(200,b'{"ok":true}')]);waits=[]
    result,_=fetch(session,waits.append)
    assert result=={'ok':True} and waits==[2,30]
    assert all(url.endswith('/public/waterlevel_load') and not options['allow_redirects'] for url,options in session.options)

@pytest.mark.parametrize('response,reason',[(Response(302),'http_error'),(Response(200,b'{"v":NaN}'),'invalid_json'),(Response(200,b'x'*(8*1024*1024+1)),'response_budget_exceeded')])
def test_unsafe_responses_are_rejected_without_details(response,reason):
    with pytest.raises(ProviderRequestError) as error:fetch(Session([response]),lambda _:None)
    assert str(error.value)==reason
