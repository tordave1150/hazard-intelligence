"""Value-free checks for one private GISTDA sample, never product acceptance.

RFC 7946 syntax/topology and pinned administrative identities can be checked
without publishing coordinates or guessing the provider's units and timestamps.
No geometry is repaired, reprojected, simplified, persisted or returned here.
"""
import math
import re

from shapely.geometry import shape

from pipelines.shared.locations import load_areas

MAX_POSITIONS = 20_000
MAX_RINGS = 256
AREAS = load_areas()
PROVINCES = {a['id'][5:] for a in AREAS if a['level'] == 'province'}
DISTRICTS = {a['id'][5:]: a['province_id'][5:] for a in AREAS if a['level'] == 'district'}
THAILAND_BBOX = next(a['bbox'] for a in AREAS if a['id'] == 'TH')


def _code(value, digits):
    # No float rounding, boolean coercion, prefix guessing or identifier logging.
    value = str(value) if type(value) is int else value
    return value if isinstance(value, str) and re.fullmatch(r'[0-9]{' + str(digits) + '}', value) else None


def administrative_quality(properties, requested_district=''):
    province = _code(properties.get('pv_idn'), 2)
    district = _code(properties.get('ap_idn'), 4)
    tambon = _code(properties.get('tb_idn'), 6)
    known_province = province in PROVINCES
    known_district = district in DISTRICTS
    return {
        'province': 'KNOWN_PINNED_CODE' if known_province else 'MISSING_OR_UNRECOGNIZED',
        'district': 'KNOWN_PINNED_CODE' if known_district else 'MISSING_OR_UNRECOGNIZED',
        'province_district_relationship': (
            'MATCH' if DISTRICTS[district] == province else 'MISMATCH'
        ) if known_province and known_district else 'UNVERIFIED',
        'requested_district': (
            'MATCH' if district == requested_district else 'MISMATCH'
        ) if requested_district and known_district else ('UNVERIFIED' if requested_district else 'NOT_REQUESTED'),
        'tambon_parent_prefix': (
            'MATCH_FORMAT_ONLY' if tambon[:4] == district else 'MISMATCH'
        ) if tambon and known_district else 'UNVERIFIED',
        'tambon_identity': 'NOT_VERIFIED',
        'registry_currency': 'Pinned DOPA directory 2023-09-01; later changes/legal boundaries unverified',
        'meaning': 'Property code consistency only; not spatial clipping or coverage verification',
    }


def geometry_quality(geometry, legacy_crs=False):
    result = {
        'status': 'UNVERIFIED',
        'geometry_type': 'UNSUPPORTED_OR_MISSING',
        'positions_checked': 0,
        'rings_checked': 0,
        'coordinate_interpretation': 'RFC 7946 longitude/latitude syntax test; provider CRS still unverified',
        'within_pinned_thailand_bbox': None,
        'spatial_accuracy': 'UNVERIFIED',
    }
    if geometry is None:
        return {**result, 'status': 'NULL_GEOMETRY'}
    if not isinstance(geometry, dict):
        return {**result, 'status': 'INVALID_GEOMETRY'}
    geometry_type = geometry.get('type')
    if geometry_type not in ('Polygon', 'MultiPolygon'):
        return {**result, 'status': 'UNSUPPORTED_GEOMETRY_TYPE'}
    result['geometry_type'] = geometry_type
    if legacy_crs or 'crs' in geometry:
        return {**result, 'status': 'LEGACY_CRS_REQUIRES_REVIEW'}
    coordinates = geometry.get('coordinates')
    if not isinstance(coordinates, list) or not coordinates:
        return {**result, 'status': 'INVALID_COORDINATE_STRUCTURE'}
    polygons = [coordinates] if geometry_type == 'Polygon' else coordinates
    within = True
    min_lon, min_lat, max_lon, max_lat = THAILAND_BBOX
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            return {**result, 'status': 'INVALID_COORDINATE_STRUCTURE'}
        for ring in polygon:
            result['rings_checked'] += 1
            if result['rings_checked'] > MAX_RINGS:
                return {**result, 'status': 'SAMPLE_COMPLEXITY_LIMIT'}
            if not isinstance(ring, list) or len(ring) < 4:
                return {**result, 'status': 'INVALID_LINEAR_RING'}
            result['positions_checked'] += len(ring)
            if result['positions_checked'] > MAX_POSITIONS:
                return {**result, 'status': 'SAMPLE_COMPLEXITY_LIMIT'}
            dimension = None
            for position in ring:
                if not isinstance(position, list) or len(position) not in (2, 3):
                    return {**result, 'status': 'INVALID_POSITION'}
                if any(not (type(n) is int or type(n) is float and math.isfinite(n)) for n in position):
                    return {**result, 'status': 'INVALID_POSITION'}
                if dimension is not None and dimension != len(position):
                    return {**result, 'status': 'MIXED_POSITION_DIMENSIONS'}
                dimension = len(position)
                lon, lat = position[:2]
                if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                    return {**result, 'status': 'OUT_OF_RANGE_LONGITUDE_LATITUDE'}
                within = within and min_lon <= lon <= max_lon and min_lat <= lat <= max_lat
            if ring[0] != ring[-1]:
                return {**result, 'status': 'UNCLOSED_LINEAR_RING'}
    # Do not expose GEOS exception messages or explain_validity coordinates.
    try:
        candidate = shape(geometry)
        valid = not candidate.is_empty and candidate.is_valid
    except Exception:
        valid = False
    return {**result, 'status': 'SYNTAX_AND_TOPOLOGY_VALID' if valid else 'INVALID_TOPOLOGY',
            'within_pinned_thailand_bbox': within}


def sample_quality(feature, requested_district='', legacy_crs=False):
    properties = feature['properties']
    return {
        'scope': 'One inspected feature only; no complete dataset or source acceptance',
        'geometry': geometry_quality(feature.get('geometry'), legacy_crs or 'crs' in feature),
        'administrative_codes': administrative_quality(properties, requested_district),
        'provider_metadata_presence': {field: properties.get(field) is not None for field in (
            '_createdAt', '_updatedAt', 'file_name', 'f_area', 'h3_area', '_area', 'rice_area')},
        'acquisition_time_status': 'UNVERIFIED',
        'area_units_status': 'UNVERIFIED',
        'empty_and_coverage_semantics': 'UNVERIFIED',
        'public_display_permission': 'UNVERIFIED',
        'public_layer_ready': False,
        'no_inference': 'No acquisition date from metadata/filename; no flood area, exposure counts or all-clear inferred',
    }
