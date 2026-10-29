"""Three-day retrieval, bounded chunks and complete-generation retention."""
from copy import deepcopy
import json
import sys

import mongomock
import pytest

from scripts.gistda_national import collect_national_candidate
from scripts.gistda_common import CandidateError
from pipelines.gistda import limits
from pipelines.gistda.data import normalize
from pipelines.gistda.chunks import ThreeDayPublisher, split_feed, check_chunks, size
from pipelines.shared.schemas import validate_record
from scripts.mongo_admin import verify_database

NOW = '2026-10-29T14:00:00Z'
KEY = 'synthetic-only-three-day-secret'


def feature(index):
    x = 100 + index / 100000
    return {'type':'Feature', 'properties':{'pv_idn':10, 'ap_idn':1001, 'private':KEY},
            'geometry':{'type':'Polygon', 'coordinates':[[[x,13],[x+.000001,13],[x+.000001,13.000001],[x,13]]]}}


class Response:
    status_code = 200
    def __init__(self, payload): self.raw=json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, chunk_size): yield self.raw


def candidate(count=210, *, change_count=False):
    calls=[]
    def get(url, **kwargs):
        calls.append((url,kwargs))
        offset=kwargs['params']['offset']
        rows=[feature(i) for i in range(offset,min(offset+100,count))]
        return Response({'type':'FeatureCollection','features':rows,'numberMatched':count+int(change_count and offset>0),
                         'numberReturned':len(rows),'timeStamp':NOW,'links':[{'href':'https://invalid/?key='+KEY}]})
    return collect_national_candidate(KEY, get=get, now=lambda:NOW, three_day=True), calls


def feed(count=210):
    value,_=candidate(count)
    return normalize(value,NOW)


def test_observed_national_capacity_7846_is_fully_collected_and_chunked_without_provider_values():
    value,calls=candidate(7846)
    assert len(calls)==79 and value['record_count']==7846 and value['page_count']==79
    assert all(url==limits.ENDPOINT and kwargs['params']=={'limit':100,'offset':i*100}
               and not kwargs['allow_redirects'] for i,(url,kwargs) in enumerate(calls))
    value=normalize(value,NOW)
    chunks=split_feed(value)
    assert len(chunks)==79 and all(len(row['records'])<=100 and size(row)<limits.CHUNK_BYTES for row in chunks)
    assert check_chunks(chunks,[row['chunk_id'] for row in chunks])['feature_count']==7846
    text=json.dumps(chunks)
    assert KEY not in text and 'href' not in text and 'private' not in text
    assert value['observed_at'] is None and value['product_window']=='3days'


def test_empty_three_day_query_is_one_complete_empty_chunk():
    chunks=split_feed(feed(0))
    assert len(chunks)==1 and chunks[0]['records']==[]
    assert check_chunks(chunks)['feature_count']==0


def test_byte_bound_can_split_before_feature_bound_and_reject_oversized_single_feature(monkeypatch):
    value=feed(25)
    monkeypatch.setattr(limits,'CHUNK_BYTES',size({**split_feed(value)[0],'records':value['records'][:4]})+256)
    chunks=split_feed(value)
    assert len(chunks)>1 and all(size(row)<=limits.CHUNK_BYTES for row in chunks)
    check_chunks(chunks)
    monkeypatch.setattr(limits,'CHUNK_BYTES',100)
    with pytest.raises(ValueError,match='individual feature'):split_feed(value)


@pytest.mark.parametrize('corruption',['missing','duplicate','metadata','count','geometry','identity','window'])
def test_incomplete_or_mixed_chunks_never_promote(corruption):
    db=mongomock.MongoClient().test
    publisher=ThreeDayPublisher(db)
    chunks=split_feed(feed())
    publisher.publish(chunks,[row['chunk_id'] for row in chunks])
    before=db.snapshot_control.find_one({'_id':'gistda:'+limits.PRODUCT})
    bad=deepcopy(chunks)
    if corruption=='missing':bad.pop()
    if corruption=='duplicate':bad[1]=deepcopy(bad[0])
    if corruption=='metadata':bad[1]['feed']['response_at']='2026-10-29T13:00:00Z'
    if corruption=='count':bad[1]['chunk_count']=1
    if corruption=='geometry':bad[0]['records'][0]['geometry']['coordinates'][0][0]=[0,0]
    if corruption=='identity':bad[1]['records'][0]['id']=bad[0]['records'][0]['id']
    if corruption=='window':bad[0]['feed']['product_window']='1day'
    with pytest.raises(Exception):publisher.publish(bad,[row['chunk_id'] for row in bad])
    assert db.snapshot_control.find_one({'_id':'gistda:'+limits.PRODUCT})==before
    assert publisher.read()==chunks


