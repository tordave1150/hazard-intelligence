import json
import requests
from scripts import probe_gistda as probe

KEY='test-only-key-not-a-real-credential'


class Response:
    def __init__(self,payload,status=200):self.raw=json.dumps(payload).encode();self.status_code=status
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,chunk_size):yield self.raw


def test_structure_never_logs_values_or_reflected_keys():
    response={'message':'https://example.invalid/?api_key='+KEY,'api_key':KEY,KEY:'reflected',
              'data':[{'geometry':{'type':'Polygon','coordinates':[[[100,13]]]},'acquired_at':'2026-10-26T01:00:00Z'}]}
    output=json.dumps(probe.structure(response,KEY))
    assert KEY not in output and 'example.invalid' not in output and '2026-10-26' not in output
    assert 'geometry' in output and 'acquired_at' in output and 'Polygon' not in output


def test_one_request_only_to_selected_endpoint_and_no_guessed_area():
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response({'data':[]})
    result,code=probe.inspect(KEY,get=get)
    assert code==0 and result['result']=='RESPONSE_RECEIVED_SCHEMA_UNVERIFIED'
    assert len(calls)==1 and calls[0][0]==probe.ENDPOINT
    assert calls[0][1]['params']=={'api_key':KEY}
    assert calls[0][1]['allow_redirects'] is False and calls[0][1]['stream'] is True
    assert KEY not in json.dumps(result)


def test_explicit_area_is_encoded_as_data_and_not_reported():
    calls=[]
    def get(url,**kwargs):calls.append(kwargs);return Response({'data':[]})
    value='user-supplied documented area'
    result,code=probe.inspect(KEY,value,get=get)
    assert code==0 and calls[0]['params']['area']==value and result['area_supplied']
    assert value not in json.dumps(result)


def test_valid_coordinate_pair_is_sent_without_inventing_area():
    calls=[]
    def get(url,**kwargs):calls.append(kwargs);return Response({'data':[]})
    report,code=probe.inspect(KEY,get=get,lat='13.719961',lon='100.602017')
    assert code==0 and report['point_supplied'] and not report['area_supplied']
    assert calls[0]['params']=={'api_key':KEY,'lat':13.719961,'lon':100.602017}
    assert '13.719961' not in json.dumps(report)


def test_undefined_missing_nonfinite_and_out_of_range_points_never_call_provider():
    def forbidden(*a,**k):raise AssertionError('must not call network')
    for lat,lon in [('undefined','undefined'),('13',''),('','100'),('nan','100'),('13','inf'),
                    ('91','100'),('13','181'),('-91','100'),('13','-181'),(KEY,'100')]:
        report,code=probe.inspect(KEY,get=forbidden,lat=lat,lon=lon)
        assert code==1 and report['result']=='INVALID_POINT_INPUT' and KEY not in json.dumps(report)


def test_auth_redirect_and_http200_provider_error_are_not_data_success():
    for status,result,payload in [(407,'AUTHENTICATION_OR_ENTITLEMENT_NOT_VERIFIED',{'detail':'Authentication Required'}),
        (302,'REDIRECT_REJECTED',{}),(400,'HTTP_ERROR_REQUIRES_PARAMETER_OR_PROVIDER_REVIEW',{'message':KEY}),
        (200,'PROVIDER_ERROR_REQUIRES_REVIEW',{'statusCode':404,'message':KEY})]:
        report,code=probe.inspect(KEY,get=lambda *a,**k:Response(payload,status))
        assert code==1 and report['result']==result and KEY not in json.dumps(report)


def test_transport_exceptions_never_expose_prepared_url():
    def fail(*a,**k):raise requests.ConnectionError('https://example.invalid?api_key='+KEY)
    report,code=probe.inspect(KEY,get=fail)
    assert code==1 and report['result']=='TRANSPORT_FAILURE' and KEY not in json.dumps(report)
    def unexpected(*a,**k):raise RuntimeError('private provider detail '+KEY)
    report,code=probe.inspect(KEY,get=unexpected)
    assert code==1 and report['result']=='INSPECTION_FAILED' and KEY not in json.dumps(report)


def test_invalid_input_and_size_bound_stop_without_publication(monkeypatch):
    def forbidden(*a,**k):raise AssertionError('must not call network')
    for key,area in [('', ''),(KEY,'undefined'),(KEY,'null'),(KEY,'https://example.invalid?api_key='+KEY),
                     ('GISTDA_API_KEY='+KEY,'')]:
        report,code=probe.inspect(key,area,get=forbidden)
        assert code==1 and KEY not in json.dumps(report)
    monkeypatch.setattr(probe,'MAX_BYTES',10)
    report,code=probe.inspect(KEY,get=lambda *a,**k:Response({'message':'x'*100}))
    assert code==1 and report['result']=='RESPONSE_TOO_LARGE'
    monkeypatch.setattr(probe,'MAX_BYTES',2*1024*1024)
    ticks=iter([0,46])
    report,code=probe.inspect(KEY,get=lambda *a,**k:Response({}),clock=lambda:next(ticks))
    assert code==1 and report['result']=='DEADLINE_EXCEEDED'
    response=Response({});response.raw=b'not JSON '+KEY.encode()
    report,code=probe.inspect(KEY,get=lambda *a,**k:response)
    assert code==1 and report['result']=='NON_JSON_RESPONSE' and KEY not in json.dumps(report)
