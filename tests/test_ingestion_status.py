"""A recovered run must not advertise the previous run's failure as current."""
import sys
import mongomock
from pipelines.open_meteo import run


def test_success_clears_prior_error_after_publication(monkeypatch,area,forecast):
    client=mongomock.MongoClient()
    db=client.weather_db
    key='open_meteo:daily_forecast'
    db.source_status.insert_one({'_id':key,'status':'FAILED','error_summary':'ValueError'})
    monkeypatch.setenv('MONGODB_URI','mongodb://unused-test-host')
    monkeypatch.setenv('MONGODB_DB_NAME','weather_db')
    monkeypatch.setattr(run,'MongoClient',lambda *args,**kwargs:client)
    monkeypatch.setattr(run,'weather_locations',lambda level:[area])
    monkeypatch.setattr(run,'collect_forecasts',lambda locations:([forecast],[]))
    monkeypatch.setattr(sys,'argv',['run','--level','all','--publish'])
    run.main()
    status=db.source_status.find_one({'_id':key})
    control=db.snapshot_control.find_one({'_id':key})
    assert status['status']=='SUCCESS' and 'error_summary' not in status
    assert status['records_published']==1 and status['last_success']
    assert control['active_run_id']==status['active_generation'] and control['record_count']==1
