from copy import deepcopy
from pathlib import Path
import json
import mongomock
import pytest
import requests
from jsonschema import ValidationError
from pipelines.tmd.transform import feed_index,normalize,make_feed,xml
from pipelines.tmd.client import collect,request,ProviderRequestError
from pipelines.tmd.publication import WarningPublisher
from pipelines.tmd.data import SOURCE
from pipelines.shared.schemas import validate_record
from scripts.mongo_admin import verify_database

FIXTURES=Path(__file__).parent/'fixtures/tmd'
FETCHED='2026-10-26T08:10:00Z'


@pytest.fixture
def cap_feed():
    items,generated=feed_index((FIXTURES/'feed-2026-10-26.xml').read_bytes())
    records=[normalize((FIXTURES/f'alert-{i}.xml').read_bytes(),item['url'],FETCHED) for i,item in enumerate(items)]
    return make_feed(items,generated,records,FETCHED)


def test_real_cap_feed_preserves_times_geometry_and_agency_labels(cap_feed):
    assert len(cap_feed['records'])==6 and cap_feed['ignored_item_count']==0
    row=cap_feed['records'][0]
    assert row['warning_id']=='TMD20261025055042_2' and row['issued_at']=='2026-10-24T22:45:00Z'
    assert row['expires_at']=='2026-10-25T11:00:00Z' and row['agency_severity']=='Severe'
    assert len(row['geometry']['coordinates'])==81 and len(row['area_ids'])==12
    assert 'TH-P-38' in row['area_ids'] # Keep source geocode even when source prose omits it.
    assert all(r['expires_at']<FETCHED for r in cap_feed['records'])
    assert row['geometry']['coordinates'][0][0][0][0]>96 # GeoJSON longitude first.


def test_real_provider_unmapped_code_keeps_complete_warning_without_inventing_a_province():
    raw=(FIXTURES/'alert-2026-10-27-unmapped-code.xml').read_bytes()
    row=normalize(raw,'https://www.tmd.go.th/uploads/CAP/CAPTMD20261027054131_2.xml','2026-10-27T11:50:00Z')
    assert row['warning_id']=='TMD20261027054131_2' and len(row['area_ids'])==30
    assert len(row['geometry']['coordinates'])==123
    assert sum(len(a['geocodes']) for a in row['source_areas'])==31
    assert any(c=={'value_name':'ISO3166-2','value':'R-07'} for a in row['source_areas'] for c in a['geocodes'])
    assert 'TH-P-07' not in row['area_ids'] and 'TH-P-7' not in row['area_ids']
    forged=deepcopy(row);forged['area_ids'].append('TH-P-07')
    with pytest.raises((ValueError,ValidationError)):validate_record('AgencyWarning',forged)
    feed=make_feed([{'id':row['warning_id'],'url':row['content_ref']}],'2026-10-27T11:50:00Z',[row],'2026-10-27T11:50:00Z')
    publisher=WarningPublisher(mongomock.MongoClient().test);publisher.publish([feed],['latest'])
    assert publisher.read()[0]['records'][0]==row


@pytest.mark.parametrize('code',['R-07','TH-99','TH-1'])
def test_unmapped_agency_geocodes_stay_verbatim_outside_canonical_scope(code):
    raw=(FIXTURES/'alert-0.xml').read_bytes().replace(b'<value>TH-80</value>',f'<value>{code}</value>'.encode())
    row=normalize(raw,'https://www.tmd.go.th/uploads/CAP/CAPTMD20261025055042_2.xml',FETCHED)
    assert 'TH-P-80' not in row['area_ids']
    assert any(c['value']==code for a in row['source_areas'] for c in a['geocodes'])


