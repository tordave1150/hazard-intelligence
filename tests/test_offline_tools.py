from copy import deepcopy
import hashlib
from io import BytesIO
import json
import struct
import zipfile
import pytest
import shapefile
from pyproj import CRS
from scripts.inspect_flood_shapefile import inspect, InspectionError
from scripts import gistda_cadence as cadence


def archive(tmp_path, mutate=None, invalid=False):
    shp, shx, dbf = BytesIO(), BytesIO(), BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    for name, kind, size, decimal in [('pv_idn','N',2,0),('ap_idn','N',4,0),('tb_idn','N',6,0),('house','N',8,0),('F_AREA','F',14,3),('flood_area','F',14,3),('private','C',40,0)]:
        writer.field(name,kind,size,decimal)
    ring = [[100.5,13.7],[100.5,13.71],[100.51,13.71],[100.51,13.7],[100.5,13.7]]
    if invalid: ring = [[100.5,13.7],[100.51,13.71],[100.51,13.7],[100.5,13.71],[100.5,13.7]]
    for _ in range(2):
        writer.poly([ring]);writer.record(10,1001,100101,0,3200,2,'private-value-never-print')
    writer.close()
    parts = {'data.shp':shp.getvalue(),'data.shx':shx.getvalue(),'data.dbf':dbf.getvalue(),
             'data.prj':CRS.from_epsg(4326).to_wkt().encode(),
             'data.shp.xml':b'<LatestWKID>32647</LatestWKID><ProcessDate>2026-10-08T13:50:00</ProcessDate>'}
    if mutate: mutate(parts)
    path = tmp_path/'rd2_20261003_0608.zip'
    with zipfile.ZipFile(path,'w') as out:
        for name,value in parts.items(): out.writestr(name,value)
    return path


def test_offline_report_preserves_provenance_unknowns_and_original_without_values(tmp_path):
    path=archive(tmp_path); before=hashlib.sha256(path.read_bytes()).hexdigest()
    report=inspect(path)
    assert report['records']==2 and report['positions']==10 and report['exact_geometry_duplicates']==1
    assert report['final_prj_crs']==('EPSG','4326') and report['lineage_crs_mentions']==['32647']
    assert report['filename_time']=='UNVERIFIED_FILENAME_TIME' and report['observed_at'] is None
    assert report['public_layer_ready'] is False and report['public_redistribution']=='UNKNOWN'
    assert report['area_relation_check']['matches']==2
    assert report['administrative_relationship_counts']=={'MATCH':2}
    assert report['unique_source_code_counts']=={'province':1,'district':1,'tambon':1}
    assert 'private-value-never-print' not in json.dumps(report)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_escaped_lineage_codes_are_not_confused_with_the_final_projection(tmp_path):
    report=inspect(archive(tmp_path,lambda parts:parts.update({'data.shp.xml':b'WKID&gt;32647 EPSG&amp;quot;,32647'})))
    assert report['lineage_crs_mentions']==['32647'] and report['final_prj_crs']==('EPSG','4326')


def test_invalid_topology_is_reported_without_repair_export_or_coordinate_errors(tmp_path):
    report=inspect(archive(tmp_path,invalid=True))
    assert report['invalid_topology']==2 and sum(report['topology_failure_categories'].values())==2
    assert all('[' not in reason for reason in report['topology_failure_categories'])
    assert report['geometry_exported'] is False and report['public_layer_ready'] is False


@pytest.mark.parametrize('name',['../outside.shp','/absolute','C:/drive.shp','folder\\..\\escape'])
def test_archive_paths_cannot_escape_even_without_extracting(tmp_path,name):
    path=archive(tmp_path,lambda parts:parts.update({name:b'bad'}))
    with pytest.raises(InspectionError,match='UNSAFE_ARCHIVE_PATH'):inspect(path)


@pytest.mark.parametrize('mutation,reason',[
    (lambda parts:parts.pop('data.prj'),'MISSING_REQUIRED_COMPONENT'),
    (lambda parts:parts.update({'DATA.SHP':parts['data.shp']}),'DUPLICATE_ARCHIVE_MEMBER'),
    (lambda parts:parts.update({'data.shx':parts['data.shx'][:100]}),'SHAPE_FILE_LENGTH_MISMATCH'),
    (lambda parts:parts.update({'data.dbf':parts['data.dbf'][:4]+struct.pack('<I',3)+parts['data.dbf'][8:]}),'DBF_SHAPE_COUNT_MISMATCH'),
    (lambda parts:parts.update({'data.prj':b'not a coordinate system'}),'INVALID_OR_UNKNOWN_CRS'),
])
def test_missing_corrupt_or_ambiguous_components_are_rejected(tmp_path,mutation,reason):
    with pytest.raises(InspectionError,match=reason):inspect(archive(tmp_path,mutation))


def test_cadence_empty_and_unknown_version_can_coexist_without_new_image_claim():
    feed={'record_count':0,'response_at':'2026-10-28T00:15:00Z','fetched_at':'2026-10-28T00:15:01Z'}
    health={'status':'SUCCESS','completed_at':'2026-10-28T00:15:02Z'}
    item=cadence.receipt(feed,health,'2026-10-28T00:16:00Z')
    assert item['query_state']=='EMPTY_RESULT' and item['version_state']=='UNKNOWN_VERSION'
    assert item['provider_published_at'] is None and item['observed_at'] is None
    journal=cadence.append_receipt({},item)
    assert len(cadence.append_receipt(journal,item)['receipts'])==1
    failed=cadence.receipt(feed,{**health,'status':'FAILED'},'2026-10-28T00:17:00Z')
    assert failed['query_state']=='FAILED' and failed['response_at'] is None
    assert cadence.receipt(feed,health,cadence.END) is None
    not_checked=cadence.receipt(feed,health,'2026-10-28T01:00:00Z','2026-10-28T00:59:00Z')
    assert not_checked['query_state']=='NOT_CHECKED' and not_checked['response_at'] is None
    for index in range(70): journal=cadence.append_receipt(journal,{**item,'check_id':str(index)})
    assert len(journal['receipts'])==56
    assert cadence.summarize(journal)['publication_interval'] is None


def test_only_reviewed_version_evidence_allows_change_and_values_are_hashed():
    assert cadence.version_state(None,'untrusted',False)==('UNKNOWN_VERSION',None)
    state,digest=cadence.version_state(None,'reviewed-version-1',True)
    assert state=='FIRST_SEEN_VERIFIED' and 'reviewed-version-1' not in digest
    assert cadence.version_state(digest,'reviewed-version-1',True)[0]=='UNCHANGED'
    assert cadence.version_state(digest,'reviewed-version-2',True)[0]=='CHANGED_VERIFIED'
