"""Synthetic geometry fixtures only; no provider coordinates/values are stored."""
import copy
import json

import pytest

from scripts import gistda_sample_quality as quality
from scripts import probe_gistda_features as probe

KEY = 'test-only-gistda-private-key'
RING = [[101, 14], [101.01, 14], [101.01, 14.01], [101, 14.01], [101, 14]]


def feature():
    return {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [copy.deepcopy(RING)]},
            'properties': {'pv_idn': '26', 'ap_idn': '2604', 'tb_idn': '260401',
                           'file_name': KEY, '_createdAt': KEY, 'f_area': 12345}}


def test_valid_sample_checks_topology_and_known_parents_without_acceptance_or_values():
    row = feature()
    original = copy.deepcopy(row)
    result = quality.sample_quality(row, '2604')
    assert row == original  # No implicit geometry repair/normalization.
    assert result['geometry']['status'] == 'SYNTAX_AND_TOPOLOGY_VALID'
    assert result['geometry']['rings_checked'] == 1 and result['geometry']['positions_checked'] == 5
    assert result['geometry']['within_pinned_thailand_bbox'] is True
    assert result['administrative_codes']['province_district_relationship'] == 'MATCH'
    assert result['administrative_codes']['requested_district'] == 'MATCH'
    assert result['administrative_codes']['tambon_parent_prefix'] == 'MATCH_FORMAT_ONLY'
    assert result['administrative_codes']['tambon_identity'] == 'NOT_VERIFIED'
    assert result['provider_metadata_presence']['_createdAt'] is True
    assert result['provider_metadata_presence']['_updatedAt'] is False
    assert not result['public_layer_ready']
    assert result['public_display_permission'] == result['area_units_status'] == result['acquisition_time_status'] == 'UNVERIFIED'
    serialized = json.dumps(result)
    assert KEY not in serialized and '12345' not in serialized and '260401' not in serialized
    assert json.dumps(RING) not in serialized


def test_multipolygon_holes_and_clockwise_rings_remain_unchanged():
    row = feature()
    hole = [[101.002, 14.002], [101.004, 14.002], [101.004, 14.004], [101.002, 14.002]]
    row['geometry'] = {'type': 'MultiPolygon', 'coordinates': [[list(reversed(RING)), hole]]}
    original = copy.deepcopy(row)
    result = quality.sample_quality(row)
    assert result['geometry']['status'] == 'SYNTAX_AND_TOPOLOGY_VALID'
    assert result['geometry']['rings_checked'] == 2 and row == original


@pytest.mark.parametrize('geometry,status', [
    (None, 'NULL_GEOMETRY'),
    ([], 'INVALID_GEOMETRY'),
    ({'type': KEY, 'coordinates': []}, 'UNSUPPORTED_GEOMETRY_TYPE'),
    ({'type': 'Point', 'coordinates': [101, 14]}, 'UNSUPPORTED_GEOMETRY_TYPE'),
    ({'type': 'Polygon', 'coordinates': []}, 'INVALID_COORDINATE_STRUCTURE'),
    ({'type': 'MultiPolygon', 'coordinates': [[]]}, 'INVALID_COORDINATE_STRUCTURE'),
    ({'type': 'Polygon', 'coordinates': [[[101, 14]]]}, 'INVALID_LINEAR_RING'),
    ({'type': 'Polygon', 'coordinates': [[[101, 14], [102, 14], [101, 15], [102, 15]]]}, 'UNCLOSED_LINEAR_RING'),
    ({'type': 'Polygon', 'coordinates': [[[101, 14]] * 4]}, 'INVALID_TOPOLOGY'),
    ({'type': 'Polygon', 'coordinates': [[[101, 14], [102, 15], [102, 14], [101, 15], [101, 14]]]}, 'INVALID_TOPOLOGY'),
])
def test_unusable_geometry_has_fixed_value_free_reasons(geometry, status):
    result = quality.geometry_quality(geometry)
    assert result['status'] == status and KEY not in json.dumps(result)


@pytest.mark.parametrize('position,status', [
    ([True, 14], 'INVALID_POSITION'), ([101, float('nan')], 'INVALID_POSITION'),
    ([101, float('inf')], 'INVALID_POSITION'), ([101, KEY], 'INVALID_POSITION'),
    ([101], 'INVALID_POSITION'), ([101, 14, 0, 0], 'INVALID_POSITION'),
    ([1e10, 14], 'OUT_OF_RANGE_LONGITUDE_LATITUDE'),
    ([10**400, 14], 'OUT_OF_RANGE_LONGITUDE_LATITUDE'),
    ([14, 101], 'OUT_OF_RANGE_LONGITUDE_LATITUDE'),
    ([101, 14, 0], 'MIXED_POSITION_DIMENSIONS'),
])
def test_positions_reject_boolean_nonfinite_axis_swap_and_mixed_dimension(position, status):
    ring = copy.deepcopy(RING)
    ring[1] = position
    assert quality.geometry_quality({'type': 'Polygon', 'coordinates': [ring]})['status'] == status


