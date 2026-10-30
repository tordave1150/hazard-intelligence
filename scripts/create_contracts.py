"""Reproducible language-neutral contracts; no database-specific fields."""
import json
from pathlib import Path

string = {'type': 'string', 'minLength': 1}
time = {'type': 'string', 'format': 'date-time', 'pattern': r'(Z|\+00:00)$'}
nullable_time = {'anyOf': [time, {'type': 'null'}]}
number = {'type': ['number', 'null']}
nonnegative = {**number, 'minimum': 0}
pct = {**number, 'minimum': 0, 'maximum': 100}


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': required or list(properties), 'additionalProperties': False}


point = obj({'lat': {'type': 'number', 'minimum': -90, 'maximum': 90}, 'lon': {'type': 'number', 'minimum': -180, 'maximum': 180}})
common = {'schema_version': {'const': '2.0'}, 'source_id': string, 'data_state': string, 'ingested_at': time}
flood_position = {'type':'array','minItems':2,'maxItems':3,'items':{'type':'number'}}
flood_ring = {'type':'array','minItems':4,'maxItems':20000,'items':flood_position}
flood_polygon = {'type':'array','minItems':1,'maxItems':256,'items':flood_ring}
flood_geometry = {'anyOf':[
    obj({'type':{'const':'Polygon'},'coordinates':flood_polygon}),
    obj({'type':{'const':'MultiPolygon'},'coordinates':{'type':'array','minItems':1,'maxItems':256,'items':flood_polygon}})]}
