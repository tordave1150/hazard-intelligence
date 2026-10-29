import json
import re
from pathlib import Path
from datetime import timedelta
from shapely.geometry import Polygon
from pipelines.shared.time_units import instant

SOURCE='https://www.tmd.go.th/api/xml/CAP'
PRODUCT='cap_warnings'
KEY=f'tmd:{PRODUCT}'
MAX_ITEMS=50
MAX_DOCUMENT_BYTES=2*1024*1024
ROOT=Path(__file__).resolve().parents[2]
PROVINCES={r['id'] for r in json.loads((ROOT/'apps/web/data/areas.json').read_text(encoding='utf-8')) if r['level']=='province'}


def allowed_document(url):
    return bool(re.fullmatch(r'https://www\.tmd\.go\.th/uploads/CAP/CAPTMD[0-9A-Za-z_-]+\.xml',url))


def mapped_provinces(source_areas):
    """Keep canonical scope strict; original unsupported codes stay in source_areas."""
    return {'TH-P-'+code['value'][3:] for area in source_areas for code in area['geocodes']
            if code['value_name']=='ISO3166-2' and re.fullmatch(r'TH-[0-9]{2}',code['value'])
            and 'TH-P-'+code['value'][3:] in PROVINCES}


def warning_time_quality(row):
    if not row['effective_start'] or not row['expires_at']:
        return 'NOT_SUPPLIED'
    return ('INVALID_PROVIDER_INTERVAL' if instant(row['expires_at'])<=instant(row['effective_start'])
            else 'VALID_INTERVAL')


def check_warning(row):
    if not allowed_document(row['content_ref']) or row['content_ref'].rsplit('/CAP',1)[-1][:-4]!=row['warning_id']:
        raise ValueError('Unverified CAP document identity')
    if instant(row['issued_at'])>instant(row['fetched_at'])+timedelta(minutes=5):raise ValueError('Future CAP issue time')
    if instant(row['fetched_at'])>instant(row['ingested_at']):raise ValueError('Ingestion precedes retrieval')
    for ref in row['references']:
        if ref['sender']!='TMD' or instant(ref['issued_at'])>instant(row['issued_at']):raise ValueError('Invalid CAP reference')
    if row['message_type'] in ['Update','Cancel'] and not row['references']:raise ValueError('CAP update/cancel requires references')
    if row['message_type']!='Cancel' and any(row[k] is None for k in ['effective_start','event','headline','language','agency_severity','urgency','certainty']):
        raise ValueError('Missing CAP information')
    quality=warning_time_quality(row)
    if row.get('time_quality') is not None and row['time_quality']!=quality:
        raise ValueError('CAP time quality does not match original timestamps')
    if quality=='INVALID_PROVIDER_INTERVAL' and row.get('time_quality')!=quality:
        raise ValueError('Invalid CAP effective interval must be explicitly flagged')
    codes=mapped_provinces(row['source_areas'])
    if codes!=set(row['area_ids']) or not codes<=PROVINCES:raise ValueError('Unverified CAP province code')
    if row['geometry']:
        total=0
        for rings in row['geometry']['coordinates']:
            ring=rings[0];total+=len(ring)
            if ring[0]!=ring[-1] or any(not (96<=lon<=107 and 5<=lat<=22) for lon,lat in ring):raise ValueError('Invalid CAP WGS84 polygon')
            polygon=Polygon(ring)
            if not polygon.is_valid or polygon.area<=0:raise ValueError('Invalid CAP polygon topology')
        if total>100000:raise ValueError('CAP geometry exceeds product bound')


def check_feed(feed):
    rows=feed['records']
    if feed['feed_item_count']!=len(rows)+feed['ignored_item_count']:raise ValueError('Incomplete CAP feed')
    if len({r['warning_id'] for r in rows})!=len(rows):raise ValueError('Duplicate CAP identity')
    if instant(feed['feed_generated_at'])>instant(feed['fetched_at'])+timedelta(minutes=5):raise ValueError('Future CAP feed time')
    if instant(feed['fetched_at'])>instant(feed['ingested_at']):raise ValueError('Ingestion precedes retrieval')
    for row in rows:check_warning(row)