def test_global_valid_geometry_outside_country_is_not_treated_as_thailand_coverage():
    result = quality.geometry_quality({'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]})
    assert result['status'] == 'SYNTAX_AND_TOPOLOGY_VALID'
    assert result['within_pinned_thailand_bbox'] is False
    assert result['spatial_accuracy'] == 'UNVERIFIED'


def test_complexity_and_legacy_crs_fail_before_topology(monkeypatch):
    def forbidden(*args):
        raise AssertionError('must not allocate a complex/unknown-CRS shape')
    monkeypatch.setattr(quality, 'shape', forbidden)
    monkeypatch.setattr(quality, 'MAX_POSITIONS', 4)
    row = feature()
    assert quality.sample_quality(row)['geometry']['status'] == 'SAMPLE_COMPLEXITY_LIMIT'
    assert quality.sample_quality(row, legacy_crs=True)['geometry']['status'] == 'LEGACY_CRS_REQUIRES_REVIEW'
    row['crs'] = KEY
    assert quality.sample_quality(row)['geometry']['status'] == 'LEGACY_CRS_REQUIRES_REVIEW'
    row.pop('crs')
    row['geometry']['crs'] = KEY
    assert quality.sample_quality(row)['geometry']['status'] == 'LEGACY_CRS_REQUIRES_REVIEW'
    row['geometry'].pop('crs')
    monkeypatch.setattr(quality, 'MAX_POSITIONS', 20_000)
    monkeypatch.setattr(quality, 'MAX_RINGS', 0)
    assert quality.sample_quality(row)['geometry']['status'] == 'SAMPLE_COMPLEXITY_LIMIT'


def test_topology_exceptions_do_not_escape_with_coordinates_or_secret(monkeypatch):
    def fail(*args):
        raise ValueError(KEY + ' 101.01 14.01')
    monkeypatch.setattr(quality, 'shape', fail)
    result = quality.sample_quality(feature())
    assert result['geometry']['status'] == 'INVALID_TOPOLOGY'
    assert KEY not in json.dumps(result) and '101.01' not in json.dumps(result)


@pytest.mark.parametrize('changes,field,status', [
    ({'pv_idn': '10'}, 'province_district_relationship', 'MISMATCH'),
    ({'ap_idn': '2601'}, 'requested_district', 'MISMATCH'),
    ({'tb_idn': '100101'}, 'tambon_parent_prefix', 'MISMATCH'),
    ({'ap_idn': 2604.0}, 'district', 'MISSING_OR_UNRECOGNIZED'),
    ({'pv_idn': True}, 'province', 'MISSING_OR_UNRECOGNIZED'),
    ({'ap_idn': KEY}, 'requested_district', 'UNVERIFIED'),
    ({'tb_idn': '260499'}, 'tambon_parent_prefix', 'MATCH_FORMAT_ONLY'),
])
def test_admin_consistency_never_guesses_or_certifies_tambon(changes, field, status):
    result = quality.administrative_quality({**feature()['properties'], **changes}, '2604')
    assert result[field] == status and result['tambon_identity'] == 'NOT_VERIFIED'
    assert KEY not in json.dumps(result)


def test_integer_admin_identifiers_match_without_float_or_bool_coercion():
    result = quality.administrative_quality({'pv_idn': 26, 'ap_idn': 2604, 'tb_idn': 260401}, '2604')
    assert result['province_district_relationship'] == result['requested_district'] == 'MATCH'


def test_real_client_reports_quality_for_one_page_only_without_returning_geometry():
    payload = {'type': 'FeatureCollection', 'features': [feature()], 'numberMatched': 184323,
               'numberReturned': 1, 'timeStamp': '2026-10-27T12:00:00Z',
               'links': [{'href': 'https://example.invalid/?api_key=' + KEY}]}
    class Response:
        status_code = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size): yield json.dumps(payload).encode()
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    report, code = probe.inspect_features(KEY, '30days', '', get=get)
    assert code == 0 and len(calls) == 1
    assert calls[0][1]['params'] == {'limit': 1, 'offset': 0}
    assert report['sample_quality']['geometry']['status'] == 'SYNTAX_AND_TOPOLOGY_VALID'
    assert not report['sample_quality']['public_layer_ready']
    assert not report['page_metadata']['complete_collection']
    assert report['product_window'] == '30days'
    serialized = json.dumps(report)
    assert KEY not in serialized and 'example.invalid' not in serialized and '12345' not in serialized
    assert '101.01' not in serialized
