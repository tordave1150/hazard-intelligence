import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from pipelines.shared.time_units import instant,utc_now

SOURCE='https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load'
PRODUCT='national_waterlevel'
KEY='thaiwater:'+PRODUCT
COLLECTION='gauge_latest'
MAX_DOCUMENT_BYTES=4*1024*1024
AREAS={a['id']:a for a in json.loads((Path(__file__).resolve().parents[2]/'apps/web/data/areas.json').read_text(encoding='utf-8'))}


def text(value,limit=256):
    return value.strip()[:limit] or None if isinstance(value,str) else None


def number(value):
    if type(value) in (float,int):return float(value) if math.isfinite(value) and abs(value)<=10000 else None
    if isinstance(value,str) and len(value)<30 and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)',value.strip()):
        result=float(value)
        return result if math.isfinite(result) and abs(result)<=10000 else None
    return None


def valid_wall_time(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}',value):return False
    try:datetime.strptime(value,'%Y-%m-%d %H:%M');return True
    except ValueError:return False


def normalize(payload,fetched_at,ingested_at=None):
    if not isinstance(payload,dict):raise ValueError('Invalid station response')
    automatic=payload.get('waterlevel_data',{});manual=payload.get('waterlevel_manual_data',{})
    if automatic.get('result')!='OK' or manual.get('result')!='OK':raise ValueError('Provider did not confirm station response')
    rows=automatic.get('data');manual_rows=manual.get('data')
    if not isinstance(rows,list) or len(rows)>10000 or not isinstance(manual_rows,list) or len(manual_rows)>10000:raise ValueError('Invalid station inventory')
    records=[];excluded=[];seen=set()
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('station'),dict) or not isinstance(row.get('geocode'),dict):raise ValueError('Missing station identity')
        if row.get('station_type')!='tele_waterlevel':raise ValueError('Unsupported automatic station type')
        station=row['station'];geo=row['geocode'];identity=station.get('id')
        if type(identity) not in (int,str) or not re.fullmatch(r'[0-9]{1,12}',str(identity)):raise ValueError('Invalid station identity')
        identity=str(identity)
        if identity in seen:raise ValueError('Duplicate station identity')
        seen.add(identity)
        province='TH-P-'+str(geo.get('province_code',''));parent=AREAS.get(province)
        if not parent or parent['level']!='province':
            label=geo.get('area_name') or geo.get('province_name') or {}
            excluded.append({'source_station_id':identity,'provider_province_code':text(str(geo['province_code'])) if geo.get('province_code') is not None else None,
                'provider_area_name':text(label.get('en') or label.get('th')) if isinstance(label,dict) else None,'reason':'NOT_CANONICAL_THAI_PROVINCE'})
            continue
        flags=[];district=None
        code=str(geo.get('amphoe_code',''))
        candidate='TH-D-'+province[5:]+code if re.fullmatch(r'\d{2}',code) else 'TH-D-'+code
        member=AREAS.get(candidate)
        if member and member['level']=='district' and member['province_id']==province:district=candidate
        else:flags.append('UNRECOGNIZED_DISTRICT')
        lat,lon=number(station.get('tele_station_lat')),number(station.get('tele_station_long'))
        point={'lat':lat,'lon':lon} if lat is not None and lon is not None and 5<=lat<=22 and 96<=lon<=107 else None
        if point is None:flags.append('INVALID_POINT')
        wall=text(row.get('waterlevel_datetime'),40)
        if not valid_wall_time(wall):flags.append('INVALID_PROVIDER_TIME')
        values={field:number(row.get(field)) for field in ('waterlevel_msl','waterlevel_m')}
        if any(row.get(k) is not None and values[k] is None for k in values):flags.append('INVALID_LEVEL')
        if all(v is None for v in values.values()):flags.append('NO_LEVEL')
        agency=row.get('agency') if isinstance(row.get('agency'),dict) else {}
        names=station.get('tele_station_name') if isinstance(station.get('tele_station_name'),dict) else {}
        agency_names=agency.get('agency_name') if isinstance(agency.get('agency_name'),dict) else {}
        records.append({'gauge_id':'THW-'+identity,'source_station_id':identity,'station_code':text(station.get('tele_station_oldcode')),
            'name_th':text(names.get('th')),'name_en':text(names.get('en')),'agency_name':text(agency_names.get('th') or agency_names.get('en')),
            'agency_id':text(str(agency['id'])) if agency.get('id') is not None else None,
            'province_id':province,'district_id':district,'region_id':parent['region_id'],'point':point,
            'source_observed_at':wall,'observed_at':None,'observation_time_status':'TIMEZONE_NOT_SUPPLIED',
            'water_level_msl':values['waterlevel_msl'],'water_level_m':values['waterlevel_m'],'quality_flags':flags})
    counts=Counter(r['province_id'] for r in records)
    feed={'schema_version':'2.0','source_id':'thaiwater','product_id':PRODUCT,'data_state':'observed','snapshot_id':'latest',
        'source_url':SOURCE,'fetched_at':fetched_at,'ingested_at':ingested_at or utc_now(),'record_count':len(records),
        'provider_automatic_count':len(rows),'provider_manual_count':len(manual_rows),'provider_response_accounted_for':True,
        'excluded_stations':excluded,'coverage_by_province':[{'area_id':k,'record_count':v} for k,v in sorted(counts.items())],
        'quality_issue_count':sum(bool(r['quality_flags']) for r in records),'time_unknown_count':len(records),'records':records,
        'coverage':'All canonical Thai station rows returned by this unfiltered response; complete station inventory and area-wide water conditions are not certified.',
        'units':{'water_level_msl':'m above mean sea level','water_level_m':'m as reported'}}
    from pipelines.shared.schemas import validate_record
    return validate_record('ThaiWaterFeed',feed)


