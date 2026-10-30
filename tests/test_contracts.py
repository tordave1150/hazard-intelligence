from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json
import pytest
from jsonschema import ValidationError
from pipelines.shared.schemas import validate_record
from pipelines.shared.time_units import daily_period,instant
from pipelines.shared.quality import freshness,check_batch
from pipelines.open_meteo.transform import normalize


def test_probability_and_volume_are_distinct(forecast):
    p=forecast['valid_periods'][0]
    assert (p['rainfall_mm'],p['rain_probability_pct'])==(12.5,80)
    assert 'rain_level' not in forecast
    assert forecast['forecast_reference_time'] is None


def test_missing_values_remain_null(forecast):
    assert forecast['valid_periods'][2]['rainfall_mm'] is None
    assert forecast['quality_status']=='partial'
    assert forecast['valid_periods'][1]['rainfall_mm']==0


def test_bangkok_daily_window():
    assert daily_period('2026-10-25')==('2026-10-24T17:00:00Z','2026-10-25T17:00:00Z')
    with pytest.raises(ValueError): instant('2026-10-25T00:00:00')


@pytest.mark.parametrize('field,value',[('rainfall_mm',-1),('rain_probability_pct',101),('rain_probability_pct',True)])
def test_invalid_metrics_rejected(forecast,field,value):
    forecast['valid_periods'][0][field]=value
    with pytest.raises(ValidationError):validate_record('Forecast',forecast)


def test_period_end_and_timezone_rejected(forecast):
    forecast['valid_periods'][0]['valid_end']='2026-10-25T18:00:00Z'
    with pytest.raises(ValueError):validate_record('Forecast',forecast)


@pytest.mark.parametrize('change',[{'timezone':'UTC'},{'daily_units':{}},{'utc_offset_seconds':0}])
def test_provider_semantics_rejected(payload,area,change):
    payload.update(change)
    with pytest.raises(ValueError):normalize(payload,area,'2026-10-25T01:00:00Z')


def test_nonconsecutive_and_stale_provider_periods(payload,area):
    with pytest.raises(ValueError):normalize(payload,area,'2026-10-26T01:00:00Z')
    payload['daily']['time'][1]='2026-10-29'
    with pytest.raises(ValueError):normalize(payload,area,'2026-10-25T01:00:00Z')


def test_fetched_recently_does_not_refresh_old_valid_period():
    now=datetime(2026,10,28,tzinfo=timezone.utc)
    assert freshness('2026-10-24T17:00:00Z','2026-10-28T00:00:00Z',now)=='STALE'


@pytest.mark.parametrize('age,expected',[(30,'FRESH'),(30.01,'DELAYED'),(48,'DELAYED'),(48.01,'STALE')])
def test_freshness_boundaries(age,expected):
    from datetime import timedelta
    now=datetime(2026,10,28,tzinfo=timezone.utc)
    past=(now-timedelta(hours=age)).isoformat()
    assert freshness(past,past,now)==expected


def test_geo_contract_parent_identity_and_coverage():
    root=Path(__file__).resolve().parents[1]
    areas=json.loads((root/'apps/web/data/areas.json').read_text(encoding='utf-8'))
    lookup={a['id']:a for a in areas}
    assert len(lookup)==len(areas)==1012
    assert sum(a['level']=='province' for a in areas)==77
    assert sum(a['level']=='district' for a in areas)==928
    for a in areas:
        validate_record('Area',a)
        assert a['parent_id'] is None or a['parent_id'] in lookup
        if a['level']=='district':assert a['id'][5:7]==a['province_id'][5:7]
        assert a['bbox'][0]<=a['lon']<=a['bbox'][2]
        assert a['bbox'][1]<=a['lat']<=a['bbox'][3]


def test_actual_polygon_geometry_and_ids():
    from shapely.geometry import shape,Point
    root=Path(__file__).resolve().parents[1]
    areas={a['id']:a for a in json.loads((root/'apps/web/data/areas.json').read_text(encoding='utf-8'))+json.loads((root/'apps/web/data/basins.json').read_text(encoding='utf-8'))}
    files=list((root/'apps/web/public/data').rglob('*.geojson'))
    seen=[]
    for f in files:
        for feature in json.loads(f.read_text(encoding='utf-8'))['features']:
            a=areas[feature['properties']['id']];geom=shape(feature['geometry'])
            assert geom.is_valid and not geom.is_empty
            assert geom.buffer(.004).covers(Point(a['lon'],a['lat']))
            seen.append(a['id'])
    assert len(seen)==len(set(seen))==1033
    assert sum(a.startswith('TH-B-') for a in seen)==22
    assert sum(not a.startswith('TH-B-') for a in seen)==1011
