"""Opt-in integration checks against a running app: HAZARD_TEST_URL=... pytest.

    This suite uses HTTP contracts, without controlling a browser or triggering ETL.
"""
import os
import pytest
import requests

BASE=os.getenv('HAZARD_TEST_URL')
pytestmark=pytest.mark.skipif(not BASE,reason='Set HAZARD_TEST_URL for running-app HTTP checks')


@pytest.mark.parametrize('route',['/api/overview','/api/areas?level=province','/api/area/TH-D-5709/summary','/api/weather?area_id=TH-P-57','/api/sources/status'])
def test_read_endpoints(route):
    response=requests.get(BASE+route,timeout=15)
    assert response.status_code==200
    # Vercel consumes s-maxage / stale-while-revalidate at its edge and strips
    # them from the client response. A direct origin must still emit the TTL.
    if 'x-vercel-id' in response.headers:
        assert response.headers['Cache-Control']=='public'
        assert response.headers['x-vercel-cache'] in {'HIT','MISS','STALE','REVALIDATED'}
    else:
        assert 's-maxage=60' in response.headers['Cache-Control']
    assert 'mongodb://' not in response.text and 'mongodb+srv://' not in response.text


@pytest.mark.parametrize('route',['/api/areas?level=bogus','/api/weather?metric=flood_probability','/api/gauges?kind=wrong','/api/dams?date=2026-10-27','/api/warnings?date=2026-10-27'])
def test_bad_queries_rejected(route):
    response=requests.get(BASE+route,timeout=15)
    assert response.status_code==400 and response.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('route',['/api/gauges','/api/flood-products'])
def test_planned_sources_are_never_normal(route):
    value=requests.get(BASE+route,timeout=15).json()
    assert value['status']=='UNAVAILABLE' and value['records']==[]


def test_dam_endpoint_has_independent_report_semantics():
    response=requests.get(BASE+'/api/dams',timeout=15)
    assert response.status_code==200
    data=response.json()
    assert data['source_id']=='rid' and data['status'] in ['FRESH','DELAYED','STALE','UNKNOWN','UNAVAILABLE']
    if data['records']:
        assert data['total_count']==35
        assert all(r['observed_at'] is None and r['time_precision']=='date' for r in data['records'])
    else:
        assert data['status']=='UNAVAILABLE'


def test_cap_messages_keep_expiry_separate_from_feed_freshness():
    response=requests.get(BASE+'/api/warnings',timeout=15);assert response.status_code==200
    value=response.json();assert value['source_id']=='tmd'
    assert set(value['message_states'])=={r['warning_id'] for r in value['records']}
    assert 'absence does not establish safe conditions' in value['coverage']
    assert all(r['status']=='Actual' and r['scope']=='Public' and r['source_url']=='https://www.tmd.go.th/api/xml/CAP' for r in value['records'])
    if value['feed']:
        assert value['feed']['feed_item_count']==len(value['records'])+value['feed']['ignored_item_count']
    else:assert value['status']=='UNAVAILABLE'


def test_area_identity_and_unknown_area():
    data=requests.get(BASE+'/api/areas?parent_id=TH-P-57&level=district',timeout=15).json()
    assert len(data['areas'])==18 and all(a['parent_id']=='TH-P-57' for a in data['areas'])
    assert requests.get(BASE+'/api/weather?area_id=TH-P-99',timeout=15).status_code==404
    assert requests.get(BASE+'/api/dams?area_id=TH-P-99',timeout=15).status_code==404


def test_dams_filter_by_point_scope_without_changing_report_date():
    national=requests.get(BASE+'/api/dams',timeout=15).json()
    subset=requests.get(BASE+'/api/dams?area_id=TH-P-21',timeout=15).json()
    assert all(r['province_id']=='TH-P-21' for r in subset['records'])
    assert subset['report_date']==national['report_date']
    assert subset['total_count']==national['total_count']


def test_no_write_or_ingestion_route():
    assert requests.post(BASE+'/api/overview',timeout=15).status_code==405