defs = {
    'Area': obj({'id': string, 'level': {'enum': ['national','region','province','district','basin']}, 'parent_id': {'type': ['string','null']},
                 'name': string, 'name_th': string, 'region_id': {'type': ['string','null']}, 'province_id': {'type': ['string','null']},
                 'lat': point['properties']['lat'], 'lon': point['properties']['lon'],
                 'bbox': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 4, 'maxItems': 4},
                 'geometry_ref': string, 'code_status': string}),
    'Forecast': obj({**common, 'source_id': {'const': 'open_meteo'}, 'product_id': {'const': 'daily_forecast'},
        'location_id': {'type': 'string', 'pattern': '^TH-(P-[0-9]{2}|D-[0-9]{4})$'}, 'data_state': {'const': 'forecast'},
        'forecast_reference_time': nullable_time, 'fetched_at': time, 'point': point, 'model_point': point,
        'spatial_method': string, 'quality_status': {'enum': ['valid','partial']}, 'source_url': {'type': 'string','format':'uri'},
        'units': obj({'rainfall': {'const':'mm/24h'}, 'probability': {'const':'%'}, 'temperature': {'const':'°C'}}),
        'valid_periods': {'type': 'array', 'minItems': 1, 'maxItems': 7, 'items': obj({
            'date': {'type':'string','format':'date'}, 'valid_start':time, 'valid_end':time,
            'rainfall_mm':nonnegative, 'rain_probability_pct':pct, 'temp_max_c':number, 'temp_min_c':number})}}),
    'WeatherObservation': obj({**common, 'data_state': {'const':'observed'}, 'location_id':string, 'point':point,
        'metric_type':string, 'value':number, 'unit':string, 'observed_at':time, 'fetched_at':time, 'quality_status':string}),
    'WaterGauge': obj({**common, 'data_state':{'const':'observed'}, 'gauge_id':string, 'point':point,
        'metric_type':{'enum':['river_level','rainfall']}, 'value':number, 'unit':string, 'observed_at':time,
        'fetched_at':time, 'station_datum':{'type':['string','null']}, 'threshold_definition':{'type':['string','null']}}),
    'DamObservation': obj({**common, 'source_id':{'const':'rid'}, 'product_id':{'const':'daily_dam_storage'},
        'data_state':{'const':'observed'}, 'dam_id':{'type':'string','pattern':'^RID-DAM-[0-9]{6}$'},
        'source_dam_id':{'type':'string','pattern':'^[0-9]{6}$'}, 'name_th':string, 'owner':string,
        'point':point, 'province_id':{'type':'string','pattern':'^TH-P-[0-9]{2}$'},
        'district_id':{'type':['string','null'],'pattern':'^TH-D-[0-9]{4}$'}, 'region_id':string, 'source_region':string,
        'normal_capacity_mcm':nonnegative, 'maximum_capacity_mcm':nonnegative, 'storage_volume_mcm':nonnegative,
        'storage_pct':nonnegative, 'report_date':{'type':'string','format':'date'},
        'observed_at':{'type':'null'}, 'time_precision':{'const':'date'}, 'fetched_at':time,
        'quality_status':{'enum':['valid','partial']},
        'unit_metadata':obj({'volume':{'const':'million m³'},'percentage':{'const':'% of normal storage capacity'}}),
        'source_url':{'type':'string','format':'uri'}, 'metadata_url':{'type':'string','format':'uri'},
        'license_url':{'type':'string','format':'uri'}}),
    'SatelliteFloodProduct': obj({**common, 'data_state':{'const':'satellite_observation'}, 'product_id':string,
        'satellite':string, 'satellite_acquired_at':time, 'published_at':nullable_time, 'fetched_at':time,
        'coverage_id':string, 'tile_or_layer_ref':{'type':'string','format':'uri'}, 'processing_method':string,
        'product_quality':string, 'license_metadata':string}),
    'AgencyWarning': obj({**common, 'source_id':{'const':'tmd'}, 'product_id':{'const':'cap_warnings'},
        'data_state':{'const':'agency_warning'}, 'warning_id':string, 'sender':{'const':'TMD'},
        'message_type':{'enum':['Alert','Update','Cancel']}, 'status':{'const':'Actual'}, 'scope':{'const':'Public'},
        'references':{'type':'array','maxItems':100,'items':obj({'sender':string,'warning_id':string,'issued_at':time})},
        'issued_at':time, 'fetched_at':time, 'effective_start':nullable_time, 'expires_at':nullable_time,
        'effective_time_source':{'enum':['CAP effective','CAP sent','not supplied']},
        'language':{'type':['string','null']}, 'event':{'type':['string','null']}, 'headline':{'type':['string','null']},
        'description':{'type':['string','null']}, 'instruction':{'type':['string','null']},
        'agency_severity':{'enum':['Extreme','Severe','Moderate','Minor','Unknown',None]},
        'urgency':{'enum':['Immediate','Expected','Future','Past','Unknown',None]},
        'certainty':{'enum':['Observed','Likely','Possible','Unlikely','Unknown',None]},
        'area_ids':{'type':'array','uniqueItems':True,'maxItems':77,'items':{'type':'string','pattern':'^TH-P-[0-9]{2}$'}},
        'source_areas':{'type':'array','maxItems':100,'items':obj({'description':string,
            'geocodes':{'type':'array','maxItems':100,'items':obj({'value_name':string,'value':string})}})},
        'geometry':{'anyOf':[{'type':'null'},obj({'type':{'const':'MultiPolygon'},'coordinates':{'type':'array','maxItems':1000,'items':{
            'type':'array','minItems':1,'maxItems':1,'items':{'type':'array','minItems':4,'maxItems':20000,
            'items':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'number'}}}}}})]},
        'content_ref':{'type':'string','format':'uri'}, 'source_url':{'const':'https://www.tmd.go.th/api/xml/CAP'},
        'terms_url':{'const':'https://www.tmd.go.th/content/copyright'}}),
    'WarningFeed': obj({**common, 'source_id':{'const':'tmd'}, 'product_id':{'const':'cap_warnings'},
        'data_state':{'const':'agency_warning'}, 'snapshot_id':{'const':'latest'}, 'fetched_at':time,
        'feed_generated_at':time, 'feed_url':{'const':'https://www.tmd.go.th/api/xml/CAP'},
        'feed_copyright':{'const':'public domain'}, 'feed_item_count':{'type':'integer','minimum':0,'maximum':50},
        'ignored_item_count':{'type':'integer','minimum':0,'maximum':50},
        'records':{'type':'array','maxItems':50,'items':{'$ref':'#/$defs/AgencyWarning'}}}),
    # Retired stored-envelope identity for explicit historical audits only.
    'GistdaFloodFeed': obj({**common,'source_id':{'const':'gistda'},'product_id':{'const':'flood_1day_ongkharak'},
        'data_state':{'const':'satellite_observation'},'snapshot_id':{'const':'latest'},'product_window':{'const':'1day'},
        'area_id':{'const':'TH-D-2604'},'query':obj({'ap_idn':{'const':'2604'},'limit':{'const':100},'offset':{'const':0}}),
        'source_url':{'const':'https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/1day'},
        'attribution':{'const':'GISTDA Disaster Platform'},'response_at':time,'fetched_at':time,'observed_at':{'type':'null'},
        'observation_time_status':{'const':'NOT_SUPPLIED'},'complete_provider_query':{'const':True},
        'record_count':{'type':'integer','minimum':0,'maximum':100},'coverage':string,
        'area_metrics':{'const':'NOT_USED_UNITS_UNVERIFIED'},'interpretation':string,
        'records':{'type':'array','maxItems':100,'items':obj({'type':{'const':'Feature'},
            'id':{'type':'string','pattern':'^[a-f0-9]{24}-[0-9]{1,2}$'},'geometry':flood_geometry,'properties':{'type':'null'}})}}),
    'SourceStatus': obj({'source_id':string, 'product_id':string, 'last_attempt':nullable_time, 'last_success':nullable_time,
        'reference_time':nullable_time, 'status':{'enum':['FRESH','DELAYED','STALE','UNAVAILABLE','UNKNOWN']},
        'completeness':{'type':['number','null'],'minimum':0,'maximum':1}, 'integration_status':string,
        'error_summary':{'type':['string','null']}})
}
from copy import deepcopy
defs['AgencyWarning']['properties']['time_quality']={'enum':['VALID_INTERVAL','NOT_SUPPLIED','INVALID_PROVIDER_INTERVAL']}
national_flood = deepcopy(defs['GistdaFloodFeed'])
national_props = national_flood['properties']
national_props.update(product_id={'const':'flood_1day_thailand'}, area_id={'const':'TH'},
    query=obj({'limit':{'const':100},'offset':{'const':0}}),
    page_count={'type':'integer','minimum':1,'maximum':10},
    pagination_consistency={'const':'COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN'})
