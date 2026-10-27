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
destination = Path(__file__).resolve().parents[1] / 'packages/contracts/schema.json'
destination.write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://hazard.local/contracts/2.0','$defs':defs},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
