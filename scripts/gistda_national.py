"""Complete, bounded nationwide 1day query; no district/bbox filter or window fallback.

Only canonical administrative references and validated geometry are retained.
Pagination checks counts and duplicates, but the provider supplies no snapshot token.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time

import requests

from scripts.gistda_candidate import CandidateError, ENDPOINT, _strict_object
from scripts.gistda_sample_quality import administrative_quality, geometry_quality
from scripts.probe_gistda_features import page_metadata

PRODUCT = 'flood_1day_thailand'
COLLECTION = 'satellite_flood_national_latest'
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_FEATURES = PAGE_SIZE * MAX_PAGES
MAX_BYTES = 4 * 1024 * 1024
MAX_POSITIONS = 100_000


def collect_national_candidate(api_key, get=None, clock=time.monotonic, now=None, *, three_day=False):
    api_key = api_key.strip()
    if not 8 <= len(api_key) <= 4096 or any(c in api_key for c in '\r\n') or api_key.lower().startswith(('http:', 'https:', 'gistda_api_key=')):
        raise CandidateError('INVALID_OR_MISSING_SECRET')
    from pipelines.gistda import limits
    product, window, endpoint = (limits.PRODUCT, limits.WINDOW, limits.ENDPOINT) if three_day else (PRODUCT, '1day', ENDPOINT)
    page_limit = limits.MAX_PAGES if three_day else MAX_PAGES
    feature_limit = limits.MAX_FEATURES if three_day else MAX_FEATURES
    byte_limit = limits.MAX_SOURCE_BYTES if three_day else MAX_BYTES
    position_limit = limits.MAX_POSITIONS if three_day else MAX_POSITIONS
    deadline = clock() + (limits.MAX_SECONDS if three_day else 120)
    records, seen, stamps = [], set(), []
    matched = None
    size = positions = 0
    fetched_at = None
    try:
        for page in range(page_limit):
            if clock() > deadline:
                raise CandidateError('DEADLINE_EXCEEDED')
            # No returned href is ever followed: it may contain a credential.
            with (get or requests.get)(endpoint, params={'limit': PAGE_SIZE, 'offset': len(records)},
                    headers={'Accept': 'application/json', 'API-Key': api_key},
                    timeout=(5, 25), allow_redirects=False, stream=True) as response:
                if 300 <= response.status_code < 400:
                    raise CandidateError('REDIRECT_REJECTED')
                if response.status_code in (401, 403):
                    raise CandidateError('AUTHENTICATION_OR_ENTITLEMENT_ERROR')
                if response.status_code == 404:
                    raise CandidateError('NOT_FOUND_NOT_A_VERIFIED_EMPTY_COLLECTION')
                if response.status_code != 200:
                    raise CandidateError('HTTP_ERROR')
                chunks = []
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > byte_limit:
                        raise CandidateError('RESPONSE_TOO_LARGE')
                    if clock() > deadline:
                        raise CandidateError('DEADLINE_EXCEEDED')
                    chunks.append(chunk)
                try:
                    def reject_constant(_): raise ValueError('Non-finite JSON')
                    payload = json.loads(b''.join(chunks).decode('utf-8-sig'),
                                         parse_constant=reject_constant, object_pairs_hook=_strict_object)
                except (ValueError, UnicodeDecodeError, RecursionError):
                    raise CandidateError('INVALID_JSON') from None
            fetched_at = now() if now else datetime.now(timezone.utc).isoformat()
            if isinstance(payload, dict) and (payload.get('error') or any(
                    type(payload.get(k)) is int and payload[k] >= 400 for k in ('status', 'statusCode', 'status_code'))):
                raise CandidateError('PROVIDER_ERROR_NOT_AN_OBSERVATION')
            try:
                meta = page_metadata(payload, limit=PAGE_SIZE)
                fetched = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                responded = datetime.fromisoformat(meta['response_timestamp'].replace('Z', '+00:00'))
                if fetched.tzinfo is None or fetched.utcoffset() != timedelta(0) or responded > fetched + timedelta(minutes=5):
                    raise ValueError('Invalid time')
            except (ValueError, TypeError, KeyError, OverflowError):
                raise CandidateError('INVALID_COLLECTION_METADATA') from None
            if matched is None:
                matched = meta['number_matched']
            if meta['number_matched'] != matched:
                raise CandidateError('PROVIDER_COUNT_CHANGED_DURING_PAGINATION')
            if matched > feature_limit:
                raise CandidateError('NATIONAL_FEATURE_BUDGET_EXCEEDED')
            if 'crs' in payload:
                raise CandidateError('UNVERIFIED_COORDINATE_REFERENCE')
            stamps.append(meta['response_timestamp'])
            for feature in payload['features']:
                props = feature['properties']
                admin = administrative_quality(props)
                if admin['province_district_relationship'] != 'MATCH':
                    raise CandidateError('ADMINISTRATIVE_IDENTITY_MISMATCH')
                quality = geometry_quality(feature.get('geometry'), 'crs' in feature)
                if quality['status'] != 'SYNTAX_AND_TOPOLOGY_VALID' or not quality['within_pinned_thailand_bbox']:
                    raise CandidateError('INVALID_OR_UNVERIFIED_GEOMETRY')
                positions += quality['positions_checked']
                if positions > position_limit:
                    raise CandidateError('CANDIDATE_GEOMETRY_LIMIT')
                geometry = {k: deepcopy(feature['geometry'][k]) for k in ('type', 'coordinates')}
                digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                area_ids = ['TH-P-' + str(props['pv_idn']), 'TH-D-' + str(props['ap_idn'])]
                identity = (digest, tuple(area_ids))
                if identity in seen:
                    raise CandidateError('DUPLICATE_OR_REPEATED_PROVIDER_FEATURE')
                seen.add(identity)
                records.append({'type': 'Feature', 'id': f'{digest[:24]}-{len(records)}',
                                'geometry': geometry, 'properties': None, 'area_ids': area_ids})
            if len(records) > matched:
                raise CandidateError('INVALID_COLLECTION_METADATA')
            if len(records) == matched:
                break
            if not payload['features']:
                raise CandidateError('INCOMPLETE_QUERY_NOT_PUBLISHABLE')
        else:
            raise CandidateError('INCOMPLETE_QUERY_NOT_PUBLISHABLE')
        result = {
            'schema_version': 'gistda-candidate/1', 'source_id': 'gistda',
            'product_id': product, 'product_window': window, 'area_id': 'TH',
            'query': {'limit': PAGE_SIZE, 'offset': 0}, 'page_count': len(stamps),
            'pagination_consistency': 'COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN',
            'source_url': endpoint, 'attribution': 'GISTDA Disaster Platform',
            'response_at': min(stamps, key=lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))),
            'fetched_at': fetched_at, 'observed_at': None, 'observation_time_status': 'NOT_SUPPLIED',
            'complete_provider_query': True, 'record_count': len(records), 'records': records,
            'coverage': f'Unfiltered provider {window} query; not a certification of nationwide satellite coverage or polygon clipping',
            'area_metrics': 'NOT_USED_UNITS_UNVERIFIED',
            'interpretation': 'Empty is no returned feature; never an all-clear, water depth or current flood severity',
        }
        if api_key in json.dumps(result, ensure_ascii=False):
            raise CandidateError('REFLECTED_CREDENTIAL_REJECTED')
        return result
    except requests.RequestException:
        raise CandidateError('TRANSPORT_FAILURE') from None
