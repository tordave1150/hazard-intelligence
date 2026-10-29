from copy import deepcopy
from datetime import timedelta
import hashlib
import json

from pipelines.shared.time_units import instant, utc_now
from scripts.gistda_common import ENDPOINT
from scripts.gistda_sample_quality import geometry_quality

# Read-only compatibility for already-stored retired district envelopes. These
# identities are never used to select a current collection or publication scope.
AREA_ID = 'TH-D-2604'
MAX_POSITIONS = 20_000
PRODUCT = 'flood_1day_ongkharak'
KEY = 'gistda:' + PRODUCT
COLLECTION = 'satellite_flood_latest'
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


def normalize(candidate, ingested_at=None):
    if candidate.get('schema_version') != 'gistda-candidate/1':
        raise ValueError('Unexpected GISTDA candidate version')
    return {**deepcopy(candidate), 'schema_version':'2.0', 'snapshot_id':'latest',
            'data_state':'satellite_observation', 'ingested_at':ingested_at or utc_now()}


def check_feed(feed, national=False):
    if feed['record_count'] != len(feed['records']) or len({r['id'] for r in feed['records']}) != len(feed['records']):
        raise ValueError('Incomplete or duplicate GISTDA records')
    fetched, ingested, responded = (instant(feed[k]) for k in ('fetched_at','ingested_at','response_at'))
    if fetched > ingested or responded > fetched + timedelta(minutes=5):
        raise ValueError('Invalid GISTDA response/retrieval time')
    from . import limits
    three_day = feed['product_id'] == limits.PRODUCT
    if feed['source_url'] != (limits.ENDPOINT if three_day else ENDPOINT) or feed['area_id'] != ('TH' if national else AREA_ID):
        raise ValueError('Unexpected GISTDA product provenance')
    positions = 0
    for index, record in enumerate(feed['records']):
        if national:
            from scripts.gistda_sample_quality import DISTRICTS
            province, district = record['area_ids']
            if DISTRICTS.get(district[5:]) != province[5:]:
                raise ValueError('Invalid GISTDA administrative hierarchy')
        geometry = record['geometry']
        quality = geometry_quality(geometry)
        if quality['status'] != 'SYNTAX_AND_TOPOLOGY_VALID' or not quality['within_pinned_thailand_bbox']:
            raise ValueError('Invalid GISTDA polygon')
        positions += quality['positions_checked']
        digest = hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if record['id'] != f'{digest[:24]}-{index}':
            raise ValueError('Invalid GISTDA feature identity')
    if national:
        from scripts.gistda_national import MAX_POSITIONS as position_limit, PAGE_SIZE
        if not (feed['page_count'] == 1 if not feed['record_count'] else
                feed['page_count'] <= feed['record_count'] <= feed['page_count'] * PAGE_SIZE):
            raise ValueError('Invalid GISTDA page accounting')
    else:
        position_limit = MAX_POSITIONS
    if three_day:
        position_limit = limits.MAX_POSITIONS
    if positions > position_limit:
        raise ValueError('GISTDA geometry limit exceeded')
