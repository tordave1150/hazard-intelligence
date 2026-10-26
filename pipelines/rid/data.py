import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
METADATA=json.loads((ROOT/'apps/web/data/rid-dams.json').read_text(encoding='utf-8'))
DAMS={row['source_dam_id']:row for row in METADATA['dams']}
SOURCE='https://app.rid.go.th/reservoir/api/dam/public'
PRODUCT='daily_dam_storage'


def check_batch(records,expected_ids):
    expected=set(expected_ids)
    ids=[row['dam_id'] for row in records]
    if not expected or len(ids)!=len(set(ids)) or set(ids)!=expected:
        raise ValueError('Incomplete or duplicate RID dam coverage; last good snapshot retained')
    if len({row['report_date'] for row in records})!=1:
        raise ValueError('Mixed RID report dates; last good snapshot retained')
    return {'requested_locations':len(expected),'successful_locations':len(ids),'missing_locations':[],'completeness':1.0}
