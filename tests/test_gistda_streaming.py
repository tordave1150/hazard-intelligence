from copy import deepcopy
from datetime import datetime,timezone
import gzip,json
import mongomock
import pytest
from pipelines.gistda import streaming as stream
from scripts.gistda_common import CandidateError

KEY='fixture-only-not-a-real-provider-key'
NOW=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def feature(i=0,district='1001'):
    return {'type':'Feature','id':'source-'+str(i),'properties':{'pv_idn':district[:2],'ap_idn':district,'private_field':KEY},
            'geometry':{'type':'Polygon','coordinates':[[[100.50,13.70],[100.51,13.70],[100.51,13.71],[100.50,13.70]]]}}


class Response:
    status_code=200
    def __init__(self,payload):self.payload=json.dumps(payload).encode()
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def iter_content(self,_):yield self.payload


def getter(total=1,mutate=None):
    calls=[]
    def get(url,**kwargs):
        calls.append((url,kwargs));offset=kwargs['params']['offset'];limit=kwargs['params']['limit']
        rows=[feature(i) for i in range(offset,min(offset+limit,total))]
        payload={'type':'FeatureCollection','numberMatched':total,'numberReturned':len(rows),'features':rows,'timeStamp':NOW,'links':[{'href':'https://invalid/?key='+KEY}]}
        if mutate:mutate(payload,offset)
        return Response(payload)
    return get,calls


def collect(path,total=1,window='3days',mutate=None,storage_version='gzip-v1'):
    get,calls=getter(total,mutate)
    result=stream.collect_window(KEY,window,path,get=get,now=lambda:NOW,storage_version=storage_version)
    return result,calls


@pytest.mark.parametrize('storage_version',stream.VERSIONS)
def test_streams_more_than_old_twenty_thousand_limit_into_bounded_chunks(tmp_path,storage_version):
    manifest,calls=collect(tmp_path,20001,storage_version=storage_version)
    assert manifest['feed']['record_count']==20001 and len(calls)==21
    assert manifest['areas']['TH']['count']==20001
    assert len(manifest['chunks'])==201
    assert all(c['raw_bytes']<=1048576 and c['count']<=100 for c in manifest['chunks'])
    assert all(c[1]['params']['limit']==1000 and c[1]['allow_redirects'] is False for c in calls)
    row=stream.checked_payload(manifest['chunks'][0],(tmp_path/(manifest['chunks'][0]['hash']+'.gz')).read_bytes(),storage_version)[0]
    assert row['properties'] is None and KEY not in json.dumps(manifest) and KEY not in json.dumps(row)
    assert len(row['id'])==64 and manifest['feed']['observed_at'] is None


@pytest.mark.parametrize('fault',['duplicate','changed_count','admin','empty_page','oversize_count'])
def test_untrusted_or_incomplete_country_results_never_produce_a_manifest(tmp_path,fault):
    def mutate(payload,offset):
        if fault=='duplicate' and len(payload['features'])>1:payload['features'][1]['id']=payload['features'][0]['id']
        if fault=='changed_count' and offset:payload['numberMatched']+=1
        if fault=='admin':payload['features'][0]['properties']['ap_idn']='9999'
        if fault=='empty_page':payload['features']=[];payload['numberReturned']=0
        if fault=='oversize_count':payload['numberMatched']=stream.MAX_FEATURES+1
    with pytest.raises(CandidateError):collect(tmp_path,1001,mutate=mutate)


def test_duplicate_geometry_with_distinct_provider_identities_remains_distinct_evidence(tmp_path):
    manifest,_=collect(tmp_path,2,window='30days')
    rows=stream.checked_payload(manifest['chunks'][0],(tmp_path/(manifest['chunks'][0]['hash']+'.gz')).read_bytes())
    assert rows[0]['geometry']==rows[1]['geometry'] and rows[0]['id']!=rows[1]['id']