def check_feed(feed):
    rows=feed['records'];ids=[r['source_station_id'] for r in rows]+[r['source_station_id'] for r in feed['excluded_stations']]
    if feed['record_count']!=len(rows) or len(ids)!=feed['provider_automatic_count'] or len(set(ids))!=len(ids):raise ValueError('Incomplete station accounting')
    if instant(feed['fetched_at'])>instant(feed['ingested_at']):raise ValueError('Invalid station ingestion time')
    counts=Counter(r['province_id'] for r in rows)
    if feed['coverage_by_province']!=[{'area_id':k,'record_count':v} for k,v in sorted(counts.items())]:raise ValueError('Invalid station coverage counts')
    if feed['quality_issue_count']!=sum(bool(r['quality_flags']) for r in rows) or feed['time_unknown_count']!=len(rows):raise ValueError('Invalid station quality counts')
    for row in rows:
        parent=AREAS.get(row['province_id']);district=AREAS.get(row['district_id'])
        if not parent or parent['level']!='province' or row['region_id']!=parent['region_id']:raise ValueError('Invalid station province')
        if row['district_id'] is not None and (not district or district['province_id']!=row['province_id']):raise ValueError('Invalid station district')
        if row['gauge_id']!='THW-'+row['source_station_id']:raise ValueError('Invalid gauge identity')
        if (not valid_wall_time(row['source_observed_at']))!=('INVALID_PROVIDER_TIME' in row['quality_flags']):raise ValueError('Unflagged station time issue')
        if (row['point'] is None)!=('INVALID_POINT' in row['quality_flags']):raise ValueError('Unflagged station point issue')
        if all(row[k] is None for k in ('water_level_m','water_level_msl'))!=('NO_LEVEL' in row['quality_flags']):raise ValueError('Unflagged missing station level')
        if any(type(row[k]) not in (int,float,type(None)) or isinstance(row[k],float) and not math.isfinite(row[k]) for k in ('water_level_m','water_level_msl')):raise ValueError('Non-finite station value')
    if len(json.dumps(feed,ensure_ascii=False,allow_nan=False).encode())>MAX_DOCUMENT_BYTES:raise ValueError('Station envelope too large')
