from copy import deepcopy
import json
from pathlib import Path

import mongomock
import pytest
from jsonschema import ValidationError

from scripts import gistda_national as national
from scripts.gistda_candidate import CandidateError
from pipelines.gistda.data import normalize
from pipelines.gistda.publication import NationalFloodPublisher
from pipelines.shared.schemas import validate_record
from scripts.mongo_admin import verify_database

NOW = '2026-10-28T00:00:00Z'
KEY = 'test-only-national-key'


def feature(index=0, district='2604', province='26'):
    lon = 101 + index / 10000
    return {'type':'Feature','properties':{'pv_idn':province,'ap_idn':district,'private':KEY,'f_area':999},
            'geometry':{'type':'Polygon','coordinates':[[[lon,14],[lon+.00001,14],[lon+.00001,14.00001],[lon,14]]]}}


def page(rows=(), matched=None):
    return {'type':'FeatureCollection','features':list(rows),'numberMatched':len(rows) if matched is None else matched,
            'numberReturned':len(rows),'timeStamp':'2026-10-27T23:59:00Z',
            'links':[{'href':'https://example.invalid/?api_key='+KEY}]}


class Response:
    def __init__(self, payload, status=200): self.raw=json.dumps(payload).encode();self.status_code=status
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def iter_content(self,chunk_size): yield self.raw


def collect(pages):
    iterator=iter(pages);calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(next(iterator))
    return national.collect_national_candidate(KEY,get=get,now=lambda:NOW),calls


def test_national_empty_query_does_not_apply_the_ongkharak_or_bangkok_example_filter():
    result,calls=collect([page()])
    assert result['area_id']=='TH' and result['record_count']==0 and result['page_count']==1
    assert calls[0][0]==national.ENDPOINT and calls[0][1]['params']=={'limit':100,'offset':0}
    assert calls[0][1]['headers']['API-Key']==KEY and calls[0][1]['allow_redirects'] is False
    assert result['observed_at'] is None and result['complete_provider_query']
    assert KEY not in json.dumps(result) and 'href' not in json.dumps(result)
    validate_record('GistdaNationalFloodFeed',normalize(result,NOW))


def test_multiple_pages_include_other_districts_and_advance_by_actual_returned_count():
    result,calls=collect([page([feature()],2),page([feature(1,'1001','10')],2)])
    assert [c[1]['params']['offset'] for c in calls]==[0,1]
    assert result['page_count']==2 and result['record_count']==2
    assert result['records'][1]['area_ids']==['TH-P-10','TH-D-1001']
    assert all(row['properties'] is None for row in result['records'])
    assert result['pagination_consistency']=='COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN'
    validate_record('GistdaNationalFloodFeed',normalize(result,NOW))


@pytest.mark.parametrize('pages,reason',[
    ([page([],1001)],'NATIONAL_FEATURE_BUDGET_EXCEEDED'),
    ([page([feature()],2),page([feature(1)],3)],'PROVIDER_COUNT_CHANGED_DURING_PAGINATION'),
    ([page([feature()],2),page([feature()],2)],'DUPLICATE_OR_REPEATED_PROVIDER_FEATURE'),
    ([page([feature()],2),page([],2)],'INCOMPLETE_QUERY_NOT_PUBLISHABLE'),
    ([page([feature(district='2604',province='10')])],'ADMINISTRATIVE_IDENTITY_MISMATCH'),
])
def test_incomplete_changed_repeated_or_mismatched_queries_are_not_published(pages,reason):
    with pytest.raises(CandidateError,match=reason):collect(pages)


@pytest.mark.parametrize('status,reason',[(302,'REDIRECT_REJECTED'),(401,'AUTHENTICATION_OR_ENTITLEMENT_ERROR'),
    (404,'NOT_FOUND_NOT_A_VERIFIED_EMPTY_COLLECTION'),(503,'HTTP_ERROR')])
def test_http_errors_are_never_empty_products(status,reason):
    with pytest.raises(CandidateError,match=reason):
        national.collect_national_candidate(KEY,get=lambda *a,**k:Response(page(),status))


def test_page_time_byte_position_and_page_count_budgets_fail_closed(monkeypatch):
    monkeypatch.setattr(national,'MAX_PAGES',1)
    with pytest.raises(CandidateError,match='INCOMPLETE_QUERY_NOT_PUBLISHABLE'):collect([page([feature()],2)])
    monkeypatch.setattr(national,'MAX_BYTES',5)
    with pytest.raises(CandidateError,match='RESPONSE_TOO_LARGE'):collect([page()])
    monkeypatch.setattr(national,'MAX_BYTES',4*1024*1024)
    monkeypatch.setattr(national,'MAX_POSITIONS',3)
    with pytest.raises(CandidateError,match='CANDIDATE_GEOMETRY_LIMIT'):collect([page([feature()])])
    ticks=iter([0,121])
    with pytest.raises(CandidateError,match='DEADLINE_EXCEEDED'):
        national.collect_national_candidate(KEY,clock=lambda:next(ticks))


def test_new_product_preserves_pilot_and_retains_rollback_with_two_documents():
    db=mongomock.MongoClient().test
    from pipelines.gistda.publication import FloodPublisher
    pilot=json.loads((Path(__file__).parent/'fixtures/gistda/synthetic-feed.json').read_text(encoding='utf-8'))
    FloodPublisher(db).publish([pilot],['latest'])
    candidate,_=collect([page([feature()])]);feed=normalize(candidate,NOW);publisher=NationalFloodPublisher(db)
    publisher.publish([feed],['latest'])
    empty=deepcopy(feed);empty.update(records=[],record_count=0)
    publisher.publish([empty],['latest']);publisher.rollback()
    assert publisher.read()==[feed] and FloodPublisher(db).read()==[pilot]
    report=next(r for r in verify_database(db) if r['product_id']==national.PRODUCT)
    assert report['active_records']==1 and report['document_limit']==report['total_documents']==2
    before=db.snapshot_control.find_one({'_id':'gistda:'+national.PRODUCT})
    invalid=deepcopy(feed);invalid['record_count']=0
    with pytest.raises(ValueError):publisher.publish([invalid],['latest'])
    assert db.snapshot_control.find_one({'_id':'gistda:'+national.PRODUCT})==before


@pytest.mark.parametrize('change',[{'area_id':'TH-D-2604'},{'observed_at':NOW},{'page_count':2},
    {'query':{'ap_idn':'2604','limit':100,'offset':0}},{'complete_provider_query':False}])
def test_national_contract_cannot_be_relabelled_or_invent_observation_time(change):
    result,_=collect([page()]);feed=normalize(result,NOW);feed.update(change)
    with pytest.raises((ValueError,ValidationError)):validate_record('GistdaNationalFloodFeed',feed)


def test_reviewed_national_request_is_explicit_and_rejects_other_operations(tmp_path):
    from pipelines.gistda.run import check_request
    path=tmp_path/'request.json'
    path.write_text(json.dumps({'request_id':'2026-10-28-01','source_id':'gistda','operation':'publish_thailand_1day'}),encoding='utf-8')
    check_request(path,national=True)
    with pytest.raises(ValueError):check_request(path)
