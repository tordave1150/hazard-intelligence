"""One manual, credential-safe inspection of the user-selected GISTDA product.

No publication, database credentials, provider retries or response-body logging.
Only bounded field/type structure is reported; no product is accepted by this
diagnostic. Current parameter semantics must come from the product documents.
"""
import json
import math
import os
import re
import time
import requests

ENDPOINT='https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.1/disasters/flood-extent-1day'
ENDPOINTS={'v1.1':ENDPOINT,
           'v1.0':'https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day'}
MAX_BYTES=2*1024*1024
FIELD=re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')


def structure(value,secret,depth=0):
    """Expose schema hints, never values or reflected request URLs/credentials."""
    if isinstance(value,dict):
        if depth>=4:return {'type':'object'}
        fields={}
        for key,item in list(value.items())[:24]:
            # Unknown field names can themselves be reflected URLs or secrets.
            if not FIELD.fullmatch(key) or secret.lower() in key.lower():continue
            if any(word in key.lower() for word in ['key','token','password','secret','authorization']):continue
            fields[key]=structure(item,secret,depth+1)
        return {'type':'object','fields':fields,'field_count':len(value)}
    if isinstance(value,list):
        return {'type':'array','count':len(value),'first_item':structure(value[0],secret,depth+1) if value and depth<4 else None}
    if value is None:return {'type':'null'}
    if isinstance(value,bool):return {'type':'boolean'}
    if isinstance(value,(int,float)):return {'type':'number'}
    return {'type':'string'}


def error_hints(payload):
    """Classify fixed error signals without exposing an upstream request URL."""
    if not isinstance(payload,dict):return None
    message=payload.get('message')
    if not isinstance(message,str):return None
    return {'kind':'ROUTE_NOT_FOUND' if re.match(r'^Cannot\s+(GET|POST)\s',message,re.I) else 'UNCLASSIFIED',
            'undefined_parameters':[name for name in ['lat','lon','area'] if re.search(r'(?<![A-Za-z0-9_])'+name+r'=undefined(?:[&#\s]|$)',message)]}


def inspect(api_key,area='',get=None,clock=time.monotonic,lat='',lon='',version='v1.1'):
    api_key=api_key.strip();area=area.strip()
    if len(api_key)<8 or len(api_key)>4096 or any(c in api_key for c in '\r\n') or api_key.lower().startswith(('http:','https:','gistda_api_key=')):
        return {'result':'INVALID_OR_MISSING_SECRET'},1
    if version not in ENDPOINTS:return {'result':'INVALID_ENDPOINT_VERSION'},1
    endpoint=ENDPOINTS[version]
    if area and (len(area)>8192 or area.lower() in ['undefined','null'] or api_key in area or
                 re.search(r'https?://|api[_-]?key\s*=',area,re.I)):
        return {'result':'INVALID_AREA_INPUT'},1
    lat=lat.strip();lon=lon.strip()
    point=None
    if lat or lon:
        try:
            if not lat or not lon:raise ValueError('Both coordinates required')
            latitude=float(lat);longitude=float(lon)
            if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90<=latitude<=90 or not -180<=longitude<=180:
                raise ValueError('Invalid coordinate range')
            point={'lat':latitude,'lon':longitude}
        except ValueError:
            return {'result':'INVALID_POINT_INPUT'},1
    # The official catalog documents api_key authentication. This single
    # v1.1 probe verifies compatibility rather than assuming the key works.
    params={'api_key':api_key}
    if area:params['area']=area
    if point:params.update(point)
    report={'product_number':25,'endpoint':endpoint,'endpoint_version':version,'area_supplied':bool(area),'point_supplied':point is not None,
            'scope':'Response structure inspection only; no data acceptance or publication'}
    deadline=clock()+45
    try:
        with (get or requests.get)(endpoint,params=params,headers={'Accept':'application/json'},
                                   timeout=(5,25),allow_redirects=False,stream=True) as response:
            status=response.status_code
            report['http_status']=status
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
            report['response_structure']=structure(payload,api_key)
            hints=error_hints(payload)
            if hints is not None:report['provider_error_hints']=hints
            if status in [401,403,407]:return {**report,'result':'AUTHENTICATION_OR_ENTITLEMENT_NOT_VERIFIED'},1
            if not 200<=status<300:return {**report,'result':'HTTP_ERROR_REQUIRES_PARAMETER_OR_PROVIDER_REVIEW'},1
            # A JSON error can be wrapped in HTTP 200 by an upstream service.
            if isinstance(payload,dict) and (payload.get('error') or
               any(type(payload.get(k)) is int and payload[k]>=400 for k in ['status','statusCode','status_code'])):
                return {**report,'result':'PROVIDER_ERROR_REQUIRES_REVIEW'},1
            return {**report,'result':'RESPONSE_RECEIVED_SCHEMA_UNVERIFIED'},0
    except requests.RequestException:
        # requests errors can contain the prepared URL and query credential.
        return {**report,'result':'TRANSPORT_FAILURE'},1
    except Exception:
        # Keep diagnostic failures as safe as provider failures: no traceback,
        # response content, headers or request URL reaches public Actions logs.
        return {**report,'result':'INSPECTION_FAILED'},1


def main():
    report,code=inspect(os.getenv('GISTDA_API_KEY',''),os.getenv('GISTDA_PROBE_AREA',''),
                        lat=os.getenv('GISTDA_PROBE_LAT',''),lon=os.getenv('GISTDA_PROBE_LON',''),
                        version=os.getenv('GISTDA_PROBE_VERSION','v1.1'))
    print(json.dumps(report,ensure_ascii=True,allow_nan=False))
    raise SystemExit(code)


if __name__=='__main__':main()