def test_two_slot_chunk_retention_and_rollback_are_verified():
    db=mongomock.MongoClient().test
    publisher=ThreeDayPublisher(db)
    full=split_feed(feed())
    empty=split_feed(feed(0))
    for _ in range(3):
        publisher.publish(full,[r['chunk_id'] for r in full])
        publisher.publish(empty,['0000'])
    publisher.rollback()
    pointer=db.snapshot_control.find_one({'_id':'gistda:'+limits.PRODUCT})
    assert pointer['feature_count']==210 and pointer['chunk_count']==3
    assert sorted(publisher.read(),key=lambda r:r['chunk_id'])==full
    report=next(r for r in verify_database(db) if r['product_id']==limits.PRODUCT)
    assert report['status']=='VERIFIED' and report['total_documents']==4
    assert report['document_limit']==2*limits.MAX_CHUNKS


def test_provider_count_changes_or_feature_budget_excess_are_not_publishable(monkeypatch):
    with pytest.raises(CandidateError,match='COUNT_CHANGED'):candidate(change_count=True)
    monkeypatch.setattr(limits,'MAX_FEATURES',100)
    with pytest.raises(CandidateError,match='FEATURE_BUDGET'):candidate()


def test_three_day_request_and_schema_cannot_be_relabelled_as_one_day(tmp_path):
    from pipelines.gistda.run import check_request
    path=tmp_path/'request.json'
    path.write_text(json.dumps({'request_id':'2026-10-29-01','source_id':'gistda','operation':'publish_thailand_3days'}))
    check_request(path,three_day=True)
    with pytest.raises(ValueError):check_request(path,three_day=False)
    value=feed(1)
    validate_record('GistdaThreeDayFeed',value)
    value['source_url']=value['source_url'].replace('3days','1day')
    with pytest.raises(Exception):validate_record('GistdaThreeDayFeed',value)


def test_failed_refresh_retains_previous_complete_three_day_generation(monkeypatch,capsys):
    from pipelines.gistda import run
    from scripts import gistda_national
    client=mongomock.MongoClient()
    db=client.weather_db
    publisher=ThreeDayPublisher(db)
    chunks=split_feed(feed(1));publisher.publish(chunks,['0000'])
    before=db.snapshot_control.find_one({'_id':'gistda:'+limits.PRODUCT})
    def failure(*args,**kwargs):raise CandidateError('PROVIDER_COUNT_CHANGED_DURING_PAGINATION')
    monkeypatch.setattr(run,'collect_national_candidate',failure)
    monkeypatch.setattr(run,'MongoClient',lambda *args,**kwargs:client)
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test')
    monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(sys,'argv',['gistda','--publish','--three-day'])
    with pytest.raises(RuntimeError):run.main()
    assert db.snapshot_control.find_one({'_id':'gistda:'+limits.PRODUCT})==before
    assert db.source_status.find_one({'_id':'gistda:'+limits.PRODUCT})['status']=='FAILED'
    assert KEY not in capsys.readouterr().out


def test_default_publication_succeeds_for_thailand_and_clears_previous_failure(monkeypatch,capsys):
    from pipelines.gistda import run
    client=mongomock.MongoClient();db=client.weather_db
    candidate=feed(1)
    candidate['schema_version']='gistda-candidate/1'
    for key in ('snapshot_id','data_state','ingested_at'):candidate.pop(key)
    monkeypatch.setattr(run,'collect_national_candidate',lambda key,**options:candidate)
    monkeypatch.setattr(run,'MongoClient',lambda *args,**kwargs:client)
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test')
    monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(sys,'argv',['gistda','--publish'])
    db.source_status.insert_one({'_id':'gistda:'+limits.PRODUCT,'status':'FAILED','error_summary':'old'})
    run.main()
    status=db.source_status.find_one({'_id':'gistda:'+limits.PRODUCT})
    assert status['status']=='SUCCESS' and status['scope_area_id']=='TH' and status['record_count']==1
    assert 'error_summary' not in status
    assert json.loads(capsys.readouterr().out)['product_window']=='3days'
