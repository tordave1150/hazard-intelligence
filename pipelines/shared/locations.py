import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_areas():
    return json.loads((ROOT / 'apps/web/data/areas.json').read_text(encoding='utf-8'))


def weather_locations(level='all'):
    areas = load_areas()
    return [a for a in areas if a['level'] in ({'province', 'district'} if level == 'all' else {level})]