national_props['record_count']['maximum'] = national_props['records']['maxItems'] = 1000
national_feature = national_props['records']['items']
national_feature['properties']['id']['pattern'] = '^[a-f0-9]{24}-[0-9]{1,3}$'
national_feature['properties']['area_ids'] = {'type':'array','minItems':2,'maxItems':2,
    'prefixItems':[{'type':'string','pattern':'^TH-P-[0-9]{2}$'},{'type':'string','pattern':'^TH-D-[0-9]{4}$'}], 'items':False}
national_feature['required'].append('area_ids')
national_flood['required'] += ['page_count','pagination_consistency']
defs['GistdaNationalFloodFeed'] = national_flood

# The current three-day product is stored and served in bounded chunks, while
# the earlier one-day contracts remain available only for historical auditing.
from pipelines.gistda import limits as flood_limits
three_day = deepcopy(national_flood)
three_props = three_day['properties']
three_props.update(product_id={'const':flood_limits.PRODUCT}, product_window={'const':'3days'},
    source_url={'const':flood_limits.ENDPOINT}, page_count={'type':'integer','minimum':1,'maximum':flood_limits.MAX_PAGES})
three_props['record_count']['maximum'] = three_props['records']['maxItems'] = flood_limits.MAX_FEATURES
three_props['records']['items']['properties']['id']['pattern'] = '^[a-f0-9]{24}-[0-9]{1,5}$'
defs['GistdaThreeDayFeed'] = three_day
metadata = deepcopy(three_day)
del metadata['properties']['records']
metadata['required'].remove('records')
defs['GistdaThreeDayMetadata'] = metadata
defs['GistdaThreeDayChunk'] = obj({'source_id':{'const':'gistda'},'product_id':{'const':flood_limits.PRODUCT},
    'chunk_id':{'type':'string','pattern':'^[0-9]{4}$'},
    'chunk_count':{'type':'integer','minimum':1,'maximum':flood_limits.MAX_CHUNKS},
    'feed':{'$ref':'#/$defs/GistdaThreeDayMetadata'},
    'records':{'type':'array','maxItems':flood_limits.CHUNK_FEATURES,'items':deepcopy(three_props['records']['items'])}})

