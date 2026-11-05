"""Exact bounding-box index for original footprint chunks. No geometry resampling."""
import gzip,hashlib,math
from .encoding import binary_rows,checked_raw,unpacked,CURRENT_VERSION

SPATIAL_VERSION=1
SPATIAL_RAW_LIMIT=8192
SPATIAL_BUDGET_BYTES=32*1024*1024


def feature_bounds(row):
    west=south=math.inf;east=north=-math.inf
    stack=[row['geometry']['coordinates']]
    while stack:
        value=stack.pop()
        if isinstance(value[0],(int,float)):
            x,y=value[:2];west=min(west,x);east=max(east,x);south=min(south,y);north=max(north,y)
        else:stack.extend(value)
    box=[west,south,east,north]
    if not valid_box(box):raise ValueError('Invalid spatial bounds')
    return box


def valid_box(box):
    return isinstance(box,list) and len(box)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in box) and -180<=box[0]<=box[2]<=180 and -90<=box[1]<=box[3]<=90


def union(boxes):
    return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]


def build_spatial(rows):
    boxes=[feature_bounds(row) for row in rows];raw=binary_rows(boxes)
    if not boxes or len(boxes)>100 or len(raw)>SPATIAL_RAW_LIMIT:raise ValueError('Invalid spatial index size')
    packed=gzip.compress(raw,mtime=0)
    return {'bbox':union(boxes),'spatial_hash':hashlib.sha256(raw).hexdigest(),
            'spatial_raw_bytes':len(raw),'spatial_compressed_bytes':len(packed)},packed


def validate_spatial_descriptor(c):
    if not valid_box(c.get('bbox')) or not isinstance(c.get('spatial_hash'),str) or len(c['spatial_hash'])!=64 or any(v not in '0123456789abcdef' for v in c['spatial_hash']):raise ValueError('Invalid spatial descriptor')
    if any(type(c.get(k)) is not int or not 1<=c[k]<=SPATIAL_RAW_LIMIT for k in ['spatial_raw_bytes','spatial_compressed_bytes']):raise ValueError('Spatial byte limit exceeded')


def checked_spatial(c,data,rows=None):
    validate_spatial_descriptor(c)
    raw=checked_raw({'hash':c['spatial_hash'],'raw_bytes':c['spatial_raw_bytes'],'compressed_bytes':c['spatial_compressed_bytes']},data)
    boxes=unpacked(raw,CURRENT_VERSION)
    if not isinstance(boxes,list) or len(boxes)!=c['count'] or any(not valid_box(b) for b in boxes) or union(boxes)!=c['bbox']:raise ValueError('Invalid spatial accounting')
    if rows is not None and boxes!=[feature_bounds(row) for row in rows]:raise ValueError('Spatial index differs from original geometry')
    return boxes
