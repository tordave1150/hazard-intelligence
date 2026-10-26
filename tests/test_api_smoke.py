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
    assert 's-maxage=60' in response.headers['Cache-Control']
    assert 'mongodb://' not in response.text and 'mongodb+srv://' not in response.text


@pytest.mark.parametrize('route',['/api/areas?level=bogus','/api/weather?metric=flood_probability','/api/gauges?kind=wrong'])
def test_bad_queries_rejected(route):
    response=requests.get(BASE+route,timeout=15)
    assert response.status_code==400 and response.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('route',['/api/dams','/api/gauges','/api/warnings','/api/flood-products'])
def test_planned_sources_are_never_normal(route):
    value=requests.get(BASE+route,timeout=15).json()
    assert value['status']=='UNAVAILABLE' and value['records']==[]


def test_area_identity_and_unknown_area():
    data=requests.get(BASE+'/api/areas?parent_id=TH-P-57&level=district',timeout=15).json()
    assert len(data['areas'])==18 and all(a['parent_id']=='TH-P-57' for a in data['areas'])
    assert requests.get(BASE+'/api/weather?area_id=TH-P-99',timeout=15).status_code==404


def test_no_write_or_ingestion_route():
    assert requests.post(BASE+'/api/overview',timeout=15).status_code==405
