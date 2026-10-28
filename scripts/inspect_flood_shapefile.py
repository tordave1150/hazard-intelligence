"""Read-only, bounded local ZIP inspection. Never extracts or publishes geometry.

Optional dependencies: pip install -r scripts/requirements-shapefile.txt
Reports contain technical metadata/counts, not raw attribute values or URLs.
"""
import argparse
from collections import Counter
import hashlib
import html
from io import BytesIO
from itertools import zip_longest
import json
import logging
import math
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import time
import zipfile

MAX_BYTES = 256 * 1024 * 1024
MAX_ENTRIES = 128
MAX_RECORDS = 100_000
MAX_POSITIONS = 5_000_000


class InspectionError(ValueError):
    pass


def _members(path):
    if path.stat().st_size > MAX_BYTES: raise InspectionError('ARCHIVE_SIZE_LIMIT')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES: raise InspectionError('ARCHIVE_ENTRY_LIMIT')
        names, total = set(), 0
        for entry in entries:
            name = entry.filename
            member = PurePosixPath(name)
            if '\\' in name or ':' in name or member.is_absolute() or '..' in member.parts or '\x00' in name:
                raise InspectionError('UNSAFE_ARCHIVE_PATH')
            if name.casefold() in names: raise InspectionError('DUPLICATE_ARCHIVE_MEMBER')
            names.add(name.casefold())
            if stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1:
                raise InspectionError('UNSUPPORTED_ARCHIVE_MEMBER')
            total += entry.file_size
            if total > MAX_BYTES or entry.file_size > max(1, entry.compress_size) * 200:
                raise InspectionError('DECOMPRESSION_LIMIT')
        return {entry.filename: archive.read(entry) for entry in entries if not entry.is_dir()}


def _pairing(parts):
    shapes = [name for name in parts if name.lower().endswith('.shp')]
    if len(shapes) != 1: raise InspectionError('EXPECTED_ONE_SHAPEFILE')
    stem = shapes[0][:-4]
    lookup = {name.casefold(): name for name in parts}
    required = {}
    for extension in ('shp', 'shx', 'dbf', 'prj'):
        name = lookup.get((stem + '.' + extension).casefold())
        if name is None: raise InspectionError('MISSING_REQUIRED_COMPONENT')
        required[extension] = parts[name]
    shp, shx = required['shp'], required['shx']
    if len(shp) < 100 or len(shx) < 100 or (len(shx) - 100) % 8:
        raise InspectionError('INVALID_SHAPE_INDEX')
    if any(struct.unpack('>i', data[:4])[0] != 9994 or struct.unpack('<i', data[28:32])[0] != 1000 for data in (shp, shx)) or shp[32:36] != shx[32:36]:
        raise InspectionError('INVALID_SHAPE_HEADER')
    if struct.unpack('>i', shp[24:28])[0] * 2 != len(shp) or struct.unpack('>i', shx[24:28])[0] * 2 != len(shx):
        raise InspectionError('SHAPE_FILE_LENGTH_MISMATCH')
    count = (len(shx) - 100) // 8
    if not 0 < count <= MAX_RECORDS: raise InspectionError('RECORD_COUNT_LIMIT')
    offset = 100
    for index in range(count):
        position, words = struct.unpack('>ii', shx[100 + index * 8:108 + index * 8])
        if position * 2 != offset or words < 2 or offset + 8 + words * 2 > len(shp):
            raise InspectionError('SHAPE_INDEX_MISMATCH')
        number, actual = struct.unpack('>ii', shp[offset:offset + 8])
        if number != index + 1 or actual != words: raise InspectionError('SHAPE_RECORD_MISMATCH')
        offset += 8 + words * 2
    if offset != len(shp): raise InspectionError('UNINDEXED_SHAPE_RECORDS')
    cpg = parts.get(lookup.get((stem + '.cpg').casefold(), ''), b'UTF-8').decode('ascii').strip().upper()
    encodings = {'UTF-8': 'utf-8', 'UTF8': 'utf-8', '65001': 'utf-8', '874': 'cp874', 'CP874': 'cp874',
                 'WINDOWS-874': 'cp874', 'TIS-620': 'tis-620', '1252': 'cp1252', 'WINDOWS-1252': 'cp1252'}
    if cpg not in encodings: raise InspectionError('UNSUPPORTED_DBF_ENCODING')
    return required, count, encodings[cpg]