# Preserve the independently introduced hourly contract in reproducible generation.
defs['HourlyForecast'] = {'type': 'object',
 'properties': {'schema_version': {'const': '2.0'},
                'source_id': {'const': 'open_meteo'},
                'data_state': {'const': 'forecast'},
                'ingested_at': {'type': 'string',
                                'format': 'date-time',
                                'pattern': '(Z|\\+00:00)$'},
                'product_id': {'const': 'today_hourly'},
                'location_id': {'type': 'string', 'pattern': '^TH-(P-[0-9]{2}|D-[0-9]{4})$'},
                'forecast_reference_time': {'type': 'null'},
                'fetched_at': {'type': 'string', 'format': 'date-time', 'pattern': '(Z|\\+00:00)$'},
                'point': {'type': 'object',
                          'properties': {'lat': {'type': 'number', 'minimum': -90, 'maximum': 90},
                                         'lon': {'type': 'number',
                                                 'minimum': -180,
                                                 'maximum': 180}},
                          'required': ['lat', 'lon'],
                          'additionalProperties': False},
                'model_point': {'type': 'object',
                                'properties': {'lat': {'type': 'number',
                                                       'minimum': -90,
                                                       'maximum': 90},
                                               'lon': {'type': 'number',
                                                       'minimum': -180,
                                                       'maximum': 180}},
                                'required': ['lat', 'lon'],
                                'additionalProperties': False},
                'spatial_method': {'type': 'string', 'minLength': 1},
                'source_url': {'const': 'https://open-meteo.com/en/docs'},
                'units': {'type': 'object',
                          'properties': {'rainfall': {'const': 'mm/1h'},
                                         'probability': {'const': '%'},
                                         'temperature': {'const': '°C'}},
                          'required': ['rainfall', 'probability', 'temperature'],
                          'additionalProperties': False},
                'forecast_date': {'type': 'string', 'format': 'date'},
                'valid_hours': {'type': 'array',
                                'minItems': 24,
                                'maxItems': 24,
                                'items': {'type': 'object',
                                          'properties': {'valid_start': {'type': 'string',
                                                                         'format': 'date-time',
                                                                         'pattern': '(Z|\\+00:00)$'},
                                                         'valid_end': {'type': 'string',
                                                                       'format': 'date-time',
                                                                       'pattern': '(Z|\\+00:00)$'},
                                                         'temperature_valid_at': {'type': 'string',
                                                                                  'format': 'date-time',
                                                                                  'pattern': '(Z|\\+00:00)$'},
                                                         'rainfall_mm': {'type': ['number', 'null'],
                                                                         'minimum': 0},
                                                         'rain_probability_pct': {'type': ['number',
                                                                                           'null'],
                                                                                  'minimum': 0,
                                                                                  'maximum': 100},
                                                         'temperature_c': {'type': ['number',
                                                                                    'null']}},
                                          'required': ['valid_start',
                                                       'valid_end',
                                                       'temperature_valid_at',
                                                       'rainfall_mm',
                                                       'rain_probability_pct',
                                                       'temperature_c'],
                                          'additionalProperties': False}}},
 'required': ['schema_version',
              'source_id',
              'data_state',
              'ingested_at',
              'product_id',
              'location_id',
              'forecast_reference_time',
              'fetched_at',
              'point',
              'model_point',
              'spatial_method',
              'source_url',
              'units',
              'forecast_date',
              'valid_hours'],
 'additionalProperties': False}

from pipelines.thaiwater.contracts import definitions as thaiwater_definitions
defs.update(thaiwater_definitions())
destination = Path(__file__).resolve().parents[1] / 'packages/contracts/schema.json'
destination.write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://hazard.local/contracts/2.0','$defs':defs},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
