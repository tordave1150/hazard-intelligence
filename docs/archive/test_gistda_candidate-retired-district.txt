import copy
import json

import pytest
import requests

from scripts import gistda_candidate as candidate

KEY = 'test-only-candidate-secret'
NOW = '2026-10-27T13:00:00+00:00'


def feature():
    return {'type': 'Feature', 'id': KEY,
            'properties': {'ap_idn': '2604', 'pv_idn': '26', 'f_area': 123456,
                           '_createdAt': '2026-10-27T00:00:00Z', 'private': KEY},
            'geometry': {'type': 'Polygon', 'coordinates': [
                [[101, 14], [101.01, 14], [101.01, 14.01], [101, 14]]], 'private': KEY}}


def page(rows=None, matched=None):
    rows = [] if rows is None else rows
    return {'type': 'FeatureCollection', 'features': rows, 'numberReturned': len(rows),
            'numberMatched': len(rows) if matched is None else matched,
            'timeStamp': '2026-10-27T12:00:00Z', 'links': [{'href': 'https://example.invalid/?api_key=' + KEY}]}


class Response:
    def __init__(self, payload, status=200):
        self.raw = json.dumps(payload).encode()
        self.status_code = status
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, chunk_size): yield self.raw


def test_complete_empty_query_is_usable_with_unknown_observation_and_not_all_clear():
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response(page())
    result = candidate.collect_candidate(KEY, get=get, now=lambda: NOW)
    assert len(calls) == 1 and calls[0][0] == candidate.ENDPOINT
    assert calls[0][1]['params'] == {'ap_idn': '2604', 'limit': 100, 'offset': 0}
    assert calls[0][1]['headers']['API-Key'] == KEY and not calls[0][1]['allow_redirects']
    assert result['records'] == [] and result['complete_provider_query']
    assert result['observed_at'] is None and result['observation_time_status'] == 'NOT_SUPPLIED'
    assert result['product_window'] == '1day' and result['area_id'] == 'TH-D-2604'
    assert 'never an all-clear' in result['interpretation']
    assert 'satellite coverage' in result['coverage']
    assert KEY not in json.dumps(result) and 'example.invalid' not in json.dumps(result)


def test_nonempty_candidate_retains_geometry_without_guessing_units_time_or_private_fields():
    row = feature()
    original = copy.deepcopy(row)
    result = candidate.build_candidate(page([row]), NOW)
    assert row == original
    assert result['record_count'] == 1 and result['observed_at'] is None
    clean = result['records'][0]
    assert clean['geometry']['coordinates'] == row['geometry']['coordinates']
    assert set(clean['geometry']) == {'type', 'coordinates'}
    assert clean['properties'] is None and not {'f_area', '_createdAt'} & set(clean)
    assert KEY not in json.dumps(result) and '123456' not in json.dumps(result)
    assert 'geometry' not in json.dumps(candidate.receipt(result))


def test_partial_response_cannot_become_complete_empty_or_partial_candidate():
    for payload in (page([], matched=1), page([feature()], matched=2)):
        with pytest.raises(candidate.CandidateError, match='INCOMPLETE_QUERY_NOT_PUBLISHABLE'):
            candidate.build_candidate(payload, NOW)


@pytest.mark.parametrize('change', [
    {'numberMatched': True}, {'numberReturned': 101}, {'numberMatched': -1},
    {'timeStamp': '2026-10-27T14:00:00Z'}, {'timeStamp': KEY}, {'features': [KEY]},
])
def test_malformed_accounting_or_time_is_not_accepted(change):
    with pytest.raises(candidate.CandidateError, match='INVALID_COLLECTION_METADATA'):
        candidate.build_candidate({**page(), **change}, NOW)


def test_empty_collection_wrapped_in_provider_error_is_rejected():
    with pytest.raises(candidate.CandidateError, match='PROVIDER_ERROR_NOT_AN_OBSERVATION'):
        candidate.build_candidate({**page(), 'statusCode': 503, 'error': KEY}, NOW)


@pytest.mark.parametrize('change', [{'ap_idn': '2601'}, {'pv_idn': '10'}, {'ap_idn': 2604.0}])
def test_feature_outside_requested_admin_identity_cannot_be_accepted(change):
    row = feature()
    row['properties'].update(change)
    with pytest.raises(candidate.CandidateError, match='DISTRICT_IDENTITY_MISMATCH'):
        candidate.build_candidate(page([row]), NOW)


