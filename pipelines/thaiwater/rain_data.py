import re,json,math
from collections import Counter
from pipelines.shared.time_units import instant,utc_now
from .data import AREAS,text,number,valid_wall_time,MAX_DOCUMENT_BYTES
SOURCE='https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h'
PRODUCT='national_rain_24h';KEY='thaiwater:'+PRODUCT;COLLECTION='rain_gauge_latest'

def normalize(payload,fetched_at,ingested_at=None):
    if not isinstance(payload,dict) or payload.get('result')!='OK' or not isinstance(payload.get('data'),list) or len(payload['data'])>10000:
        raise ValueError('Invalid public rainfall response')
    records=[];excluded=[];seen=set()
    for row in payload['data']:
        station=row.get('station',{});geo=row.get('geocode',{});identity=station.get('id')
        if row.get('station_type')!='rainfall_24h' or type(identity) not in (int,str) or not re.fullmatch(r'\d{1,12}',str(identity)):raise ValueError('Invalid rain station identity')
        identity=str(identity)
        if identity in seen:raise ValueError('Duplicate rain station')
        seen.add(identity);province='TH-P-'+str(geo.get('province_code',''));parent=AREAS.get(province)
        if not parent or parent['level']!='province':
            label=geo.get('area_name') or geo.get('province_name') or {}
            excluded.append({'source_station_id':identity,'provider_province_code':text(str(geo['province_code'])) if geo.get('province_code') is not None else None,
                'provider_area_name':text(label.get('en') or label.get('th')) if isinstance(label,dict) else None,'reason':'NOT_CANONICAL_THAI_PROVINCE'});continue
        # This product has district names, not codes. Require an exact, unique match inside the supplied province.
        candidates=[a for a in AREAS.values() if a['level']=='district' and a['province_id']==province and a['name_th']==text((geo.get('amphoe_name') or {}).get('th'))]
        district=candidates[0]['id'] if len(candidates)==1 else None
        lat,lon=number(station.get('tele_station_lat')),number(station.get('tele_station_long'));flags=[]
        point={'lat':lat,'lon':lon} if lat is not None and lon is not None and 5<=lat<=22 and 96<=lon<=107 else None
        if point is None:flags.append('INVALID_POINT')
        wall=text(row.get('rainfall_datetime'),40)
        if not valid_wall_time(wall):flags.append('INVALID_PROVIDER_TIME')
        values={k:number(row.get(k)) for k in ['rain_24h','rain_1h']}
        for k,limit in [('rain_24h',5000),('rain_1h',1000)]:
            if values[k] is not None and not 0<=values[k]<=limit:values[k]=None
        if any(row.get(k) is not None and values[k] is None for k in values):flags.append('INVALID_RAIN')
        if values['rain_24h'] is None:flags.append('NO_24H_RAIN')
        names=station.get('tele_station_name') or {};agency=(row.get('agency') or {}).get('agency_name') or {}
        records.append({'gauge_id':'THR-'+identity,'source_station_id':identity,'station_code':text(station.get('tele_station_oldcode')),
            'name_th':text(names.get('th')),'name_en':text(names.get('en')),'agency_name':text(agency.get('th') or agency.get('en')),'agency_id':None,
            'province_id':province,'district_id':district,'district_mapping':'EXACT_NAME_WITHIN_PROVIDER_PROVINCE' if district else 'UNCONFIRMED',
            'region_id':parent['region_id'],'point':point,'source_observed_at':wall,'observed_at':None,'observation_time_status':'TIMEZONE_NOT_SUPPLIED',
            'rain_24h_mm':values['rain_24h'],'rain_1h_mm':values['rain_1h'],'quality_flags':flags})
    counts=Counter(r['province_id'] for r in records)
    feed={'schema_version':'2.0','source_id':'thaiwater','product_id':PRODUCT,'data_state':'observed','snapshot_id':'latest','source_url':SOURCE,
        'fetched_at':fetched_at,'ingested_at':ingested_at or utc_now(),'record_count':len(records),'provider_automatic_count':len(payload['data']),
        'provider_response_accounted_for':True,'excluded_stations':excluded,'coverage_by_province':[{'area_id':k,'record_count':v} for k,v in sorted(counts.items())],
        'quality_issue_count':sum(bool(r['quality_flags']) for r in records),'time_unknown_count':len(records),'records':records,
        'coverage':'All canonical Thai rain station rows in the unfiltered response; station inventory and area-wide rainfall are not certified.',
        'units':{'rain_24h_mm':'mm / 24h as reported','rain_1h_mm':'mm / 1h as reported'},'window_start':None,'window_end':None}
    from pipelines.shared.schemas import validate_record
    return validate_record('ThaiWaterRainFeed',feed)

def check_feed(feed):
    rows=feed['records'];ids=[r['source_station_id'] for r in rows+feed['excluded_stations']]
    if feed['record_count']!=len(rows) or len(ids)!=feed['provider_automatic_count'] or len(set(ids))!=len(ids):raise ValueError('Incomplete rain response accounting')
    if instant(feed['fetched_at'])>instant(feed['ingested_at']):raise ValueError('Invalid rain ingestion time')
    counts=Counter(r['province_id'] for r in rows)
    if feed['coverage_by_province']!=[{'area_id':k,'record_count':v} for k,v in sorted(counts.items())]:raise ValueError('Invalid rain coverage')
    if feed['quality_issue_count']!=sum(bool(r['quality_flags']) for r in rows) or feed['time_unknown_count']!=len(rows):raise ValueError('Invalid rain quality counts')
    for r in rows:
        area=AREAS.get(r['province_id']);district=AREAS.get(r['district_id'])
        if not area or area['level']!='province' or r['region_id']!=area['region_id'] or r['gauge_id']!='THR-'+r['source_station_id']:raise ValueError('Invalid rain identity')
        if r['district_id'] is not None and (not district or district['province_id']!=r['province_id']):raise ValueError('Invalid rain district')
        if (r['district_id'] is None)!=(r['district_mapping']=='UNCONFIRMED'):raise ValueError('Invalid district mapping status')
        if (not valid_wall_time(r['source_observed_at']))!=('INVALID_PROVIDER_TIME' in r['quality_flags']):raise ValueError('Unflagged rain time')
        if (r['point'] is None)!=('INVALID_POINT' in r['quality_flags']) or (r['rain_24h_mm'] is None)!=('NO_24H_RAIN' in r['quality_flags']):raise ValueError('Unflagged rain quality')
    if len(json.dumps(feed,ensure_ascii=False,allow_nan=False).encode())>MAX_DOCUMENT_BYTES:raise ValueError('Rain envelope too large')
