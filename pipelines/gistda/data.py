from copy import deepcopy
from datetime import timedelta
import hashlib
import json

from pipelines.shared.time_units import instant, utc_now
from scripts.gistda_candidate import ENDPOINT, AREA_ID, MAX_POSITIONS
from scripts.gistda_sample_quality import geometry_quality

PRODUCT = 'flood_1day_ongkharak'
KEY = 'gistda:' + PRODUCT
COLLECTION = 'satellite_flood_latest'
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


def normalize(candidate, ingested_at=None):
    if candidate.get('schema_version') != 'gistda-candidate/1':
        raise ValueError('Unexpected GISTDA candidate version')
    return {**deepcopy(candidate), 'schema_version':'2.0', 'snapshot_id':'latest',
            'data_state':'satellite_observation', 'ingested_at':ingested_at or utc_now()}


def check_feed(feed):
    if feed['record_count'] != len(feed['records']) or len({r['id'] for r in feed['records']}) != len(feed['records']):
        raise ValueError('Incomplete or duplicate GISTDA records')
    fetched, ingested, responded = (instant(feed[k]) for k in ('fetched_at','ingested_at','response_at'))
    if fetched > ingested or responded > fetched + timedelta(minutes=5):
        raise ValueError('Invalid GISTDA response/retrieval time')
    if feed['source_url'] != ENDPOINT or feed['area_id'] != AREA_ID:
        raise ValueError('Unexpected GISTDA product provenance')
    positions = 0
    for index, record in enumerate(feed['records']):
        geometry = record['geometry']
        quality = geometry_quality(geometry)
        if quality['status'] != 'SYNTAX_AND_TOPOLOGY_VALID' or not quality['within_pinned_thailand_bbox']:
            raise ValueError('Invalid GISTDA polygon')
        positions += quality['positions_checked']
        digest = hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if record['id'] != f'{digest[:24]}-{index}':
            raise ValueError('Invalid GISTDA feature identity')
    if positions > MAX_POSITIONS:
        raise ValueError('GISTDA geometry limit exceeded')
