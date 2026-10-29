import mongomock
from pipelines.shared.run_status import start_run, workflow_context


def test_running_status_preserves_previous_success_and_links_only_valid_workflow(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY','tordave1150/hazard-intelligence')
    monkeypatch.setenv('GITHUB_RUN_ID','12345')
    monkeypatch.setenv('GITHUB_EVENT_NAME','schedule')
    db=mongomock.MongoClient().test
    db.source_status.insert_one({'_id':'test','last_success':'previous','completed_at':'old','error_summary':'old'})
    start_run(db,'test',{'last_attempt':'now'})
    row=db.source_status.find_one({'_id':'test'})
    assert row['status']=='RUNNING' and row['last_success']=='previous'
    assert 'completed_at' not in row and 'error_summary' not in row
    assert row['run_url']=='https://github.com/tordave1150/hazard-intelligence/actions/runs/12345'
    monkeypatch.setenv('GITHUB_REPOSITORY','https://private.invalid/secret')
    assert 'run_url' not in workflow_context()


def test_hourly_failure_reports_safe_reason_without_response_or_credentials(tmp_path,monkeypatch,capsys):
    from pipelines.open_meteo import hourly
    from pipelines.open_meteo.client import ProviderRequestError
    monkeypatch.setattr('sys.argv',['hourly','--export',str(tmp_path/'unused.json')])
    monkeypatch.setattr(hourly,'weather_locations',lambda _: [])
    def fail(*args):raise ProviderRequestError('rate_limited',429)
    monkeypatch.setattr(hourly,'collect',fail)
    import pytest,json
    with pytest.raises(RuntimeError):hourly.main()
    assert json.loads(capsys.readouterr().out)=={'status':'FAILED','product_id':'today_hourly','stage':'collect','reason':'rate_limited','http_status':429,'transport_type':None}
    assert not (tmp_path/'unused.json').exists()
