from copy import deepcopy
import json
from pathlib import Path
import pytest
import mongomock
from pipelines.shared.geography_migrations import CORRECTIONS,canonical_stored_forecast
from pipelines.shared.locations import weather_locations
from pipelines.shared.quality import check_batch
from pipelines.shared.publication import Publisher
from scripts.audit_dopa_geography import active_areas,comparable_name
from scripts.mongo_admin import verify_database

ROOT=Path(__file__).resolve().parents[1]


def test_official_cancellation_and_bangkok_name_semantics():
    rows=[{'A':'10000000','B':'กรุงเทพมหานคร','D':'0'},
          {'A':'10010000','B':'เขตพระนคร','D':'0'},
          {'A':'10010100','B':'พระบรมมหาราชวัง','D':'0'},
          {'A':'10020000','B':'ยกเลิก*','D':'0'},
          {'A':'10030000','B':'จำหน่าย','D':'25490101'}]
    assert active_areas(rows)=={'TH-P-10':'กรุงเทพมหานคร','TH-D-1001':'เขตพระนคร'}
    assert comparable_name('TH-D-1001','เขตพระนคร')=='พระนคร'
    assert comparable_name('TH-D-4030','เขตพระนคร')=='เขตพระนคร'
    with pytest.raises(ValueError):active_areas([rows[0],rows[0]])


def test_corrected_directory_facts_reach_both_metadata_and_display_geometry():
    areas={a['id']:a for a in weather_locations()}
    assert len(areas)==1005
    assert 'TH-D-4026' not in areas
    alias=CORRECTIONS['id_aliases'][0]
    target=areas[alias['to']]
    assert target['name_th']==alias['name_th']
    assert {k:target[k] for k in ['lat','lon']}==alias['point']
    for identifier,name in CORRECTIONS['name_corrections'].items():
        area=areas[identifier]
        assert area['name_th']==name
        features=json.loads((ROOT/'apps/web/public'/area['geometry_ref'].lstrip('/')).read_text(encoding='utf-8'))['features']
        feature=next(f for f in features if f['id']==identifier)
        assert feature['properties']['name_th']==name
    features=json.loads((ROOT/'apps/web/public'/target['geometry_ref'].lstrip('/')).read_text(encoding='utf-8'))['features']
    assert 'TH-D-4029' in {f['id'] for f in features}
    assert 'TH-D-4026' not in {f['id'] for f in features}


def test_read_migration_preserves_values_and_times_and_rejects_point_mismatch(forecast):
    original={**forecast,'location_id':'TH-D-4026','point':dict(CORRECTIONS['id_aliases'][0]['point'])}
    before=deepcopy(original)
    migrated=canonical_stored_forecast(original)
    assert migrated['location_id']=='TH-D-4029'
    assert {**migrated,'location_id':original['location_id']}==original==before
    assert canonical_stored_forecast(migrated) is migrated
    with pytest.raises(ValueError):canonical_stored_forecast({**original,'point':{'lat':0,'lon':0}})
    with pytest.raises(ValueError):check_batch([migrated,original],['TH-D-4029'])
    with pytest.raises(ValueError):check_batch([original],['TH-D-4029'])


def test_read_only_database_audit_accepts_exact_legacy_snapshot_without_rewriting(forecast,monkeypatch):
    from scripts import mongo_admin
    alias=CORRECTIONS['id_aliases'][0]
    legacy={**forecast,'location_id':alias['from'],'point':dict(alias['point'])}
    db=mongomock.MongoClient().test
    publisher=Publisher(db);publisher.publish([legacy],[alias['from']])
    monkeypatch.setattr(mongo_admin,'weather_locations',lambda _:[{'id':alias['to']}])
    result=verify_database(db)[0]
    assert result['status']=='VERIFIED' and result['historical_identity_aliases']==1
    assert publisher.read()==[legacy]
    # A collision after normalization must fail even when the stored IDs differ.
    publisher.publish([legacy,{**legacy,'location_id':alias['to']}],[alias['from'],alias['to']])
    monkeypatch.setattr(mongo_admin,'weather_locations',lambda _:[{'id':alias['to']},{'id':'TH-D-4001'}])
    with pytest.raises(ValueError):verify_database(db)