def test_single_chunk_corruption_and_decompression_bombs_fail_before_publication(tmp_path):
    manifest,_=collect(tmp_path);c=manifest['chunks'][0];data=(tmp_path/(c['hash']+'.gz')).read_bytes()
    with pytest.raises((ValueError,Exception)):stream.checked_payload(c,data[:-5])
    bomb=gzip.compress(b'x'*(stream.CHUNK_RAW_BYTES+1))
    with pytest.raises(ValueError):stream.checked_payload({**c,'compressed_bytes':len(bomb)},bomb)


def test_atomic_publish_reuses_objects_retains_previous_and_supports_rollback(tmp_path):
    manifest,_=collect(tmp_path,250)
    db=mongomock.MongoClient().db;publisher=stream.WindowPublisher(db)
    first=publisher.publish(manifest,tmp_path,check_database=False)
    count=db.gistda_flood_objects.count_documents({})
    second=deepcopy(manifest);second['_id']='another-generation'
    publisher.publish(second,tmp_path,check_database=False)
    assert db.gistda_flood_objects.count_documents({})==count
    assert publisher.verify('3days')['active_records']==250
    publisher.rollback()
    assert db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})['active_generation']==first['active_generation']
    assert db.etl_locks.count_documents({})==0


def test_storage_guard_blocks_before_pointer_promotion_and_preserves_last_complete(tmp_path,monkeypatch):
    manifest,_=collect(tmp_path);db=mongomock.MongoClient().db;publisher=stream.WindowPublisher(db)
    publisher.publish(manifest,tmp_path,check_database=False)
    before=db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})
    monkeypatch.setattr(stream,'OBJECT_BUDGET_BYTES',0)
    next_manifest=deepcopy(manifest);next_manifest['_id']='blocked'
    with pytest.raises(CandidateError):publisher.publish(next_manifest,tmp_path,check_database=False)
    assert db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})==before
    assert publisher.verify('3days')['active_records']==1


def test_failed_object_write_never_changes_active_pointer(tmp_path,monkeypatch):
    manifest,_=collect(tmp_path);db=mongomock.MongoClient().db;publisher=stream.WindowPublisher(db)
    publisher.publish(manifest,tmp_path,check_database=False);before=db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})
    other,_=collect(tmp_path/'other',200,window='7days')
    def fail(*args,**kwargs):raise RuntimeError('simulated database write failure')
    monkeypatch.setattr(publisher.objects,'update_one',fail)
    with pytest.raises(RuntimeError):publisher.publish(other,tmp_path/'other',check_database=False)
    assert db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})==before
    assert db.snapshot_control.find_one({'_id':'gistda:flood_7days_thailand'}) is None
    assert db.etl_locks.count_documents({})==0


def test_empty_success_is_a_query_history_entry_not_evidence_of_dry_land(tmp_path):
    manifest,_=collect(tmp_path,0,window='30days')
    assert manifest['chunks']==[] and manifest['feed']['observed_at'] is None
    db=mongomock.MongoClient().db;publisher=stream.WindowPublisher(db)
    publisher.publish(manifest,tmp_path,check_database=False)
    assert publisher.verify('30days')['active_records']==0
    stored=db.gistda_flood_manifests.find_one({'_id':manifest['_id']})
    assert 'current flood state unknown' in stored['feed']['interpretation']


def test_metadata_or_area_accounting_corruption_is_rejected(tmp_path):
    manifest,_=collect(tmp_path)
    bad=deepcopy(manifest);bad['areas']['TH']['count']+=1
    with pytest.raises(ValueError):stream.validate_manifest(bad)
    bad=deepcopy(manifest);bad['feed']['product_window']='30days'
    with pytest.raises(ValueError):stream.validate_manifest(bad)


def test_provider_error_inside_collection_is_not_a_valid_zero(tmp_path):
    def mutate(payload,_):payload['error']='upstream failure'
    with pytest.raises(CandidateError,match='PROVIDER_ERROR'):collect(tmp_path,0,mutate=mutate)


