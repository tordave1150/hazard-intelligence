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
    assert calls[0][0]==probe.BASE+'3days' and len(calls)==1
    assert calls[0][1]['headers']=={'Accept':'application/json','API-Key':KEY}
    assert calls[0][1]['params']=={'limit':1,'offset':0}
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


def test_full_observed_property_count_stays_bounded_without_exposing_values_or_secret_names():
    properties={f'field_{i}':i for i in range(27)}
    properties.update({'survey_date':'2026-10-25',KEY:KEY,'api_key':KEY})
    properties.update({f'extra_{i}':KEY for i in range(50)})
    row={'type':'Feature','properties':properties,'geometry':None}
    report,code=probe.inspect_features(KEY,get=lambda *a,**k:Response(page([row],matched=184323)))
    assert code==0
    fields=report['response_structure']['fields']['features']['first_item']['fields']['properties']['fields']
    assert fields['survey_date']=={'type':'string'} and len(fields)<=48
    assert 'api_key' not in fields and KEY not in json.dumps(report) and '2026-10-25' not in json.dumps(report)


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


def test_reviewed_request_uses_only_allowed_products_filters_and_public_ids(tmp_path):
    request={'request_id':'2026-10-27-01','window':'30days','ap_idn':''}
    path=tmp_path/'request.json';path.write_text(json.dumps(request),encoding='utf-8')
    assert probe.load_reviewed_request(path)==request
    for change in [{'endpoint':'https://example.invalid/'},{'api_key':KEY},{'window':'https://example.invalid/'},
                   {'ap_idn':'9999'},{'ap_idn':None},{'request_id':KEY}]:
        path.write_text(json.dumps({**request,**change}),encoding='utf-8')
        with pytest.raises(ValueError):probe.load_reviewed_request(path)
    path.write_text(' '*1025,encoding='utf-8')
    with pytest.raises(ValueError):probe.load_reviewed_request(path)


def test_reviewed_request_selects_explicit_window_without_manual_environment_fallback(tmp_path,monkeypatch,capsys):
    path=tmp_path/'request.json'
    path.write_text(json.dumps({'request_id':'2026-10-27-01','window':'30days','ap_idn':''}),encoding='utf-8')
    monkeypatch.setattr(probe,'REQUEST_PATH',path)
    monkeypatch.setenv('GISTDA_API_KEY',KEY)
    monkeypatch.setenv('GISTDA_FEATURE_WINDOW','1day');monkeypatch.setenv('GISTDA_FEATURE_AP_IDN','2604')
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(page())
    monkeypatch.setattr(probe.requests,'get',get)
    with pytest.raises(SystemExit) as exit:probe.main(reviewed_request=True)
    assert exit.value.code==0 and len(calls)==1
    assert calls[0][0]==probe.BASE+'30days' and calls[0][1]['params']=={'limit':1,'offset':0}
    output=capsys.readouterr().out
    assert json.loads(output)['reviewed_request_id']=='2026-10-27-01' and KEY not in output
    path.write_text('{broken',encoding='utf-8')
    with pytest.raises(SystemExit) as exit:probe.main(reviewed_request=True)
    assert exit.value.code==1 and len(calls)==1
    assert json.loads(capsys.readouterr().out)=={'result':'INVALID_REVIEWED_REQUEST'}


@pytest.mark.parametrize('query_scope',[None,'national'])
def test_manual_national_scope_ignores_retained_district_default(query_scope,monkeypatch,capsys):
    monkeypatch.setenv('GISTDA_API_KEY',KEY)
    monkeypatch.setenv('GISTDA_FEATURE_WINDOW','7days')
    monkeypatch.setenv('GISTDA_FEATURE_AP_IDN','2604')
    monkeypatch.setenv('GISTDA_INSPECTION_SERVICE','features')
    if query_scope is None:monkeypatch.delenv('GISTDA_QUERY_SCOPE',raising=False)
    else:monkeypatch.setenv('GISTDA_QUERY_SCOPE',query_scope)
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(page())
    monkeypatch.setattr(probe.requests,'get',get)
    with pytest.raises(SystemExit) as exit:probe.main()
    assert exit.value.code==0 and len(calls)==1
    assert calls[0][0]==probe.BASE+'7days'
    assert calls[0][1]['params']=={'limit':1,'offset':0}
    report=json.loads(capsys.readouterr().out)
    assert report['requested_scope']=='national' and report['requested_filter']['ap_idn'] is None


def test_manual_district_scope_requires_explicit_nonempty_code(monkeypatch,capsys):
    monkeypatch.setenv('GISTDA_API_KEY',KEY)
    monkeypatch.setenv('GISTDA_QUERY_SCOPE','district')
    monkeypatch.setenv('GISTDA_FEATURE_WINDOW','7days')
    monkeypatch.setenv('GISTDA_INSPECTION_SERVICE','features')
    monkeypatch.setenv('GISTDA_FEATURE_AP_IDN','2604')
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(page())
    monkeypatch.setattr(probe.requests,'get',get)
    with pytest.raises(SystemExit) as exit:probe.main()
    assert exit.value.code==0 and calls[0][1]['params']['ap_idn']=='2604'
    assert json.loads(capsys.readouterr().out)['requested_scope']=='district'
    monkeypatch.setenv('GISTDA_FEATURE_AP_IDN',' ')
    with pytest.raises(SystemExit) as exit:probe.main()
    assert exit.value.code==1 and len(calls)==1
    assert json.loads(capsys.readouterr().out)=={'result':'DISTRICT_FILTER_REQUIRED'}


