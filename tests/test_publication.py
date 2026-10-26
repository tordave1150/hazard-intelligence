from copy import deepcopy
import mongomock
import pytest
from pipelines.shared.publication import Publisher,export_local


def publisher():return Publisher(mongomock.MongoClient().test)


def test_bounded_idempotent_two_slot_publication(forecast):
    p=publisher()
    for _ in range(8):p.publish([forecast],['TH-P-10'])
    assert p.records.count_documents({})==2
    assert p.control.count_documents({})==1
    assert p.db.etl_locks.count_documents({})==0
    assert p.read()==[forecast]


def test_partial_empty_duplicate_and_unknown_batch_preserve_last_good(forecast):
    p=publisher();p.publish([forecast],['TH-P-10'])
    active=p.control.find_one({})
    for records,expected in [([],['TH-P-10']),([forecast],['TH-P-10','TH-P-11']),([forecast,forecast],['TH-P-10']),([forecast],['TH-P-11'])]:
        with pytest.raises(ValueError):p.publish(records,expected)
        assert p.control.find_one({})==active
        assert p.read()==[forecast]


def test_write_failure_never_promotes_candidate(forecast,monkeypatch):
    p=publisher();p.publish([forecast],['TH-P-10'])
    active=p.control.find_one({})
    def fail(*args,**kwargs):raise RuntimeError('simulated database write interruption')
    monkeypatch.setattr(p.records,'insert_many',fail)
    with pytest.raises(RuntimeError):p.publish([forecast],['TH-P-10'])
    assert p.control.find_one({})==active
    assert p.read()==[forecast]
    assert p.db.etl_locks.count_documents({})==0


def test_concurrent_and_unrecovered_writer_cannot_publish(forecast):
    p=publisher();p.publish([forecast],['TH-P-10'])
    with p.lock('open_meteo:daily_forecast'):
        with pytest.raises(RuntimeError):p.publish([forecast],['TH-P-10'])
    assert p.read()==[forecast]


def test_rollback_restores_actual_previous_slot(forecast):
    p=publisher();p.publish([forecast],['TH-P-10'])
    newer=deepcopy(forecast);newer['valid_periods'][0]['rainfall_mm']=99
    p.publish([newer],['TH-P-10']);assert p.read()==[newer]
    p.rollback();assert p.read()==[forecast]


def test_mixed_period_batch_not_published(forecast):
    p=publisher();second=deepcopy(forecast);second['location_id']='TH-P-11';second['valid_periods'][0]['date']='2026-10-24'
    with pytest.raises(ValueError):p.publish([forecast,second],['TH-P-10','TH-P-11'])
    assert p.read()==[]


def test_local_export_does_not_destroy_last_good_on_failure(forecast,tmp_path):
    path=tmp_path/'weather.json'
    export_local(path,[forecast],['TH-P-10'],{})
    old=path.read_bytes()
    with pytest.raises(ValueError):export_local(path,[],['TH-P-10'],{})
    assert path.read_bytes()==old