@pytest.mark.parametrize('raw',[b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>',b'<!ENTITY x SYSTEM "file:///private">',b'a'*(2*1024*1024+1),'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>'.encode('utf-16')],ids=['doctype','entity','oversized','alternate-encoding'])
def test_xml_entities_and_size_fail_closed(raw):
    with pytest.raises(ValueError):xml(raw)


def test_feed_rejects_external_links_duplicate_ids_and_changed_terms():
    raw=(FIXTURES/'feed-2026-10-26.xml').read_bytes()
    for changed in [raw.replace(b'https://www.tmd.go.th/uploads/',b'https://other.invalid/uploads/'),raw.replace(b'public domain',b'unknown terms')]:
        with pytest.raises(ValueError):feed_index(changed)
    first=b'TMD20261025055042_2';second=b'TMD20261025054755_2'
    with pytest.raises(ValueError):feed_index(raw.replace(second,first))


def test_test_and_private_messages_are_not_public_alerts():
    raw=(FIXTURES/'alert-0.xml').read_bytes()
    for old,new in [(b'<status>Actual</status>',b'<status>Test</status>'),(b'<scope>Public</scope>',b'<scope>Private</scope>')]:
        assert normalize(raw.replace(old,new),'https://www.tmd.go.th/uploads/CAP/CAPTMD20261025055042_2.xml',FETCHED) is None


def test_missing_expiry_stays_unknown_and_effective_uses_cap_default():
    import re
    raw=(FIXTURES/'alert-0.xml').read_bytes()
    raw=re.sub(b'<expires>.*?</expires>',b'',raw)
    raw=re.sub(b'<effective>.*?</effective>',b'',raw)
    row=normalize(raw,'https://www.tmd.go.th/uploads/CAP/CAPTMD20261025055042_2.xml',FETCHED)
    assert row['expires_at'] is None and row['effective_start']==row['issued_at'] and row['effective_time_source']=='CAP sent'


@pytest.mark.parametrize('field,value',[
    ('issued_at','2026-10-27T00:00:00Z'),('expires_at','2026-10-20T00:00:00Z'),
    ('sender','Other'),('area_ids',['TH-P-99']),('content_ref','https://other.invalid/alert.xml')])
def test_unverified_identity_area_and_time_fail(cap_feed,field,value):
    row=deepcopy(cap_feed['records'][0]);row[field]=value
    with pytest.raises((ValueError,ValidationError)):validate_record('AgencyWarning',row)


def test_incomplete_candidate_never_replaces_published_feed(cap_feed):
    db=mongomock.MongoClient().test;p=WarningPublisher(db)
    for _ in range(5):p.publish([cap_feed],['latest'])
    assert db.agency_warning_latest.count_documents({})==2
    old=db.snapshot_control.find_one({'_id':'tmd:cap_warnings'})
    bad=deepcopy(cap_feed);bad['records'].pop()
    with pytest.raises(ValueError):p.publish([bad],['latest'])
    assert db.snapshot_control.find_one({'_id':old['_id']})==old and p.read()==[cap_feed]


def test_empty_feed_is_a_published_snapshot_and_can_rollback(cap_feed):
    db=mongomock.MongoClient().test;p=WarningPublisher(db);p.publish([cap_feed],['latest'])
    empty=deepcopy(cap_feed);empty.update(records=[],feed_item_count=0,ignored_item_count=0)
    p.publish([empty],['latest']);assert p.read()[0]['records']==[]
    report=next(r for r in verify_database(db) if r['source_id']=='tmd')
    assert report['status']=='VERIFIED' and report['document_limit']==2
    p.rollback();assert p.read()==[cap_feed]


class Response:
    def __init__(self,status,body=b''):self.status_code=status;self.body=body;self.headers={'Retry-After':'3'}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,size):yield self.body


class Session:
    def __init__(self,values):self.values=iter(values);self.calls=0
    def get(self,*args,**kwargs):
        assert kwargs['allow_redirects'] is False
        self.calls+=1;result=next(self.values)
        if isinstance(result,Exception):raise result
        return result


def test_complete_collection_is_required_after_a_failed_document():
    raw=(FIXTURES/'feed-2026-10-26.xml').read_bytes()
    session=Session([Response(200,raw),Response(200,(FIXTURES/'alert-0.xml').read_bytes()),Response(403)])
    with pytest.raises(ProviderRequestError) as error:collect(session,lambda _:None)
    assert error.value.reason=='http_permanent' and session.calls==3


def test_bounded_transport_recovery_and_safe_diagnostics():
    session=Session([requests.Timeout('private secret')]*4)
    with pytest.raises(ProviderRequestError) as error:request(SOURCE,session,lambda _:None)
    assert session.calls==4 and 'private' not in str(error.value) and 'secret' not in str(error.value)
    assert error.value.document_id=='rss_index'
    session=Session([Response(429),Response(200,b'<rss/>')]);wait=[]
    assert request(SOURCE,session,wait.append)[0]==b'<rss/>' and wait==[3]


def test_redirect_and_oversized_document_rejected():
    for response in [Response(302),Response(200,b'x'*(2*1024*1024+1))]:
        with pytest.raises(ProviderRequestError):request(SOURCE,Session([response]),lambda _:None)


def test_expired_collection_deadline_starts_no_request():
    session=Session([])
    with pytest.raises(ProviderRequestError) as error:request(SOURCE,session,lambda _:None,deadline=0)
    assert error.value.reason=='collection_deadline' and session.calls==0


def test_cli_schema_failure_logs_contract_path_without_source_values(tmp_path,monkeypatch,capsys):
    from pipelines.tmd import run
    monkeypatch.setattr('sys.argv',['tmd','--export',str(tmp_path/'unused.json')])
    def fail():
        raise ValidationError('private source value',validator='pattern',instance='private source value',
                              schema_path=['properties','area_ids','items','pattern'])
    monkeypatch.setattr(run,'collect',fail)
    with pytest.raises(RuntimeError):run.main()
    output=capsys.readouterr().out
    diagnostic=json.loads(output)
    assert diagnostic['stage']=='collect' and diagnostic['validator']=='pattern'
    assert diagnostic['schema_path']==['properties','area_ids','items','pattern']
    assert 'private source value' not in output and not (tmp_path/'unused.json').exists()
