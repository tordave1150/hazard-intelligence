"""Freeze only public RID map identity/coordinates; scheduled ETL uses documented GET.

Input is a saved response from the RID reservoir map's published api/dams query.
No website scripts, API keys, live observations or contact details are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
from shapely.geometry import Point, shape

ROOT=Path(__file__).resolve().parents[1]


def walk(value):
    if isinstance(value,dict):
        if 'DAM_ID' in value:
            yield value
        else:
            for item in value.values():
                yield from walk(item)
    elif isinstance(value,list):
        for item in value:
            yield from walk(item)


def build(path):
    raw=path.read_bytes()
    rows=list(walk(json.loads(raw)))
    areas={a['id']:a for a in json.loads((ROOT/'apps/web/data/areas.json').read_text(encoding='utf-8'))}
    provinces=json.loads((ROOT/'apps/web/public/data/provinces.geojson').read_text(encoding='utf-8'))['features']
    province_shapes=[(f['properties']['id'],shape(f['geometry'])) for f in provinces]
    district_shapes={}
    output=[]
    for row in sorted(rows,key=lambda r:r['DAM_ID']):
        point=Point(float(row['DAM_Lon']),float(row['DAM_Lat']))
        candidates=[pid for pid,polygon in province_shapes if polygon.covers(point)]
        if len(candidates)!=1:
            raise ValueError('RID point must have one verified province association')
        province=areas[candidates[0]]
        if province['id'] not in district_shapes:
            features=json.loads((ROOT/f"apps/web/public/data/districts/{province['id']}.geojson").read_text(encoding='utf-8'))['features']
            district_shapes[province['id']]=[(f['properties']['id'],shape(f['geometry'])) for f in features]
        districts=[did for did,polygon in district_shapes[province['id']] if polygon.covers(point)]
        output.append({'dam_id':f"RID-DAM-{row['DAM_ID']}", 'source_dam_id':row['DAM_ID'],
            'name_th':row['DAM_Name'].strip(), 'point':{'lat':point.y,'lon':point.x},
            'province_id':province['id'], 'district_id':districts[0] if len(districts)==1 else None,
            'region_id':province['region_id']})
    if len(output)!=35 or len({d['dam_id'] for d in output})!=35:
        raise ValueError('Expected the 35 unique documented large-dam identities')
    return {'metadata_version':'2026-10-26','source_page':'https://app.rid.go.th/reservoir/rsvmiddle',
        'catalog_url':'https://data.go.th/th/dataset/reservoir2',
        'license_url':'https://data.go.th/th/pages/dga-open-government-license',
        'source_response_sha256':hashlib.sha256(raw).hexdigest(),
        'coordinate_method':'Coordinates published by RID reservoir map; canonical areas joined by point-in-polygon, without moving points.',
        'dams':output}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    target=ROOT/'apps/web/data/rid-dams.json'
    target.write_text(json.dumps(build(args.input),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'metadata_records':35,'target':target.relative_to(ROOT).as_posix()}))
