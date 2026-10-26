"""Read compatibility for the one independently verified historical ID error.

New publications must use canonical IDs. Never rewrite stored data, coordinates,
measurements or source times while reading a previously published generation.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS = json.loads((ROOT/'data/geography/dopa-corrections.json').read_text(encoding='utf-8'))


def canonical_stored_forecast(record):
    for alias in CORRECTIONS['id_aliases']:
        if record.get('location_id') == alias['from']:
            if record.get('point') != alias['point']:
                raise ValueError('Historical forecast identity has an unexpected point')
            return {**record, 'location_id': alias['to']}
    return record
