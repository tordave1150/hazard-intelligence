"""Build display boundaries and conservative point membership from a reviewed DDPM response."""
import argparse,hashlib,json
from pathlib import Path
from shapely import make_valid
from shapely.geometry import shape,mapping,Point
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://gis-portal.disaster.go.th/arcgis/rest/services/MapDX/DPM_TH_Hydrology/MapServer/6'
def polygons(g):
    if g.geom_type=='Polygon':return [g]
    return [p for part in getattr(g,'geoms',[]) for p in polygons(part)]
def write(path,value):
    (ROOT/path).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-file',type=Path,required=True);args=parser.parse_args()
    raw_bytes=args.source_file.read_bytes();raw=json.loads(raw_bytes);meta=[];visual=[];cores=[];repairs=[]
    if raw.get('exceededTransferLimit') or len(raw.get('features',[]))!=22:raise ValueError('Incomplete basin source')
    for f in raw['features']:
        p=f['properties'];original=shape(f['geometry']);g=unary_union(polygons(make_valid(original)))
        delta=abs(g.area-original.area)/original.area
        if not g.is_valid or g.is_empty or delta>1e-6:raise ValueError('Unacceptable basin topology change')
        if not original.is_valid:repairs.append({'code':p['รหัสลุ่มน้ำ'],'relative_area_change':delta})
        code=p['รหัสลุ่มน้ำ'];identity='TH-B-'+code;center=g.representative_point()
        if len(code)!=2 or not code.isdigit():raise ValueError('Invalid basin code')
        props={'id':identity,'name':p['ชื่อลุ่มน้ำ_En_'],'name_th':p['ชื่อลุ่มน้ำ']}
        # Interior-only association avoids assigning points near simplified/coastal borders.
        core=g.simplify(.0002,preserve_topology=True).buffer(-.0005).simplify(.0001,preserve_topology=True)
        if not core.is_valid or core.is_empty:raise ValueError('Invalid basin membership core')
        if core.difference(g).area>1e-8:raise ValueError('Membership core extends outside source boundary')
        meta.append({'id':identity,'level':'basin','parent_id':'TH','name':props['name'],'name_th':props['name_th'],
            'region_id':None,'province_id':None,'lat':center.y,'lon':center.x,'bbox':list(g.bounds),
            'geometry_ref':'/data/basins.geojson','code_status':'DDPM_22_BASINS_SOURCE_CODE'})
        visual.append({'type':'Feature','properties':props,'geometry':mapping(g.simplify(.002,preserve_topology=True))})
        cores.append({'type':'Feature','properties':{'id':identity,'bbox':list(core.bounds)},'geometry':mapping(core)})
    if len({a['id'] for a in meta})!=22:raise ValueError('Duplicate basin identity')
    write('apps/web/data/basins.json',meta)
    write('apps/web/public/data/basins.geojson',{'type':'FeatureCollection','features':visual})
    write('apps/web/data/basin-membership-cores.json',{'type':'FeatureCollection','features':cores})
    dams=json.loads((ROOT/'apps/web/data/rid-dams.json').read_text(encoding='utf-8'))['dams'];matches={}
    for dam in dams:
        point=Point(dam['point']['lon'],dam['point']['lat'])
        hits=[f['properties']['id'] for f in cores if shape(f['geometry']).contains(point)]
        matches[dam['dam_id']]=hits[0] if len(hits)==1 else None
    write('apps/web/data/dam-basin-membership.json',matches)
    receipt={'source_url':SOURCE,'source_sha256':hashlib.sha256(raw_bytes).hexdigest(),'source_crs':'EPSG:4326','basin_count':22,
        'source_publisher':'DDPM GIS Portal','catalog_reference':'https://gdcatalog.go.th/th/dataset/gdpublish-dataset-32-0113',
        'license':'Not specified by the reviewed catalog; no unrestricted license claimed','topology_repairs':repairs,
        'display_simplification_degrees':.002,'membership_simplification_degrees':.0002,'membership_inward_buffer_degrees':.0005,
        'interpretation':'Conservative point-to-basin context. Border/coastal/unmatched points stay unassigned. No river-network or upstream/downstream connectivity inferred.',
        'dam_count':len(dams),'dams_with_confirmed_interior_match':sum(x is not None for x in matches.values())}
    write('docs/basin-context-source-2026-10-30.json',receipt)
    print(json.dumps({'basins':22,'matched_dams':receipt['dams_with_confirmed_interior_match'],'topology_repairs':len(repairs)}))
if __name__=='__main__':main()
