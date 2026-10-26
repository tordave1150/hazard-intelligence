import math
from datetime import date
from pipelines.shared.schemas import validate_record
from pipelines.shared.time_units import utc_now, instant, BANGKOK
from .data import DAMS, METADATA, SOURCE, PRODUCT, check_batch


def number(value):
    if value is None:
        return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise ValueError('Invalid RID numeric value')
    return value


def normalize(payload,fetched_at):
    report=date.fromisoformat(payload['date'])
    if report>instant(fetched_at).astimezone(BANGKOK).date():
        raise ValueError('Future RID report date')
    rows=[]
    for group in payload['data']:
        for item in group['dam']:
            meta=DAMS.get(item['id'])
            if meta is None or item['name'].strip()!=meta['name_th']:
                raise ValueError('Unverified RID identity or name change')
            normal=number(item['storage']); maximum=number(item['capacity'])
            volume=number(item['volume']); percent=number(item['percent_storage'])
            if normal is not None and maximum is not None and maximum<normal:
                raise ValueError('RID maximum capacity below normal storage capacity')
            if normal is not None and normal>0 and volume is not None and percent is not None:
                if abs(percent-volume/normal*100)>.08:
                    raise ValueError('RID percent does not match normal-capacity denominator')
            row={'schema_version':'2.0','source_id':'rid','product_id':PRODUCT,'data_state':'observed',**meta,
                'owner':item['owner'], 'source_region':group['region'],
                'normal_capacity_mcm':normal,'maximum_capacity_mcm':maximum,'storage_volume_mcm':volume,
                'storage_pct':percent,'report_date':report.isoformat(),'observed_at':None,'time_precision':'date',
                'fetched_at':fetched_at,'ingested_at':utc_now(),
                'quality_status':'partial' if any(v is None for v in [normal,maximum,volume,percent]) else 'valid',
                'unit_metadata':{'volume':'million m³','percentage':'% of normal storage capacity'},
                'source_url':SOURCE,'metadata_url':METADATA['source_page'],'license_url':METADATA['license_url']}
            rows.append(validate_record('DamObservation',row))
    if payload['total']!=len(rows):
        raise ValueError('RID declared count mismatch')
    check_batch(rows,[m['dam_id'] for m in DAMS.values()])
    return rows