def test_old_query_metadata_survives_geometry_eviction_without_touching_current_or_previous(tmp_path,monkeypatch):
    db=mongomock.MongoClient().db;publisher=stream.WindowPublisher(db);manifests=[]
    from datetime import timedelta
    for i in range(1,5):
        m,_=collect(tmp_path/str(i),i)
        stamp=(datetime.now(timezone.utc)-timedelta(days=4-i)).isoformat().replace('+00:00','Z')
        for k in ['response_at','fetched_at','ingested_at']:m['feed'][k]=stamp
        manifests.append(m)
        if i<4:publisher.publish(m,tmp_path/str(i),check_database=False)
    budget=sum(m['compressed_bytes'] for m in manifests[1:])
    monkeypatch.setattr(stream,'OBJECT_BUDGET_BYTES',budget)
    publisher.publish(manifests[3],tmp_path/'4',check_database=False)
    oldest=db.gistda_flood_manifests.find_one({'_id':manifests[0]['_id']})
    assert oldest['feed']['record_count']==1 and not oldest['geometry_available']
    assert oldest['geometry_retention_reason']=='STORAGE_BUDGET'
    assert publisher.verify('3days')['active_records']==4
    publisher.rollback();assert publisher.verify('3days')['active_records']==3


def test_later_empty_success_does_not_erase_failure_history(monkeypatch,capsys):
    from pipelines.gistda import run
    client=mongomock.MongoClient();db=client.weather_db;calls=[]
    db.source_status.insert_one({'_id':'gistda:flood_3days_thailand','consecutive_empty_queries':2})
    monkeypatch.setenv('MONGODB_URI','mongodb://fixture-only');monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(run,'MongoClient',lambda *a,**k:client)
    monkeypatch.setattr('sys.argv',['gistda','--publish'])
    def failed(*a,**k):raise CandidateError('PROVIDER_COUNT_CHANGED_DURING_PAGINATION')
    monkeypatch.setattr(run,'collect_window',failed)
    with pytest.raises(RuntimeError):run.main()
    assert db.source_status.find_one({'_id':'gistda:flood_3days_thailand'})['consecutive_empty_queries']==0
    reason=db.source_status.find_one({'_id':'gistda:flood_3days_thailand'})['last_failure_reason']
    class Publisher:
        def __init__(self,db):pass
        def publish(self,*a):return {'active_generation':'fixture','record_count':0,'compressed_bytes':0,'archive_evicted_count':0}
    monkeypatch.setattr(run,'WindowPublisher',Publisher)
    monkeypatch.setattr(run,'collect_window',lambda key,window,directory,**k:calls.append(window) or {'feed':{'record_count':0,'page_count':1,'fetched_at':NOW}})
    run.main()
    status=db.source_status.find_one({'_id':'gistda:flood_3days_thailand'})
    assert status['status']=='SUCCESS' and status['last_failure_reason']==reason and status['consecutive_empty_queries']==1
    assert db.gistda_flood_runs.count_documents({})==2 and calls==['3days']
    assert KEY not in capsys.readouterr().out


def test_window_failures_are_independent_and_never_substitute_another_product(monkeypatch):
    from pipelines.gistda import run
    client=mongomock.MongoClient();db=client.weather_db;calls=[]
    monkeypatch.setenv('MONGODB_URI','mongodb://fixture-only');monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(run,'MongoClient',lambda *a,**k:client);monkeypatch.setattr('sys.argv',['gistda','--publish','--all-windows'])
    def collect(key,window,directory,**options):
        calls.append(window)
        if window=='7days':raise CandidateError('TRANSPORT_FAILURE')
        return {'feed':{'record_count':1 if window=='3days' else 0,'page_count':1,'fetched_at':NOW}}
    class Publisher:
        def __init__(self,db):pass
        def publish(self,*a):return {'active_generation':'fixture','record_count':1,'compressed_bytes':0,'archive_evicted_count':0}
    monkeypatch.setattr(run,'collect_window',collect);monkeypatch.setattr(run,'WindowPublisher',Publisher)
    with pytest.raises(RuntimeError):run.main()
    assert calls==['3days','7days','30days']
    assert [db.source_status.find_one({'_id':'gistda:'+stream.product(w)})['status'] for w in calls]==['SUCCESS','FAILED','SUCCESS']
    assert db.source_status.find_one({'_id':'gistda:flood_3days_thailand'})['record_count']==1