def test_invalid_manual_scope_never_becomes_an_unfiltered_request(monkeypatch,capsys):
    monkeypatch.setenv('GISTDA_QUERY_SCOPE',KEY)
    def forbidden(*args,**kwargs):pytest.fail('Invalid scope must not make a request')
    monkeypatch.setattr(probe.requests,'get',forbidden)
    with pytest.raises(SystemExit) as exit:probe.main()
    assert exit.value.code==1
    assert json.loads(capsys.readouterr().out)=={'result':'INVALID_QUERY_SCOPE'}


def stac_item(**times):
    return {'type':'Feature','stac_version':'1.0.0','id':'not-logged','geometry':None,
            'properties':{'datetime':'2026-10-26T00:00:00Z',**times},
            'links':[{'href':'https://example.invalid/?api_key='+KEY}],
            'assets':{'raster':{'href':'https://example.invalid/?api_key='+KEY}}}


def test_documented_stac_item_is_one_header_request_without_asset_or_link_following():
    calls=[]
    def get(url,**kwargs):calls.append((url,kwargs));return Response(stac_item())
    report,code=probe.inspect_features(KEY,'1day','',get=get,service='stac')
    assert code==0 and report['result']=='STAC_ITEM_OBSERVED_SCHEMA_UNVERIFIED' and len(calls)==1
    assert calls[0][0]=='https://api-gateway.gistda.or.th/api/2.0/resources/stac/flood/collections/flood1day_r2/items/items_flood1day_r2'
    assert calls[0][1]['params']=={} and calls[0][1]['headers']['API-Key']==KEY
    assert not calls[0][1]['allow_redirects']
    assert not {'links','assets'}&set(report['response_structure']['fields'])
    metadata=report['stac_metadata']
    assert metadata['item_temporal_metadata']['datetime']=='2026-10-26T00:00:00Z'
    assert metadata['acquisition_time_status']=='UNVERIFIED' and 'nominal' in metadata['temporal_meaning']
    assert metadata['returned_assets_not_followed']==metadata['returned_links_discarded']==1
    assert KEY not in json.dumps(report) and 'example.invalid' not in json.dumps(report) and 'not-logged' not in json.dumps(report)


@pytest.mark.parametrize('change',[{'datetime':KEY},{'datetime':'2026-10-26T07:00:00+07:00'},
    {'datetime':'2026-10-26T00:00:00-00:00'},{'datetime':'2026-10-26'},
    {'datetime':None,'start_datetime':'2026-10-26T00:00:00Z'},
    {'datetime':None,'start_datetime':'2026-10-26T00:00:00Z','end_datetime':'2026-10-25T00:00:00Z'}])
def test_stac_time_errors_do_not_publish_dates_or_expose_values(change):
    report,code=probe.inspect_features(KEY,'1day','',get=lambda *a,**k:Response(stac_item(**change)),service='stac')
    assert code==1 and report['result']=='STAC_ITEM_SCHEMA_UNVERIFIED' and 'stac_metadata' not in report
    assert KEY not in json.dumps(report)


def test_stac_interval_is_reported_as_item_metadata_not_feature_acquisition():
    payload=stac_item(datetime=None,start_datetime='2026-09-27T00:00:00Z',end_datetime='2026-10-26T23:59:59Z')
    report,code=probe.inspect_features(KEY,'30days','',get=lambda *a,**k:Response(payload),service='stac')
    assert code==0 and report['product_window']=='30days'
    assert report['stac_metadata']['temporal_status']=='PRESENT_MEANING_UNVERIFIED'
    assert report['stac_metadata']['acquisition_time_status']=='UNVERIFIED'


def test_service_and_stac_filter_validation_prevent_network_and_arbitrary_targets(tmp_path):
    def forbidden(*a,**k):raise AssertionError('must not call network')
    for service,ap_idn in [('https://example.invalid/',''),('stac','2604')]:
        report,code=probe.inspect_features(KEY,ap_idn=ap_idn,service=service,get=forbidden)
        assert code==1 and report['result'] in ['INVALID_SERVICE','INVALID_STAC_FILTER']
    path=tmp_path/'request.json'
    request={'request_id':'2026-10-27-03','service':'stac','window':'1day','ap_idn':''}
    path.write_text(json.dumps(request),encoding='utf-8');assert probe.load_reviewed_request(path)==request
    for change in [{'service':'https://example.invalid/'},{'ap_idn':'2604'}]:
        path.write_text(json.dumps({**request,**change}),encoding='utf-8')
        with pytest.raises(ValueError):probe.load_reviewed_request(path)
