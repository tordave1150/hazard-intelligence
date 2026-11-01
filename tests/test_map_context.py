"""The focus mask is derived context, not a replacement for canonical geography."""
import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]


def test_focus_input_remains_the_pinned_77_province_display_geometry():
    source = ROOT / 'apps/web/public/data/provinces.geojson'
    receipt = json.loads((ROOT / 'docs/map-context-geometry-2026-11-01.json').read_text())
    assert len(json.loads(source.read_text(encoding='utf-8'))['features']) == 77
    assert hashlib.sha256(source.read_bytes().replace(b'\r\n',b'\n')).hexdigest() == receipt['source_sha256']
    assert receipt['relative_area_change'] < 0.002


def test_context_shades_outside_and_preserves_thailand_interior():
    path = ROOT / 'apps/web/public/data/thailand-context.geojson'
    receipt = json.loads((ROOT / 'docs/map-context-geometry-2026-11-01.json').read_text())
    assert receipt['hash_encoding'] == 'UTF-8 with LF line endings'
    assert hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest() == receipt['output_sha256']
    data = json.loads(path.read_text())
    shapes = {feature['properties']['role']:shape(feature['geometry']) for feature in data['features']}
    assert set(shapes) == {'country','outside'}
    assert all(geometry.is_valid for geometry in shapes.values())
    assert shapes['country'].contains(Point(100.5018,13.7563))
    assert not shapes['outside'].contains(Point(100.5018,13.7563))
    assert shapes['outside'].contains(Point(105.85,21.03))
    assert shapes['country'].intersection(shapes['outside']).area < 1e-9
    assert path.stat().st_size < 200_000
