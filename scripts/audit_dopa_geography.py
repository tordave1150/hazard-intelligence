"""Compare code/name facts with the pinned official DOPA directory download.

Read-only with respect to project geography; no network, spreadsheet execution,
personal population data, dependency on an Excel installation or archive extract.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=json.loads((ROOT/'data/geography/dopa-corrections.json').read_text(encoding='utf-8'))
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def xml_member(archive,name):
    info=archive.getinfo(name)
    if info.file_size>16*1024*1024:raise ValueError('Directory XML exceeds input bound')
    raw=archive.read(name)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper() or b'\x00' in raw:
        raise ValueError('Unsafe directory XML')
    return ET.fromstring(raw.decode('utf-8-sig'))


def directory_rows(path):
    with ZipFile(path) as archive:
        strings=[]
        for item in xml_member(archive,'xl/sharedStrings.xml').findall('m:si',NS):
            strings.append(''.join(t.text or '' for t in item.findall('m:t',NS)+item.findall('m:r/m:t',NS)))
        rows=[]
        for row in xml_member(archive,'xl/worksheets/sheet1.xml').findall('m:sheetData/m:row',NS):
            values={}
            for cell in row.findall('m:c',NS):
                if cell.find('m:f',NS) is not None:raise ValueError('Formula is not directory data')
                column=re.fullmatch(r'([A-Z]+)[0-9]+',cell.get('r',''))
                if not column:raise ValueError('Invalid directory cell reference')
                value=cell.findtext('m:v','',NS)
                if cell.get('t')=='s':value=strings[int(value)]
                values[column[1]]=value.strip()
            rows.append(values)
    if len(rows)<5 or rows[2].get('A')!='ข้อมูล ณ วันที่ 1 กันยายน 2566':
        raise ValueError('Unexpected directory version; review before accepting a new table')
    return rows[5:]


def active_areas(rows):
    active={}
    for row in rows:
        code=row.get('A','');name=row.get('B','')
        if not re.fullmatch(r'[0-9]{8}',code) or not code.endswith('0000'):continue
        # DOPA marks cancelled codes with * and a cancellation date. Neither
        # a cancelled district nor a subdistrict is a current district entry.
        if '*' in name or row.get('D')!='0':continue
        if not name:raise ValueError('Missing active area name')
        identifier='TH-P-'+code[:2] if code.endswith('000000') else 'TH-D-'+code[:4]
        if identifier in active:raise ValueError('Duplicate active official code')
        active[identifier]=name
    return active


def comparable_name(identifier,name):
    # DOPA includes เขต on Bangkok district rows; the display omits it.
    return name.removeprefix('เขต') if identifier.startswith('TH-D-10') else name


def audit(path,areas):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=REFERENCE['source_sha256']:
        raise ValueError('Pinned official directory checksum mismatch')
    active=active_areas(directory_rows(path))
    if sum(k.startswith('TH-P-') for k in active)!=77 or sum(k.startswith('TH-D-') for k in active)!=928:
        raise ValueError('Unexpected official directory coverage')
    selected=[a for a in areas if a['level'] in ['province','district']]
    project={a['id']:a for a in selected}
    if len(project)!=len(selected):raise ValueError('Duplicate project geography')
    differences=[{'id':key,'project_name':project[key]['name_th'],'official_name':active[key]}
                 for key in sorted(project.keys()&active.keys())
                 if comparable_name(key,project[key]['name_th'])!=comparable_name(key,active[key])]
    parents=[a['id'] for a in selected if a['level']=='district' and
             (a['parent_id']!='TH-P-'+a['id'][5:7] or a['province_id']!=a['parent_id'])]
    missing=sorted(active.keys()-project.keys());extra=sorted(project.keys()-active.keys())
    return {'reference':REFERENCE,'official_provinces':77,'official_districts':928,
            'project_provinces':sum(a['level']=='province' for a in selected),
            'project_districts':sum(a['level']=='district' for a in selected),
            'missing_project_ids':missing,'unexpected_project_ids':extra,
            'name_differences':differences,'invalid_parents':parents,
            'result':'PASS' if not (missing or extra or differences or parents) else 'DIFFERENCES',
            'limitation':'Code/name comparison to the official downloadable 2023-09-01 table; no certification of 2026 legal geography or boundary accuracy.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True,help='Saved official ccaatt.xlsx, downloaded from the cited public directory')
    parser.add_argument('--areas',type=Path,default=ROOT/'apps/web/data/areas.json')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    result=audit(args.input,json.loads(args.areas.read_text(encoding='utf-8')))
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.write_text(output,encoding='utf-8')
    print(output)
    if args.check and result['result']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
