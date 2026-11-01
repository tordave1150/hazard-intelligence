"""Derive display-only Thailand focus geometry from the pinned province display file."""
import hashlib
import json
from pathlib import Path

from shapely.geometry import Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'apps/web/public/data/provinces.geojson'
    data = json.loads(source.read_text(encoding='utf-8'))
    assert len(data['features']) == 77
    original = unary_union([shape(feature['geometry']) for feature in data['features']])
    assert original.is_valid and original.geom_type == 'MultiPolygon'
    # Interior seams are not foreign territory. This geometry is never used for
    # source membership, selecting an administrative area, or scientific metrics.
    land = unary_union([Polygon(part.exterior) for part in original.geoms])
    country = land.simplify(0.008, preserve_topology=True)
    assert country.is_valid and country.geom_type == 'MultiPolygon'
    relative_change = abs(country.area - land.area) / land.area
    assert relative_change < 0.002
    mask = orient(Polygon([(-180,-85),(180,-85),(180,85),(-180,85),(-180,-85)],
        [list(part.exterior.coords) for part in country.geoms]), sign=1)
    assert mask.is_valid
    result = {'type':'FeatureCollection','features':[
        {'type':'Feature','properties':{'role':'country'},'geometry':mapping(country)},
        {'type':'Feature','properties':{'role':'outside'},'geometry':mapping(mask)},
    ]}
    # Six decimal places exceed the precision needed for this low-zoom context.
    result = json.loads(json.dumps(result), parse_float=lambda value: round(float(value),6))
    assert all(shape(feature['geometry']).is_valid for feature in result['features'])
    target = ROOT / 'apps/web/public/data/thailand-context.geojson'
    target.write_text(json.dumps(result,separators=(',',':'))+'\n',encoding='utf-8')
    receipt = {'source':str(source.relative_to(ROOT)).replace('\\','/'),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'source_provinces':77,'simplification_degrees':0.008,'relative_area_change':relative_change,
        'output_bytes':target.stat().st_size,'role':'Display-only basemap focus; not legal geometry or a membership boundary',
        'attribution':'OpenGISData-Thailand / upstream DOPA; CC BY 4.0; existing boundary notices apply'}
    (ROOT / 'docs/map-context-geometry-2026-11-01.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
