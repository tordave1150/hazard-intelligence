import os
import time
import requests
from pipelines.shared.time_units import utc_now

DAILY = 'precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min'


def fetch_batch(locations, session=None, sleep=time.sleep):
    """One multi-coordinate request, with conservative bounded retries.

    API accounting still charges each coordinate; batching is not a quota bypass.
    No raw response or key is logged.
    """
    session = session or requests.Session()
    key = os.getenv('OPEN_METEO_API_KEY')
    url = 'https://customer-api.open-meteo.com/v1/forecast' if key else 'https://api.open-meteo.com/v1/forecast'
    params = {'latitude': ','.join(str(x['lat']) for x in locations), 'longitude': ','.join(str(x['lon']) for x in locations),
              'daily': DAILY, 'timezone': 'Asia/Bangkok', 'forecast_days': 4}
    if key:
        params['apikey'] = key
    for attempt in range(4):
        try:
            response = session.get(url, params=params, timeout=(10, 60))
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 3:
                    raise RuntimeError('Provider unavailable after retries')
                delay = min(120, max(2 ** (attempt + 1), int(response.headers.get('Retry-After', '0')) if response.headers.get('Retry-After', '').isdigit() else 0))
                sleep(delay)
                continue
            response.raise_for_status()
            payload = response.json()
            payload = payload if isinstance(payload, list) else [payload]
            if len(payload) != len(locations):
                raise ValueError('Provider returned incomplete multi-location batch')
            return payload, utc_now()
        except requests.RequestException:
            if attempt == 3:
                raise RuntimeError('Open-Meteo request failed; details suppressed to protect credentials') from None
            sleep(2 ** (attempt + 1))
    raise RuntimeError('Provider unavailable')
