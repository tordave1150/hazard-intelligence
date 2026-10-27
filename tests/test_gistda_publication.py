from copy import deepcopy
import json
from pathlib import Path
import sys

import mongomock
import pytest
from jsonschema import ValidationError

from pipelines.gistda.data import KEY, normalize
from pipelines.gistda.publication import FloodPublisher
from pipelines.shared.schemas import validate_record
from scripts.mongo_admin import verify_database


@pytest.fixture
def feed():
    return json.loads((Path(__file__).parent/'fixtures/gistda/synthetic-feed.json').read_text(encoding='utf-8'))


def test_published_geometry_keeps_unknown_acquisition_without_area_or_private_properties(feed):
    assert validate_record('GistdaFloodFeed',feed) == feed
    assert feed['observed_at'] is None and feed['area_metrics']=='NOT_USED_UNITS_UNVERIFIED'
    assert all(row['properties'] is None for row in feed['records'])
    assert feed['query']=={'ap_idn':'2604','limit':100,'offset':0}


def test_empty_query_is_a_published_envelope_and_rollback_restores_nonempty_feed(feed):
    db=mongomock.MongoClient().test;p=FloodPublisher(db)
    p.publish([feed],['latest'])
    empty=deepcopy(feed);empty.update(records=[],record_count=0)
    p.publish([empty],['latest'])
    assert p.read()==[empty]
    report=next(r for r in verify_database(db) if r['source_id']=='gistda')
    assert report['active_records']==1 and report['document_limit']==report['total_documents']==2
    p.rollback();assert p.read()==[feed]


def test_incomplete_candidate_does_not_replace_last_good_and_repeated_runs_stay_bounded(feed):
    db=mongomock.MongoClient().test;p=FloodPublisher(db)
    for _ in range(6):p.publish([feed],['latest'])
    before=db.snapshot_control.find_one({'_id':KEY})
    bad=deepcopy(feed);bad['records']=[]
    with pytest.raises(ValueError):p.publish([bad],['latest'])
    assert db.snapshot_control.find_one({'_id':KEY})==before and p.read()==[feed]
    assert db.satellite_flood_latest.count_documents({})==2 and db.etl_locks.count_documents({})==0


@pytest.mark.parametrize('field,value',[
    ('observed_at','2026-10-27T12:00:00Z'),('product_window','30days'),('area_id','TH-D-5709'),
    ('record_count',True),('response_at','2026-10-27T15:00:00Z'),('ingested_at','2026-10-26T00:00:00Z'),
    ('complete_provider_query',False),('source_url','https://example.invalid/')])
def test_invented_time_scope_incomplete_and_unverified_provenance_fail(feed,field,value):
    feed[field]=value
    with pytest.raises((ValueError,ValidationError)):validate_record('GistdaFloodFeed',feed)


def test_geometry_or_identity_corruption_and_raw_properties_are_rejected(feed):
    for change in ('identity','coordinate','raw'):
        bad=deepcopy(feed)
        if change=='identity':bad['records'][0]['id']='a'*24+'-0'
        if change=='coordinate':bad['records'][0]['geometry']['coordinates'][0][0]=[0,0]
        if change=='raw':bad['records'][0]['properties']={'api_key':'never-persist-this'}
        with pytest.raises((ValueError,ValidationError)):validate_record('GistdaFloodFeed',bad)


def test_missing_unique_index_and_unbounded_documents_fail_verification(feed):
    db=mongomock.MongoClient().test;p=FloodPublisher(db);p.publish([feed],['latest'])
    index=next(name for name,definition in db.satellite_flood_latest.index_information().items() if definition.get('unique'))
    db.satellite_flood_latest.drop_index(index)
    with pytest.raises(ValueError,match='unique'):verify_database(db)
    p=FloodPublisher(db);p.publish([feed],['latest'])
    db.satellite_flood_latest.insert_one({'unrelated':'not permitted in bounded latest collection'})
    with pytest.raises(ValueError,match='bounded'):verify_database(db)


def test_success_clears_failure_and_failed_collection_retains_active_snapshot(feed,monkeypatch,capsys):
    from pipelines.gistda import run
    client=mongomock.MongoClient();db=client.weather_db
    candidate={k:v for k,v in feed.items() if k not in ('snapshot_id','data_state','ingested_at')}
    candidate['schema_version']='gistda-candidate/1'
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test-host')
    monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(run,'MongoClient',lambda *a,**k:client)
    monkeypatch.setattr(run,'collect_candidate',lambda key:candidate)
    monkeypatch.setattr(sys,'argv',['gistda','--publish'])
    db.source_status.insert_one({'_id':KEY,'status':'FAILED','error_summary':'old-failure'})
    run.main()
    status=db.source_status.find_one({'_id':KEY})
    assert status['status']=='SUCCESS' and 'error_summary' not in status
    before=db.snapshot_control.find_one({'_id':KEY})
    def fail(key):raise ValueError('private URI or upstream credential')
    monkeypatch.setattr(run,'collect_candidate',fail)
    with pytest.raises(RuntimeError):run.main()
    assert db.snapshot_control.find_one({'_id':KEY})==before
    assert db.source_status.find_one({'_id':KEY})['status']=='FAILED'
    assert 'private URI' not in capsys.readouterr().out


def test_reviewed_publication_request_cannot_change_source_product_or_credentials(tmp_path):
    from pipelines.gistda.run import check_request
    request={'request_id':'2026-10-27-01','source_id':'gistda','operation':'publish_ongkharak_1day'}
    path=tmp_path/'request.json';path.write_text(json.dumps(request),encoding='utf-8');check_request(path)
    for change in ({'source_id':'tmd'},{'operation':'publish_national'},{'api_key':'private'},{'request_id':False}):
        path.write_text(json.dumps({**request,**change}),encoding='utf-8')
        with pytest.raises(ValueError):check_request(path)
