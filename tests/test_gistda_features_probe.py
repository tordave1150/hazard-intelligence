import json
import requests
import pytest
from scripts import probe_gistda_features as probe

KEY='test-only-feature-secret-not-a-real-key'


def page(features=None,matched=0):
    features=[] if features is None else features
    return {'type':'FeatureCollection','features':features,'numberMatched':matched,'numberReturned':len(features),
            'timeStamp':'2026-10-26T16:22:22.657Z','links':[{'href':'https://example.invalid/?api_key='+KEY}]}


class Response:
    def __init__(self,payload,status=200):self.raw=json.dumps(payload).encode();self.status_code=status
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,chunk_size):yield self.raw


def test_real_envelope_shape_empty_is_observed_without_link_or_key_exposure():
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(page())
    report,code=probe.inspect_features(KEY,get=get)
    assert code==0 and report['result']=='EMPTY_FEATURE_COLLECTION_OBSERVED'
    assert calls[0][0]==probe.BASE+'1day' and len(calls)==1
    assert calls[0][1]['headers']=={'Accept':'application/json','API-Key':KEY}
    assert calls[0][1]['params']=={'limit':1,'offset':0,'ap_idn':'2604'}
    assert not calls[0][1]['allow_redirects']
    output=json.dumps(report)
    assert KEY not in output and 'example.invalid' not in output and 'href' not in output
    assert 'links' not in report['response_structure']['fields']
    meta=report['page_metadata']
    assert meta['number_matched']==meta['number_returned']==0 and meta['empty_result']
    assert meta['returned_links_discarded']==1 and meta['acquisition_time_status']=='UNVERIFIED'
    assert meta['response_timestamp']=='2026-10-26T16:22:22.657Z'
    assert 'not satellite acquisition' in meta['timestamp_meaning']


def test_window_and_unfiltered_query_stay_explicit_without_paging_or_links():
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(page())
    report,code=probe.inspect_features(KEY,window='7days',ap_idn='',get=get)
    assert code==0 and report['product_window']=='7days'
    assert calls[0][0]==probe.BASE+'7days' and calls[0][1]['params']=={'limit':1,'offset':0}
    assert len(calls)==1


def test_nonempty_page_is_not_claimed_complete_or_source_accepted():
    row={'type':'Feature','id':'not-logged','properties':{'acquisition_date':'2026-10-25','private_ref':KEY},
         'geometry':{'type':'Polygon','coordinates':[[[100,13],[101,13],[101,14],[100,13]]]}}
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response(page([row],matched=10)))
    assert code==0 and report['result']=='FEATURE_PAGE_OBSERVED_SCHEMA_UNVERIFIED'
    assert not report['page_metadata']['complete_collection']
    assert KEY not in json.dumps(report) and 'not-logged' not in json.dumps(report)
    assert '2026-10-25' not in json.dumps(report)


@pytest.mark.parametrize('change',[{'numberReturned':True},{'numberMatched':-1},{'numberMatched':False},
    {'numberReturned':1},{'features':'bad'},{'type':'error'},{'timeStamp':'2026-10-26T16:22:22'},
    {'timeStamp':KEY},{'links':KEY}])
def test_malformed_metadata_does_not_become_a_valid_empty_collection(change):
    payload={**page(),**change}
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response(payload))
    assert code==1 and report['result']=='FEATURE_COLLECTION_SCHEMA_UNVERIFIED'
    assert KEY not in json.dumps(report)


def test_auth_http_error_and_redirect_never_become_valid_zero():
    for status,result in [(401,'AUTHENTICATION_OR_ENTITLEMENT_NOT_VERIFIED'),
                          (403,'AUTHENTICATION_OR_ENTITLEMENT_NOT_VERIFIED'),
                          (404,'HTTP_ERROR_NOT_AN_EMPTY_OBSERVATION'),(302,'REDIRECT_REJECTED')]:
        report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response({'message':KEY},status))
        assert code==1 and report['result']==result and 'page_metadata' not in report
        assert KEY not in json.dumps(report)


def test_invalid_inputs_are_rejected_before_network():
    def forbidden(*a,**k):raise AssertionError('must not call network')
    for key,window,area in [('', '1day','2604'),(KEY,'https://example.invalid/','2604'),
                            (KEY,'1day','undefined'),(KEY,'1day','9999'),(KEY,'1day','2604&api_key='+KEY)]:
        report,code=probe.inspect_features(key,window,area,get=forbidden)
        assert code==1 and KEY not in json.dumps(report)


def test_error_wrapped_in_http_200_is_not_accepted_as_an_empty_observation():
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response({**page(),'statusCode':503,'error':KEY}))
    assert code==1 and report['result']=='PROVIDER_ERROR_NOT_AN_EMPTY_OBSERVATION'
    assert 'page_metadata' not in report and KEY not in json.dumps(report)


def test_size_deadline_json_and_exception_failures_are_sanitized(monkeypatch):
    monkeypatch.setattr(probe,'MAX_BYTES',10)
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response(page()))
    assert code==1 and report['result']=='RESPONSE_TOO_LARGE'
    monkeypatch.setattr(probe,'MAX_BYTES',2*1024*1024)
    ticks=iter([0,46]);report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response(page()),clock=lambda:next(ticks))
    assert code==1 and report['result']=='DEADLINE_EXCEEDED'
    response=Response({});response.raw=b'not JSON '+KEY.encode()
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:response)
    assert code==1 and report['result']=='NON_JSON_RESPONSE' and KEY not in json.dumps(report)
    def fail(*a,**k):raise requests.ConnectionError('secret request detail '+KEY)
    report,code=probe.inspect_features(KEY,get=fail)
    assert code==1 and report['result']=='TRANSPORT_FAILURE' and KEY not in json.dumps(report)
