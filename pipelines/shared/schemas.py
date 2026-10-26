import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .time_units import instant

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / 'packages/contracts/schema.json').read_text(encoding='utf-8'))


def validate_record(kind, record):
    validator = Draft202012Validator({**SCHEMA, '$ref': f'#/$defs/{kind}'}, format_checker=FormatChecker())
    validator.validate(record)
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
    return record
