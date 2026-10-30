def definitions():
    def obj(properties):
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    text={'type':'string','minLength':1,'maxLength':256}
    nullable_text={'type':['string','null'],'maxLength':256}
    instant={'type':'string','format':'date-time','pattern':r'(Z|\+00:00)$'}
    count={'type':'integer','minimum':0,'maximum':10000}
    point=obj({'lat':{'type':'number','minimum':5,'maximum':22},'lon':{'type':'number','minimum':96,'maximum':107}})
    station=obj({'gauge_id':{'type':'string','pattern':'^THW-[0-9]{1,12}$'},
        'source_station_id':{'type':'string','pattern':'^[0-9]{1,12}$'},'station_code':nullable_text,
        'name_th':nullable_text,'name_en':nullable_text,'agency_name':nullable_text,'agency_id':nullable_text,
        'province_id':{'type':'string','pattern':'^TH-P-[0-9]{2}$'},
        'district_id':{'type':['string','null'],'pattern':'^TH-D-[0-9]{4}$'},'region_id':text,
        'point':{'anyOf':[point,{'type':'null'}]},'source_observed_at':{'type':['string','null'],'maxLength':40},
        'observed_at':{'type':'null'},'observation_time_status':{'const':'TIMEZONE_NOT_SUPPLIED'},
        'water_level_msl':{'type':['number','null'],'minimum':-10000,'maximum':10000},
        'water_level_m':{'type':['number','null'],'minimum':-10000,'maximum':10000},
        'quality_flags':{'type':'array','uniqueItems':True,'maxItems':5,'items':{'enum':[
            'INVALID_POINT','INVALID_PROVIDER_TIME','INVALID_LEVEL','NO_LEVEL','UNRECOGNIZED_DISTRICT']}}})
    feed=obj({'schema_version':{'const':'2.0'},'source_id':{'const':'thaiwater'},
        'product_id':{'const':'national_waterlevel'},'data_state':{'const':'observed'},'snapshot_id':{'const':'latest'},
        'source_url':{'const':'https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load'},
        'fetched_at':instant,'ingested_at':instant,'record_count':count,'provider_automatic_count':count,
        'provider_manual_count':count,'provider_response_accounted_for':{'const':True},
        'excluded_stations':{'type':'array','maxItems':10000,'items':obj({'source_station_id':text,
            'provider_province_code':nullable_text,'provider_area_name':nullable_text,'reason':{'const':'NOT_CANONICAL_THAI_PROVINCE'}})},
        'coverage_by_province':{'type':'array','maxItems':77,'items':obj({'area_id':{'type':'string','pattern':'^TH-P-[0-9]{2}$'},'record_count':count})},
        'quality_issue_count':count,'time_unknown_count':count,'records':{'type':'array','maxItems':5000,'items':station},
        'coverage':text,'units':obj({'water_level_msl':{'const':'m above mean sea level'},'water_level_m':{'const':'m as reported'}})})
    from copy import deepcopy
    rain=deepcopy(station);rp=rain['properties'];rp['gauge_id']['pattern']='^THR-[0-9]{1,12}$'
    for k in ['water_level_msl','water_level_m']:del rp[k]
    rp.update(rain_24h_mm={'type':['number','null'],'minimum':0,'maximum':5000},rain_1h_mm={'type':['number','null'],'minimum':0,'maximum':1000},
        district_mapping={'enum':['EXACT_NAME_WITHIN_PROVIDER_PROVINCE','UNCONFIRMED']})
    rp['quality_flags']['items']['enum']=['INVALID_POINT','INVALID_PROVIDER_TIME','INVALID_RAIN','NO_24H_RAIN'];rain['required']=list(rp)
    rainfeed=deepcopy(feed);fp=rainfeed['properties'];del fp['provider_manual_count']
    fp['product_id']={'const':'national_rain_24h'};fp['source_url']={'const':'https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h'}
    fp['records']={'type':'array','maxItems':10000,'items':rain}
    fp['units']=obj({'rain_24h_mm':{'const':'mm / 24h as reported'},'rain_1h_mm':{'const':'mm / 1h as reported'}})
    fp.update(window_start={'type':'null'},window_end={'type':'null'});rainfeed['required']=list(fp)
    return {'ThaiWaterStation':station,'ThaiWaterFeed':feed,'ThaiWaterRainStation':rain,'ThaiWaterRainFeed':rainfeed}
