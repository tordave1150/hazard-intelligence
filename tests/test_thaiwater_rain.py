import json
from pathlib import Path
from copy import deepcopy
import mongomock,pytest
from jsonschema import ValidationError
from pipelines.thaiwater.rain_data import normalize,KEY
from pipelines.thaiwater.rain_publication import RainPublisher
from pipelines.shared.schemas import validate_record
ROOT=Path(__file__).parent
STAMP='2026-10-30T16:00:00Z'
@pytest.fixture
def payload():return json.loads((ROOT/'fixtures/thaiwater/public-rain-subset.json').read_text(encoding='utf-8'))

def test_real_rain_rows_keep_zero_units_and_unknown_window(payload):
    f=normalize(payload,STAMP)
    assert f['record_count']==2 and f['provider_automatic_count']==3 and len(f['excluded_stations'])==1
    assert f['records'][0]['rain_24h_mm']==136.5 and f['records'][1]['rain_24h_mm']==0
    assert all(r['observed_at'] is None for r in f['records']) and f['window_start'] is None and f['window_end'] is None
    assert all(r['district_id'] for r in f['records']) and f['quality_issue_count']==0
    assert not any('water_level_msl' in r for r in f['records'])

def test_invalid_missing_and_zero_rain_are_separate(payload):
    payload['data'][0].update(rain_24h=None,rain_1h=0)
    payload['data'][1].update(rain_24h=-999,rain_1h=True,rainfall_datetime='invalid')
    f=normalize(payload,STAMP);a,b=f['records']
    assert a['rain_24h_mm'] is None and a['rain_1h_mm']==0 and 'NO_24H_RAIN' in a['quality_flags']
    assert b['rain_1h_mm'] is None and {'INVALID_RAIN','INVALID_PROVIDER_TIME','NO_24H_RAIN'}<=set(b['quality_flags'])

def test_district_name_must_match_exactly_inside_provider_province(payload):
    payload['data'][0]['geocode']['amphoe_name']['th']='unknown district'
    row=normalize(payload,STAMP)['records'][0]
    assert row['district_id'] is None and row['district_mapping']=='UNCONFIRMED'

def test_duplicate_station_ids_reject_the_entire_candidate(payload):
    payload['data'].append(deepcopy(payload['data'][0]))
    with pytest.raises(ValueError):normalize(payload,STAMP)

def test_unverified_instants_units_and_accounting_cannot_be_stored(payload):
    for change in [lambda f:f.update(window_end=STAMP),lambda f:f.update(record_count=99),lambda f:f['records'][0].update(observed_at=STAMP),lambda f:f['units'].update(rain_24h_mm='mm/hour')]:
        f=normalize(payload,STAMP);change(f)
        with pytest.raises((ValueError,ValidationError)):validate_record('ThaiWaterRainFeed',f)

def test_rain_publication_has_independent_bounded_slots_and_retains_good_generation(payload):
    db=mongomock.MongoClient().test;publisher=RainPublisher(db);feed=normalize(payload,STAMP)
    for _ in range(3):publisher.publish([feed],['latest'])
    assert db.rain_gauge_latest.count_documents({})==2 and publisher.read()==[feed] and db.gauge_latest.count_documents({})==0
    pointer=db.snapshot_control.find_one({'_id':KEY});bad=deepcopy(feed);bad['records'].pop()
    with pytest.raises((ValueError,ValidationError)):publisher.publish([bad],['latest'])
    assert db.snapshot_control.find_one({'_id':KEY})==pointer
    publisher.rollback();assert publisher.read()==[feed]
    from scripts.mongo_admin import verify_database
    result=next(r for r in verify_database(db) if r['product_id']=='national_rain_24h')
    assert result['status']=='VERIFIED' and result['unique_index_verified']
