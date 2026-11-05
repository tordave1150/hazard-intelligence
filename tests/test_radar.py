import base64
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib
import json
import mongomock
import pytest
from pipelines.radar.client import parse_list,sampled_frames,validate_png,capture,BASE
from pipelines.radar.publication import RadarPublisher
from pipelines.radar.run import wait_for_receiver
from scripts.mongo_admin import verify_database

PNG=(Path(__file__).parent/'fixtures/radar/synthetic-transparent.png').read_bytes()
NOW=datetime(2026,11,4,12,45,tzinfo=timezone.utc).timestamp()
LIST='\n'.join(f'background_THA.png "2026-11-04 12:{minute:02}" overlay=zr/{i:02}.png' for i,minute in enumerate([0,15,30,45]))
CONFIG=b"RADAR_COORDS: [[95,22.5],[108,22.5],[108,4],[95,4]], BASEMAP: ''; PCAPPI Z-R; mm/hr; new Date(date + 'T' + time + ':00Z')"


def test_recovery_due_check_preserves_source_clocks_and_retries_only_after_cooldown():
    from pipelines.radar.refresh import due_decision
    now=datetime(2026,11,5,1,52,tzinfo=timezone.utc).timestamp()
    state={'feed':{'frames':[{'observed_at':'2026-11-05T01:30:00Z'}]},'health':{'status':'SUCCESS','last_attempt':'2026-11-05T01:45:00Z'}}
    before=deepcopy(state)
    assert not due_decision(state,now)['due'] and state==before
    state['feed']['frames'][0]['observed_at']='2026-11-05T01:00:00Z'
    assert not due_decision(state,now)['due']
    assert due_decision(state,now+181)['due']
    state['health']['status']='FAILED'
    assert due_decision(state,now+181)['due']
    assert due_decision({'feed':None,'health':None},now)['due']


def test_due_skip_never_calls_capture_or_publication(monkeypatch):
    from pipelines.radar import run
    monkeypatch.setattr('sys.argv',['radar','--publish','--if-due'])
    monkeypatch.setattr(run,'wait_for_receiver',lambda:None)
    monkeypatch.setattr(run,'check_due',lambda:{'due':False,'reason':'LATEST_SAMPLE_ALREADY_PUBLISHED'})
    monkeypatch.setattr(run,'capture',lambda:pytest.fail('Unneeded provider call'))
    monkeypatch.setattr(run,'publish',lambda _:pytest.fail('Freshness must not be rewritten by a due check'))
    run.main()


def test_compatible_receiver_survives_newer_documentation_commit_and_retries():
    class Ready:
        status_code=200
        def json(self):return {'deployment_commit':'a-newer-documentation-commit','ingestion_protocol':'tmd-radar-v1','publication_sampling_minutes':30}
    seen=[]
    wait_for_receiver(lambda *args,**kwargs:seen.append(args) or Ready(),lambda _:pytest.fail('Compatible receiver must not sleep'))
    assert len(seen)==1


def test_incompatible_receiver_wait_is_bounded():
    class NotReady:
        status_code=404
    sleeps=[]
    with pytest.raises(RuntimeError):wait_for_receiver(lambda *args,**kwargs:NotReady(),sleeps.append)
    assert sleeps==[5]*29


class Response:
    status_code=200
    def __init__(self,data):self.data=data
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def iter_content(self,_):yield self.data


def test_capture_hashes_original_times_and_both_passes():
    seen=[]
    def get(url,**kwargs):
        seen.append(url);assert kwargs['allow_redirects'] is False
        return Response(CONFIG if url.endswith('.html') else LIST.encode() if url.endswith('.list') else b'2026-11-04 12:45' if url.endswith('.latest') else PNG)
    feed=capture(get,NOW)
    assert len(feed['frames'])==2 and len(seen)==9
    assert feed['frames'][-1]['observed_at']=='2026-11-04T12:30:00Z'
    assert feed['sampling_minutes']==30
    assert feed['frames'][0]['sha256']==hashlib.sha256(PNG).hexdigest()


@pytest.mark.parametrize('fault',['clock','list_change','image_change','missing','oversize','source_geometry'])
def test_capture_rejects_partial_and_mutable_generations(fault):
    counts={}
    def get(url,**_):
        counts[url]=counts.get(url,0)+1
        if url.endswith('.html'):data=CONFIG.replace(b'22.5',b'23.5') if fault=='source_geometry' else CONFIG
        elif url.endswith('.list'):data=(LIST+'\ninvalid' if fault=='list_change' and counts[url]>1 else LIST).encode()
        elif url.endswith('.latest'):data=b'2026-11-04 12:30' if fault=='clock' else b'2026-11-04 12:45'
        else:
            data=PNG
            if fault=='image_change' and counts[url]>1:data=PNG+b'changed'
            if fault=='missing':
                response=Response(b'');response.status_code=404;return response
            if fault=='oversize':data=b'x'*800001
        return Response(data)
    with pytest.raises(ValueError):capture(get,NOW)


