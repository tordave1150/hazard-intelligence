from copy import deepcopy
from datetime import timedelta
import json
import mongomock
import pytest
from jsonschema import ValidationError
from pipelines.open_meteo import hourly
from pipelines.open_meteo.budget import RequestBudget, BudgetExceeded, request_budget
from pipelines.open_meteo.client import fetch_batch, fetch_hourly_batch, ProviderRequestError
from pipelines.shared.locations import weather_locations
from pipelines.shared.schemas import validate_record
from pipelines.shared.time_units import daily_period, instant
from pipelines.shared.publication import export_local

DAY = '2026-10-28'
FETCHED = '2026-10-28T01:00:00Z'


@pytest.fixture
def hourly_record(monkeypatch):
    monkeypatch.setattr(hourly, 'utc_now', lambda: FETCHED)
    start = instant(daily_period(DAY)[0])
    payload = {'latitude': 13.75, 'longitude': 100.5, 'timezone': 'Asia/Bangkok', 'utc_offset_seconds': 25200,
               'hourly_units': {'time': 'unixtime', 'precipitation': 'mm', 'precipitation_probability': '%', 'temperature_2m': '°C'},
               'hourly': {'time': [int((start + timedelta(hours=i + 1)).timestamp()) for i in range(24)],
                          'precipitation': [1.5] * 24, 'precipitation_probability': [60] * 24, 'temperature_2m': [29] * 24}}
    return hourly.normalize(payload, weather_locations('all')[0], DAY, FETCHED)


def test_hourly_contract_preserves_full_intervals_including_last_hour_and_null_issue(hourly_record):
    record = hourly_record
    assert record['valid_hours'][0]['valid_start'] == '2026-10-27T17:00:00+00:00'
    assert record['valid_hours'][-1]['valid_end'] == '2026-10-28T17:00:00+00:00'
    assert record['forecast_reference_time'] is None and record['units']['rainfall'] == 'mm/1h'
    for change in ({'product_id': 'daily_forecast'}, {'forecast_reference_time': FETCHED}, {'forecast_date': '2026-10-27'}):
        with pytest.raises((ValueError, ValidationError)):
            validate_record('HourlyForecast', {**record, **change})
    with pytest.raises((ValueError, ValidationError)):
        validate_record('HourlyForecast', {**record, 'model_point': {'lat': float('nan'), 'lon': 100.5}})
    for change in ({'valid_start': FETCHED}, {'temperature_valid_at': FETCHED}, {'rainfall_mm': True}, {'rain_probability_pct': 101}):
        bad = deepcopy(record); bad['valid_hours'][0].update(change)
        with pytest.raises((ValueError, ValidationError)):
            validate_record('HourlyForecast', bad)


def test_hourly_publication_is_independent_bounded_atomic_and_can_rollback(hourly_record, tmp_path):
    db = mongomock.MongoClient().test
    p = hourly.HourlyPublisher(db); ids = [hourly_record['location_id']]
    p.publish([hourly_record], ids)
    old = db.snapshot_control.find_one({'_id': 'open_meteo:today_hourly'})
    bad = deepcopy(hourly_record); bad['valid_hours'].pop()
    with pytest.raises((ValueError, ValidationError)): p.publish([bad], ids)
    assert db.snapshot_control.find_one({'_id': 'open_meteo:today_hourly'}) == old
    newer = deepcopy(hourly_record); newer['valid_hours'][0]['rainfall_mm'] = 2
    for _ in range(4): p.publish([newer], ids)
    p.publish([hourly_record], ids); p.rollback()
    assert p.read() == [newer] and db.weather_hourly_latest.count_documents({}) == 2
    assert db.weather_latest.count_documents({}) == 0
    destination = tmp_path / 'hourly.json'
    export_local(destination, [hourly_record], ids, {}, kind='HourlyForecast', check=hourly.check_hourly_batch)
    assert json.loads(destination.read_text(encoding='utf-8'))['records'] == [hourly_record]


def test_shared_rolling_budget_accounts_for_two_jobs_and_failed_attempts():
    db = mongomock.MongoClient().test
    clock = [100000]
    daily = RequestBudget(db, clock=lambda: clock[0])
    hourly_budget = RequestBudget(db, clock=lambda: clock[0])
    for _ in range(10): daily.reserve(25)
    for _ in range(10): hourly_budget.reserve(25)
    with pytest.raises(BudgetExceeded): hourly_budget.reserve(1)
    clock[0] += 61; hourly_budget.reserve(25)
    clock[0] += 3601
    for _ in range(9):
        for _ in range(20): hourly_budget.reserve(25)
        clock[0] += 61
    with pytest.raises(BudgetExceeded): hourly_budget.reserve(25)
    clock[0] += 3601
    for index in range(159):
        hourly_budget.reserve(25)
        if index % 20 == 19: clock[0] += 61
    with pytest.raises(BudgetExceeded): hourly_budget.reserve(25)
    assert sum(event['units'] for event in db.provider_request_budget.find_one()['events']) == 9000
    # A new rolling day prunes the same single ledger instead of growing a collection.
    clock[0] += 86401; daily.reserve(25)
    assert len(db.provider_request_budget.find_one()['events']) == 1
    assert db.provider_request_budget.count_documents({}) == 1


def test_budget_exhaustion_sends_no_http_request_and_does_not_retry():
    class Session:
        def get(self, *args, **kwargs): raise AssertionError('HTTP must not be sent')
    with request_budget(clock=lambda: 100000):
        from pipelines.open_meteo.budget import active_budget
        for _ in range(20): active_budget.get().reserve(25)
        with pytest.raises(ProviderRequestError) as error:
            fetch_batch([weather_locations('all')[0]], session=Session(), sleep=lambda _: None)
        assert error.value.retryable is False


def test_hourly_request_includes_final_midnight_boundary_and_no_daily_variables():
    class Response:
        status_code = 200
        def json(self): return {'hourly': {}}
    class Session:
        def get(self, url, **kwargs):
            params = kwargs['params']
            assert params['start_hour'] == '2026-10-28T01:00' and params['end_hour'] == '2026-10-29T00:00'
            assert params['timeformat'] == 'unixtime' and 'daily' not in params
            return Response()
    fetch_hourly_batch([weather_locations('all')[0]], DAY, session=Session())


def test_stream_limit_closes_response_without_retry_and_failure_attempts_consume_budget():
    class Stream:
        status_code = 200
        closed = False
        def iter_content(self, size): yield b'x' * (2 * 1024 * 1024 + 1)
        def close(self): self.closed = True
    response = Stream()
    class Session:
        def get(self, *args, **kwargs):
            assert kwargs['stream'] and kwargs['allow_redirects'] is False
            return response
    with request_budget(clock=lambda: 100000):
        from pipelines.open_meteo.budget import active_budget
        with pytest.raises(ProviderRequestError) as error:
            fetch_hourly_batch([weather_locations('all')[0]], DAY, session=Session(), sleep=lambda _: pytest.fail('No retry'))
        assert not error.value.retryable and response.closed
        assert sum(e['units'] for e in active_budget.get().local['events']) == 1
