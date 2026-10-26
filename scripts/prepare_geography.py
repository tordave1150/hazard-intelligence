"""Versioned, attributed geometry build; preserve raw inputs and split local LOD."""
import hashlib
import json
from pathlib import Path
import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'fafcea179cda88b689f5697c3866a449e79cd298'
BASE = f'https://raw.githubusercontent.com/chingchai/OpenGISData-Thailand/{REVISION}'
EXPECTED_SHA256 = {'provinces.geojson':'310c3adf5c3f5ce574e0ecbc4fadc5761f520d02050fcc3a6373fd9f22d011c0',
                   'districts.geojson':'329315c2d1ee067b42abc2fe2ac24e825fac4cdb02257a530afb62c6903de995'}
REGIONS = {'North': ('Northern', 'ภาคเหนือ'), 'Northeast': ('Northeastern', 'ภาคตะวันออกเฉียงเหนือ'),
           'Central': ('Central', 'ภาคกลาง'), 'East': ('Eastern','ภาคตะวันออก'),
           'West': ('Western','ภาคตะวันตก'), 'South': ('Southern','ภาคใต้')}


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',',':'),allow_nan=False),encoding='utf-8')


def main():
    raw = ROOT/'data/boundaries/raw'
    raw.mkdir(parents=True,exist_ok=True)
    checksums = {}
    inputs = {}
    for filename in ('provinces.geojson','districts.geojson'):
        path = raw/filename
        if not path.exists():
            response = requests.get(f'{BASE}/{filename}',timeout=90)
            response.raise_for_status()
            path.write_bytes(response.content)
        checksums[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksums[filename] != EXPECTED_SHA256[filename]:
            raise ValueError(f'Pinned boundary checksum mismatch: {filename}')
        inputs[filename] = json.loads(path.read_text(encoding='utf-8'))['features']
    out = ROOT/'apps/web/public/data'
    areas, geometries = [], {}
    report = {'source_revision':REVISION,'sha256':checksums,'invalid_rejected':[], 'maximum_area_change_fraction':0}
    def area(identifier, level, parent, name, name_th, geom, region_id=None, province_id=None):
        point = geom.representative_point()
        a = {'id':identifier,'level':level,'parent_id':parent,'name':name,'name_th':name_th,
             'region_id':region_id,'province_id':province_id,'lat':round(point.y,6),'lon':round(point.x,6),
             'bbox':[round(n,6) for n in geom.bounds], 'geometry_ref':'/data/provinces.geojson' if level=='province' else
             f'/data/districts/{province_id}.geojson' if level=='district' else '/data/regions.geojson',
             'code_status':'DOPA codes as published by OpenGISData-Thailand; independent current registry audit pending' if level in ('province','district') else 'Project region classification: upstream reg_royin, pinned 2026-10-18'}
        areas.append(a)
        geometries[identifier] = geom
        return a
    def feature(a, tolerance):
        original = geometries[a['id']]
        simplified = original.simplify(tolerance, preserve_topology=True)
        if not simplified.is_valid or simplified.is_empty:
            raise ValueError('Invalid simplified geometry')
        difference = abs(simplified.area-original.area)/original.area
        if difference > .03:
            simplified=original
            difference=0
        report['maximum_area_change_fraction'] = max(report['maximum_area_change_fraction'],difference)
        return {'type':'Feature','id':a['id'],'properties':{k:a[k] for k in ('id','level','name','name_th','parent_id','region_id','province_id')},'geometry':mapping(simplified)}
    for raw_feature in inputs['provinces.geojson']:
        p=raw_feature['properties']; geom=shape(raw_feature['geometry'])
        if not geom.is_valid: raise ValueError(f"Invalid province: {p['pro_code']}")
        region_id=f"TH-R-{p['reg_royin'].upper()}"
        area(f"TH-P-{p['pro_code']}",'province',region_id,p['pro_en'],p['pro_th'],geom,region_id,f"TH-P-{p['pro_code']}")
    provinces=list(areas)
    for name,(english,thai) in REGIONS.items():
        identifier=f'TH-R-{name.upper()}'
        members=[geometries[a['id']] for a in provinces if a['region_id']==identifier]
        if not members: raise ValueError(f'Unknown region classification: {name}')
        area(identifier,'region','TH',english,thai,unary_union(members),identifier)
    regions=[a for a in areas if a['level']=='region']
    area('TH','national',None,'Thailand','ประเทศไทย',unary_union([geometries[a['id']] for a in provinces]))
    for raw_feature in inputs['districts.geojson']:
        p=raw_feature['properties']; geom=shape(raw_feature['geometry'])
        if not geom.is_valid: raise ValueError(f"Invalid district: {p['amp_code']}")
        province_id=f"TH-P-{p['pro_code']}"
        area(f"TH-D-{p['amp_code']}",'district',province_id,p['amp_en'],p['amp_th'],geom,f"TH-R-{p['reg_royin'].upper()}",province_id)
    if len(provinces)!=77 or sum(a['level']=='district' for a in areas)!=928 or len({a['id'] for a in areas})!=len(areas):
        raise ValueError('Unexpected geography counts or duplicate canonical IDs')
    for name,selection,tolerance in [('provinces',provinces,.003),('regions',regions,.006)]:
        write(out/f'{name}.geojson',{'type':'FeatureCollection','features':[feature(a,tolerance) for a in selection]})
    for province in provinces:
        districts=[a for a in areas if a['level']=='district' and a['province_id']==province['id']]
        write(out/'districts'/f"{province['id']}.geojson",{'type':'FeatureCollection','features':[feature(a,.001) for a in districts]})
    write(ROOT/'apps/web/data/areas.json', sorted(areas,key=lambda a:a['id']))
    report.update(provinces=77,districts=928,regions=len(regions),total_areas=len(areas),
                  attribution='Administrative boundaries: chingchai/OpenGISData-Thailand (DOPA attribution), CC BY 4.0; simplified for display',
                  limitations='Display boundaries; not a legal survey. Geometry codes verified for uniqueness and parent integrity; current DOPA registry audit remains a release check.')
    write(ROOT/'docs/geography-build-report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
