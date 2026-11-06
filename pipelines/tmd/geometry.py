"""Validate source CAP polygons without closing, repairing or replacing them."""
import math
from shapely.geometry import Polygon


class CapDataError(ValueError):
    def __init__(self,reason):
        self.reason=reason
        self.document_id=None
        super().__init__(reason)


def inspect_polygons(source):
    if len(source)>1000:raise CapDataError('CAP_GEOMETRY_SIZE_LIMIT')
    polygons=[];issues=[];total=0
    for index,raw in enumerate(source):
        tokens=raw.split();total+=len(tokens)
        if len(tokens)>20000 or total>100000:raise CapDataError('CAP_GEOMETRY_SIZE_LIMIT')
        reason=None;ring=[]
        try:
            for token in tokens:
                pair=token.split(',')
                if len(pair)!=2:raise ValueError()
                lat,lon=map(float,pair)
                if not math.isfinite(lat) or not math.isfinite(lon):raise ValueError()
                ring.append([lon,lat])
            if len(ring)<4:reason='INVALID_COORDINATES'
            elif any(not(96<=lon<=107 and 5<=lat<=22) for lon,lat in ring):reason='OUTSIDE_ACCEPTED_BOUNDS'
            elif ring[0]!=ring[-1]:reason='UNCLOSED_RING'
            else:
                polygon=Polygon(ring)
                if not polygon.is_valid or polygon.area<=0:reason='INVALID_TOPOLOGY'
        except (ValueError,TypeError,OverflowError):reason='INVALID_COORDINATES'
        if reason:issues.append({'polygon_index':index,'reason':reason})
        polygons.append([ring])
    return polygons,issues


def checked_warning_geometry(row):
    quality=row.get('geometry_quality');source=row.get('source_polygons');issues=row.get('geometry_issues')
    if quality=='INVALID_PROVIDER_GEOMETRY':
        if row['geometry'] is not None or not source or not issues:raise CapDataError('CAP_GEOMETRY_QUALITY_MISMATCH')
        _,expected=inspect_polygons(source)
        if issues!=expected:raise CapDataError('CAP_GEOMETRY_QUALITY_MISMATCH')
        return
    if source is not None or issues is not None:raise CapDataError('CAP_GEOMETRY_QUALITY_MISMATCH')
    if quality is not None and quality!=('VALID' if row['geometry'] else 'NOT_SUPPLIED'):raise CapDataError('CAP_GEOMETRY_QUALITY_MISMATCH')
    if row['geometry']:
        total=0
        for rings in row['geometry']['coordinates']:
            ring=rings[0];total+=len(ring)
            if ring[0]!=ring[-1] or any(not(96<=lon<=107 and 5<=lat<=22) for lon,lat in ring):raise CapDataError('CAP_INVALID_RENDER_GEOMETRY')
            polygon=Polygon(ring)
            if not polygon.is_valid or polygon.area<=0:raise CapDataError('CAP_INVALID_RENDER_GEOMETRY')
        if total>100000:raise CapDataError('CAP_GEOMETRY_SIZE_LIMIT')
