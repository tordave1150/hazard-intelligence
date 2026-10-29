"""Opt-in integration checks against a running app: HAZARD_TEST_URL=... pytest.

    This suite uses HTTP contracts, without controlling a browser or triggering ETL.
"""
import os
import pytest
import requests

BASE=os.getenv('HAZARD_TEST_URL')
pytestmark=pytest.mark.skipif(not BASE,reason='Set HAZARD_TEST_URL for running-app HTTP checks')


def complete_flood_query(area_id='TH'):
    first=requests.get(BASE+'/api/flood-products',params={'area_id':area_id},timeout=25)
    assert first.status_code==200
    value=first.json();records=list(value['records']);cursor=value.get('pagination')
    if not value['feed']:return value
    generation=cursor['generation'];chunk_count=cursor['chunk_count']
    assert 1<=chunk_count<=512
    while cursor['next_chunk'] is not None:
        response=requests.get(BASE+'/api/flood-products',params={'area_id':area_id,'chunk':cursor['next_chunk'],'generation':generation},timeout=25)
        assert response.status_code==200 and len(response.content)<2*1024*1024
        page=response.json()
        assert page['feed']==value['feed'] and page['pagination']['generation']==generation
        assert page['pagination']['chunk']==cursor['chunk']+1
        records.extend(page['records']);cursor=page['pagination']
    assert cursor['chunk']==chunk_count-1 and len({r['id'] for r in records})==len(records)
    return {**value,'records':records,'status':'AVAILABLE' if records else 'EMPTY_RESULT'}


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


@pytest.mark.parametrize('route',['/api/gauges'])
def test_planned_sources_are_never_normal(route):
    value=requests.get(BASE+route,timeout=15).json()
    assert value['status']=='UNAVAILABLE' and value['records']==[]


def test_source_health_separates_planned_source_and_supplies_schedule_evidence():
    value=requests.get(BASE+'/api/sources/status',timeout=25).json()
    assert value['checked_at'] and len(value['sources'])==6
    for source in value['sources']:
        monitor=source['monitoring']
        if source['id']=='thaiwater':assert monitor['state']=='PLANNED' and not monitor['needs_attention']
        else:assert monitor['cadence_hours'] and monitor['actions_url'].startswith('https://github.com/tordave1150/hazard-intelligence/actions/workflows/')


def test_gistda_scoped_summary_and_detail_agree_without_national_geometry():
    first=requests.get(BASE+'/api/flood-products',params={'area_id':'TH-P-26','view':'summary'},timeout=25)
    assert first.status_code==200
    summary=first.json()
    if not summary['feed']:return
    assert summary['status']=='SUMMARY_ONLY' and summary['records']==[]
    assert summary['scope']['area_id']=='TH-P-26' and summary['scope']['mode']=='summary'
    detail=requests.get(BASE+'/api/flood-products',params={'area_id':'TH-P-26','view':'detail'},timeout=25).json()
    records=list(detail['records']);page=detail['pagination']
    while page['next_chunk'] is not None:
        value=requests.get(BASE+'/api/flood-products',params={'area_id':'TH-P-26','view':'detail','chunk':page['next_chunk'],'generation':page['generation']},timeout=25).json()
        assert value['scope']==detail['scope'] and value['feed']==detail['feed']
        records.extend(value['records']);page=value['pagination']
    assert len(records)==summary['scope']['record_count']==len({r['id'] for r in records})
    assert all('TH-P-26' in row['area_ids'] for row in records)
    for query in ['view=bogus','view=summary&chunk=1&generation=local','view=summary&view=detail']:
        assert requests.get(BASE+'/api/flood-products?'+query,timeout=15).status_code==400


def test_gistda_empty_is_distinct_from_unavailable_and_observation_age_is_unknown():
    value=complete_flood_query()
    assert value['source_id']=='gistda' and value['integration_status'] in ['pilot','national_query']
    if value['feed']:
        assert value['scope_area_id'] in ['TH','TH-D-2604'] and value['in_scope'] is True
        assert value['status'] in ['AVAILABLE','EMPTY_RESULT'] and value['freshness']=='UNKNOWN'
        assert value['feed']['observed_at'] is None and value['feed']['complete_provider_query'] is True
        assert value['feed']['record_count']==len(value['records'])<=20000
        assert value['feed']['product_window']=='3days'
        if value['scope_area_id']=='TH':
            assert 'ap_idn' not in value['feed']['query']
            assert all(row['area_ids'] for row in value['records'])
        else:assert value['feed']['query']['ap_idn']=='2604'
        assert all(row['properties'] is None for row in value['records'])
    else:assert value['status']=='UNAVAILABLE' and value['records']==[]


def test_gistda_rejects_other_windows_and_never_turns_outside_scope_into_no_flood():
    value=complete_flood_query('TH-D-5709')
    if value['feed'] and value['feed']['area_id']=='TH':
        assert value['in_scope'] is True and value['status'] in ['AVAILABLE','EMPTY_RESULT']
        assert all('TH-D-5709' in row['area_ids'] for row in value['records'])
    else:
        assert value['in_scope'] is False and value['records']==[]
        assert value['status']==('OUT_OF_SCOPE' if value['feed'] else 'UNAVAILABLE')
    assert requests.get(BASE+'/api/flood-products?window=30days',timeout=15).status_code==400
    assert requests.get(BASE+'/api/flood-products?area_id=TH-P-99',timeout=15).status_code==404
    assert requests.post(BASE+'/api/flood-products',timeout=15).status_code==405
    for query in ['chunk=1','chunk=512','chunk=-1','generation=invalid','chunk=0&chunk=1']:
        assert requests.get(BASE+'/api/flood-products?'+query,timeout=15).status_code==400


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
    issues=value['geography_issues']['unmapped_geocodes']
    assert isinstance(issues,list) and 'not assigned' in value['geography_issues']['scope']
    for issue in issues:
        row=next(r for r in value['records'] if r['warning_id']==issue['warning_id'])
        assert any(c=={'value_name':issue['value_name'],'value':issue['value']} for a in row['source_areas'] for c in a['geocodes'])
        if issue['value_name']=='ISO3166-2':assert 'TH-P-'+issue['value'][3:] not in row['area_ids']
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


def test_corrected_wiang_kao_identity_and_forecast_read_compatibility():
    matches=requests.get(BASE+'/api/areas?q=เวียงเก่า&level=district',timeout=15).json()['areas']
    assert len(matches)==1 and matches[0]['id']=='TH-D-4029'
    data=requests.get(BASE+'/api/weather?area_id=TH-D-4029',timeout=15).json()
    if data['records']:
        assert len(data['records'])==1 and data['records'][0]['location_id']=='TH-D-4029'
        assert data['records'][0]['point']=={'lat':16.725377,'lon':102.291901}
    assert requests.get(BASE+'/api/weather?area_id=TH-D-4026',timeout=15).status_code==404