def test_compatible_reader_wait_requires_storage_protocol_and_is_bounded():
    from pipelines.gistda.run import wait_for_receiver
    class Response:
        status_code=200
        def __init__(self,protocol):self.protocol=protocol
        def json(self):return {'storage_protocol':self.protocol,'storage_versions':['gzip-v1','msgpack-gzip-v1'] if self.protocol=='gistda-gzip-v1' else []}
    sleeps=[]
    wait_for_receiver(lambda *a,**k:Response('gistda-gzip-v1'),lambda _:pytest.fail('Ready reader must not wait'))
    with pytest.raises(RuntimeError):wait_for_receiver(lambda *a,**k:Response('old-reader'),sleeps.append)
    assert sleeps==[5]*71


def test_migration_rollback_can_restore_legacy_and_return_to_compressed_generation(tmp_path):
    import hashlib
    from pipelines.gistda.chunks import ThreeDayPublisher,split_feed
    manifest,_=collect(tmp_path,2);db=mongomock.MongoClient().db
    original=deepcopy(manifest['feed']);original.update(schema_version='2.0',query={'limit':100,'offset':0},record_count=1)
    geometry=feature()['geometry'];digest=hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    original['records']=[{'type':'Feature','id':digest[:24]+'-0','geometry':geometry,'properties':None,'area_ids':['TH-P-10','TH-D-1001']}]
    chunks=split_feed(original);ThreeDayPublisher(db).publish(chunks,['0000'])
    publisher=stream.WindowPublisher(db);publisher.publish(manifest,tmp_path,check_database=False)
    publisher.rollback()
    assert db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})['active_slot']=='A'
    assert ThreeDayPublisher(db).read()[0]['feed']['record_count']==1
    publisher.rollback();assert publisher.verify('3days')['active_records']==2
    assert db.satellite_flood_3days_latest.count_documents({})==1


def test_capacity_measurement_is_read_only_and_preserves_double_precision(tmp_path,monkeypatch):
    from pipelines.gistda.capacity import capacity_report
    from pipelines.gistda.encoding import binary_rows,unpacked,CURRENT_VERSION
    import struct
    values=[100.12345678912345,13.98765432198765,-0.0,100,13.0]
    restored=unpacked(binary_rows(values),CURRENT_VERSION)
    assert [struct.pack('>d',v) for v in values]==[struct.pack('>d',v) for v in restored]
    db=mongomock.MongoClient().db;m,_=collect(tmp_path,201,window='30days');p=stream.WindowPublisher(db)
    p.publish(m,tmp_path,check_database=False)
    before={name:list(db[name].find({})) for name in db.list_collection_names()}
    monkeypatch.setattr(db,'command',lambda *a,**k:{'dataSize':12345,'indexSize':1000,'storageSize':20000})
    report=capacity_report(db,measure=True)
    assert report['database_headroom_bytes']==stream.DATABASE_CEILING_BYTES-13345
    assert report['windows'][0]['record_count']==201
    assert report['windows'][0]['measured_compressed_bytes']>0
    assert {name:list(db[name].find({})) for name in db.list_collection_names()}==before


