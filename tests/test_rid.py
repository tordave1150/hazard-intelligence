from copy import deepcopy
from pathlib import Path
import json
import mongomock
import pytest
import requests
from jsonschema import ValidationError
from pipelines.rid.data import DAMS,check_batch
from pipelines.rid.transform import normalize
from pipelines.rid.publication import DamPublisher
from pipelines.rid.client import fetch,ProviderRequestError
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from scripts import mongo_admin

FETCHED='2026-10-26T07:00:00Z'


@pytest.fixture
def rid_payload():
    return json.loads((Path(__file__).parent/'fixtures/rid-daily-2026-10-26.json').read_text(encoding='utf-8'))


@pytest.fixture
def rid_records(rid_payload):
    return normalize(rid_payload,FETCHED)


def test_real_report_complete_and_date_precision_preserved(rid_records):
    assert len(rid_records)==35
    assert {r['dam_id'] for r in rid_records}=={m['dam_id'] for m in DAMS.values()}
    assert all(r['observed_at'] is None and r['time_precision']=='date' for r in rid_records)
    assert all(r['report_date']=='2026-10-26' for r in rid_records)
    assert all('inflow' not in r and 'outflow' not in r for r in rid_records)


def test_percentage_above_100_is_valid_and_uses_normal_capacity(rid_payload):
    row=rid_payload['data'][0]['dam'][0]
    row.update(storage=10,capacity=20,volume=12,percent_storage=120)
    value=next(r for r in normalize(rid_payload,FETCHED) if r['source_dam_id']==row['id'])
    assert value['storage_pct']==120 and value['normal_capacity_mcm']==10 and value['maximum_capacity_mcm']==20


def test_nulls_and_measured_zero_are_distinct(rid_payload):
    rows=rid_payload['data'][0]['dam']
    rows[0].update(volume=None,percent_storage=None)
    rows[1].update(volume=0,percent_storage=0)
    result={r['source_dam_id']:r for r in normalize(rid_payload,FETCHED)}
    assert result[rows[0]['id']]['storage_volume_mcm'] is None and result[rows[0]['id']]['quality_status']=='partial'
    assert result[rows[1]['id']]['storage_volume_mcm']==0 and result[rows[1]['id']]['quality_status']=='valid'


@pytest.mark.parametrize('change',[{'volume':-1},{'volume':True},{'percent_storage':10},{'capacity':1}])
def test_bad_measurements_fail_closed(rid_payload,change):
    rid_payload['data'][0]['dam'][0].update(change)
    with pytest.raises((ValueError,ValidationError)):
        normalize(rid_payload,FETCHED)


def test_wrong_identity_missing_and_duplicate_reports_rejected(rid_payload):
    for mode in ['unknown','missing','duplicate']:
        bad=deepcopy(rid_payload)
        if mode=='unknown':bad['data'][0]['dam'][0]['id']='999999'
        elif mode=='missing':bad['data'][0]['dam'].pop()
        else:bad['data'][0]['dam'][1]=deepcopy(bad['data'][0]['dam'][0])
        with pytest.raises(ValueError):normalize(bad,FETCHED)


def test_no_invented_time_or_shifted_coordinate(rid_records):
    for key,value in [('observed_at',FETCHED),('point',{'lat':0,'lon':0}),('report_date','2026-10-27')]:
        row=deepcopy(rid_records[0]);row[key]=value
        with pytest.raises((ValueError,ValidationError)):validate_record('DamObservation',row)


def test_bounded_publication_and_failed_report_keep_weather_and_active_slot(rid_records,forecast):
    db=mongomock.MongoClient().weather_db
    weather=Publisher(db);weather.publish([forecast],[forecast['location_id']])
    publisher=DamPublisher(db);expected=[r['dam_id'] for r in rid_records]
    for _ in range(4):publisher.publish(rid_records,expected)
    assert db.dam_latest.count_documents({})==70 and len(publisher.read())==35
    before=db.snapshot_control.find_one({'_id':'rid:daily_dam_storage'})
    with pytest.raises(ValueError):publisher.publish(rid_records[:-1],expected)
    assert db.snapshot_control.find_one({'_id':before['_id']})==before
    assert weather.read()==[forecast]
    publisher.rollback()
    assert len(publisher.read())==35


def test_read_only_live_verifier_enforces_identity_index_and_retention(monkeypatch,rid_records,forecast,area):
    db=mongomock.MongoClient().weather_db
    monkeypatch.setattr(mongo_admin,'weather_locations',lambda level:[area])
    Publisher(db).publish([forecast],[forecast['location_id']])
    expected=[r['dam_id'] for r in rid_records]
    DamPublisher(db).publish(rid_records,expected)
    before={name:list(db[name].find()) for name in db.list_collection_names()}
    report=mongo_admin.verify_database(db)
    assert all(r['status']=='VERIFIED' and r['unique_index_verified'] for r in report)
    assert before=={name:list(db[name].find()) for name in db.list_collection_names()}
    index=next(i for i in db.dam_latest.list_indexes() if i.get('unique'))
    db.dam_latest.drop_index(index['name'])
    with pytest.raises(ValueError,match='unique'):mongo_admin.verify_database(db)


def test_verifier_rejects_unbounded_documents(monkeypatch,rid_records):
    db=mongomock.MongoClient().weather_db
    publisher=DamPublisher(db);expected=[r['dam_id'] for r in rid_records]
    publisher.publish(rid_records,expected);publisher.publish(rid_records,expected)
    db.dam_latest.insert_one({'source_id':'rid','product_id':'daily_dam_storage','slot':'C','dam_id':'unexpected'})
    with pytest.raises(ValueError,match='bounded'):mongo_admin.verify_database(db)


class Response:
    def __init__(self,status,payload=None):
        self.status_code=status
        self.headers={'Retry-After':'3'}
        self.payload=payload

    def json(self):
        if isinstance(self.payload,Exception):raise self.payload
        return self.payload


class Session:
    def __init__(self,replies):self.replies=iter(replies);self.calls=0
    def get(self,*args,**kwargs):
        self.calls+=1
        response=next(self.replies)
        if isinstance(response,Exception):raise response
        return response


def test_rid_request_recovers_transient_errors_without_logging_details():
    session=Session([requests.ConnectionError('private detail'),Response(429),Response(200,{'ok':True})])
    waits=[]
    payload,_=fetch(session,waits.append)
    assert payload=={'ok':True} and session.calls==3 and waits==[2,4]


@pytest.mark.parametrize('response,reason,status',[
    (Response(403),'http_permanent',403),
    (Response(200,ValueError('private body')),'invalid_json',None),
])
def test_rid_permanent_and_invalid_response_fail_without_retry(response,reason,status):
    session=Session([response])
    with pytest.raises(ProviderRequestError) as error:fetch(session,lambda _:None)
    assert session.calls==1 and error.value.reason==reason and error.value.status==status
    assert 'private' not in str(error.value)


def test_rid_request_exhaustion_is_bounded_and_sanitized():
    session=Session([requests.Timeout('mongodb://user:secret@private') for _ in range(4)])
    with pytest.raises(ProviderRequestError) as error:fetch(session,lambda _:None)
    assert session.calls==4 and error.value.reason=='transport'
    assert all(value not in str(error.value) for value in ['secret','private','mongodb://'])