def test_coordinate_reference_null_invalid_and_overbudget_geometry_are_rejected(monkeypatch):
    with pytest.raises(candidate.CandidateError, match='UNVERIFIED_COORDINATE_REFERENCE'):
        candidate.build_candidate({**page(), 'crs': 'EPSG:3857'}, NOW)
    for geometry in (None, {'type': 'Point', 'coordinates': [101, 14]},
                     {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]}):
        row = feature()
        row['geometry'] = geometry
        with pytest.raises(candidate.CandidateError, match='INVALID_OR_UNVERIFIED_GEOMETRY'):
            candidate.build_candidate(page([row]), NOW)
    monkeypatch.setattr(candidate, 'MAX_POSITIONS', 3)
    with pytest.raises(candidate.CandidateError, match='CANDIDATE_GEOMETRY_LIMIT'):
        candidate.build_candidate(page([feature()]), NOW)


@pytest.mark.parametrize('status,reason', [(302, 'REDIRECT_REJECTED'), (401, 'AUTHENTICATION_OR_ENTITLEMENT_ERROR'),
    (403, 'AUTHENTICATION_OR_ENTITLEMENT_ERROR'), (404, 'NOT_FOUND_NOT_A_VERIFIED_EMPTY_COLLECTION'), (429, 'HTTP_ERROR')])
def test_http_errors_never_become_empty_observations(status, reason):
    with pytest.raises(candidate.CandidateError, match=reason):
        candidate.collect_candidate(KEY, get=lambda *a, **k: Response(page(), status))


def test_deadline_size_invalid_json_duplicate_keys_and_transport_are_bounded(monkeypatch):
    monkeypatch.setattr(candidate, 'MAX_BYTES', 10)
    with pytest.raises(candidate.CandidateError, match='RESPONSE_TOO_LARGE'):
        candidate.collect_candidate(KEY, get=lambda *a, **k: Response(page()))
    monkeypatch.setattr(candidate, 'MAX_BYTES', 2 * 1024 * 1024)
    ticks = iter([0, 46])
    with pytest.raises(candidate.CandidateError, match='DEADLINE_EXCEEDED'):
        candidate.collect_candidate(KEY, get=lambda *a, **k: Response(page()), clock=lambda: next(ticks))
    for raw in (b'not-json ' + KEY.encode(), b'{"type":"FeatureCollection","type":"error"}'):
        response = Response({})
        response.raw = raw
        with pytest.raises(candidate.CandidateError, match='INVALID_JSON'):
            candidate.collect_candidate(KEY, get=lambda *a, **k: response)
    def fail(*args, **kwargs):
        raise requests.ConnectionError(KEY)
    with pytest.raises(candidate.CandidateError, match='TRANSPORT_FAILURE') as error:
        candidate.collect_candidate(KEY, get=fail)
    assert KEY not in str(error.value)


def test_reviewed_request_cannot_change_endpoint_district_window_or_credentials(tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    monkeypatch.setattr(candidate, 'REQUEST_PATH', path)
    path.write_text('{"request_id":"2026-10-27-01"}', encoding='utf-8')
    assert candidate.reviewed_request_id() == '2026-10-27-01'
    for request in ({'request_id': KEY}, {'request_id': '2026-10-27-01', 'endpoint': 'https://example.invalid'},
                    {'request_id': '2026-10-27-01', 'window': '30days'}, {'request_id': '2026-10-27-01', 'api_key': KEY}):
        path.write_text(json.dumps(request), encoding='utf-8')
        with pytest.raises(ValueError): candidate.reviewed_request_id()


def test_cli_outputs_only_receipt_and_does_not_log_raw_feature_or_secret(monkeypatch, capsys):
    monkeypatch.setenv('GISTDA_API_KEY', KEY)
    result = candidate.build_candidate(page([feature()]), NOW)
    monkeypatch.setattr(candidate, 'collect_candidate', lambda key: result)
    candidate.main()
    output = capsys.readouterr().out
    assert json.loads(output)['status'] == 'CANDIDATE_VALIDATED'
    assert KEY not in output and 'coordinates' not in output and 'f_area' not in output
    def fail(key): raise ValueError(KEY)
    monkeypatch.setattr(candidate, 'collect_candidate', fail)
    with pytest.raises(SystemExit): candidate.main()
    assert KEY not in capsys.readouterr().out
