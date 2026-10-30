"""Regression checks that public entry points cannot restore a local trial scope."""
import json
import sys
from pathlib import Path
import mongomock
import pytest
from scripts import gistda_candidate,probe_gistda_features
from scripts.mongo_admin import verify_database
from pipelines.gistda import run,limits


def test_candidate_cli_requests_three_day_thailand_without_a_district(monkeypatch,capsys):
    calls=[]
    def collect(key,**options):
        calls.append(options)
        return dict(source_id='gistda',product_id=limits.PRODUCT,product_window='3days',area_id='TH',
            record_count=0,page_count=1,observed_at=None,complete_provider_query=True,fetched_at='2026-10-29T12:00:00Z')
    monkeypatch.setattr(gistda_candidate,'collect_national_candidate',collect)
    gistda_candidate.main()
    assert calls==[{'three_day':True}]
    result=json.loads(capsys.readouterr().out)
    assert result['area_id']=='TH' and result['product_window']=='3days'


def test_publisher_without_optional_flags_uses_current_country_product(monkeypatch,capsys):
    client=mongomock.MongoClient();calls=[]
    def stop(key,**options):
        calls.append(options)
        raise ValueError('test stop before publication')
    monkeypatch.setattr(run,'collect_national_candidate',stop)
    monkeypatch.setattr(run,'MongoClient',lambda *a,**k:client)
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test')
    monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(sys,'argv',['gistda','--publish'])
    with pytest.raises(RuntimeError):run.main()
    assert calls==[{'three_day':True}]
    status=client.weather_db.source_status.find_one({'_id':'gistda:'+limits.PRODUCT})
    assert status['status']=='FAILED'
    assert client.weather_db.source_status.count_documents({})==1
    assert 'test stop' not in capsys.readouterr().out


def test_routine_workflow_audit_excludes_retired_products():
    report=verify_database(mongomock.MongoClient().test)
    assert len(report)==6
    assert [row['product_id'] for row in report if row['source_id']=='gistda']==[limits.PRODUCT]
    assert len(verify_database(mongomock.MongoClient().test,include_retired=True))==8


def test_actions_form_and_versioned_request_are_national():
    root=Path(__file__).resolve().parents[1]
    text=(root/'.github/workflows/gistda-access.yml').read_text(encoding='utf-8')
    assert 'inputs.ap_idn' not in text and 'inputs.query_scope' not in text
    assert 'GISTDA_QUERY_SCOPE: national' in text
    assert "default: '3days'" in text
    request=probe_gistda_features.load_reviewed_request()
    assert request['window']=='3days' and request['ap_idn']==''