@pytest.mark.parametrize('listing',[LIST+'\n'+LIST.splitlines()[0],LIST.replace('12:15','12:00'),LIST.replace('12:15','12:16'),LIST.replace('zr/00.png','https://evil.invalid/x'),LIST.replace('2026-11-04','2026-02-30')])
def test_rejects_unsafe_duplicate_and_impossible_source_entries(listing):
    with pytest.raises(ValueError):parse_list(listing,NOW)


def test_original_gaps_are_preserved_and_old_or_future_frames_rejected():
    gap='\n'.join([LIST.splitlines()[0],LIST.splitlines()[-1]])
    assert len(parse_list(gap,NOW))==2
    with pytest.raises(ValueError):parse_list(LIST,NOW+5401)
    with pytest.raises(ValueError):parse_list(LIST,NOW-600)


def test_half_hour_policy_is_fixed_even_for_delayed_collection_and_keeps_three_hours():
    end=datetime.fromtimestamp(NOW,timezone.utc)
    listing='\n'.join(f'background_THA.png "{end-timedelta(minutes=15*(24-i)):%Y-%m-%d %H:%M}" overlay=zr/{i:02}.png' for i in range(25))
    rows=sampled_frames(parse_list(listing,NOW))
    assert len(rows)==7
    assert rows[0]['observed_at']=='2026-11-04T09:30:00Z'
    assert rows[-1]['observed_at']=='2026-11-04T12:30:00Z'
    assert all(datetime.fromisoformat(r['observed_at'].replace('Z','+00:00')).minute in [0,30] for r in rows)
    gap=[r for r in rows if r['observed_at']!='2026-11-04T11:00:00Z']
    assert len(sampled_frames(gap))==6
    with pytest.raises(ValueError):sampled_frames([{'observed_at':'2026-11-04T12:45:00Z'}])


@pytest.mark.parametrize('stage',['wait','capture','publish','export'])
def test_only_source_capture_failures_send_capture_failed(monkeypatch,tmp_path,stage):
    import pipelines.radar.run as runner
    def fail(*_):raise RuntimeError('simulated failure')
    calls=[]
    def publishing(payload):
        calls.append(payload)
        if payload!={'capture_failed':True}:fail()
    monkeypatch.setattr('sys.argv',['radar','--publish']+(['--export',str(tmp_path)] if stage=='export' else []))
    monkeypatch.setattr(runner,'wait_for_receiver',fail if stage=='wait' else lambda:None)
    monkeypatch.setattr(runner,'capture',fail if stage=='capture' else lambda:{'frames':[]})
    monkeypatch.setattr(runner,'publish',publishing)
    # An existing directory cannot be replaced by an export file.
    with pytest.raises(RuntimeError):runner.main()
    assert ({'capture_failed':True} in calls)==(stage=='capture')


@pytest.mark.parametrize('data',[b'not png',PNG[:-10],PNG+b'trailing',PNG[:50]+bytes([PNG[50]^1])+PNG[51:]],ids=['text','truncated','trailing','corrupt'])
def test_png_rejects_bad_format_checksum_and_truncation(data):
    with pytest.raises(ValueError):validate_png(data)


def test_metadata_publication_is_bounded_and_invalid_candidate_preserves_active():
    frame={**validate_png(PNG),'observed_at':'2026-11-04T12:45:00Z'}
    frame['url']='https://fixture.public.blob.vercel-storage.com/tmd-radar/20261104T124500Z-'+frame['sha256']+'.png'
    feed={'schema_version':'2.0','source_id':'tmd_radar','product_id':'composite_rain_rate','data_state':'radar_estimate','snapshot_id':'latest',
        'fetched_at':'2026-11-04T12:46:00Z','source_url':BASE+'index_composite.html','coordinates':[[95,22.5],[108,22.5],[108,4],[95,4]],'units':'mm/hour',
        'generation_consistency':'MANIFEST_CLOCK_AND_DOUBLE_IMAGE_HASH_CHECKED_NO_VERSION_TOKEN','frames':[frame]}
    db=mongomock.MongoClient().db;p=RadarPublisher(db)
    for _ in range(3):p.publish([feed],['latest'])
    assert db.radar_latest.count_documents({})==2
    assert next(row for row in verify_database(db) if row['source_id']=='tmd_radar')['status']=='VERIFIED'
    before=p.read()
    for mutation in ['image_bytes','url','duplicate']:
        bad=deepcopy(feed)
        if mutation=='image_bytes':bad['frames'][0]['image_base64']=base64.b64encode(PNG).decode()
        elif mutation=='url':bad['frames'][0]['url']='https://evil.invalid/image.png'
        else:bad['frames']*=2
        with pytest.raises(Exception):p.publish([bad],['latest'])
        assert p.read()==before
