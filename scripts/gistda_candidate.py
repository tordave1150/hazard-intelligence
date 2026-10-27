"""Build one complete, bounded Ongkharak daily candidate in memory.

No database, raw export, polling, map publication or agency-contact requirement.
Unknown acquisition time/area units remain unknown. CLI emits a receipt only.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

import requests

from scripts.gistda_sample_quality import administrative_quality, geometry_quality
from scripts.probe_gistda_features import page_metadata

ENDPOINT = 'https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/1day'
AREA_ID = 'TH-D-2604'
DISTRICT = '2604'
MAX_FEATURES = 100
MAX_BYTES = 2 * 1024 * 1024
MAX_POSITIONS = 20_000
REQUEST_PATH = Path(__file__).resolve().parents[1] / '.github/gistda-candidate-request.json'


class CandidateError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def build_candidate(payload, fetched_at):
    """Use only geometry and checked query metadata, not unknown business fields."""
    if isinstance(payload, dict) and (payload.get('error') or any(
            type(payload.get(key)) is int and payload[key] >= 400
            for key in ('status', 'statusCode', 'status_code'))):
        raise CandidateError('PROVIDER_ERROR_NOT_AN_OBSERVATION')
    try:
        meta = page_metadata(payload, limit=MAX_FEATURES)
        fetched = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
        responded = datetime.fromisoformat(meta['response_timestamp'].replace('Z', '+00:00'))
        if fetched.tzinfo is None or fetched.utcoffset() != timedelta(0):
            raise ValueError('Retrieval time must be UTC')
        if responded > fetched + timedelta(minutes=5):
            raise ValueError('Future provider response time')
    except (ValueError, TypeError, KeyError, OverflowError):
        raise CandidateError('INVALID_COLLECTION_METADATA') from None
    if not meta['complete_collection']:
        raise CandidateError('INCOMPLETE_QUERY_NOT_PUBLISHABLE')
    if 'crs' in payload:
        raise CandidateError('UNVERIFIED_COORDINATE_REFERENCE')
    records = []
    positions = 0
    for index, feature in enumerate(payload['features']):
        admin = administrative_quality(feature['properties'], DISTRICT)
        if admin['province_district_relationship'] != 'MATCH' or admin['requested_district'] != 'MATCH':
            raise CandidateError('DISTRICT_IDENTITY_MISMATCH')
        quality = geometry_quality(feature.get('geometry'), 'crs' in feature)
        if quality['status'] != 'SYNTAX_AND_TOPOLOGY_VALID' or not quality['within_pinned_thailand_bbox']:
            raise CandidateError('INVALID_OR_UNVERIFIED_GEOMETRY')
        positions += quality['positions_checked']
        if positions > MAX_POSITIONS:
            raise CandidateError('CANDIDATE_GEOMETRY_LIMIT')
        geometry = {key: deepcopy(feature['geometry'][key]) for key in ('type', 'coordinates')}
        digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        records.append({'type': 'Feature', 'id': f'{digest[:24]}-{index}', 'geometry': geometry})
    return {
        'schema_version': 'gistda-candidate/1', 'source_id': 'gistda',
        'product_id': 'flood_1day_ongkharak', 'product_window': '1day', 'area_id': AREA_ID,
        'query': {'ap_idn': DISTRICT, 'limit': MAX_FEATURES, 'offset': 0},
        'source_url': ENDPOINT, 'attribution': 'GISTDA Disaster Platform',
        'response_at': meta['response_timestamp'], 'fetched_at': fetched_at,
        'observed_at': None, 'observation_time_status': 'NOT_SUPPLIED',
        'complete_provider_query': True, 'record_count': len(records), 'records': records,
        'coverage': 'Provider district query only; satellite coverage and clipping not independently verified',
        'area_metrics': 'NOT_USED_UNITS_UNVERIFIED',
        'interpretation': 'Empty is no returned feature; never an all-clear, water depth or current flood severity',
    }


def collect_candidate(api_key, get=None, clock=time.monotonic, now=None):
    api_key = api_key.strip()
    if not 8 <= len(api_key) <= 4096 or any(c in api_key for c in '\r\n') or api_key.lower().startswith(('http:', 'https:', 'gistda_api_key=')):
        raise CandidateError('INVALID_OR_MISSING_SECRET')
    deadline = clock() + 45
    try:
        with (get or requests.get)(ENDPOINT, params={'limit': MAX_FEATURES, 'offset': 0, 'ap_idn': DISTRICT},
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
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
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
            candidate = build_candidate(payload, fetched_at)
            # Returned links and properties can echo keys; none are included in
            # the candidate. Reject even an unexpected reflected key in metadata.
            if api_key in json.dumps(candidate, ensure_ascii=False):
                raise CandidateError('REFLECTED_CREDENTIAL_REJECTED')
            return candidate
    except requests.RequestException:
        raise CandidateError('TRANSPORT_FAILURE') from None


def receipt(candidate):
    return {key: candidate[key] for key in (
        'schema_version', 'source_id', 'product_id', 'product_window', 'area_id',
        'response_at', 'fetched_at', 'observed_at', 'observation_time_status',
        'complete_provider_query', 'record_count', 'coverage', 'area_metrics', 'interpretation')}


def reviewed_request_id():
    if REQUEST_PATH.stat().st_size > 1024:
        raise ValueError('Request file too large')
    request = json.loads(REQUEST_PATH.read_text(encoding='utf-8'))
    if not isinstance(request, dict) or set(request) != {'request_id'} or not isinstance(request['request_id'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{2}', request['request_id']):
        raise ValueError('Invalid fixed-scope request')
    return request['request_id']


def main(reviewed=False):
    try:
        request_id = reviewed_request_id() if reviewed else None
        candidate = collect_candidate(os.getenv('GISTDA_API_KEY', ''))
        report = {'status': 'CANDIDATE_VALIDATED' if candidate['records'] else 'CANDIDATE_VALIDATED_EMPTY',
                  **receipt(candidate)}
        if request_id: report['reviewed_request_id'] = request_id
        print(json.dumps(report, ensure_ascii=True, allow_nan=False))
    except Exception as error:
        reason = error.reason if isinstance(error, CandidateError) else 'CANDIDATE_FAILED'
        print(json.dumps({'source_id': 'gistda', 'status': 'FAILED', 'reason': reason}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-request', action='store_true')
    main(parser.parse_args().reviewed_request)
