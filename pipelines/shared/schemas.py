import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .time_units import instant

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'packages/contracts/schema.json').read_text(encoding='utf-8'))


def validate_record(kind, record):
    validator = Draft202012Validator({**SCHEMA, '$ref': f'#/$defs/{kind}'}, format_checker=FormatChecker())
    validator.validate(record)
    if kind == 'HourlyForecast':
        from pipelines.open_meteo.hourly import check_record
        check_record(record)
    if kind == 'Forecast':
        dates = [p['date'] for p in record['valid_periods']]
        if dates != sorted(set(dates)):
            raise ValueError('Forecast dates must be unique and ascending')
        for period in record['valid_periods']:
            if instant(period['valid_end']) - instant(period['valid_start']) != __import__('datetime').timedelta(days=1):
                raise ValueError('Daily accumulation must span 24 hours')
            from .time_units import daily_period
            if (period['valid_start'], period['valid_end']) != daily_period(period['date']):
                raise ValueError('Daily period must follow Asia/Bangkok local date')
        if instant(record['fetched_at']) > instant(record['ingested_at']):
            raise ValueError('Ingestion cannot precede retrieval')
    if kind == 'DamObservation':
        from datetime import date
        from pipelines.shared.time_units import BANGKOK
        from pipelines.rid.data import DAMS, METADATA, SOURCE
        meta=DAMS.get(record['source_dam_id'])
        if meta is None or any(record[key]!=value for key,value in meta.items()):
            raise ValueError('Unverified RID identity or point metadata')
        if record['source_url']!=SOURCE or record['metadata_url']!=METADATA['source_page'] or record['license_url']!=METADATA['license_url']:
            raise ValueError('Unverified RID provenance')
        if instant(record['fetched_at'])>instant(record['ingested_at']):
            raise ValueError('Ingestion cannot precede retrieval')
        if date.fromisoformat(record['report_date'])>instant(record['fetched_at']).astimezone(BANGKOK).date():
            raise ValueError('Future RID report date')
        normal=record['normal_capacity_mcm'];maximum=record['maximum_capacity_mcm']
        volume=record['storage_volume_mcm'];percent=record['storage_pct']
        if normal is not None and maximum is not None and maximum<normal:
            raise ValueError('RID maximum capacity below normal capacity')
        if normal is not None and normal>0 and volume is not None and percent is not None and abs(percent-volume/normal*100)>.08:
            raise ValueError('Invalid RID percentage denominator')
    if kind in ['AgencyWarning','WarningFeed']:
        from pipelines.tmd.data import check_warning,check_feed
        (check_warning if kind=='AgencyWarning' else check_feed)(record)
    if kind == 'GistdaFloodFeed':
        from pipelines.gistda.data import check_feed
        check_feed(record)
    if kind == 'GistdaNationalFloodFeed':
        from pipelines.gistda.data import check_feed
        check_feed(record, national=True)
    if kind == 'GistdaThreeDayFeed':
        from pipelines.gistda.data import check_feed
        check_feed(record, national=True)
    return record
