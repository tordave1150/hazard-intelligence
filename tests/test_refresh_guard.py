from datetime import datetime,timezone
import pytest
from scripts.refresh_guard import decision

NOW=datetime(2026,10,30,15,0,tzinfo=timezone.utc)
def test_scheduler_ticks_skip_recent_success_without_provider_request():
    status={'status':'SUCCESS','last_success':'2026-10-30T14:50:00Z','forecast_date':'2026-10-30'}
    assert decision('tmd',status,NOW)==(False,'recent_success')
    assert decision('hourly',status,NOW)==(False,'recent_success')
    assert decision('tmd',status,NOW,force=True)==(True,'explicit_request')

def test_due_boundary_failed_attempt_and_new_bangkok_day():
    status={'status':'SUCCESS','last_success':'2026-10-30T11:00:00Z','forecast_date':'2026-10-30'}
    assert decision('hourly',status,NOW)==(True,'refresh_due')
    status['last_success']='2026-10-30T14:59:00Z';status['status']='FAILED'
    assert decision('hourly',status,NOW)==(True,'retry_failed_attempt')
    status.update(status='SUCCESS',forecast_date='2026-10-29')
    assert decision('hourly',status,NOW)==(True,'new_forecast_day')

@pytest.mark.parametrize('stamp',[None,'invalid','2026-10-30T22:00:00','2026-10-31T00:00:00Z'])
def test_unknown_success_time_does_not_hide_missing_data(stamp):
    assert decision('tmd',{'last_success':stamp},NOW)==(True,'invalid_success_time')

def test_missing_status_and_unsupported_source():
    assert decision('tmd',None,NOW)==(True,'no_success')
    with pytest.raises(ValueError):decision('other',None,NOW)

def test_scheduled_cli_reads_status_and_skips_without_changing_success(monkeypatch,tmp_path,capsys):
    import mongomock,json
    from scripts import refresh_guard
    dbclient=mongomock.MongoClient();stamp=datetime.now(timezone.utc).isoformat()
    row={'_id':'tmd:cap_warnings','status':'SUCCESS','last_success':stamp}
    dbclient.test.source_status.insert_one(row)
    monkeypatch.setattr(refresh_guard,'MongoClient',lambda *a,**k:dbclient)
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test');monkeypatch.setenv('MONGODB_DB_NAME','test')
    monkeypatch.delenv('REFRESH_FORCE',raising=False);monkeypatch.setenv('GITHUB_OUTPUT',str(tmp_path/'output'))
    monkeypatch.setattr('sys.argv',['guard','--source','tmd']);refresh_guard.main()
    assert json.loads(capsys.readouterr().out)['due'] is False
    assert (tmp_path/'output').read_text()=='due=false\n'
    assert dbclient.test.source_status.find_one()==row
