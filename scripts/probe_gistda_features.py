"""Bounded Disaster Platform Features inspection, following the official manual.

One page/item, one fixed-host GET, API-Key header only. No MongoDB/publication.
Logs contain bounded structure and validated response/item-time metadata only;
no returned links, assets, raw feature values or credentials reach artifacts.
An observed empty page is not an all-clear or a satellite acquisition timestamp.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
import requests
from scripts.probe_gistda import structure,error_hints
from scripts.gistda_sample_quality import sample_quality

BASE='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/'
WINDOWS={'1day','3days','7days','30days'}
STAC_ENDPOINTS={window:'https://api-gateway.gistda.or.th/api/2.0/resources/stac/flood/collections/flood'+window+'_r2/items/items_flood'+window+'_r2' for window in WINDOWS}
MAX_BYTES=2*1024*1024
ROOT=Path(__file__).resolve().parents[1]
REQUEST_PATH=ROOT/'.github/gistda-inspection.json'
DISTRICTS={a['id'][5:] for a in json.loads((ROOT/'apps/web/data/areas.json').read_text(encoding='utf-8')) if a['level']=='district'}


def load_reviewed_request(path=None):
    """A public, versioned request can select products/filters, never credentials or hosts."""
    path=REQUEST_PATH if path is None else path
    if path.stat().st_size>1024:raise ValueError('Request file too large')
    request=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(request,dict) or not {'request_id','window','ap_idn'}<=set(request) or set(request)-{'request_id','window','ap_idn','service'}:
        raise ValueError('Invalid request fields')
    if any(not isinstance(v,str) for v in request.values()):raise ValueError('Invalid request types')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{2}',request['request_id']):raise ValueError('Invalid request ID')
    if request['window'] not in WINDOWS:raise ValueError('Invalid request window')
    if request['ap_idn'] and request['ap_idn'] not in DISTRICTS:raise ValueError('Invalid request district')
    if request.get('service','features') not in ['features','stac']:raise ValueError('Invalid service')
    if request.get('service')=='stac' and request['ap_idn']:raise ValueError('STAC item has no district filter')
    return request


def stac_metadata(payload,secret):
    """Expose validated item times, never infer per-pixel/feature acquisition from them."""
    if not isinstance(payload,dict) or payload.get('type')!='Feature' or not isinstance(payload.get('properties'),dict):
        raise ValueError('Invalid STAC feature')
    version=payload.get('stac_version')
    if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+',version) or secret in version:
        raise ValueError('Invalid STAC version')
    if not isinstance(payload.get('links'),list) or not isinstance(payload.get('assets'),dict):
        raise ValueError('Invalid STAC links/assets')
    temporal={}
    for field in ['datetime','start_datetime','end_datetime']:
        value=payload['properties'].get(field)
        if value is None:temporal[field]=None;continue
        if not isinstance(value,str) or len(value)>40 or secret in value or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)',value):
            raise ValueError('Invalid STAC UTC time')
        instant=datetime.fromisoformat(value.replace('Z','+00:00'))
        if instant.tzinfo is None:raise ValueError('Invalid STAC timezone')
        temporal[field]=value
    start=temporal['start_datetime'];end=temporal['end_datetime']
    if bool(start)!=bool(end):raise ValueError('Incomplete STAC interval')
    if start and datetime.fromisoformat(start.replace('Z','+00:00'))>datetime.fromisoformat(end.replace('Z','+00:00')):
        raise ValueError('Reversed STAC interval')
    return {'stac_version':version,'item_temporal_metadata':temporal,
            'temporal_status':'PRESENT_MEANING_UNVERIFIED' if temporal['datetime'] or start else 'UNAVAILABLE',
            'temporal_meaning':'STAC item search/nominal time or interval; not verified per-feature or per-pixel satellite acquisition',
            'returned_links_discarded':len(payload['links']),'returned_assets_not_followed':len(payload['assets']),
            'acquisition_time_status':'UNVERIFIED'}


def page_metadata(payload,limit=1):
    if not isinstance(payload,dict) or payload.get('type')!='FeatureCollection' or not isinstance(payload.get('features'),list):
        raise ValueError('Invalid FeatureCollection')
    features=payload['features'];matched=payload.get('numberMatched');returned=payload.get('numberReturned')
    if type(matched) is not int or type(returned) is not int or not 0<=returned<=limit or matched<returned or returned!=len(features):
        raise ValueError('Invalid feature accounting')
    stamp=payload.get('timeStamp')
    if not isinstance(stamp,str) or len(stamp)>40 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:\d{2})',stamp):
        raise ValueError('Invalid response timestamp')
    instant=datetime.fromisoformat(stamp.replace('Z','+00:00'))
    if instant.tzinfo is None:raise ValueError('Missing response timezone')
    links=payload.get('links',[])
    if not isinstance(links,list):raise ValueError('Invalid links envelope')
    for feature in features:
        if not isinstance(feature,dict) or feature.get('type')!='Feature' or not isinstance(feature.get('properties'),dict):
            raise ValueError('Invalid feature envelope')
    return {'number_matched':matched,'number_returned':returned,'response_timestamp':stamp,
            'timestamp_meaning':'API response time; not satellite acquisition time',
            'empty_result':matched==0 and returned==0,'complete_collection':matched==returned,
            'returned_links_discarded':len(links),
            'coverage':'Requested service/filter only; zero features does not establish safe or complete satellite coverage',
            'acquisition_time_status':'UNVERIFIED'}


def inspect_features(api_key,window='1day',ap_idn='2604',get=None,clock=time.monotonic,service='features'):
    api_key=api_key.strip();ap_idn=ap_idn.strip()
    if len(api_key)<8 or len(api_key)>4096 or any(c in api_key for c in '\r\n') or api_key.lower().startswith(('http:','https:','gistda_api_key=')):
        return {'result':'INVALID_OR_MISSING_SECRET'},1
    if window not in WINDOWS:return {'result':'INVALID_PRODUCT_WINDOW'},1
    if service not in ['features','stac']:return {'result':'INVALID_SERVICE'},1
    if ap_idn and (not re.fullmatch(r'[0-9]{4}',ap_idn) or ap_idn not in DISTRICTS):
        return {'result':'INVALID_DISTRICT_FILTER'},1
    if service=='stac' and ap_idn:return {'result':'INVALID_STAC_FILTER'},1
    endpoint=BASE+window if service=='features' else STAC_ENDPOINTS[window]
    params={'limit':1,'offset':0} if service=='features' else {}
    if ap_idn:params['ap_idn']=ap_idn
    report={'service':'GISTDA Disaster Platform Features' if service=='features' else 'GISTDA Disaster Platform STAC','product_window':window,'endpoint':endpoint,
            'authentication_transport':'API-Key header','requested_filter':{'ap_idn':ap_idn or None},
            'scope':'Single-page metadata/schema inspection; no source acceptance or publication'}
    deadline=clock()+45
    try:
        with (get or requests.get)(endpoint,params=params,headers={'Accept':'application/json','API-Key':api_key},
                                   timeout=(5,25),allow_redirects=False,stream=True) as response:
            status=response.status_code;report['http_status']=status
            if 300<=status<400:return {**report,'result':'REDIRECT_REJECTED'},1
            chunks=[];size=0
            for chunk in response.iter_content(chunk_size=65536):
                size+=len(chunk)
                if size>MAX_BYTES:return {**report,'result':'RESPONSE_TOO_LARGE'},1
                if clock()>deadline:return {**report,'result':'DEADLINE_EXCEEDED'},1
                chunks.append(chunk)
            try:
                def reject_constant(_):raise ValueError('Non-finite JSON')
                payload=json.loads(b''.join(chunks).decode('utf-8-sig'),parse_constant=reject_constant)
            except (UnicodeDecodeError,ValueError):
                return {**report,'result':'NON_JSON_RESPONSE'},1
            if status in [401,403,407]:return {**report,'result':'AUTHENTICATION_OR_ENTITLEMENT_NOT_VERIFIED'},1
            if not 200<=status<300:
                hints=error_hints(payload)
                if hints is not None:report['provider_error_hints']=hints
                return {**report,'result':'HTTP_ERROR_NOT_AN_EMPTY_OBSERVATION'},1
            if isinstance(payload,dict) and (payload.get('error') or
               any(type(payload.get(k)) is int and payload[k]>=400 for k in ['status','statusCode','status_code'])):
                return {**report,'result':'PROVIDER_ERROR_NOT_AN_EMPTY_OBSERVATION'},1
            # Drop links BEFORE schema inspection. The real service can echo
            # api_key inside href even when authentication used only a header.
            discarded={'links','assets'} if service=='stac' else {'links'}
            safe={k:v for k,v in payload.items() if k not in discarded} if isinstance(payload,dict) else payload
            report['response_structure']=structure(safe,api_key,max_fields=48)
            if service=='stac':
                try:report['stac_metadata']=stac_metadata(payload,api_key)
                except (ValueError,TypeError,OverflowError):return {**report,'result':'STAC_ITEM_SCHEMA_UNVERIFIED'},1
                return {**report,'result':'STAC_ITEM_OBSERVED_SCHEMA_UNVERIFIED'},0
            try:report['page_metadata']=page_metadata(payload)
            except (ValueError,TypeError,OverflowError):return {**report,'result':'FEATURE_COLLECTION_SCHEMA_UNVERIFIED'},1
            if api_key in report['page_metadata']['response_timestamp']:
                return {**report,'page_metadata':None,'result':'FEATURE_COLLECTION_SCHEMA_UNVERIFIED'},1
            if payload['features']:
                report['sample_quality']=sample_quality(payload['features'][0],ap_idn,'crs' in payload)
            result='EMPTY_FEATURE_COLLECTION_OBSERVED' if report['page_metadata']['empty_result'] else 'FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED'
            return {**report,'result':result},0
    except requests.RequestException:
        return {**report,'result':'TRANSPORT_FAILURE'},1
    except Exception:
        return {**report,'result':'INSPECTION_FAILED'},1


def main(reviewed_request=False):
    request=None
    if reviewed_request:
        try:request=load_reviewed_request()
        except (OSError,ValueError,TypeError):
            print(json.dumps({'result':'INVALID_REVIEWED_REQUEST'}))
            raise SystemExit(1) from None
    window=request['window'] if request else os.getenv('GISTDA_FEATURE_WINDOW','1day')
    if request:
        ap_idn=request['ap_idn']
    else:
        query_scope=os.getenv('GISTDA_QUERY_SCOPE','national')
        if query_scope not in ('national','district'):
            print(json.dumps({'result':'INVALID_QUERY_SCOPE'}))
            raise SystemExit(1) from None
        # National scope must not depend on whether GitHub preserves an empty
        # text input. Ignore even a retained/default district value explicitly.
        ap_idn='' if query_scope=='national' else os.getenv('GISTDA_FEATURE_AP_IDN','').strip()
        if query_scope=='district' and not ap_idn:
            print(json.dumps({'result':'DISTRICT_FILTER_REQUIRED'}))
            raise SystemExit(1) from None
    service=request.get('service','features') if request else os.getenv('GISTDA_INSPECTION_SERVICE','features')
    report,code=inspect_features(os.getenv('GISTDA_API_KEY',''),window,ap_idn,service=service)
    if request:report['reviewed_request_id']=request['request_id']
    else:report['requested_scope']=query_scope
    print(json.dumps(report,ensure_ascii=True,allow_nan=False))
    raise SystemExit(code)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Inspect one bounded GISTDA Features page without publication')
    parser.add_argument('--reviewed-request',action='store_true',help='Use the fixed repository request file instead of manual inputs')
    main(parser.parse_args().reviewed_request)