def test_binary_collector_retains_every_coordinate_and_checks_corrupt_payloads(tmp_path):
    import struct
    legacy,_=collect(tmp_path/'json',101)
    binary,_=collect(tmp_path/'binary',101,storage_version='msgpack-gzip-v1')
    for left,right in zip(legacy['chunks'],binary['chunks']):
        old=stream.checked_payload(left,(tmp_path/'json'/(left['hash']+'.gz')).read_bytes())
        packed=(tmp_path/'binary'/(right['hash']+'.gz')).read_bytes()
        rows=stream.checked_payload(right,packed,binary['storage_version'])
        assert stream.encoded(rows)==stream.encoded(old)
        assert struct.pack('>d',rows[0]['geometry']['coordinates'][0][0][0])==struct.pack('>d',old[0]['geometry']['coordinates'][0][0][0])
        with pytest.raises(ValueError):stream.checked_payload(right,packed[:-5],binary['storage_version'])
    db=mongomock.MongoClient().db;p=stream.WindowPublisher(db)
    p.publish(binary,tmp_path/'binary',check_database=False)
    assert p.verify('3days')['active_records']==101


def test_repack_preserves_query_time_previous_query_and_cached_old_objects(tmp_path):
    from datetime import timedelta
    db=mongomock.MongoClient().db;p=stream.WindowPublisher(db)
    older,_=collect(tmp_path/'older',1);p.publish(older,tmp_path/'older',check_database=False)
    latest,_=collect(tmp_path/'latest',201);p.publish(latest,tmp_path/'latest',check_database=False)
    db.source_status.insert_one({'_id':'gistda:flood_3days_thailand','last_success':NOW,'last_attempt':NOW,'status':'SUCCESS'})
    result=p.repack('3days',tmp_path/'repack',check_database=False)
    pointer=db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})
    candidate=db.gistda_flood_manifests.find_one({'_id':pointer['active_generation']})
    assert candidate['feed']==latest['feed'] and candidate['areas']==latest['areas']
    assert result['record_count']==201 and candidate['query_identity']==latest['_id']
    assert pointer['previous']['active_generation']==older['_id']
    assert db.source_status.find_one({'_id':pointer['_id']})['last_attempt']==NOW
    old=db.gistda_flood_manifests.find_one({'_id':latest['_id']})
    p._verify_objects(old,True)  # Old cached generation remains readable during grace.
    assert old['replaced_by']==candidate['_id']
    p.rollback();assert p.verify('3days')['active_records']==1
    p.rollback();assert p.verify('3days')['active_records']==201
    db.gistda_flood_manifests.update_one({'_id':latest['_id']},{'$set':{'retire_after':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat().replace('+00:00','Z')}})
    p._gc();assert db.gistda_flood_manifests.find_one({'_id':latest['_id']}) is None
    assert p.verify('3days')['active_records']==201


def test_three_binary_generations_for_all_windows_reuse_unchanged_data_and_rollback(tmp_path):
    db=mongomock.MongoClient().db;p=stream.WindowPublisher(db)
    for window in stream.WINDOWS:
        for i in range(3):
            m,_=collect(tmp_path/window/str(i),301,window,storage_version='msgpack-gzip-v1')
            p.publish(m,tmp_path/window/str(i),check_database=False)
        assert p.verify(window)['active_records']==301
        p.rollback(window);assert p.verify(window)['active_records']==301
    # All windows can reuse identical normalized records, without conflating their clocks/products.
    assert db.gistda_flood_objects.count_documents({})==4


def test_repack_budget_failure_leaves_original_active_and_previous_untouched(tmp_path,monkeypatch):
    db=mongomock.MongoClient().db;p=stream.WindowPublisher(db)
    m,_=collect(tmp_path/'old',201);p.publish(m,tmp_path/'old',check_database=False)
    before=db.snapshot_control.find_one({'_id':'gistda:flood_3days_thailand'})
    monkeypatch.setattr(stream,'OBJECT_BUDGET_BYTES',m['compressed_bytes'])
    with pytest.raises(CandidateError):p.repack('3days',tmp_path/'new',check_database=False)
    assert db.snapshot_control.find_one({'_id':before['_id']})==before
    assert p.verify('3days')['active_records']==201