def inspect(path, clock=time.monotonic):
    import shapefile
    import shapely
    import pyproj
    from pyproj import CRS
    from shapely.geometry import shape
    from shapely.validation import explain_validity
    from scripts.gistda_sample_quality import administrative_quality, _code
    deadline = clock() + 120
    parts = _members(Path(path))
    components, expected, encoding = _pairing(parts)
    try:
        crs = CRS.from_wkt(components['prj'].decode('utf-8-sig'))
    except Exception:
        raise InspectionError('INVALID_OR_UNKNOWN_CRS') from None
    reader = shapefile.Reader(shp=BytesIO(components['shp']), shx=BytesIO(components['shx']),
                              dbf=BytesIO(components['dbf']), encoding=encoding, encodingErrors='strict')
    if reader.numRecords != expected: raise InspectionError('DBF_SHAPE_COUNT_MISMATCH')
    fields = reader.fields[1:]
    if len(fields) > 256: raise InspectionError('DBF_FIELD_LIMIT')
    names = [field[0] for field in fields]
    if len({name.casefold() for name in names}) != len(names): raise InspectionError('DUPLICATE_DBF_FIELD')
    profiles = {name: {'nulls': 0, 'zeros': 0} for name in names}
    types, admin, seen = Counter(), Counter(), set()
    invalid_reasons, tambon_prefixes = Counter(), Counter()
    unique_codes = {'province': set(), 'district': set(), 'tambon': set()}
    count = positions = invalid = empty = duplicates = nonfinite = 0
    area_tested = area_matches = 0
    coordinate_conflict = False
    lower = {name.casefold(): name for name in names}
    def field(values, candidates):
        for candidate in candidates:
            if candidate in lower: return values[lower[candidate]]
        return None
    # pyshp may warn about ring orientation; no provider values are sent to logs.
    logger = logging.getLogger('shapefile'); was_disabled = logger.disabled; logger.disabled = True
    try:
        for geometry, record in zip_longest(reader.iterShapes(), reader.iterRecords()):
            if clock() > deadline: raise InspectionError('INSPECTION_DEADLINE')
            if geometry is None or record is None: raise InspectionError('SHAPE_DBF_ITERATION_MISMATCH')
            count += 1
            if count > expected: raise InspectionError('RECORD_COUNT_MISMATCH')
            if geometry.shapeType not in (0, 5, 15, 25): raise InspectionError('UNSUPPORTED_NONPOLYGON_GEOMETRY')
            types[geometry.shapeTypeName] += 1
            n = len(geometry.points); positions += n
            if positions > MAX_POSITIONS or n > 200_000: raise InspectionError('GEOMETRY_COMPLEXITY_LIMIT')
            values = dict(zip(names, record))
            for name, value in values.items():
                profiles[name]['nulls'] += value is None
                profiles[name]['zeros'] += isinstance(value, (int, float)) and value == 0
            identities = {'pv_idn': field(values, ('pv_idn', 'prov_code', 'p_code')),
                          'ap_idn': field(values, ('ap_idn', 'amp_code', 'a_code')),
                          'tb_idn': field(values, ('tb_idn', 'tam_code', 't_code'))}
            quality = administrative_quality(identities)
            admin[quality['province_district_relationship']] += 1
            tambon_prefixes[quality['tambon_parent_prefix']] += 1
            for label, name, digits in [('province','pv_idn',2),('district','ap_idn',4),('tambon','tb_idn',6)]:
                code = _code(identities[name], digits)
                if code is not None: unique_codes[label].add(code)
            original = field(values, ('f_area',)); derived = field(values, ('flood_area',))
            if type(original) in (int, float) and type(derived) in (int, float) and math.isfinite(original) and math.isfinite(derived):
                area_tested += 1; area_matches += math.isclose(original / 1600, derived, rel_tol=1e-5, abs_tol=.001)
            if geometry.shapeType == 0 or n == 0: empty += 1; continue
            if any(not math.isfinite(value) for point in geometry.points for value in point):
                nonfinite += 1; continue
            if crs.is_geographic and any(abs(point[0]) > 180 or abs(point[1]) > 90 for point in geometry.points):
                coordinate_conflict = True
            try:
                polygon = shape(geometry.__geo_interface__)
                invalid += not polygon.is_valid
                if not polygon.is_valid: invalid_reasons[explain_validity(polygon).split('[')[0]] += 1
                digest = hashlib.sha256(polygon.wkb).hexdigest()
                duplicates += digest in seen; seen.add(digest)
            except Exception:
                invalid += 1
                invalid_reasons['GEOMETRY_CONVERSION_FAILED'] += 1
    finally:
        logger.disabled = was_disabled
        reader.close()
    if count != expected: raise InspectionError('RECORD_COUNT_MISMATCH')
    lineage = html.unescape(html.unescape('\n'.join(data[:1024 * 1024].decode('utf-8', errors='replace') for name, data in parts.items() if name.lower().endswith('.xml'))))
    lineage_codes = sorted(set(re.findall(r'(?:EPSG[^0-9]{0,12}|(?:Latest)?WKID>)(\d{4,6})', lineage, flags=re.I)))[:16]
    file_time = bool(re.search(r'20\d{6}[_-]?\d{4}', Path(path).stem))
    bbox = list(reader.bbox) if hasattr(reader, 'bbox') else None
    hash_value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''): hash_value.update(chunk)
    return {'schema': 'offline-shapefile-inspection/1', 'source_sha256': hash_value.hexdigest(), 'records': count,
            'validation_method': 'GEOS/OGC after SHP-to-OGC conversion',
            'tool_versions': {'pyshp': shapefile.__version__, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string, 'pyproj': pyproj.__version__},
            'positions': positions, 'geometry_types': dict(types), 'invalid_topology': invalid, 'empty_geometry': empty,
            'topology_failure_categories': dict(invalid_reasons), 'geometry_interpretation': 'SHP rings converted to OGC geometry; no repair applied',
            'nonfinite_geometry': nonfinite, 'exact_geometry_duplicates': duplicates, 'bbox_source_coordinates': bbox,
            'fields': [{'name': name, 'type': kind, 'length': length, 'decimals': decimals, **profiles[name]} for name, kind, length, decimals in fields],
            'final_prj_crs': crs.to_authority(), 'crs_kind': 'geographic' if crs.is_geographic else 'projected',
            'coordinate_order': 'SHP XY; axis order/location accuracy requires source confirmation',
            'coordinate_range_conflict': coordinate_conflict, 'lineage_crs_mentions': lineage_codes,
            'administrative_relationship_counts': dict(admin), 'tambon_identity': 'NOT_VERIFIED',
            'unique_source_code_counts': {key: len(value) for key, value in unique_codes.items()}, 'tambon_parent_prefix_counts': dict(tambon_prefixes),
            'geometry_boundary_overlap': 'NOT_CHECKED; administrative codes do not certify clipping',
            'filename_time': 'UNVERIFIED_FILENAME_TIME' if file_time else 'NOT_IDENTIFIED',
            'zip_member_times': 'ARCHIVE_TIMES_NOT_ACQUISITION', 'xml_times': 'LOCAL_PROCESSING_TIME_UNVERIFIED_TIMEZONE' if lineage else 'NOT_SUPPLIED',
            'observed_at': None, 'provider_published_at': None,
            'area_relation_check': {'hypothesis': 'flood_area=F_AREA/1600', 'tested': area_tested, 'matches': area_matches, 'units': 'UNVERIFIED'},
            'constant_zero_interpretation': 'Zero values alone do not establish absence of affected houses or missing-value semantics',
            'source_url': None, 'license': 'UNKNOWN', 'public_redistribution': 'UNKNOWN', 'public_layer_ready': False,
            'geometry_exported': False, 'original_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip_path')
    parser.add_argument('--output', help='Optional new report file under this project artifacts directory only')
    args = parser.parse_args()
    try:
        report = inspect(args.zip_path)
        encoded = json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2)
        if args.output:
            target = Path(args.output).resolve()
            artifacts = Path(__file__).resolve().parents[1] / 'artifacts'
            if not target.is_relative_to(artifacts): raise InspectionError('REPORT_OUTPUT_MUST_BE_PRIVATE_ARTIFACT')
            with target.open('x', encoding='utf-8') as stream: stream.write(encoded)
        else: print(encoded)
    except Exception as error:
        reason = str(error) if isinstance(error, InspectionError) else 'SHAPEFILE_INSPECTION_FAILED'
        print(json.dumps({'status': 'REJECTED', 'reason': reason, 'geometry_exported': False}))
        raise SystemExit(2) from None


if __name__ == '__main__': main()
