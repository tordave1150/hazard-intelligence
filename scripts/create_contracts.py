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
    'AgencyWarning': obj({**common, 'data_state':{'const':'agency_warning'}, 'warning_id':string,
        'area_ids':{'type':'array','items':string,'minItems':1,'maxItems':1200}, 'issued_at':time,
        'effective_start':time, 'expires_at':time, 'agency_severity':string,
        'content_ref':{'type':'string','format':'uri'}, 'last_updated_at':time}),
    'SourceStatus': obj({'source_id':string, 'product_id':string, 'last_attempt':nullable_time, 'last_success':nullable_time,
        'reference_time':nullable_time, 'status':{'enum':['FRESH','DELAYED','STALE','UNAVAILABLE','UNKNOWN']},
        'completeness':{'type':['number','null'],'minimum':0,'maximum':1}, 'integration_status':string,
        'error_summary':{'type':['string','null']}})
}
destination = Path(__file__).resolve().parents[1] / 'packages/contracts/schema.json'
destination.write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://hazard.local/contracts/2.0','$defs':defs},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
